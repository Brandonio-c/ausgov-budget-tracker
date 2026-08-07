# Cloudflare browser-navigation 404 diagnosis

Timestamp: `2026-08-07T19:19:04Z`  
Branch / starting revision: `main` / `3f6ecf6` (matched `origin/main`)  
Production Worker: `ausgov-budget-tracker-frontend-vibefactory`  
Fix deployment: `a69f37b2-b7c8-4ffb-be7e-d029a355ed1d`

## Result

The defect was caused by Cloudflare Workers Static Assets navigation routing, not by the Next.js export, browser state, or a stale 404 alone.

`wrangler.vibefactory.toml` has compatibility date `2026-07-20`, so Cloudflare's `assets_navigation_prefers_asset_serving` behavior is active. A top-level request carrying `Sec-Fetch-Mode: navigate` was sent to Static Assets before the Worker. Static Assets therefore looked up the incoming, host-prefixed path such as `out/ausgov-budget-tracker/explorers/gfs/`. That path does not exist: the export root is already `out/`, with the page at `out/explorers/gfs/index.html`. The lookup fell through to `not_found_handling = "404-page"` and returned the exported Next.js `out/404.html` with status 404.

A plain curl request does not carry the navigation header. After the direct asset lookup missed, it reached `asset-worker.js`, which correctly stripped `/ausgov-budget-tracker`, fetched `/explorers/gfs/` from the binding, and returned the real page. This is why plain curl was never proof that browser navigation worked.

