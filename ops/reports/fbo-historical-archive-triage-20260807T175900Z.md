# Historical FBO/archive triage (20260807T175900Z)

## Queue split

Canonical position 9 contains two materially different items:

1. an acquired, in-repository 1998-99 through 2018-19 Final Budget Outcome
   population; and
2. an external Trove/parliamentary-paper search for 1985-86 and 1986-87
   function statements.

They are assessed separately rather than treating acquisition and parsing as
one task.

## Acquired pre-2019 FBO inventory

The repository holds **all 21 annual FBO editions from 1998-99 through
2018-19**, one per financial year. The exact editions are:

- 1998-99, 1999-00;
- 2000-01 through 2009-10; and
- 2010-11 through 2018-19.

Every PDF is text-extractable without OCR. The directly checked consolidated
documents contain 58 to 122 pages and yield roughly 129,000 to 348,000 text
characters. This supersedes the older roadmap's shorthand that the family is
primarily an OCR problem; it remains a layout/table-generation problem.

The already-loaded archive source contains 415 safe Appendix A facts for
2019-20 through 2023-24, and the separate 2024-25 Appendix A source is also
complete. Pre-FBO BP1 Table I already supplies 26 cash-outlay facts for 1996-97
and 1997-98 and must stay accounting-basis-separated from accrual FBO data.

## Parser safety result

The existing `fbo_appendix_a.extract()` was dry-run read-only against all 21
older FBOs. It is **not safe to reuse unchanged**:

- it returns zero rows for 1998-99, 2001-02, and 2002-03;
- for the other editions it returns 819 to 1,092 rows (224 for 1999-00), far
  above the approximately 83 function/subfunction rows in a standalone modern
  Appendix A;
- the first returned labels include `Gross income tax withholding`, `Gross
  PAYG withholding`, and `Sales of goods and services`, proving that the broad
  `Table A.1` start condition latches onto unrelated revenue tables earlier in
  each consolidated FBO; and
- 1999-00 produces a malformed label containing embedded numeric columns.

Publishing any of that output would contaminate the function hierarchy. A
safe adapter needs edition-generation-specific page/table-title boundaries,
header-column resolution, end-of-table detection, row-vocabulary validation,
and an explicit bridge for classification changes. No row can be inferred
from the current dry run.

## Disposition of acquired work

**Deferred after failed safe-adapter feasibility check.** The source is fully
acquired and readable, but the available adapter demonstrably parses unrelated
tables. This is an explicit semantic/parser blocker, not a guess or an access
problem. A future milestone should start with a page-level inventory of the
21 intended expense-by-function tables and implement bounded generation
parsers, beginning with the internally consistent 2010-11–2018-19 cluster.

No staging file or database was written, so no backup/load/idempotency cycle is
applicable. Counts remain 289,315 facts, 133 source documents, 222,575 nodes,
and 0 edges.

## 1985-86 and 1986-87 external archive gap

The repository evidence remains current: archive.budget.gov.au and historical
CDX checks found only Budget Paper No. 7 (`Payments to or for the States`) for
those years, not the Budget Paper No. 1 / Statement No. 2 function-outlay
series. The next action is an external Trove digitised-books or parliamentary-
papers search and acquisition. It is **external/out-of-repository** and was not
worked around or fabricated in this loop.

Frontend, dashboard rerun, and production verification are not applicable to
this no-change triage. The preceding Task 9/dashboard baselines remain clean.
