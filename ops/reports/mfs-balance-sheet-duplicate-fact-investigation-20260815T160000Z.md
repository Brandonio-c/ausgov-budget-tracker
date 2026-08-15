# MFS Balance Sheet duplicate-fact candidate investigation

Generated: 2026-08-15T16:00:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Loading `federal_mfs_balance_sheet` (item 7.1, one of the five MFS sibling workbooks (Note 3, Operating Statement, Balance Sheet, Tax Notes 1-2, and Monthly Profiles - Monthly Profiles remains the one still outstanding)) onto
a disposable copy of `data/facts.db` produced 29 `unresolved_duplicate_facts` hard
failures from `scripts/ops/task9_sql_integrity_checks.py`, all newly introduced by this
load (the unmodified live database has 0 hard failures). Each was individually
categorized and directly verified against the extracted staging CSV before any registry
entry was written.

## Root cause: the same class of false positive already documented for every other MFS sibling and QLD on-time-payments - now confirmed for a stock measure too

`task9_sql_integrity_checks.py`'s `duplicate_facts()` groups by `(node_id, source_key,
financial_year, measure_type, estimate_status, COALESCE(amount_aud, quantity))` - it does
not include the reporting month/period_end. Balance Sheet is this database's first
**stock** (point-in-time balance) source to hit this false-positive class: unlike a flow
measure (where a flat YTD figure implies "nothing new happened this month"), a stock
measure being flat between two consecutive months means "the balance genuinely did not
change" - an entirely normal, expected real-world outcome, not a data-quality signal at
all. All 29 groups were individually verified directly against
`data/staging/breakdowns/mfs_balance_sheet.csv` (not database metadata alone) with a
small Python script comparing each flagged `(measure_type, financial_year, value)` triple
against every extracted row for that measure/year - every one matched cleanly, confirming
each group corresponds to real, independently-sourced rows for genuinely different
reporting months.

## Breakdown of the 29 groups by measure_type

| measure_type | groups |
| --- | --- |
| `mfs_balance_sheet_assets_held_for_sale` | 9 |
| `mfs_balance_sheet_equity_accounted_investments` | 8 |
| `mfs_balance_sheet_investment_property` | 7 |
| `mfs_balance_sheet_biological_assets` | 3 |
| `mfs_balance_sheet_deposits_held` | 2 |

## Representative evidence, verified directly against the extracted staging CSV

**`Assets held for sale`, FY2019-20** (full YTD sequence around the flagged pair):

| reporting date | value ($) |
| --- | --- |
| ... | ... |
| 2020-01-31 | 302,875,000 |
| 2020-02-29 | 260,857,000 |
| **2020-03-31** | **256,000,000** |
| **2020-04-30** | **256,000,000** |
| 2020-05-31 | 297,886,000 |

March and April 2020 genuinely report the identical balance - two independently-sourced
cells, no accidental duplicate insert.

**`Equity accounted investments`, FY2008-09**: nine consecutive months (2008-07-31
through 2009-03-31) all report exactly $222,314,000, then a second, larger group of two
months (2009-04-30, 2009-05-31) both report $223,100,000 - two genuinely distinct
flat-then-revised periods within the same year, both correctly loaded from independent
source cells.

Every one of the remaining 27 groups follows this identical pattern: two or more
independently-sourced monthly balance-sheet columns for the same measure genuinely
reporting the same figure, correctly extracted and correctly loaded, not an accidental
duplicate insert.

## Disposition

All 29 groups classified `query_false_positive` and added to
`config/audit/reviewed_duplicate_facts.yaml` (exact-match on every field - a changed
year, month's resulting value, or measure_type falls through to a hard failure again, so
this can never silently widen to cover an unreviewed group). `task9_sql_integrity_checks.py
--db <disposable copy>` confirmed 0 hard failures after the registry update (registry grew
138 -> 167; 164 reviewed matches reported, the 3-entry gap being the same
already-documented, benign stale `qld_qgip_expenditure` entries from an earlier milestone
- verified directly, not assumed, by diffing the matched-vs-registered key sets).

## Not investigated as a duplicate risk (out of scope for this check)

Every other loaded Balance Sheet measure (`mfs_balance_sheet_advances_paid`,
`mfs_balance_sheet_investments_loans_placements`, `mfs_balance_sheet_other_receivables`,
`mfs_balance_sheet_investments_other_public_sector_entities`,
`mfs_balance_sheet_investments_shares`, `mfs_balance_sheet_land`,
`mfs_balance_sheet_buildings`, `mfs_balance_sheet_plant_equipment_infrastructure`,
`mfs_balance_sheet_inventories`, `mfs_balance_sheet_intangibles`,
`mfs_balance_sheet_heritage_cultural_assets`, `mfs_balance_sheet_other_non_financial_assets`,
`mfs_balance_sheet_deposits_held` (only 2 of its groups flagged),
`mfs_balance_sheet_government_securities`, `mfs_balance_sheet_loans`,
`mfs_balance_sheet_other_borrowing`, `mfs_balance_sheet_superannuation_liability`,
`mfs_balance_sheet_other_employee_liabilities`, `mfs_balance_sheet_suppliers_payable`,
`mfs_balance_sheet_personal_benefits_payable`, `mfs_balance_sheet_subsidies_payable`,
`mfs_balance_sheet_grants_payable`, `mfs_balance_sheet_other_provisions_and_payables`,
`mfs_balance_sheet_other_payables`, `mfs_balance_sheet_provisions`, and all 4 subtotal/
net-position measures) showed zero duplicate candidates - their month-to-month balances
change every reporting period in the real corpus for this source, so this false-positive
pattern does not arise for them.
