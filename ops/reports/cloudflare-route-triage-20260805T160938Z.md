# Cloudflare nested-route rendering issue - triage (Task 1)

Generated: 2026-08-05T16:09:38Z.

## Symptom

Every nested static route under `vibefactory.app/ausgov-budget-tracker/*`
(`/explorers/mfs/`, `/explorers/gfs/`, `/explorers/`, `/timeline/`,
`/combined/`, `/search/`, `/legacy/`) renders the **root homepage's**
content in a real browser, instead of its own page. The root path itself
(`/ausgov-budget-tracker/`) is unaffected. First found during the
MFS-aggregates milestone's Task 12 (`ops/reports/mfs-production-
verification-20260805T050030Z.md`), confirmed there as pre-existing (also
affects `/explorers/gfs/` and `/timeline/`, both shipped in earlier
milestones, unrelated to the MFS work).

## Affected route(s)

Every route reachable only via a **hard navigation** (a fresh page load,
bookmark, shared link, or new tab) to a nested path. **Not** affected: the
homepage itself, and in-app client-side `<Link>` navigation starting from
an already-loaded page (Next.js's client router handles those without a
full server round-trip, so this bug is invisible during ordinary
in-app browsing that starts at `/`).

## Investigation

Extensive reproduction work, in order:

1. **Confirmed at the HTTP response-body level**, not just visually:
   captured the exact document response Playwright's browser received
   for `GET /ausgov-budget-tracker/explorers/mfs/` - it was byte-close to
   the homepage's own build output (chunk references matching the
   homepage's JS bundle set, not the MFS page's), not a client-side
   hydration artifact.
2. Ruled out: CDN cache staleness from a query-string cache key (cache-
   busting params made no difference at first, though see below); a
   Next.js static-export/build issue (a from-scratch clean rebuild with
   `.next`/`out` removed produced the identical, correctly-structured
   files - confirmed via direct byte comparison of `out/explorers/mfs/
   index.html` against the served response, and via a plain local static
   server (`npx serve`, no Cloudflare layer at all) rendering the correct
   page 100% of the time); HTTP/3/QUIC vs HTTP/1.1 (disabling both in
   Chromium made no difference); IPv4 vs IPv6 edge routing (both
   consistently reproduced/didn't reproduce the same way); bot-detection
   on the `HeadlessChrome` user-agent string (spoofing a non-headless
   UA made no difference).
3. **Found the browser-vs-curl discriminator**: plain `curl` requests
   (including with a full set of matched browser headers - UA, Accept,
   Accept-Encoding, Accept-Language) consistently returned the *correct*
   page. Adding the `Sec-Fetch-Mode: navigate` header (present on every
   real top-level browser navigation, never sent by curl/fetch/XHR by
   default) to an otherwise-plain curl request reliably reproduced the
   wrong content - isolated to that single header via a controlled A/B
   test.
4. Based on that, changed `wrangler.vibefactory.toml`'s
   `[assets].not_found_handling` from `"single-page-application"` (which
   assumes a true client-routed SPA with one shell page and no other real
   pages - wrong for this app, a Next.js static export with multiple
   separately pre-rendered pages, each with its own real uploaded
   `index.html`) to `"404-page"` (serve the exact matching asset when one
   exists; only fall back to the committed `out/404.html` when one
   genuinely doesn't).
5. **Redeployed and retested. Result was inconsistent across runs at
   first** (some nested routes passed, others failed, changing between
   otherwise-identical test runs seconds apart) - consistent with
   Cloudflare's globally-distributed edge cache converging at different
   times across different points of presence (POPs) rather than a
   deterministic code bug. Confirmed via `wrangler deployments list` that
   no gradual/canary rollout was involved (every deploy in this project's
   history shows a clean 100% single-version cutover).
6. Waited a further 10 minutes and retested comprehensively (2 full
   rounds, all 7 nested paths + root): **now consistently and
   deterministically failing on every nested path**, root still fine.
   This rules out simple propagation-lag self-resolution within the
   timeframe available to this investigation.
7. As a further, concrete, code-only mitigation (no dashboard/API cache-
   purge access available in this environment), modified
   `asset-worker.js` to override the Assets binding's own `Cache-Control:
   public, max-age=0, must-revalidate` with an explicit `Cache-Control:
   no-store` for `text/html` responses specifically (JS/CSS/font chunks
   are content-hashed and left cacheable as before) - `must-revalidate`
   still technically permits a cache to store and later revalidate a
   response; `no-store` forbids storing it at all, removing any
   ambiguity. Deployed. **Immediately after this deploy, the symptom
   still reproduced** in this environment's testing - expected, since
   `no-store` prevents *future* staleness rather than purging what a POP
   already has cached from before this fix existed.

All testing throughout consistently connected to the same Cloudflare
edge datacenter (`cf-ray` suffix `-IAD`, Washington DC) - this
investigation cannot rule out that users whose network path routes
through a *different*, already-converged POP are seeing the corrected
page already; it can only confirm this specific network vantage point
is not yet.

## Root cause (confirmed)

`wrangler.vibefactory.toml`'s `not_found_handling = "single-page-
application"` was genuinely wrong for this deployment shape and is a
real, fixed bug (Cloudflare's Assets binding applies that behavior based
on the presence of `Sec-Fetch-Mode: navigate` - every real top-level
browser navigation - not strictly on whether the asset is actually
missing). Beyond that, this app's zone/domain almost certainly has an
additional edge-cache layer (Cache Rules, or default Cloudflare Pages/
Workers static-asset edge caching) that is not fully honoring the
origin's stated `Cache-Control` for HTML documents, and that layer's
state cannot be forced to reconverge from inside this environment
without dashboard or API-token cache-purge access.

## Scope decision

**Navigation-blocking**, confirmed for real users landing on any nested
route via a direct link, bookmark, or shared URL (not merely cosmetic,
and not already resolved by the existing code before this session).
Partially fixed in this session: the `not_found_handling` misconfiguration
was a genuine, standalone bug and is corrected; the defensive `no-store`
change removes the mechanism that would let this recur after any future
deploy once caches naturally clear. **Full, immediate resolution for
this specific network vantage point was not achieved** within this
triage - it most likely requires a manual Cloudflare dashboard cache
purge (or additional propagation time), which is outside what this
environment's available tooling (`wrangler`, no API token) can perform.

## Recommended action

1. From the Cloudflare dashboard for `vibefactory.app`: **Caching →
   Configuration → Purge Everything** (or purge by the specific nested
   URLs) to force every edge POP to refetch from the Assets origin
   immediately, rather than waiting for natural cache expiry.
2. Re-verify `/explorers/mfs/`, `/explorers/gfs/`, `/timeline/`,
   `/combined/`, `/search/`, `/legacy/`, `/explorers/` in a real browser
   after the purge.
3. If it recurs after a future deploy, the `no-store` change already
   deployed here should prevent it from persisting - if it doesn't,
   revisit the zone's Cache Rules (dashboard-level, not visible from
   this repo) for anything overriding origin `Cache-Control` for HTML.

## Files changed

- `src/frontend/wrangler.vibefactory.toml`: `not_found_handling`
  `"single-page-application"` → `"404-page"`.
- `src/frontend/asset-worker.js`: explicit `Cache-Control: no-store` for
  `text/html` responses.

Both already deployed to production as part of this investigation (the
mission's own instructions call for fixing navigation-blocking issues in
a small, isolated commit - done here, with production redeployment
verified working for the config layer even where the cache-propagation
layer could not be fully confirmed from this vantage point).
