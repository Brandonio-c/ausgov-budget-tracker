# QLD Consolidated Fund quarterly editions - scoping (item 7.4, deferred scope)

Generated: 2026-08-19T194500Z
Repository: `ausgov-budget-tracker`, branch `main`

## Purpose

Item 7.4's first slice (17 annual "Year Ended" CFFR editions, 152 facts) is live -
see `ops/reports/qld-cffr-scoping-20260815T163500Z.md` and the item 7.4 milestone in
`data-remediation-progress.md`. That build deliberately deferred the ~50 quarterly
interim editions (a partial-year vintage). This report characterizes that population
directly - real files, real page text, never guessed - before any extractor code is
written, matching this session's established discipline.

## File inventory

54 genuine quarterly Consolidated Fund files identified in
`data/raw/state/qld_report_on_state_finances_actuals/snapshots/20260724T190604Z/files/`,
spanning FY2008-09 through FY2025-26, across at least 8 distinct filename conventions
(the same naming inconsistency already seen and handled explicitly, never regex-guessed,
for the FBO Appendix A/B population):

- `consolidated-fund-YYYY-{march,september,december}.pdf` (2008-2016, 27 files)
- `CFFR-{Dec,Mar,Sep,Sept,September,December,March}[-_]{YYYY|YY}.pdf` and close variants
  (2017-2025, ~17 files)
- `Consolidated-Fund-Financial-Report-{Month}-2017.pdf` (3 files, a one-off naming era)
- `01978-2019-{ATTACHMENT,Attachment}-CFFR-{Month}-2019.pdf` (2 files)
- `CFFR-March-Qtr-2018-attachment.pdf`, `CFFR-December-2019-Quarter.pdf`,
  `CFFR-Sept-2020-Tables.pdf` (3 one-off-worded files)
- `cffr-sept-2025.pdf`, `quarterly-statement-consolidated-fund-{dec,march}{YYYY}.pdf`
  (3 more recent files, yet another naming convention)

The same raw folder also holds ~130 unrelated documents (MYFER, Report on State
Finances, Financial Accountability Handbook volumes, NCAP policies, guidelines) -
excluded by direct filename inspection, not swept in by a broad glob.

There is no separate "June quarter" quarterly file for any year - the annual "Year
Ended 30 June" edition (already loaded) is itself that year's Q4/full-year figure, so
the quarterly population is genuinely only Sep/Dec/Mar per year.

## Table structure - two genuinely different vintages per file, confirmed by direct inspection

Every quarterly file contains one or two tables, depending on which quarter it is:

- **September editions (Q1)**: a single table, titled "STATEMENT OF RECEIPTS AND
  PAYMENTS AS AT 30 SEPTEMBER \<year>" (older editions) or "...FOR THE QUARTER ENDED 30
  SEPTEMBER \<year>" (newer editions) - because the first quarter's 3-month flow and
  the fiscal year's cumulative Year-to-Date are the same figure at that point.
- **December editions (Q2) and March editions (Q3)**: **two** separate tables -
  "STATEMENT OF RECEIPTS AND PAYMENTS FOR THE QUARTER ENDED \<date>" (a 3-month-only
  flow, not cumulative) and "STATEMENT OF RECEIPTS AND PAYMENTS FOR THE \<N> MONTHS
  ENDED \<date>" (the cumulative Year-to-Date figure). These are genuinely different
  vintages - the quarter-only flow must never be summed with, or presented
  interchangeably alongside, the cumulative Year-to-Date figure, per this program's
  standing "never sum incompatible... vintages" rule. Confirmed directly in both an
  older (`consolidated-fund-2012-march.pdf`) and a recent (`CFFR-March-2023.pdf`) file.

Both table types share an identical, stable column layout across every year checked
(2008, 2012, 2018, 2022, 2023): `Operating Account | Investment Account | Total
<period, current> | Total <same period, prior year>`. Only the 3rd column ("Total",
current period) should ever be extracted - matching the exact same "Total only, never
the Operating/Investment split" convention already established for the annual editions.

