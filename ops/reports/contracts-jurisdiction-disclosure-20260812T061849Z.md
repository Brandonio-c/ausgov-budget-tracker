# Contracts explorer jurisdiction-mix disclosure and a source_breakdown facet for /v2/tree

Generated: 2026-08-12T06:18:49Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Discovered while scoping plan item 6.1 (reusable explorer API/registry, plan section
6.1's required capability "facets for year, jurisdiction, source edition, measure, basis
and status"). Not itself a numbered plan item, but a truthfulness defect directly in the
critical path of that work, fixed immediately per this program's standing rule not to
defer findings that fit current scope.

## Previous behavior

The `commitment / commitment / contract` compatibility triple used by the contracts
explorer (item 6.3, `9b3e675`) is shared by four independent sources:
`federal_austender_contracts`, `nsw_procurement_ocds_registry`,
`nt_awarded_government_contracts`, and `qld_contract_disclosure_agency_datasets`. For the
explorer's default year (2024-25), the scope is **100% NSW/NT/QLD state contract
disclosure data - zero federal AusTender contracts**:

```
nsw_procurement_ocds_registry:            5,004
qld_contract_disclosure_agency_datasets:  3,502
nt_awarded_government_contracts:            530
                                    total: 9,036  (matches the page's reported total exactly)
```

The page was titled plainly "Contracts explorer" with no disclosure of this jurisdiction
mix, unlike every sibling family page (PBS, grants, VIC output performance, ACT invoices),
which is single-source or explicitly `source_key`-scoped. A reader would reasonably read
"9,036 contracts for 2024-25" as federal AusTender data, matching the plan's own per-bullet
family naming convention - it is not. This is not a cross-group summation error (the
`commitment` compatibility group correctly certifies these sources as additive/comparable),
but it is a provenance-hiding defect: exactly the "semantic mismatch hidden behind
visualization" pattern this program's non-negotiable rules forbid, just at the
jurisdiction-attribution level rather than the accounting-basis level.

## Changes

- `src/backend/routers/v2/query.py`: `/v2/tree` now returns `source_breakdown`, a
  `GROUP BY source_documents.source_key` list of `{source_key, count, value}` over the
  full scope (independent of page `limit`, same truthful-totals discipline as
  `total_count`/`total_value`). Present on every response, including single-source scopes
  (a length-1 array).
- `tests/api/test_v2_tree_pagination.py`: two new tests -
  `test_source_breakdown_reveals_a_multi_jurisdiction_scope` (proves the breakdown for the
  real 2024-25 contracts scope matches a direct SQL `GROUP BY` exactly and sums to the
  reported totals) and `test_source_breakdown_is_single_entry_for_an_already_single_source_scope`.
- `src/frontend/lib/api.ts`: `V2Tree` type gains `source_breakdown`.
- `src/frontend/app/explorers/contracts/page.tsx`: renders the breakdown beneath the
  summary line with readable jurisdiction labels, and the header copy now states plainly
  that the scope combines federal AusTender with three state contract-disclosure
  registers and is not federal-only.

## Validation

- `npx tsc --noEmit`, `npm run lint:ci` (unchanged baseline), `npm run build` (14 static
  routes, unchanged - no new route): all passed.
- Live browser verification via Playwright: summary unchanged ("9,036 contracts for
  2024-25, total value $39,337,071,294 — 200 loaded"), new breakdown line visible with all
  three real jurisdiction labels present, disclosure sentence present in the page body,
  zero console errors.
- Full backend suite, run in the project's dedicated conda environment: 648 passed
  (up from 646; the two new tests), 0 regressions.

## Data impact

None. No database write; `source_breakdown` is a new, always-present, additive response
field - no existing consumer reads a fixed key set from `/v2/tree`'s top level, so this is
backward compatible.

## Dashboard impact

Once deployed, the contracts explorer discloses its real jurisdiction mix instead of
presenting an unqualified national-sounding total. No other live family page's reported
total changes (PBS, grants, VIC output performance and ACT invoices are already
single-source, confirmed by direct SQL before this change).

## Remaining risks

Splitting "Contracts explorer" into genuinely separate federal/NSW/NT/QLD family pages
(rather than one page with a disclosed breakdown) remains a legitimate scope boundary for
item 6.1/6.3, matching the plan's stated migration order and exit gate, which only require
contracts to be "reachable... with truthful pagination and totals" - now satisfied,
including truthful provenance. The production deployment lag continues to apply.

## Next item

Item 6.1's fuller reusable explorer API/registry (family registry config, `/v2/explorers`
endpoints, generic frontend shell) remains open; this milestone builds one of its required
facet capabilities (source/jurisdiction breakdown) and used it to fix a live defect
immediately rather than deferring the finding.
