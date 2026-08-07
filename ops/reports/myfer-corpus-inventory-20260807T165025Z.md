# Queensland MYFER corpus inventory and cluster selection

Generated: 2026-08-07T16:50:25Z  
Population: `qld_report_on_state_finances_actuals`

## Current-state readout

- Starting commit: `9275d07` on `main`, equal to `origin/main` after fetch.
- Starting tree: not clean only because the previously requested consolidated
  backlog report was untracked; no pre-existing code or data edits were found.
- MYFER remains the first unfinished human-curated QLD family after both RSF
  clusters and the RSF Net Debt/Borrowing follow-up completed.
- This is PDF work. It is neither structured-workbook work nor Cloudflare or
  other external-infrastructure work.

The companion CSV is the complete 21-edition inventory and contains the exact
source record ID, filename, SHA-256, candidate table/page, financial year,
publication date where available, observed shape, unit, period semantics,
pre-milestone fact/quarantine counts, support decision, text status, and OCR
decision for every edition.

## Corpus findings

- 20 of 21 PDFs have usable embedded text. `mid-year-review-2002-03.pdf`
  yields characters, but its character map converts the document to gibberish
  in both pypdf and Poppler; it is not safely text-extractable and requires OCR.
- The files do not share one schema. The corpus contains early detailed UPF
  tables, a distinct 2005 Special Fiscal and Economic Statement, later detailed
  GGS operating statements, and modern compact key-aggregate tables.
- No MYFER facts or MYFER-specific quarantine records existed before this
  milestone. The 364 existing facts under the population source document are
  RSF facts, and exact MYFER cached paths occur in none of their citations.
- The related `Budget Update` files for 2021-22 through 2024-25 were not silently
  added. They have different publication titles and are outside the explicitly
  named MYFER corpus; a later decision may establish whether they are formal
  successors.

## Selected safe cluster

Select six compact key-fiscal-aggregate tables:

1. 2015-16, Table 3, PDF page 23;
2. 2016-17, Table 3, PDF page 23;
3. 2017-18, Table 3, PDF page 13;
4. 2018-19, Table 3, PDF page 14;
5. 2019-20, Table 3, PDF page 16; and
6. 2025-26, Table 2, PDF page 7.

Each has one label column and six fiscal columns: prior actual/outcome,
current budget, current MYFER/revised estimate, and three projections. The
adapter selects only the third numeric column and only five common GGS rows:
Revenue, Expenses, Net operating balance, PNFA/purchases of non-financial
assets, and Fiscal balance. This yields 30 publishable observations.

The 2016-17 source contains a genuine `54,9 53` text-extraction artifact, and
2018-19 contains spaced parenthesized digits. Both are bounded repairs covered
by tests. Parenthesized amounts remain negative.

## Risks and exclusions

- Borrowing changes from a generic row to instrument-specific `Borrowing with
  QTC`; later tables also add leases, securities/derivatives, Net debt, and an
  NFPS borrowing row. These are excluded rather than semantically guessed.
- Editions through 2014-15 use materially different detailed operating-table
  shapes. Some remain plausible future subclusters, but are not covered by the
  first adapter.
- 2012-13 and 2013-14 have pervasive split-digit extraction artifacts and need
  their own bounded layout rules.
- The 2005 document is explicitly a Special Fiscal and Economic Statement and
  remains a separate shape despite being stored under a `mid-year-review-*`
  filename.
- Publication dates in the CSV come from explicit cover text where present or
  PDF creation metadata where consistent. `unknown` is retained for 2001-02 and
  2002-03 rather than turning unreliable metadata into asserted publication
  dates.
