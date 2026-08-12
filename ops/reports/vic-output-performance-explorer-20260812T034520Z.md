# VIC Output Performance explorer surfacing (Wave 4, item 6.3)

Generated: 2026-08-12T03:45:20Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.3: "VIC output performance — immediate surfacing of the seven already-
loaded output nodes."

## Previous behavior

`ops/reports/vic-output-performance-implementation-20260807T173750Z.md` recorded 14 facts
(7 output nodes x actual/budget) loaded and live since 2026-08-07, reachable via the
generic compatibility-guarded `/v2/tree` endpoint, but with **no frontend page at all** -
confirmed by a repository-wide search finding zero frontend references to this family
before this change. The data existed but was unreachable by any user.

## Changes

- Added `src/frontend/app/explorers/vic-output-performance/page.tsx`: a small,
  self-contained page (no backend change - reuses the same `/v2/tree` endpoint the
  contracts fix uses) that fetches both `estimate_status=actual` and
  `estimate_status=budget` for `compatibility_group=vic_output_total_cost`,
  `financial_year=2024-25` (the only loaded year) and merges them by output name into a
  table: Output | Actual | Target | Variance, with a citation panel per row.
- Registered the page in `src/frontend/app/explorers/page.tsx`'s index.
- The page text explicitly states this is a specialist performance-measurement product,
  never additive to or part of the whole-of-government tree, and that only the seven
  dollar-denominated rows are shown - the other 70 count/date/percentage/ratio KPI rows
  from the same source workbook remain deliberately unpublished, per the plan's
  non-negotiable rule against collapsing specialist products into the canonical tree.

## Validation

- `npx tsc --noEmit`: passed.
- `npm run lint:ci`: passed at the existing accepted baseline (25 errors / 13 warnings,
  unchanged).
- `npm run build`: passed, 13 static routes (was 12).
- `npm run test:unit`: passed.
- **Live browser verification** (Playwright against `next dev` + a local `uvicorn` backend
  bound to the real `data/facts.db`): all 7 output rows rendered; the first row read
  "Budget and Financial Advice $46,300,000 $39,000,000 $7,300,000" - exactly matching the
  live database's actual/budget/variance for that output; clicking a row populated the
  citation panel with the full workbook/sheet/cell locator
  (`workbook:Output-performance-measures-2024-25.xlsx | sheet:Budget and Financial
  Advice | cell:C25 | row:Total output cost | fy:2024-25 | estimate_status:actual`); zero
  console errors.

## Data impact

None. No backend, database, or API contract change.

## Dashboard impact

Once deployed (see the production-deployment-lag finding recorded elsewhere in this
ledger), all seven Victorian departmental outputs' 2024-25 actual-vs-target total cost
become reachable and citable for the first time, clearly separated from the annual
additive tree.

## Remaining risks

The 70 non-dollar KPI rows (counts, dates, percentages, ratios) from the same acquired
workbook remain out of scope, matching the original implementation's deliberate deferral -
not attempted here, and not silently coerced into a dollar figure. This page only shows
FY2024-25 since that is the only year with loaded facts for this family; a year selector
was deliberately not added since it would either be dead UI or invite a future-year
fallback, both of which the plan's non-negotiable rules forbid.
