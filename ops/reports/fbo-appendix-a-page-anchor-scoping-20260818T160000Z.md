# Pre-2019 FBO Appendix A - page-anchor scoping (item 8.1)

Generated: 2026-08-18T16:00:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Item 8.1: build generation-bounded parsers for the 21 acquired pre-2019 FBO editions,
following the earlier `fbo-historical-archive-triage-20260807T175900Z.md` triage's own
finding that the existing broad `fbo_appendix_a.extract()` is unsafe to reuse (it latches
onto unrelated summary tables earlier in each consolidated FBO, e.g. `Table 5:
Australian Government general government sector expenses by function` - a function-level-
only table, not the sub-function-level `Table A1` in the true Appendix A) and that report's
own recommendation to "start with the internally consistent 2010-11-2018-19 cluster."

## Finding: the "2010-11-2018-19 cluster" is not internally consistent - at least 4 sub-generations exist within it

Before writing any parser code, a distinctive page-anchor string
(`"Appendix A: Expenses by Function and Sub-function"`, the running header that appears on
every continuation page of the true sub-function-level table, confirmed directly for
FY2010-11) was checked across all 9 years in the recommended cluster:

| financial year | anchor found? | pages | notes |
| --- | --- | --- | --- |
| 2010-11 | yes | 104-106 (3 pages) | |
| 2011-12 | yes | 106-107 (2 pages) | |
| 2012-13 | yes | 108-109 (2 pages) | |
| 2013-14 | yes | 96-97 (2 pages) | |
| 2014-15 | **no** | - | running-header wording differs in this sub-generation |
| 2015-16 | **no** | - | running-header wording differs in this sub-generation |
| 2016-17 | **no** | - | running-header wording differs in this sub-generation |
| 2017-18 | false positive | page 5 | matches a Table-of-Contents mention, not the real table |
| 2018-19 | false positive | page 5 | matches a Table-of-Contents mention, not the real table |

Directly checked 2018-19's real content: its `Table 5` (page 18) is the same
function-level-only summary table the original triage already found the broad parser
incorrectly contaminates on - **not** the genuine sub-function-level Appendix A table,
which was not located by this anchor at all for 2018-19 (needs its own investigation to
find the correct page/anchor for this sub-generation, if it exists in this file at all -
by 2019-20 the source switches to a separate `..._05_appendix_a.pdf` file per edition,
so 2017-18/2018-19 may be a genuine transition point to that later convention).

This means the "2010-11-2018-19 cluster" the earlier triage recommended as the easiest
starting point actually contains **at least 4 distinct sub-generations** requiring their
own page-anchor/header-wording strategy:

1. **FY2010-11..FY2013-14** (4 years) - confirmed stable anchor, though the table's own
   page-length varies (3, 2, 2, 2 pages) - worth verifying this is genuine content growth/
   shrinkage, not a further internal split, before building.
2. **FY2014-15..FY2016-17** (3 years) - anchor text differs, not yet identified.
3. **FY2017-18..FY2018-19** (2 years) - the genuine Appendix A table's location/format is
   not yet identified at all; may require a different extraction strategy entirely.
4. Everything before FY2010-11 (FY1998-99 through FY2009-10, per the original triage's
   dry-run: 0 rows for 1998-99/2001-02/2002-03, and malformed labels for 1999-00) - a
   further, larger set of sub-generations not investigated in this pass.

## Disposition

No extractor code written this pass. The genuinely tractable slice (FY2010-11..FY2013-14,
4 years, confirmed stable page-anchor) is real and worth building first in a dedicated
future pass, following the exact discipline already proven this session for MFS Balance
Sheet/Tax Notes and QLD CFFR: verify every candidate year's actual table content and
column/row-label stability directly (not assumed from a shared filename convention or a
single-year sample) before writing any extraction regex, and extract only the true
`Table A1` sub-function table (never the earlier function-level-only summary table the
broad parser already contaminates on).

## Next item

A dedicated future pass should: (1) build the FY2010-11..FY2013-14 4-year slice first,
using the confirmed page-anchor; (2) separately investigate FY2014-15..FY2016-17's
correct anchor text; (3) separately investigate whether FY2017-18/FY2018-19 have a
genuine Appendix A sub-function table in this file at all, or whether they need to be
acquired as separate files matching the later `..._05_appendix_a.pdf` convention;
(4) tackle the pre-2010-11 population (FY1998-99..FY2009-10) as its own, likely
multi-sub-generation project, matching the original triage's finding that a naive parse
returns 0 rows for 3 of those years and malformed labels for a 4th.
