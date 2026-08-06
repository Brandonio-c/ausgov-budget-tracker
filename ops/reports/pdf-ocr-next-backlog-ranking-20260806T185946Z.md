# PDF/OCR next backlog ranking (Task 1)

Generated: 2026-08-06T18:59:46Z.

## Ground truth verified before ranking

- `git status --short`: clean. Branch `main`. `HEAD` and `origin/main`
  both at `738c808`.
- `ops/reports/current-state.md`: general project overview, no
  TAS/QLD-PDF-specific detail affecting this ranking.
- Prior milestone's own backlog ranking
  (`ops/reports/qld-tas-next-backlog-ranking-20260806T171537Z.md`) had
  already fully triaged the structured (xlsx/csv) candidates in both
  jurisdictions and explicitly deferred the two PDF-heavy populations
  named in this mission - `tas_treasurer_annual_financial_reports`'s
  76 PDF siblings and `qld_report_on_state_finances_actuals`/`qld_
  report_on_state_finances`'s 187 PDFs - to a dedicated PDF/OCR
  milestone. This report performs that triage.
- `config/procurement_sources.yaml`: both entries unchanged since the
  prior milestone's inspection (`handoff_already_on_disk: true`, no
  new acquisition needed).
- No existing PDF-sourced extractor/loader/measure-semantics file
  exists for either jurisdiction today (confirmed:
  `scripts/ingest/extractors/` and `config/measure-semantics/` contain
  no TAS-PDF or QLD-PDF-specific files).

## TAS: 76 PDFs, inspected directly by filename cohort and content

Grouped the 76 files by content, not filename guesswork:

1. **23 "Treasurer's Annual Financial Report" (TAFR) editions**,
   2003-04 through 2024-25 - the core annual actuals report. Directly
   opened multiple editions and found **two distinct internal shapes**:
   - **2010-11 to 2012-13 (3 editions)**: a clean, stable "Table 2.1:
     Key Financial Indicators" table (General Government Sector rows:
     Net Operating Surplus/(Deficit), Fiscal Surplus/(Deficit), Net
     Debt, Net Worth, Net Financial Liabilities - Budget/Actual/Prior-
     Year-Actual columns) plus a "Summary of Operating Result" table
     (Revenue from transactions, Expenses from transactions, Net
     Operating Balance, Fiscal Balance - Budget/Actual/Variation
     columns). Confirmed structurally identical labels and column shape
     across all 3 editions by direct inspection of each one's raw
     extracted text - not assumed from one sample.
   - **2003-04 to 2009-10 (7 editions, one of which - 2009-10 - was
     directly checked)**: an older narrative-format Executive Summary
     with the same underlying measures (Fiscal Surplus, Net Debt, Net
     Financial Liabilities, Cash Surplus) embedded in running prose and
     small multi-year bar-chart-adjacent number lists, not a labelled
     table. Genuinely harder to parse safely - deferred (documented,
     not implemented this milestone).
   - **2013-14 to 2024-25 (13 editions)**: these years are **already
     fully covered** by the already-loaded `tas_ggs_*` family (from the
     GGS Key Fiscal Measures Time Series xlsx, per the prior milestone)
     - re-extracting them from these PDFs would be pure duplication.
     Excluded from scope entirely (not a candidate at all).
2. **~11 "Revised Estimates Report" / "Preliminary Outcomes Report" /
   "Quarterly Report" / "MYFR" documents** - in-year vintage snapshots.
   The GGS xlsx already captures the authoritative `revised_estimate`/
   `forward_estimate` vintage per year; these add within-year detail
   without clear incremental dashboard value for this milestone.
   Deferred.
3. **~11 general economic-indicator briefs** (Bankruptcy-
   Administrations, Building-Approvals, Consumer-Price-Index,
   International-Trade-In-Goods, Labour-Force, Population, State-
   Accounts, Wage-Price-Index, etc.) - off-topic ABS-style economic
   statistics, not TAS Treasury's own fiscal aggregates. Deferred,
   consistent with how similarly off-topic structured QLD candidates
   were deferred in the prior milestone.

**Selected sub-shape: the 3 tabular-format TAFR editions (2010-11,
2011-12, 2012-13)** - see Task 2 for the full selection rationale.