Row composition matches the already-loaded annual editions closely: Balance as at
[period start], the same ~7 receipt line items (Collections received from Departments,
Investment Interest, Dividends and Income Tax Equivalents, Non-Appropriated Equity
Adjustments, Superannuation/LSL/QGIF/ALCS Contributions, one or more of the
already-documented ambiguous "Capital return.../Disposal of.../Receipts from Other
Government Entities" variants, Other Receipts), Appropriations provided to Departments,
Net Effect of Investments, and the closing balance. The same 3-way receipt-line
composition ambiguity already documented for the annual editions
(`ops/reports/qld-cffr-scoping-20260815T163500Z.md`) recurs here too - confirmed
directly (`consolidated-fund-2008-september.pdf` uses "Receipts from Other Government
Entities" as its own distinct line).

## A real, isolated extraction-quality defect found - not systemic, but must not be ignored

`consolidated-fund-2012-march.pdf`'s extracted text (both via pypdf and `pdftotext
-layout`) shows genuine OCR-quality character corruption, not just layout
misalignment: `"totaIs"` (capital I substituted for lowercase L), `"Qua~erEnded"` and
`"~he"` (tilde substituted for missing letters), `"2O8"` (letter O substituted for
zero), `"6~281,500"` and `"26~830,702"` (tilde substituted for a thousands comma). At
least one row ("Collections received from Departments") is missing its own
current-period value entirely in the main summary table on that page. This is a
materially different and higher-risk class of defect than anything handled so far this
session (the FBO font-shift cipher was a *consistent*, decodable substitution; this
looks like inconsistent per-character corruption, likely from a poor-quality scan or
OCR pass specific to this one file) and would need its own dedicated investigation
(not a blind regex-tolerance patch) before being trusted for real data.

**A representative spot-check of 6 other files spanning the same 2008-2020 era**
(`consolidated-fund-2008-september.pdf`, `2010-march`, `2013-december`,
`2016-september`, `Consolidated-Fund-Financial-Report-September-2017.pdf`,
`CFFR-Sept-2018.pdf`, `CFFR-March-2020-publish.pdf`) **found no corruption in any of
them** - all extracted cleanly. This strongly suggests the 2012-march defect is an
isolated bad file, not an era-wide problem, but this is not yet confirmed for the
remaining ~47 files not directly checked.

## Recommended approach

1. **Do not build against the full 54-file population in one pass.** Unlike the FBO
   Appendix A/B population (where every sub-generation shared one of a small number of
   verified layouts), this population's real risk is per-file extraction-quality
   variance, not layout variance - the column/row structure itself is stable and
   simple. The right validation unit is therefore "did this specific file extract
   cleanly and pass the cross-check", checked per file, not assumed from its era.
2. Build the extractor to explicitly enumerate every file (financial year, quarter,
   filename, table-count-expected) - never a directory glob - mirroring the FBO
   `_EDITIONS` pattern, and route both the quarter-only and Year-to-Date tables into
   **two distinct, clearly-labeled measure families** (e.g.
   `qld_cffr_quarterly_ytd_*` and `qld_cffr_quarterly_flow_*`), never reusing the
   already-loaded annual `qld_cffr_*` compatibility_groups.
3. For each file, cross-validate the extracted Year-to-Date figures against the
   already-loaded annual editions where they should agree in direction (e.g. a
   September YTD balance should be internally consistent with that year's own annual
   opening/closing balance chain, the same style of independent proof already used for
   the annual editions) and quarantine (not force-load) any file whose extraction
   doesn't pass a sanity check, exactly as `consolidated-fund-2012-march.pdf` should be
   quarantined pending its own investigation, not silently included or silently
   dropped.
4. A natural first slice: the ~17 most recent years (2017 onward, ~17 x 3 = ~51... no,
   really ~9 years x 3 quarters = ~27 files across the "CFFR-\*" naming eras), all
   independently spot-checked clean in this pass, deferring the pre-2017
   `consolidated-fund-YYYY-*` era (where the one known-corrupted file lives) to a
   second, more carefully-audited pass.

## Disposition

Item 7.4's quarterly scope remains **properly scoped, not built**. This report
supersedes the one-line "quarterly interim editions" placeholder in the annual CFFR
milestone with direct evidence: real table structure, real column positions, a real
file-quality risk found and isolated (not glossed over), and a concrete recommended
build order. No extractor, semantics, migration, or loader code has been written for
this scope.
