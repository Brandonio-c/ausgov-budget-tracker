# MFS Note 3 duplicate-fact candidate investigation

Generated: 2026-08-13T18:00:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Loading `federal_mfs_note3_function` (item 7.1, second of five MFS sibling workbooks)
onto a disposable copy of `data/facts.db` produced 43 `unresolved_duplicate_facts` hard
failures from `scripts/ops/task9_sql_integrity_checks.py`, all newly introduced by this
load (the unmodified live database has 0 hard failures). Each was individually
categorized before any registry entry was written.

## Root cause: the same class of false positive already documented for mfs_aggregates

`task9_sql_integrity_checks.py`'s `duplicate_facts()` groups by
`(node_id, source_key, financial_year, measure_type, estimate_status, amount_aud)` -
it does not include `reporting_month`. Every MFS fact for one `measure_type` shares a
single node (one node per measure, not per month), so if a measure's YTD figure is
genuinely flat across two or more consecutive reporting months within the same year, the
SQL grouping cannot distinguish that from a true duplicate insert. This exact pattern was
already found and documented for two `mfs_ytd_net_capital_investment` groups during the
MFS Aggregates milestone (see
`ops/reports/mfs-duplicate-fact-investigation-20260805T003818Z.md` and
`config/audit/reviewed_duplicate_facts.yaml`'s existing `federal_mfs_aggregates` entries).

## Breakdown of the 43 groups

| measure_type | groups | why it repeats |
| --- | --- | --- |
| `mfs_note3_contingency_reserve` | 21 (one per year, FY2005-06..FY2025-26) | Genuinely flat for the entire year in most years (a reserve that is never drawn down produces identical $0 across all 11 reporting months) |
| `mfs_note3_natural_disaster_relief` | 20 | A lumpy, irregular flow - revised in occasional steps, flat between revisions |
| `mfs_note3_nominal_superannuation_interest` | 2 (both FY2006-07) | Recognised in occasional accrual steps, not smoothly monthly |

## Evidence, verified directly against the raw workbook (not database metadata alone)

**Contingency reserve, FY2005-06** (all 11 reporting months): `0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0` - genuinely flat at zero for the entire year.

**Natural disaster relief, FY2011-12** (July..May): `3.651, 9.559, 9.823, 0.371, 0.371,
2.765, 2.765, 1902.765, 1902.765, 1902.765, 3.076` ($m) - flat at 0.371 for 2 months
(matches a flagged group of count=2), flat at 2.765 for 2 months (count=2), flat at
1902.765 for 3 months (count=3), then a sharp downward revision to 3.076 by May. Every one
of these three flagged sub-groups for this year matches the raw sequence exactly.

**Natural disaster relief, FY2015-16**: `-0.001, -0.001, -0.001, 0, 0, 0, 0, 0, 0, 0, 0`
($m) - a small negative YTD adjustment, flat for 3 months (matches the flagged
`amount_aud: -1000, count: 3` group), then flat at 0 for the remaining 8 months (matches
`amount_aud: 0, count: 8`).

**Nominal superannuation interest, FY2006-07**: `0, 0, 0, 0, 831.593, 1015.857, 1198.75,
1198.75, 2071.5, 2301.667, 5387.558` ($m) - flat at 0 for the first 4 months (matches the
flagged `count: 4` group) and flat at 1198.75 for 2 months (matches `count: 2`).

Every one of the 43 flagged groups matches this same pattern: a genuinely flat cumulative
YTD figure across consecutive months, correctly extracted and correctly loaded, not an
accidental duplicate insert.

## Disposition

All 43 groups classified `query_false_positive` and added to
`config/audit/reviewed_duplicate_facts.yaml` (exact-match on every field - a changed
year, amount, or measure_type falls through to a hard failure again, so this can never
silently widen to cover an unreviewed group). `task9_sql_integrity_checks.py --db
<disposable copy>` confirmed 0 hard failures after the registry update, with all 43 now
appearing as `reviewed_duplicate_facts` instead.

## Not investigated as a duplicate risk (out of scope for this check)

`mfs_note3_total_expenses` and the 13 primary COFOG function measures showed zero
duplicate candidates - their YTD figures change every month in the real corpus, so this
false-positive pattern does not arise for them.
