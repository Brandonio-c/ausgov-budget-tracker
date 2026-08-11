# Repair federal_pbs_2026_27_ndia (item 5.5, part 1)

Generated: 2026-08-11T23:02:53Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 5.5, sub-item 1: "Repair `federal_pbs_2026_27_ndia` with a source-specific
fixture."

## Previous behavior

`federal_pbs_2026_27_ndia` is a real, acquired 22-page PDF (`config/procurement_sources.yaml`
id `federal_pbs_2026_27_ndia`; on-disk manifest confirms `status: downloaded`), but the
generalized `scripts/ingest/extractors/pbs_programs_all.py` adapter published **zero**
facts under it. `ops/reports/ingestion-coverage-20260808T161257Z.md` and earlier reports
record it as `adapter_broken`. It is not a duplicate alias and not a download failure -
the raw content is present and fully text-extractable.

## Root cause

Two independent findings from running the generalized extractor directly against this one
PDF and tracing it through `main()`'s cross-document dedupe:

1. The extractor's page-layout assumptions (multi-portfolio Table 2.1 with an
   Administered/Departmental split) do not match this document's actual layout: a single
   entity, two programs, "Revenue from Government" resourcing lines, "Total for Program N"
   totals, and an "Outcome 1 totals by resource type" cross-program reconciliation table.
   Extracted labels came out visibly malformed (column-header text concatenated into the
   label).
2. `main()`'s cross-document dedupe key is `(portfolio, program_label.lower(), fy,
   estimate_status, amount)` with no source_id component. `_portfolio_from_source()`
   assigns NDIA the portfolio label `"Health Disability and Ageing"` - the same label used
   by an unrelated, much larger, separately-loaded PBS document. Even where extraction
   succeeded (86 raw rows, confirmed by direct invocation), rows with any coincidentally
   matching key were silently discarded as apparent duplicates of that other document,
   collapsing NDIA's contribution toward zero.

## Fix

Added `scripts/ingest/extractors/federal_pbs_2026_27_ndia.py`, a bounded, source-specific
adapter (following the same design as item 5.3's historical Treasury PBS extractor)
covering exactly this one document: 1 entity, 1 outcome, 2 programs, Table 2.1.1. Excludes
the "Outcome 1 totals by resource type" reconciliation section from being treated as
program detail, using the same defect pattern already fixed for Treasury in item 5.3.

### A second, more serious defect found before deployment

Loading NDIA's program totals under the generalized family's own `measure_type:
budget_estimate` (`compatibility_group: budget_expense`) was tested on a disposable
database copy and found to add NDIA's **entire** FY2029-30 outcome total ($56,528,831,000)
on top of the `federal_budget_latest` root total. Investigating why found that
`federal_pbs_programs_all` already carries the portfolio department's own administered
expense line `"Program 3.2 – National Disability Insurance Scheme"` (~$34-38 billion for
FY2024-25/2025-26, confirmed by direct query against the live database) - the same
underlying Commonwealth-to-NDIA transfer that NDIA's own document reports receiving as
`"Payment from related entities"` revenue (~$38-40 billion for the same years). Summing
both additively double-counts that transfer, the same class of defect fixed for historical
Statement 6/PBS evidence in item 5.4.

Applied the same isolation pattern: migration `019_ndia_pbs_measure.sql` registers a new
`federal_pbs_2026_27_ndia_expense` measure with its own compatibility group,
`additive_across_nodes=0`, `root_total_allowed=0` - structurally invisible to every
existing dashboard mode's raw fact walk while remaining reachable by node id for a future
`related_breakdown` crosswalk edge, exactly as item 5.4 did for historical PBS/Statement 6.

## Validation

- Extractor unit checks (`tests/ingest/test_federal_pbs_2026_27_ndia.py`, 5 tests): row/kind
  counts (50 rows: 40 component + 10 program), uniqueness, component sums reconcile
  exactly to every published `"Total for Program N"` row (0 mismatches across 10
  program×year combinations - no rounding tolerance needed here, unlike the Treasury
  extractor), reconciliation-table exclusion, exact-year citation completeness.
- Disposable-copy dry run under the naive `budget_estimate` measure type: confirmed the
  $56.5b root-total inflation described above (proof of the defect) before any live write.
- Disposable-copy re-run under the corrected isolated measure type: 50/50 published, 0
  quarantined; `task9_sql_integrity_checks.py` 0 hard failures;
  `dashboard_depth_audit.py --check-fixture` byte-identical to the reviewed baseline for
  every one of the 10 required projections (only the database path differed).
- Live deployment: backup taken first (`facts-20260811T225929Z.db`, baseline 289,268
  facts). Migration 019 applied idempotently. 50 facts loaded (289,268 → 289,318); a second
  run replaced all 50 and left the count unchanged (idempotent).
  `task9_sql_integrity_checks.py`: 0 hard failures. `dashboard_depth_audit.py
  --check-fixture`: **`fixture_matches: true`**.
- New regression suite `tests/api/test_ndia_pbs_isolation.py` (3 tests): the new measure
  type can never anchor a root total, zero canonical-dataset assignment, and the live
  facts.db's program totals exactly match the extractor's own validated output.
- Full backend suite after live deployment: **637 passed** (629 baseline + 8 new), 0
  regressions. `ruff check` on all three new Python files: passed.

## Data impact

`data/facts.db`: +1 `measure_definitions` row, +50 facts under the new mode-invisible
compatibility group. No existing fact, node, edge, or canonical assignment changed.

## Dashboard impact

None observable. NDIA's own program-level facts are now correctly extracted and safely
loaded, but - like the historical Statement 6/PBS evidence in item 5.4 before its
crosswalk was built - remain structurally unreachable from any dashboard mode until a
future related_breakdown edge deliberately attaches them beneath a non-additive parent
(e.g. the Social Services or Health portfolio's own "National Disability Insurance
Scheme" node), which is out of scope for this repair.

## Remaining work (item 5.5)

This covers only the first of item 5.5's four sub-asks. Still open:

- Produce current unmapped-node coverage by source origin and portfolio (using the
  `_facts_by_origin` per-source-lineage mechanism already built for the coverage audit).
- Improve classifier precision on known malformed published labels (the semantic quality
  audit at `ops/reports/pbs-semantic-quality-audit-20260803T200915Z.md` documents
  `malformed_concatenated_row` and `unknown` classifications recurring across many
  portfolios in the generalized `federal_pbs_programs_all` extractor - a substantial,
  separate engineering task against a 597-line shared extractor, not attempted here).
- Reconsider quarantined rows only with page/table evidence; never bulk promote.
