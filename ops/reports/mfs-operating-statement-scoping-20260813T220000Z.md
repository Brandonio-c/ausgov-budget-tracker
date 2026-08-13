# MFS Operating Statement - scoping investigation, deferred with evidence

Generated: 2026-08-13T22:00:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 7.1, third MFS sibling workbook in the stated order (Note 3 - workbook 2 -
was completed in the prior milestone). Investigated before writing any extractor code, per
this program's standing discipline; found genuinely multi-generation complexity and
deferred rather than rushed.

## What was found

`federal_mfs_operating_statement` (21 sheets, FY2005-06..FY2025-26) is **not** a richer
version of the same single-table shape Note 3 and Aggregates share. Direct inspection of
every sheet found at least three structurally distinct eras:

1. **FY2005-06, FY2006-07** - an "Income Statement" (not yet called "Operating
   Statement"), 13-17 high-level line items only (`Total Taxation Revenue`, `Total
   Non-Tax Revenue`, `Total Gains`, `Income`, `Total Goods and Services`, `Total
   Subsidies Benefits and Grants`, `Total Borrowing costs`, `Total Expenses`, `Operating
   Result`), plus a **separate second table** on the same sheet ("Reconciliation of the
   Operating Result to Fiscal Balance": `Operating result`, `GFS Net Operating Balance`,
   `Fiscal Balance (GFS Net Lending)`). No itemized expense/revenue breakdown exists in
   these two years at all.
2. **FY2007-08** - transitional and uniquely malformed. Uses `GFS revenue`/`GFS expenses`
   section wording (not `Revenue`/`Expenses`), different row wording throughout (`Salaries
   and wages` not `Wages and salaries`; `Payment for supply of goods and services` not
   `Supply of goods and services`; `Grant expenses` not `Current grants`; `Capital
   transfers` as a single value, not a subsection), and two rows whose label is split
   across two physical Excel rows by a line-wrap ("plus Other movements in non-financial "
   / " assets" as two separate cells, the value landing on the second) - a genuine,
   file-specific formatting artifact, not a second data point.
3. **FY2008-09..FY2025-26** (18 years) - the modern, richly itemized Operating Statement
   (Revenue/Expenses/Current transfers/Capital transfers/Other economic flows/Non-owner
   movements in equity/Net acquisition of non-financial assets/Fiscal balance). Even
   within this "modern" era, the Other-economic-flows/equity subsection alone has gone
   through at least four distinct vocabularies as it evolved (`Revaluation of
   equity(b)` FY2008-09/09-10 -> `Gain/loss on equity and on sale of assets(b)`
   FY2010-11..12-13 -> a plain `Other economic flows` era with no separate equity split
   FY2011-12/12-13 -> `Non-owner movements in equity(b)` FY2013-14..15-16 ->
   `Non-owner movements in equity` FY2016-17+), and section-header text itself carries
   inconsistent trailing footnote markers year to year (`- included in operating
   result` vs `- included in operating result(b)`), which would need to be stripped from
   section labels the same way row labels already are, not just row labels.

A structural section-collision was also confirmed as real, not a parsing bug: the label
`"Actuarial revaluations"` appears **twice per sheet** from FY2013-14 onward, under two
different sections (`- included in operating result` and `Non-owner movements in
equity`) with **different values** - these are genuinely two different GFS concepts that
happen to share a row label, and would be silently and incorrectly conflated by any
extractor that maps on row label alone without section context. `"Net operating
balance"` also appears twice per sheet, but as a genuine same-value cross-reference
(the statement restates it for the reader partway down the table) - safe to load once,
but the second occurrence must be explicitly recognized and skipped, not accidentally
inserted a second time under an identical `fact_key`.

## Why this is deferred rather than attempted now

Building a correct extractor here requires the same generation-bounded discipline the
plan already prescribes for the historical FBO long-tail (Wave 6, item 8.1): "Never
restore the current broad Table A.1 latch... [need] page/table-title manifest; header and
outcome-column resolution; end-of-table detection; allowed row vocabulary;
classification-version bridge; negative fixtures." Attempting a single mapping across
`FY2005-06..FY2025-26` - or even across just the "modern" `FY2008-09..FY2025-26` span
without fully resolving the equity-subsection's internal era boundaries - would mean
guessing which of several genuinely different section vocabularies a given year's row
belongs to, which is exactly what this program's non-negotiable rules forbid ("never
infer missing hierarchy from label similarity alone", "never hide a semantic mismatch
behind a visualization trick"). This is a real, evidenced-necessary scope boundary, not
scope avoidance: the investigation above is the "establish a baseline" step done
properly: it stops here because doing the next step (writing the label-to-measure map)
correctly requires more dedicated, focused verification per era than fits inside this
already-long session, not because the work is unclear in principle.

## Disposition

Deferred, not abandoned. No code was written for this workbook (only investigated) -
nothing to quarantine or roll back. Recorded in the progress ledger as `deferred` with
this evidence, distinct from `not_started` (which would imply no investigation has
happened yet).

## Recommended next steps for a dedicated future pass

1. Treat FY2005-06/FY2006-07 ("Income Statement") as its own small, separate generation
   - only ~9-13 line items, likely the fastest of the three to adapt correctly.
2. Treat FY2007-08 as either its own single-year generation or explicitly excluded
   (only one year of coverage at stake) given its unique malformed-label-wrap defect.
3. For FY2008-09..FY2025-26, fully resolve the Other-economic-flows/equity subsection's
   internal era boundaries (at least 4 identified above) before writing any mapping -
   each needs its own verified `source_label_variants` list and `not_published_before/
   only_published_financial_years` gate, exactly as `mfs_note3_asset_sales` and the
   Note 3 wording-drift measures were handled.
4. Extend `mfs_common.py`'s footnote-stripping to section-header labels (currently only
   applied to data-row labels via `clean_label()`), or build a dedicated
   section-aware extraction module if the two extraction shapes (flat vs sectioned)
   diverge enough to not share `extract_ytd_workbook()` cleanly.
5. Build the "Actuarial revaluations" section-collision handling and the "Net operating
   balance" cross-reference-skip logic with explicit tests before touching real data.

## Next item

Item 7.1's remaining workbooks (Operating Statement generations above, then Balance
Sheet, Tax Notes 1/2, Monthly Profiles) remain open for future dedicated passes. Given
this discovery, redirecting this session's Wave 5 effort to item 7.2 (QLD QGIP repair),
an independent, differently-scoped item with its own already-documented defects (amount-
column defect, missing subprogram structure, the 2099-00 observation) rather than rushing
Operating Statement's real complexity.
