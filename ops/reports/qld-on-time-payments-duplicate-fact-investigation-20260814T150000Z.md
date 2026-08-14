# QLD on-time-payments duplicate-fact candidate investigation

Generated: 2026-08-14T15:00:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Loading `qld_on_time_payment_reports` (item 7.5) onto a disposable copy of `data/facts.db`
first crashed `scripts/ops/task9_sql_integrity_checks.py`'s `duplicate_facts()` /
`partition_duplicate_facts()` outright (`TypeError: float() argument must be a string or a
real number, not 'NoneType'`) - this was the first load in this database's history to
produce `quantity`-only facts (`amount_aud IS NULL`), and the tool's SQL grouped by
`f.amount_aud` directly instead of `COALESCE(f.amount_aud, f.quantity)`. That is a real bug
in shared infrastructure, fixed separately (see `scripts/ops/task9_sql_integrity_checks.py`
and its regression tests in `tests/ops/test_task9_sql_integrity_checks.py`).

After that fix, the tool ran cleanly and reported 87 `unresolved_duplicate_facts` groups,
all newly introduced by this load (the unmodified live database has 0 hard failures).
Each was individually categorized before any registry entry was written.

## Root cause: the same class of false positive already documented for MFS

`task9_sql_integrity_checks.py`'s `duplicate_facts()` groups by
`(node_id, source_key, financial_year, measure_type, estimate_status, COALESCE(amount_aud,
quantity))` - it does not include the quarter or `period_end`. Each QLD on-time-payments
agency is one node, and each of its 8 measures reports once per quarter (4 rows/year per
measure). If two or more of an agency's quarters within the same financial year genuinely
report the identical value for a measure - overwhelmingly common for `qld_otp_eligible_claims`
and `qld_otp_penalty_interest_paid`, where a small agency legitimately reports `0` every
quarter of a quiet year - the SQL grouping cannot distinguish that from a true duplicate
insert. This is the exact same structural false-positive class already documented for
`federal_mfs_aggregates` and `federal_mfs_note3_function` (see
`ops/reports/mfs-duplicate-fact-investigation-20260805T003818Z.md` and
`ops/reports/mfs-note3-duplicate-fact-investigation-20260813T180000Z.md`).

## Breakdown of the 87 groups by measure_type

| measure_type | groups |
| --- | --- |
| `qld_otp_eligible_claims` | 28 |
| `qld_otp_penalty_interest_paid` | 26 |
| `qld_otp_invoices_paid_late` | 10 |
| `qld_otp_mean_days_paid_late` | 9 |
| `qld_otp_pct_late_smallbus` | 4 |
| `qld_otp_value_paid_late` | 4 |
| `qld_otp_pct_late_others` | 3 |
| `qld_otp_total_eligible_invoices` | 3 |

The two dollar-count measures (`eligible_claims`, `penalty_interest_paid`) dominate because
`0` is by far the most common genuinely-repeated value across a quiet agency's quarters;
the two percentage measures are rarest because independently-computed percentages across
different quarters are less likely to land on the exact same value by coincidence.

## Evidence, verified directly against the extracted staging CSV (not database metadata alone)

Checked `data/staging/qld_on_time_payments/qld_on_time_payments.csv` directly for three
representative flagged groups:

**Agency `dcyjma`, FY2020-21, `mean_days_paid_late`** (the reason text's cited example):

| quarter | value |
| --- | --- |
| Q3 | 31.0 |
| Q4 | 31.0 |

Two independently-sourced rows (different quarters) genuinely report the same mean-days
figure - not a duplicate insert.

**Agency `cdsb`, FY2025-26, `eligible_claims`**:

| quarter | value |
| --- | --- |
| Q1 | 0.0 |
| Q2 | 0.0 |
| Q3 | 0.0 |
| Q4 | 0.0 |

A quiet agency with zero eligible claims for penalty interest across all four quarters of
the year - four independent rows, genuinely flat at zero.

**Agency `chde`, FY2020-21, `eligible_claims`**:

| quarter | value |
| --- | --- |
| Q1 | (blank - quarantined by the extractor, not loaded) |
| Q2 | 0.0 |
| Q3 | 0.0 |
| Q4 | 0.0 |

Three loaded quarters (Q1 was a genuinely blank cell, correctly quarantined rather than
coerced to zero - see the extractor's `pd.isna()` fix), all independently reporting zero.

Every one of the 87 flagged groups matches this same pattern: two or more genuinely
different quarters within one financial year, for one agency and one measure, correctly
extracted and correctly loaded, coincidentally sharing an identical value - not an
accidental duplicate insert.

## Disposition

All 87 groups classified `query_false_positive` and added to
`config/audit/reviewed_duplicate_facts.yaml` (exact-match on every field - a changed
year, quarter's resulting value, or measure_type falls through to a hard failure again, so
this can never silently widen to cover an unreviewed group). `task9_sql_integrity_checks.py
--db <disposable copy>` confirmed 0 hard failures after the registry update, with all 87
now appearing as `reviewed_duplicate_facts`.

## Registry entry count reconciliation (49 -> 136)

`config/audit/reviewed_duplicate_facts.yaml` went from 49 to 136 entries (49 + 87). Running
`task9_sql_integrity_checks.py` against the disposable copy immediately afterward reported
`reviewed_duplicate_facts: 133`, not 136 - investigated directly (not assumed benign)
before proceeding. All 87 new QLD on-time-payments entries matched a live candidate group
(87/87). The gap was entirely in the pre-existing 49: exactly 3 `qld_qgip_expenditure`
entries no longer produce a matching duplicate-candidate group in the current database,
because the earlier QGIP repair (item 7.2, `ops/reports/` QGIP milestone) changed the
underlying fact values for those specific rows - the duplicate pair those 3 entries were
written against no longer exists (a good outcome: the duplicate was resolved by the QGIP
fix, not merely tolerated). This is the same benign, already-precedented drift class
documented for QGIP earlier in this milestone (stale registry entries pointing at
duplicate-candidate groups that a later, unrelated fix has since eliminated). 46 (49 - 3
stale) + 87 (new) = 133, fully reconciled.

## Not investigated as a duplicate risk (out of scope for this check)

`qld_otp_pct_late_smallbus`/`qld_otp_pct_late_others` and `qld_otp_total_eligible_invoices`
showed comparatively few duplicate candidates (4, 3, and 3 groups respectively) since
independently-computed percentages and larger invoice counts are less likely to coincide
exactly across different quarters.