Cloudflare documents this navigation preference for Static Assets deployments with `not_found_handling` and compatibility dates on or after `2025-04-01`. It also documents `assets.run_worker_first` as the explicit way to execute Worker code before asset-serving behavior: [Static site generation and custom 404 pages](https://developers.cloudflare.com/workers/static-assets/routing/static-site-generation/), [compatibility flags](https://developers.cloudflare.com/workers/configuration/compatibility-flags/), and [Static Assets binding](https://developers.cloudflare.com/workers/static-assets/binding/).

## Reproduction before the fix

The five required URLs were tested with plain curl, browser-like curl, and real headless Chromium navigation:

| URL under `https://vibefactory.app` | Plain curl | Browser-like curl | Playwright |
| --- | ---: | ---: | ---: |
| `/ausgov-budget-tracker/` | 200 | 404 | 404 |
| `/ausgov-budget-tracker/explorers/gfs/` | 200 | 404 | 404 |
| `/ausgov-budget-tracker/explorers/mfs/` | 200 | 404 | 404 |
| `/ausgov-budget-tracker/combined/` | 200 | 404 | 404 |
| `/ausgov-budget-tracker/timeline/` | 200 | 404 | 404 |

All five browser-like response bodies were byte-for-byte identical (SHA-256 `3fe2f5bb4fa09ca78818205b810d3495c4f8615b5bde166cb82d116931807537`) and were 10,048 bytes after Cloudflare Web Analytics injection.

Representative plain response:

```http
HTTP/2 200
content-type: text/html
cf-cache-status: HIT
cache-control: no-store
server: cloudflare
```

Representative browser-navigation response:

```http
HTTP/2 404
content-type: text/html
cf-cache-status: HIT
cache-control: public, max-age=0, must-revalidate
server-timing: cfCacheStatus;desc="HIT"
server-timing: cfEdge;dur=19,cfOrigin;dur=0
server: cloudflare
```

The 404 was cached by the Static Assets layer (`cf-cache-status: HIT`) and was served without an origin request (`cfOrigin;dur=0`). It was not Cloudflare-branded: its body contained Next.js' `404: This page could not be found.`, an `<h1>404</h1>`, and `_not-found` RSC markers. It was the app's exported `404.html`.

## Discriminator and Worker reachability

A cache-busted request with no special header returned 200. Adding only this header returned 404:

```http
Sec-Fetch-Mode: navigate
```

Changing that value to `cors` returned 200 again. Desktop User-Agent, Accept, and the other `Sec-Fetch-*` headers were not required to trigger the problem. Repeating the local test under `wrangler dev` produced the exact same `plain=200`, `navigate=404`, `cors=200` split. Wrangler logged that the navigation request was using `not_found_handling` behavior.

The response headers also identify whether the Worker ran:

- Working plain responses had `cache-control: no-store`, which only `asset-worker.js` adds to HTML.
- Failing navigation responses retained the Assets binding default `public, max-age=0, must-revalidate`, so the prefix-rewriting Worker had not run.
- After the fix, a browser-navigation response included `cfWorker;dur=9`, returned 200, and carried `cache-control: no-store`.

This makes a browser/profile artifact impossible and proves the relevant Worker mapping code was bypassed rather than incorrect.

## Worker and export inspection

The three configuration layers are internally consistent once the Worker executes:

- `next.config.ts` uses `output: "export"`, `basePath: "/ausgov-budget-tracker"`, and `trailingSlash: true`.
- Live HTML references `/ausgov-budget-tracker/_next/static/...`; the corresponding files are present under `out/_next/static/...` (39 files during inspection).
- Required exported pages are present as `out/index.html`, `out/explorers/gfs/index.html`, `out/explorers/mfs/index.html`, `out/combined/index.html`, and `out/timeline/index.html`.
- There is intentionally no `out/ausgov-budget-tracker/...` directory. The host-level prefix is removed by `asset-worker.js`.
- `asset-worker.js` strips the prefix correctly, preserves the query, canonicalizes the bare prefix with a 308 redirect, and appends a trailing slash only for extensionless paths.
- `not_found_handling = "404-page"` is compatible after prefix rewriting: exported routes resolve to their own HTML, while a genuinely absent route still resolves to `404.html` with status 404. Cloudflare's default auto-trailing-slash HTML handling is also compatible with this output shape: [HTML handling](https://developers.cloudflare.com/workers/static-assets/routing/advanced/html-handling/).

The local export sizes also matched the pre-fix live successful curl bodies for the required pages (for example, GFS 9,634 bytes, MFS 14,822 bytes, combined/timeline 10,094 bytes). The build itself was not the defect.

## Cloudflare route, Pages, rules, and cache checks

Read-only account inspection established:

- The active Worker routes are exactly `vibefactory.app/ausgov-budget-tracker` and `vibefactory.app/ausgov-budget-tracker/*`, both bound to `ausgov-budget-tracker-frontend-vibefactory`.
- A broader `vibefactory.app/*` route also exists, but Cloudflare's returned route inventory confirms the two more-specific routes. The intended Worker received ordinary requests and received all navigation requests after `run_worker_first`, so route shadowing was not the cause.
- The account has three Pages projects, none using `vibefactory.app` or this path. Pages shadowing was ruled out.
- The available Wrangler OAuth credentials could read the zone and Worker routes but were denied access to Development Mode, Page Rules, and the Redirect/Transform/Cache Rules entry points. Those settings were therefore not mutated or claimed to have been fully inventoried.

No live evidence points to a redirect, transform, custom cache key, or Page Rule as the cause. The failure reproduced in local Wrangler without zone rules, was controlled solely by `Sec-Fetch-Mode: navigate`, and exactly matches Cloudflare's documented Static Assets navigation behavior. A previous full cache purge did not fix it because the same direct asset lookup simply regenerated the same cached `404.html`. Development Mode was not toggled because that would mutate the shared zone and the local reproduction had already proved the mechanism.

## Fix

The smallest safe repository change was one line in `src/frontend/wrangler.vibefactory.toml`:

```toml
[assets]
directory = "./out"
binding = "ASSETS"
run_worker_first = true
```

This expresses the actual deployment requirement: every request beneath the host prefix must pass through `asset-worker.js` so the prefix is removed before asset lookup. No application code, page code, data, or export layout changed.

## Validation

Before deployment:

- `npm run lint:ci`: passed; observed 25 errors and 13 warnings exactly matched the repository baseline.
- Raw `npm run lint`: failed with the same pre-existing 25 errors and 13 warnings; the TOML-only change introduced none.
- `npm run build:vibefactory`: passed; all 12 static pages generated.
- `wrangler deploy --dry-run`: passed; 140 asset files read.
- Local Wrangler matrix: both plain and navigation requests returned 200 on all five required routes; a fabricated route returned 404 in both modes; the bare-prefix 308 redirect remained correct.

Production deployment completed at `2026-08-07T19:15:56Z` as version `a69f37b2-b7c8-4ffb-be7e-d029a355ed1d`, assigned 100% of traffic. The first seconds after deployment showed mixed old/new edge behavior while the new asset-routing configuration propagated. Once converged:

- 10 navigation requests per required route: 50/50 returned 200.
- Three independent fresh Playwright contexts per required route: 15/15 returned 200 with the expected page heading.
- Representative fixed browser response:

```http
HTTP/2 200
content-type: text/html
cf-cache-status: HIT
cache-control: no-store
server-timing: cfCacheStatus;desc="HIT"
server-timing: cfEdge;dur=14,cfOrigin;dur=0,cfWorker;dur=9
server: cloudflare
```

The browser-navigation defect is resolved in production. No further remediation is required. If it recurs, the first check should be whether a deployment removed `assets.run_worker_first`; cache purging alone is not a fix for this mechanism.

## Principal commands

```text
curl (plain, isolated Sec-Fetch-Mode values, and full browser-navigation headers)
node --input-type=module ... Playwright chromium page.goto(...)
npx wrangler dev --config wrangler.vibefactory.toml --local --port 8788
npx wrangler whoami
npx wrangler deployments list/status --config wrangler.vibefactory.toml
npx wrangler versions view a69f37b2-b7c8-4ffb-be7e-d029a355ed1d --config wrangler.vibefactory.toml
npx wrangler pages project list
Cloudflare API GETs for zones, Worker routes, zone settings, Page Rules, and ruleset entry points
npm run lint
npm run lint:ci
npm run build:vibefactory
npx wrangler deploy --config wrangler.vibefactory.toml --dry-run
npx wrangler deploy --config wrangler.vibefactory.toml
find / rg / sed / sha256sum / git status / git diff
```
