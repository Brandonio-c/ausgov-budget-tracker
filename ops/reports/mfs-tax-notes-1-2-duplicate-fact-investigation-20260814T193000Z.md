# MFS Tax Notes 1-2 duplicate-fact candidate investigation

Generated: 2026-08-14T19:30:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Loading `federal_mfs_tax_notes_1_2` (item 7.1, fourth of five MFS sibling workbooks) onto
a disposable copy of `data/facts.db` produced 2 `unresolved_duplicate_facts` hard failures
from `scripts/ops/task9_sql_integrity_checks.py`, both newly introduced by this load (the
unmodified live database has 0 hard failures). Each was individually categorized before
any registry entry was written.

## Root cause: the same class of false positive already documented for MFS Note 3/Aggregates and QLD on-time-payments

`task9_sql_integrity_checks.py`'s `duplicate_facts()` groups by
`(node_id, source_key, financial_year, measure_type, estimate_status, COALESCE(amount_aud,
quantity))` - it does not include `reporting_month`/`period_end`. Every Tax Notes 1-2 fact
for one `measure_type` shares a single node (one node per measure, not per month), so if a
measure's YTD figure is genuinely flat across two or more consecutive reporting months
within the same year, the SQL grouping cannot distinguish that from a true duplicate
insert. This exact pattern was already found and documented for
`federal_mfs_aggregates`, `federal_mfs_note3_function`, and
`qld_on_time_payment_reports` (see
`ops/reports/mfs-duplicate-fact-investigation-20260805T003818Z.md`,
`ops/reports/mfs-note3-duplicate-fact-investigation-20260813T180000Z.md`, and
`ops/reports/qld-on-time-payments-duplicate-fact-investigation-20260814T150000Z.md`).

## The 2 groups

| measure_type | financial_year | value | months involved |
| --- | --- | --- | --- |
| `mfs_tax1_petroleum_resource_rent_tax` | 2006-07 | $1,202,243,000 | February, March |
| `mfs_tax2_carbon_pricing_mechanism` | 2012-13 | $0 | July, August, September |

## Evidence, verified directly against the extracted staging CSV (not database metadata alone)

**Petroleum resource rent tax, FY2006-07** (full 11-month YTD sequence):

| month | value ($) |
| --- | --- |
| July | -3,448,000 |
| August | 245,415,000 |
| September | 255,794,000 |
| October | 905,703,000 |
| November | 890,487,000 |
| December | 967,828,000 |
| January | 1,198,627,000 |
| **February** | **1,202,243,000** |
| **March** | **1,202,243,000** |
| April | 1,390,959,000 |
| May | 1,524,638,000 |

February and March genuinely report the identical cumulative figure - no PRRT activity
accrued between those two months, correctly extracted and correctly loaded from two
independent source cells, not an accidental duplicate insert.

**Carbon pricing mechanism, FY2012-13** (full 11-month YTD sequence):

| month | value ($) |
| --- | --- |
| **July** | **0** |
| **August** | **0** |
| **September** | **0** |
| October | 2,563,333,000 |
| November | 3,204,167,000 |
| December | 3,845,000,000 |
| January | 4,485,833,000 |
| February | 5,126,667,000 |
| March | 5,767,500,000 |
| April | 6,408,333,000 |
| May | 6,911,667,000 |

The carbon pricing mechanism commenced 1 July 2012; its first liability/revenue
recognition did not land until October, so July, August, and September all correctly
report $0 - three independent source cells, correctly loaded, not an accidental duplicate
insert.

## Disposition

Both groups classified `query_false_positive` and added to
`config/audit/reviewed_duplicate_facts.yaml` (exact-match on every field - a changed
year, month's resulting value, or measure_type falls through to a hard failure again, so
this can never silently widen to cover an unreviewed group). `task9_sql_integrity_checks.py
--db <disposable copy>` confirmed 0 hard failures after the registry update (135 reviewed:
133 pre-existing + 2 new, no gap this time - both new entries matched cleanly).

## Not investigated as a duplicate risk (out of scope for this check)

Every other loaded Tax Notes 1-2 measure (`mfs_tax1_gross_income_tax_withholding`,
`mfs_tax1_gross_other_individuals`, `mfs_tax1_less_refunds`,
`mfs_tax1_total_individuals_withholding_tax`, `mfs_tax1_company_tax`,
`mfs_tax1_superannuation_fund_taxes`, `mfs_tax1_fringe_benefits_tax`,
`mfs_tax1_total_income_other_sources`, `mfs_tax2_excise_duty`, `mfs_tax2_customs_duty`,
`mfs_tax2_goods_and_services_tax`, `mfs_tax2_wine_equalisation_tax`,
`mfs_tax2_luxury_car_tax`, `mfs_tax2_total_indirect_taxation_revenue`) showed zero
duplicate candidates - their YTD figures change every month in the real corpus for this
source, so this false-positive pattern does not arise for them.
