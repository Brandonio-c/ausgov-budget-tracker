# QLD Consolidated Fund Financial Report (CFFR) - scoping and first-slice build

Generated: 2026-08-15T16:35:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Item 7.4: QLD Consolidated Fund, ledgered as "not_started, 46 acquired PDFs; no product
model." Investigated before writing any code, per this program's standing discipline.

## Finding: the raw files are genuinely two document families, co-located under an unrelated already-loaded source

All 67 "consolidated fund"/"CFFR"-named files live under
`data/raw/state/qld_report_on_state_finances_actuals/` - the SAME raw-acquisition folder
as Queensland's annual "Report on State Finances" (already loaded, a different table with
GFS/UPF-basis fiscal aggregates - see `config/measure-semantics/qld_report_on_state_finances.yaml`).
Confirmed directly (`grep` for "CFFR"/"Consolidated Fund" across every extractor in this
repo) that no existing pipeline touches this content - `qld_report_on_state_finances.py`'s
own `EDITIONS` list is a hardcoded filename set that never includes any CFFR file. This is
a genuine, unadapted gap, matching the ledger's characterization.

The 67 files split into two genuinely different document series:

- **17 annual (Year Ended 30 June) editions**, FY2008-09..FY2024-25 - a complete,
  unbroken series, one per financial year.
- **~50 quarterly interim editions** (Sep/Dec/Mar snapshots within a year) - a partial-year
  vintage, not attempted this pass.

## Finding: the annual editions are exceptionally well-structured and stable

Every annual edition has an identical "Statement of Receipts and Payments for the Quarter
ended and Year ended 30 June" page, of which only the "Year Ended" table (the second of
the two on the page) is in scope - genuinely Gross Cash Basis (the source's own explicit
statement: "The Consolidated Fund Financial Report records transactions on the cash basis
of accounting, in contrast to Departmental reporting which is on the accrual basis").

**Independent, chained correctness proof**: every edition's own "Balance as at 1 July"
(Total column) was verified to exactly match the immediately prior edition's own
"Consolidated Fund Balance as at 30 June" (Total column) - across the full 16 links in the
17-year chain, with zero mismatches. This is a genuine data-integrity proof, not merely
"the extractor ran without crashing" - two independently-sourced PDF files, acquired and
extracted separately, agree to the cent across a 17-year span.

## What was built this pass

- `scripts/ingest/extractors/qld_cffr_annual.py` (new): a regex-based row parser (mirroring
  the established pattern already used for messy PDF financial tables elsewhere in this
  repo, e.g. `scripts/ingest/adapters/state_debt_instruments.py`) - locates the "Year Ended"
  block (never the earlier "Quarter Ended" table on the same page), matches 9 known labels,
  and extracts only the "Total" (current-year) numeric column. 152/153 rows extracted
  cleanly (9 measures x 17 years); the one quarantine (FY2010-11's superannuation/LSL
  contributions label) is genuine - that one file's PDF text extraction drops the label's
  first line entirely (confirmed directly, not a regex bug: a *different*, narrower
  artifact in FY2017-18's same label - a stray placeholder dash interrupting the line wrap
  - was found and safely handled, since that one's full label text IS recoverable).
- `config/measure-semantics/qld_cffr.yaml` (new): 9 measures - 2 stocks (opening/closing
  Consolidated Fund balance) and 7 cash-basis flows.
- `scripts/ingest/migrations/025_qld_cffr_measures.sql`: measure_definitions for the 9.
- `scripts/ingest/load_qld_cffr_annual.py` (new): stock semantics for the 2 balance
  measures (`period_start=None`, matching the convention established for MFS Balance
  Sheet); a distinct `qld_cffr_annual` source_key (never conflated with
  `qld_report_on_state_finances_actuals`'s own different-methodology fiscal aggregates,
  despite sharing a raw folder).
- 14 new tests (8 extractor, 6 loader).

## Deliberately excluded from this first slice (with evidence)

- **The ~50 quarterly interim editions**: a partial-year vintage - never blended with the
  annual Year Ended figures under the same measure_type.
- **The Operating/Investment Account column split**: only the Total column is extracted
  this pass; the split is real, additional information for a future pass.
- **Three receipt sub-line-items with genuine multi-generation composition ambiguity**:
  "Capital return from Public Enterprises"/"Capital return from public enterprise
  investments" (a real wording evolution, likely safe to combine but not yet verified with
  the same rigor as the 9 loaded measures), "Disposal of Public Enterprise Investments",
  and "Receipts from Other Government Entities" - all three coexisted as **distinct rows**
  in at least FY2010-11 (`Capital Return from Public Enterprises  1,313,063` alongside
  `Disposal of Public Enterprise Investments  7,065,209` in the same year's table), so this
  is not a simple rename chain and needs its own dedicated per-generation design, matching
  the discipline already applied to MFS Balance Sheet/Tax Notes.
- **The published Receipts subtotal line**: a bare numeric row with no leading label text
  (unlike every other row extracted here) - would need a different anchoring strategy
  (e.g. "the numeric line immediately before the word 'Payments'"), not attempted this
  pass since the 7 individual receipt line items already loaded provide most of the same
  information.
- **Note 1/Note 2's department-level breakdown detail and the Statement of Appropriations
  section**: genuinely new, valuable, agency-level detail - a substantial follow-up build
  in its own right, not attempted this pass.

## Validation

- Disposable-copy-first throughout: extraction (152 rows, 1 genuine quarantine), migration,
  first apply and a second apply (152 idempotent skips, 0 new inserts) all proven on a copy
  before touching live.
- `task9_sql_integrity_checks.py --db <disposable copy>`: 0 hard failures (no new
  duplicate-fact candidates - each measure has exactly one fact per year, so the
  flat-across-periods false-positive class already documented for every YTD/monthly source
  this session does not arise here).
- `dashboard_depth_audit.py` (disposable vs live baseline, excluding metadata fields): byte-
  identical `projections`/`graph` content - zero canonical-tree impact, as expected (9 new,
  entirely isolated compatibility groups).

## Next item

Live backup + apply, full backend suite, milestone report, ledger update, commit. A future
dedicated pass could extend this to: the 3 deferred receipt sub-line-items (after per-
generation verification), the quarterly interim editions (needs its own vintage-disclosure
design), Note 1/Note 2's department-level detail, and the Statement of Appropriations
section.
