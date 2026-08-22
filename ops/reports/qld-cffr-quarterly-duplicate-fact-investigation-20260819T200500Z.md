# QLD CFFR quarterly duplicate-fact investigation (item 7.4, quarterly slice)

Generated: 2026-08-19T200500Z
Repository: `ausgov-budget-tracker`, branch `main`

## Finding

`task9_sql_integrity_checks.py`'s `duplicate_facts()` flagged 8 candidate groups, all under
node `"QLD CFFR Quarterly: Consolidated Fund balance as at 1 July"`
(`qld_cffr_quarterly_ytd_opening_balance`), one per financial year FY2017-18 through
FY2024-25, each with `count: 3`.

## Investigation

Verified directly against the extracted staging data
(`data/staging/breakdowns/qld_cffr_quarterly_ytd.csv`): for each flagged financial year, all
3 of that year's own loaded quarterly editions (September/December/March) report the
identical "Balance as at 1 July" figure - which is genuinely correct, not a duplicate. This
measure is, by its own definition, a restatement of the *same* point-in-time balance (the
financial year's own start-of-year figure) as it appears at the top of every quarter's own
Statement of Receipts and Payments - it does not change from quarter to quarter within one
financial year, only between financial years.

`duplicate_facts()` groups by `(node, financial_year, measure_type, estimate_status,
amount_aud)` and does not include the quarter (or `period_end`) in its grouping key, so it
cannot distinguish 3 genuinely different quarterly editions restating the same real-world
figure from a true duplicate - the same class of false positive already documented
extensively this session for monthly-reporting sources (`federal_mfs_aggregates`,
`federal_mfs_note3_function`, `federal_mfs_tax_notes_1_2`, `federal_mfs_balance_sheet`,
`qld_on_time_payment_reports`).

Each of the 8 flagged groups' 3 underlying `fact_id`s were individually confirmed to have
distinct `fact_key`s (differing in their `Q{quarter}` component) - genuinely 3 separate,
independently-sourced facts, not 3 rows accidentally created from the same source row.

## Disposition

All 8 candidate groups classified `query_false_positive` and added to
`config/audit/reviewed_duplicate_facts.yaml`.
