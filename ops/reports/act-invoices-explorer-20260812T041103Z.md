# ACT notifiable invoices explorer (Wave 4, item 6.3)

Generated: 2026-08-12T04:11:03Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.3, fifth migration: "ACT invoices — agency -> supplier/invoice cash-outflow
product."

## Previous behavior

46,714 `act_notifiable_invoices` facts (`measure_type: invoice_paid`, `compatibility_group:
cash_outflow`, `accounting_basis: cash`, `estimate_status: invoice`, FY2005-06 through
2026-27) have been loaded and live, but no frontend page existed - confirmed by a
repository-wide search.

## Changes

- Added `src/frontend/app/explorers/act-invoices/page.tsx`, the same proven
  `/v2/tree`-backed pagination pattern used for contracts and grants (no backend change).
  Node labels are already published as `AGENCY / SUPPLIER-OR-DESCRIPTION`, giving the
  agency/supplier structure the plan asks for at the label level even though the current
  flat `/v2/tree` shape (item 3.4) does not yet expose a true drill-down hierarchy.
- Registered in `src/frontend/app/explorers/page.tsx`'s index.
- Page copy states these are cash-basis payments, a distinct measure from accrual expense,
  never additive to the ACT's accrual expenditure in the annual tree.
- Confirmed the `cash_outflow` compatibility group is also used by an unrelated source
  (`bp1_outlays_by_function_pre_fbo`) with a different `estimate_status`
  (`estimated_actual` vs `invoice`); the required `estimate_status=invoice` filter
  correctly scopes queries to ACT invoices only - verified directly against the database
  before writing the page, not assumed.

## Validation

- `npx tsc --noEmit`, `npm run lint:ci` (unchanged baseline), `npm run build` (15 static
  routes, was 14), `npm run test:unit`: all passed.
- Live browser verification via Playwright: truthful total ("4,742 invoices for 2024-25,
  total value $1,004,198,107 — 200 loaded"), working Load-more (400 loaded, total
  unchanged), correct citation (`csv:row:57716 | payment_date:12/07/2024 |
  contract:nan`), zero console errors.

## Data impact

None. No backend, database, or API contract change.

## Dashboard impact

Once deployed, all ACT notifiable invoices for any of the 13 loaded financial years
(2005-06 through 2026-27) become reachable and truthfully paginated.

## Remaining risks

A true agency -> supplier -> invoice drill-down hierarchy (rather than a single flattened
label) and server-side search remain part of the larger item 6.1 explorer API, matching
the scope boundary already recorded for contracts, grants and VIC output performance.
