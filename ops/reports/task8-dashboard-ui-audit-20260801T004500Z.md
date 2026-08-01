# Task 8 — dashboard/API audit and UI regression suite

## What was run, against what

Real backend (`uvicorn src.backend.main:app`) against the current
`data/facts.db` (321,950 facts, post-Task-3/5 reload). Real frontend
(`src/frontend`), built and served as its actual production artifact (static
export), not a mock.

## 1. API traversal audit (automated, not manual clicking)

`scripts/ops/dashboard_api_audit.py` drives the real `/v2/dashboard/*`
endpoints over 6 named paths matching the directive's required regression
list (Federal Actuals 2024-25, Federal Budget latest, QLD state actuals
2024-25, local government actuals, federal debt, federal GDP/ratios). For
every visited node it records path, fact-node id, amount, depth,
percent-of-parent, additive-children presence, and — for every leaf ≥$1M or
≥1% of its parent (excluding grant/contract/invoice/recipient/payment-award
branches, which are related navigation, not additive GFS decomposition) —
calls the `/evidence` endpoint to verify a source file or locator exists.

Report: `ops/reports/dashboard-api-audit-20260801T002712Z.{json,md}`.

**Result**: 21,609 total nodes visited across the 6 paths; 12,595 material
leaves checked for citation completeness; **zero citation failures** - every
checked leaf has either `has_source_file: true` or a non-empty `locator`.

## 2. Real, non-trivial bugs found and fixed while setting this up

Task 8 explicitly requires starting the real backend+frontend and running a
UI regression suite - this immediately surfaced two genuine, pre-existing
issues that had to be fixed before any UI test could run at all (not worked
around or hidden):

**a) CORS blocked all local/test traffic.** `src/backend/main.py` hardcoded
`allow_origins=["https://vibefactory.app"]`. Any local dev or CI frontend
origin was rejected outright - confirmed via a direct `page.evaluate(() =>
fetch(...))` in the browser: `TypeError: Failed to fetch`. Fixed by reading
an optional `CORS_EXTRA_ORIGINS` env var (comma-separated) and appending it
to the allow-list; the production default (`https://vibefactory.app` only)
is unchanged unless the env var is explicitly set. This is a minimal,
additive change - no test asserted the old hardcoded value.

**b) `next dev` does not hydrate this app.** The frontend is configured for
static export (`next.config.ts`: `output: "export"`, `basePath:
"/ausgov-budget-tracker"`) and deployed to Cloudflare Pages. Running `next
dev` serves the correct markup (SSR/RSC output looks identical - buttons,
chart containers, "Loading…" placeholders all present) but **client-side
JavaScript never hydrates**: confirmed by monkey-patching `window.fetch` to
log every call (zero calls, ever) and by clicking the "Budget" mode button
and observing zero DOM/class change. No console error, no page error, no
failed network request - the JS bundle loads fine, it simply never takes
over the page. This is a `next dev` + `output: "export"` interaction
specific to dev mode, not a production bug: running the actual `next build`
static export and serving it under a path matching `basePath` (i.e. exactly
how it ships to production) hydrates correctly - confirmed by the same
click test then correctly toggling the button's active class, and by real
`fetch()` calls to `/v2/dashboard/*` firing and populating the chart.
**Playwright must run against the built static export, not `next dev`** -
this is now documented directly in `playwright.config.ts` so it isn't
rediscovered.

## 3. Playwright UI regression suite

`src/frontend/tests-e2e/dashboard.spec.ts` (7 tests, run via `npm run
test:e2e`), against a `next build` static export served under
`/ausgov-budget-tracker/` with a real backend (`CORS_EXTRA_ORIGINS` set to
the local test origin):

- home page loads with mode/chart controls (Actuals/Budget/Debt buttons)
- Federal Actuals 2024-25 deep link renders a populated chart (no stuck
  "Loading…")
- Federal Budget mode switch updates the chart without an error banner
- QLD state actuals branch is reachable (level=state, year=2024-25 - QLD
  appears as a real child node, confirmed)
- local government branch is reachable (level=local)
- debt view is labelled "GFS liability stocks... not Budget Paper 'net
  debt'" - the named mixed-valuation safeguard from the directive; a
  regression that silently drops or rewords this disclaimer is exactly what
  this test catches
- GDP/ratios branch (`mode=ratios`) is reachable

All 7 pass. Setup requires (documented for repeatability):

```bash
# 1. Backend, with the local test origin allowed
CORS_EXTRA_ORIGINS="http://127.0.0.1:3313,http://localhost:3313" \
  conda run -n ausgov-budget-tracker uvicorn src.backend.main:app --host 127.0.0.1 --port 8000

# 2. Static export build, served under the real basePath
cd src/frontend && npm run build
mkdir -p /tmp/static-serve-root/ausgov-budget-tracker
cp -r out/* /tmp/static-serve-root/ausgov-budget-tracker/
npx serve -l 3313 /tmp/static-serve-root

# 3. Tests
cd src/frontend && npx playwright test
```

## Not attempted in this pass

The API audit's 6 paths are a curated, named set matching the directive's
required regression list, not an exhaustive mode × level × year ×
jurisdiction crawl (state alone has 184,526 facts under `actuals`). Broader
sweep coverage, and a Playwright suite covering citation-panel-open,
cached-file-opening, and ring-depth-control interaction specifically (as
opposed to just confirming the branch loads), are natural next increments
given more time.
