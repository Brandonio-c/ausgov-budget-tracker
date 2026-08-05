# Correction: MFS measure availability windows (found during Task 8)

Generated: 2026-08-05T00:59:27Z.

## What was found

While testing the new `/v2/mfs/years?measure_type=mfs_stock_net_debt`
endpoint (Task 8), the first year returned was `2007-08` - contradicting
Task 3's semantic model, which documented
`not_published_before_financial_year: "2010-11"` for `mfs_stock_net_debt`.

## Root cause: an off-by-one bug in Task 2's own manual investigation script, not the extractor or loader

Task 2's manual row-label dump used `range(1, df.shape[0] - 1)`, assuming
the sheet's last row is always the trailing footnote-explanation
paragraph. That assumption is **false** for three sheets (`2007-08`,
`2008-09`, `2009-10`) whose last row is the real `Net debt` data row with
**no** footnote paragraph after it - the range clipped it off, making
those three years look like they had no `Net debt` row at all.

**The extractor and loader were never affected** - both correctly
iterate the full row range (`extract_workbook()`'s `for row_idx in
range(2, df.shape[0])`, stopping only when it actually encounters a
footnote-starting row via `FOOTNOTE_ROW.match()`). Confirmed directly:
`data/facts.db` already has 209 correctly-loaded `mfs_stock_net_debt`
facts spanning FY2007-08 through FY2025-26 (19 years x 11 months, minus
quarantined columns) - the real data was always correct; only Task 2/3's
**written documentation** (and the informational
`not_published_before_financial_year` field consumed by nothing except
human readers) was wrong.

## Full re-verification (unclipped row dump, every sheet, every claim)

| measure | claimed window (before) | verified window (after, full dump) | changed? |
|---|---|---|---|
| `mfs_stock_net_debt` | FY2010-11 onward | **FY2007-08 onward** | yes - corrected |
| `mfs_stock_net_worth` (gap) | absent FY2005-06 | **present in all 26 years, no gap** | yes - corrected |
| `mfs_ytd_net_capital_investment` | FY2007-08 onward | FY2007-08 onward | no change |
| `mfs_ytd_receipts` / `mfs_ytd_payments` | FY2011-12 onward | FY2011-12 onward | no change |
| `mfs_ytd_net_future_fund_earnings` | FY2013-14..FY2019-20 only | FY2013-14..FY2019-20 only | no change |

Only the two measures whose true boundary/gap fell on a sheet with no
trailing footnote paragraph were affected - every other claim was
already correct (those sheets happened to have a footnote-paragraph row,
so the buggy clip only ever removed that harmless trailing text, not a
real data row).

## Fix

`config/measure-semantics/mfs.yaml`: `mfs_stock_net_debt`'s
`not_published_before_financial_year` corrected to `"2007-08"`
(`allowed_comparisons` note updated to match); `mfs_stock_net_worth`'s
`known_gap_financial_years: ["2005-06"]` removed entirely (replaced with
a comment recording that no gap exists, verified). Both fields are
purely documentary - confirmed via `grep` that neither
`scripts/ingest/load_mfs_aggregates.py` nor
`scripts/ops/mfs_staging_audit.py` reference either field anywhere, so
**no re-load and no data change was needed** - re-ran the loader in
`--dry-run` immediately after the fix to confirm: still 3,354/3,354
already-present, 0 to insert, byte-identical to before.

## Why this is being recorded as a new report, not a silent edit to Task 2/3's committed reports

Task 2's and Task 3's original reports (`ops/reports/mfs-corpus-
inventory-20260804T234455Z.md`,
`ops/reports/mfs-measure-semantics-20260804T235453Z.md`) reflect what was
believed true at the time they were written and committed - editing them
after the fact would erase an honest record of how this was found and
corrected. This report is the authoritative correction; the semantic
model YAML (the actual load-bearing artifact) is fixed directly.

## Lesson for Task 10's tests

Add a test asserting the loader/audit's measure-availability behavviour
is driven entirely by what the extractor actually finds in each sheet
(row presence), never by an assumed row-count/offset - i.e. a synthetic
fixture sheet with **no trailing footnote row** must still extract its
true last data row correctly. (`tests/ingest/test_mfs_aggregates.py`'s
existing fixtures already include a footnote-row case; Task 10 adds one
without a footnote row specifically to guard against this exact class of
bug recurring in the extractor itself, even though this particular
instance was in a one-off manual script, not the extractor.)
