# Adapter repair batch 1 — Federal MFS Aggregates — 20260731T202800Z

Task 5, first batch: highest-ranked family from the Task 4 queue that isn't
already served by an existing adapter (Federal Monthly Financial Statements,
`commonwealth_mfs` category, 6 sources).

## What was done

- Inspected all 6 MFS xlsx files (`federal_mfs_aggregates`,
  `federal_mfs_monthly_profiles`, `federal_mfs_note3_function`,
  `federal_mfs_balance_sheet`, `federal_mfs_operating_statement`,
  `federal_mfs_tax_notes_1_2`). They split into two real shapes:
  - **Flat summary** (`aggregates`): one row per named top-line aggregate
    (Revenue, Expenses, Total assets, Net debt, ...), no parent/child
    structure. Structurally simple, safe to extract without a hierarchy
    model.
  - **Hierarchical statements** (`balance_sheet`, `operating_statement`,
    and likely `note3_function`, `monthly_profiles`): real parent/child
    rows (e.g. Assets → Financial assets → Cash and deposits, Advances
    paid, ... → Total financial assets), spanning up to 21 fiscal-year
    sheets with at least two distinct historical layouts. Extracting these
    correctly requires the same kind of hierarchy-aware, additive-vs-total
    handling built for PBS program/component tables in Task 3 - not
    attempted in this batch.
- Built and tested `scripts/ingest/extractors/mfs_aggregates.py` for the
  flat-summary file only. Handles:
  - Per-column header parsing (`ACTUAL\n<FY>\n(YTD )?<Month>\n$m|$b`),
    correctly distinguishing `$m` (×1,000,000) from `$b` (×1,000,000,000) -
    the workbook changes units between eras (early 2000s sheets are `$m`,
    2024-25/2025-26 sheets are `$b`); getting this wrong by mistake would
    silently misstate every recent-year figure by 1000x.
  - Quarantining (not guessing) any column whose header doesn't match a
    recognised `(YTD )?<Month>` pattern - confirmed the earliest sheets
    (~2005-06) label August as a bare month with no "YTD" prefix, unlike
    every later year; since a bare month name could mean either a
    standalone or cumulative figure, it's quarantined rather than assumed.
  - Row labels are preserved verbatim (normalized, footnote markers like
    `(a)` stripped) rather than canonicalized across eras (e.g. "Assets" vs
    "Total assets", "Operating Result" vs "Net operating balance") -
    equating those without verifying they're the same GFS-basis definition
    across a ~20-year span would be a guess.
  - Complete citation locator (source_id, sheet, row label, exact column
    header text) and per-row cached_copy_path/file reference.
- Verified against the real file:
  `data/raw/federal/federal_mfs_aggregates/snapshots/20260724T190604Z/files/6.-aggregates.xlsx`
  → 3,354 rows extracted, 27 quarantined, spanning 26 fiscal-year sheets.
  Spot-checked 2024-25 YTD-July Revenue: extracted `53,294,782,000` AUD
  against the raw cell value `53.294782` under a `$b` column header - exact
  match.
- Added `tests/ingest/test_mfs_aggregates.py` (4 tests, all passing) using a
  synthetic two-sheet workbook covering: `$m`/`$b` scale conversion, the
  non-YTD quarantine behaviour, footnote-row/marker handling, and citation
  completeness.

## What was deliberately NOT done: the facts.db load

`facts.measure_type` is a foreign key into `measure_definitions`. Checking
that table found `gfs_revenue`, `gfs_expense`, `gfs_liability`, `net_debt`,
and an already-defined-but-unused `monthly_actuals` measure_type whose
`compatibility_group` (`actual_expense`) is the *same* group as
`gfs_expense` - i.e. a prior design already intended monthly-actuals data
to sit alongside full-year GFS actuals in the same comparable family,
distinguished by `period_granularity = 'year_to_date'` (a value the schema
already supports) rather than a separate incompatible group.

That's a reasonable design, but I have not read the frontend/dashboard
aggregation code in this session to confirm it actually respects
`period_granularity` when deciding what's summable - and this file mixes
cash-basis rows (Receipts, Payments, Underlying/Headline cash balance) with
accrual/GFS-basis rows (Revenue, Expenses, Total assets/liabilities, Net
worth, Net debt) in the same sheet, several of which (Net worth, Net
operating balance, Fiscal balance, Underlying/Headline cash balance) have
no existing matching `measure_type` at all and would need new
`measure_definitions` rows added with correctly-verified
additive/compatibility flags.

Given the risk of silently mis-classifying a partial-year YTD figure as
comparable to a full-year actual if the compatibility-group assumption
above turns out to be wrong, and given this needs frontend verification
this session hasn't done, **the load into facts.db is deferred** rather
than guessed. The extractor is real, tested, and produces a correct staging
CSV (`data/staging/breakdowns/mfs_aggregates.csv`) ready to load once that
measure-semantics decision is confirmed (recommended as part of Task 8's
dashboard audit, which will exercise the actual aggregation code).

## Remaining MFS files and other Task 4 families

Not attempted this batch: `federal_mfs_monthly_profiles`,
`federal_mfs_note3_function`, `federal_mfs_balance_sheet`,
`federal_mfs_operating_statement`, `federal_mfs_tax_notes_1_2` (all need
hierarchy-aware parsing), and the remaining ~174 non-PBS, non-MFS families
in `ops/reports/adapter-repair-plan-20260731T202041Z.csv`. Given the size of
the remaining directive (registry hardening, QLD acquisition prep,
dashboard/API audit, reconciliation, final handoff), further adapter
batches are left as ranked, ready-to-pick-up backlog rather than attempted
in degraded/rushed form.