## QLD: 187 PDFs, spot-checked directly

The one genuine annual "Report on State Finances" edition inspected
(`2018-19-Report-on-State-Finances.pdf`, 125 pages) has real, useful
content - a "Summary of Key UPF Financial Aggregates" table with
Revenue/Expenses/Net operating balance/Fiscal balance/Capital purchases/
Borrowing figures for General Government/PNFC/Total State sectors.
However, direct inspection surfaced two real risk factors:

- **Font-encoding corruption confirmed on the cover page**: `pypdf`
  extracted glyph-name gibberish (e.g. `/two.tf/zero.tf/one.tf/eight.tf`
  instead of `2018`) rather than actual digit characters - a known
  failure mode of certain PDF-generation toolchains that use custom
  glyph names for old-style/lining figures. The specific data table
  checked (page 9) extracted correctly, but this confirms the
  population has at least one font-encoding risk area, meaning every
  candidate page/edition would need individual verification rather than
  a single trusted extraction method.
- **Column-to-sector ambiguity**: the summary table's 3 sector-pairs
  (GGS, PNFC, Total State) do not extract with clear per-sector column
  headers in plain text - correct attribution requires cross-
  referencing a second breakdown table per edition (verified this is
  possible for the one file checked, by matching `Total Revenue 60,068
  59,834` against the first table's own first pair of numbers, but this
  is real per-edition validation work, not a one-time proof).

Additionally, QLD has **no existing measure family to extend** - unlike
TAS, this would require building an entirely new semantic model and
compatibility_group set from scratch, and the 187-file population would
need a full per-file survey (most of the 187 are quarterly CFFR
economic-bulletin PDFs, not annual outcome reports) before any adapter
work could be safely scoped.

## Re-ranking against the mission's 7 criteria

1. **Existing structured/parsable availability**: TAS's 3 target
   editions are genuine, clean, stable-shape text (not scanned images,
   not narrative prose) - directly verified across all 3. QLD's one
   sample file mixes clean data (page 9) with confirmed font-encoding
   corruption elsewhere (page 0) - a real, not hypothetical, risk.
2. **Engineering effort**: TAS - 3 known-good editions, one parser. QLD
   - unknown edition count still requiring a full survey, plus new
   measure-family design work.
3. **Dashboard value**: TAS - extends 7 already-modelled, already-
   dashboard-exposed measures backward by 3 years (genuine new
   coverage, zero duplication risk). QLD - would add a wholly new
   family with unverified reach until surveyed.
4. **One adapter covering multiple editions**: TAS - one parser
   confirmed to work identically across all 3 target editions. QLD -
   unverified across editions beyond the single sample.
5. **Semantic risk**: TAS - low (unambiguous single-sector rows, no
   footnote markers found in the target pages, space-thousands-
   separator parsing already proven on the GGS xlsx's nbsp separator).
   QLD - medium-high (column-to-sector ambiguity, confirmed font-
   encoding risk).
6. **Already partially supported**: TAS - yes, extends the already-
   shipped `tas_ggs_*` compatibility_groups. QLD - no existing PDF-
   sourced family exists for this jurisdiction.
7. **Workable PDF text extractor exists**: TAS - confirmed (`pypdf`
   extracts clean, row-major text with no font-encoding issues across
   all 3 target editions). QLD - partially confirmed, with one
   documented corruption risk area.

## Recommended order

1. TAS TAFR tabular sub-shape (2010-11 to 2012-13) - **selected this
   milestone**.
2. TAS TAFR narrative sub-shape (2003-04 to 2009-10) - deferred, a
   future milestone's investigation slot.
3. TAS Revised Estimates/Preliminary Outcomes/Quarterly Reports -
   deferred, lower incremental value.
4. TAS off-topic economic-indicator briefs - deferred, wrong topic
   domain.
5. QLD Report on State Finances population - deferred to a future,
   dedicated QLD PDF/OCR milestone (needs a full per-file survey, new
   measure family, and font-encoding-corruption mitigation work beyond
   this milestone's scope).

Full table: `ops/reports/pdf-ocr-next-backlog-ranking-20260806T185946Z.csv`.

## Next

Task 2: formal scope-selection report confirming the TAS TAFR tabular
sub-shape (2010-11 to 2012-13) as the selected family.
