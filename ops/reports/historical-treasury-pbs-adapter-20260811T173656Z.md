# Historical Treasury PBS adapter (item 5.3)

Generated: 2026-08-11T17:36:56Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 5.3 (historical PBS adapter family), scoped to the Treasury-portfolio
representative already acquired in item 5.1: `scripts/ingest/extractors/historical_treasury_pbs.py`,
covering the March 2022-23, October 2022-23 and 2023-24 Portfolio Budget Statements.

## Previous state

A prior, uncommitted-to-the-ledger commit (`4efd5e8`) added the extractor module but it
had never been run successfully: every one of the three editions raised
`ValueError: duplicate year/category/status rows` on the very first execution attempt, and
no test, fixture or report existed for it. Item 5.3 was recorded as `not_started` in the
progress ledger.

## Root causes found and fixed

Investigated each edition's raw PDF text against the extractor's state machine
individually, per this repository's established duplicate/defect investigation discipline
(verify against raw source before changing anything). Four distinct defects were found and
fixed, all in `scripts/ingest/extractors/historical_treasury_pbs.py`:

1. **Outcome-level reconciliation table misattributed as a program component.**
   Every edition's "`Outcome N Totals by appropriation type`" table (a cross-program
   summary, not program detail) was still being attributed to the last-seen
   `program_number`, producing a genuine duplicate key and, worse, silently inflating that
   program's expenses with an unrelated whole-of-outcome figure. Fixed by detecting the
   section header and resetting `program_number`/`scope`/`heading` before the next program
   header appears.
2. **Multi-item appropriation-type headings only reached their first child.**
   Headings such as "`Ordinary annual services (Appropriation Bill No. 1)`" can introduce
   two or more indented line items (e.g. a named body plus a generic "`Other`" line); the
   original one-shot `pending`-buffer merge attached the heading only to the first item,
   leaving subsequent siblings (e.g. a bare "`Other`" row) under an ambiguous, unqualified
   label. Fixed with persistent `heading` state that survives across siblings and resets
   only at genuine scope/program/total boundaries (`KNOWN_HEADINGS`,
   `STANDALONE_LABEL_PREFIXES`).
3. **Row values pypdf split across more than one physical line.**
   For two Australian Taxation Office programs (1.8, 1.10) in the 2023-24 edition, the
   five year-columns of a single row rendered across two or three separate text lines
   (e.g. one number attached to the label, the next alone on its own line, the remaining
   three on a third line), causing the standard five-token line pattern to never match and
   the entire row — 10 facts across two programs — to be silently dropped. Fixed with a
   bounded `_merge_wrapped_amount_lines` pre-pass that only reassembles lines that do
   **not** already satisfy the ordinary five-token pattern, and only absorbs pure numeric
   continuation lines, so ordinary single-line rows are provably untouched.
4. **A three-line label wrap left its amounts orphaned.**
   National Competition Council's "`Expenses not requiring appropriation in the Budget
   year (a)`" wrapped across three physical label lines, filling the fixed `pending` buffer
   (cap 3) before the amounts-only line arrived; that bare `34 34 34 34 34` line had no
   attached label so the existing amount-line pattern (which required a non-empty label)
   rejected it and it was dropped. Fixed by allowing `_amount_line` to recognise a
   label-free, fully numeric line and let the existing `pending`-join logic supply the
   already-buffered label text.
   A distinct "`Movement of administered funds between years`" reconciliation table (a
   different memo concept, not expense detail) was also found reusing the `Program N:`
   line pattern and corrupting Treasury Program 1.9; excluded via the same section-header
   detection as defect 1.

## Validation

Extraction now runs cleanly on all three real, already-acquired PDFs with **zero
exceptions**, and every result was independently verified against the raw PDF text and
against the documents' own published totals, not merely against the extractor's own
output:

| Edition | Rows | Programs × 5 FY = program rows | Component-sum reconciliation |
| --- | --- | --- | --- |
| `federal_pbs_2022_23_march_treasury` | 710 | 43 × 5 = 215 ✓ | 212/215 exact; 3 within documented $1,000 rounding |
| `federal_pbs_2022_23_october_treasury` | 675 | 43 × 5 = 215 ✓ | 215/215 exact |
| `federal_pbs_2023_24_treasury` | 620 | 39 × 5 = 195 ✓ | 195/195 exact |

- Every program's `Total expenses for program N` row equals the independently summed
  `component` rows beneath it, program by program, year by year — the strongest available
  check that no row was mis-attributed, dropped, or double-counted. The only three
  exceptions (Department of the Treasury Program 1.1, March edition, FY2022-23/2023-24/
  2024-25) differ by exactly $1,000, consistent with the source documents' own
  independent per-line rounding to the nearest $'000 and explicitly whitelisted as such in
  the regression test rather than silently tolerated everywhere.
- Each fact key `(fy, category, estimate_status)` is unique within its edition (0
  duplicates in all three).
- March and October 2022-23 remain distinct publication vintages with different amounts,
  confirmed programmatically.
- Every row carries an exact-year locator (`fy:<year>` in `locator`), the resolved
  official `landing_url`/`resource_url`, and `cached_copy_path` back to the acquired PDF.
- No row's category contains the excluded reconciliation-table text
  ("totals by appropriation type", "movement of administered"), and no row has an empty
  component label.

New regression suite: [`tests/ingest/test_historical_treasury_pbs.py`](../../tests/ingest/test_historical_treasury_pbs.py),
**12 passed**.

Full backend/ingest suite (`python -m pytest -q`): **617 passed**, 0 failures — the prior
605-pass baseline plus this milestone's 12 new tests, with zero regressions elsewhere.

`ruff check` on both the extractor and the new test file: passed.

## Data impact

Staging only. `data/staging/breakdowns/federal_pbs_2022_23_march_treasury.csv`,
`federal_pbs_2022_23_october_treasury.csv` and `federal_pbs_2023_24_treasury.csv` were
generated (710/675/620 rows respectively). `data/staging/` is gitignored and not part of
`data/facts.db`; no fact, edge, canonical lineage or dashboard-visible content changed.
The live projection, root totals and existing PBS graph are untouched.

## Remaining risk / next item

This milestone produces validated, edition-bounded staged extraction only. Per the
5.2 milestone's own boundary and this plan's Wave 3 sequencing, historical PBS rows remain
**withheld from dashboard deployment** until item 5.4 (crosswalk beneath matched
Statement 6 nodes, exact-only related edges) is implemented and independently reviewed —
loading these into `data/facts.db` or wiring graph edges before that crosswalk exists
would risk exactly the kind of ungoverned depth increase the plan's non-negotiable rules
forbid. Item 5.5 (NDIA repair, current-PBS coverage-by-portfolio report, quarantine
precision review) remains a separate, not-yet-started follow-on.
