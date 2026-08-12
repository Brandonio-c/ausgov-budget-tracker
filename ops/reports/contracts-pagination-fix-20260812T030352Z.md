# Contracts explorer truthful pagination (Wave 4, item 6.3 first sub-item)

Generated: 2026-08-12T03:03:52Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.3, first migration: "Contracts — remove the 200-row truncation; agency/
category/supplier/notice depth only where present in source." Wave 4's exit gate
requires contracts be "reachable without forcing them into the annual additive tree;
pagination and totals are truthful."

## Previous behavior

`src/frontend/app/explorers/contracts/page.tsx` called the backend with a hardcoded
`limit: 200` and treated the single returned page as the complete contract list for the
selected year - no indication to the user that more existed, no way to see or reach them,
and the visible list silently stood in for "all contracts."

## Investigation

The backend already had exactly the capability needed: item 3.4's `GET /v2/tree`
(`src/backend/routers/v2/query.py`) already returns `total_count`, `total_value` (computed
over the full scope, independent of the page limit) and an opaque `next_cursor` for
continuation - built in an earlier milestone but never consumed by this page. No backend
change was required; this was a frontend-only fix, matching the plan's "smallest correct
step" principle rather than building the full Wave 4 explorer registry (item 6.1) before
fixing the one concretely-named defect.

Checking the real scale first (against the local dev backend, since the production API is
stale - see "Critical finding" below): FY2024-25 alone has **9,036 contracts totalling
$39,337,071,294** - the old page was silently hiding 8,836 of 9,036 contracts (97.8%) for
that year alone.

## Changes

- `src/frontend/app/explorers/contracts/page.tsx`: fetches the first page and displays the
  true `total_count`/`total_value` alongside how many rows are currently loaded (and how
  many match the client-side filter, when set) - never presents the loaded page as the
  complete set. Added a "Load next 200" button using `next_cursor` for incremental
  pagination, and an "All N contracts loaded" indicator once exhausted. State updates on a
  year switch happen atomically inside the fetch callback (not synchronously in the effect
  body, to satisfy this repo's `react-hooks/set-state-in-effect` lint rule without
  introducing a new baseline exception).

## Validation

- `npx tsc --noEmit`: passed.
- `npm run lint:ci`: passed at the existing accepted baseline (25 errors / 13 warnings,
  unchanged).
- `npm run build`: passed, 12 static routes generated.
- `npm run test:unit` (chart semantics): passed.
- **Live browser verification** (Playwright against `next dev` + a local `uvicorn` backend
  bound to the real `data/facts.db`, per this repository's UI-change testing requirement):
  loaded the page for FY2024-25, confirmed the rendered summary reads *"9,036 contracts for
  2024-25, total value $39,337,071,294 — 200 loaded"* with zero console errors; clicked
  "Load next 200" and confirmed it correctly appended to 400 loaded while the total stayed
  at 9,036; switched the year field to 2023-24 and confirmed the summary atomically updated
  to *"2,836 contracts for 2023-24, total value $25,994,214,805 — 200 loaded"* with no
  stale/mixed-year rows and no console errors.

## Data impact

None. No backend, database, or API contract change - purely a frontend consumer fix.

## Critical finding: the public production API has not been redeployed

While preparing to validate this fix, querying the **public production API**
(`https://ausgov-budget-api.vibefactory.app`) for the same request returned a response with
**no `total_count`/`total_value`/`next_cursor` fields at all** - i.e. the production backend
container is running a build from *before* item 3.4 (commit `dde1c08`, itself from earlier
in this remediation program), not the current `main`. Per this repository's own
architecture notes, the backend runs in a Docker container where `data/facts.db` and
`config/` are bind-mounted (so data/config fixes take effect immediately), but **Python
application code changes require an explicit container rebuild and redeploy** - something
that has evidently not happened since at least commit `dde1c08`.

This means every backend code change from this entire remediation program to date -
including this contracts fix, the item 5.4 historical PBS/Statement 6 crosswalk, the item
5.5 NDIA repair and classifier precision fix, and the underlying `/v2/tree` pagination
fix itself - is fully committed and tested on `main` but **not yet visible to real users**
on the public site. Deploying a production container is a live, user-facing, and
comparatively hard-to-reverse action affecting a shared system, so it was **not** performed
as part of this session; it requires an explicit, informed decision (and the deployment
mechanism/credentials) outside what this autonomous loop should do unilaterally. Recorded
in the progress ledger as a distinct, high-visibility open item.

## Remaining risks

- Deployment lag above is the most consequential open item - no amount of further plan
  work becomes visible to real users until it is addressed.
- This fix only fetches contract-level facts; the plan's fuller "agency/category/supplier/
  notice depth only where present in source" hierarchy is not attempted here - the current
  `/v2/tree` endpoint is flat by design (item 3.4). Building that hierarchy properly is
  part of the larger item 6.1 reusable explorer API, not this narrower truncation fix.
- The search filter remains client-side (matches only already-loaded rows); a true
  server-side search is part of the same larger item 6.1 scope.
