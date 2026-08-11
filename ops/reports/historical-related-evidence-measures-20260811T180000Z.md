# Historical Statement 6/PBS fact loading and a critical additivity defect (item 5.4, part 1)

Generated: 2026-08-11T18:00:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 5.4 (crosswalk historical PBS beneath matched Statement 6 nodes). This
report covers the first of 5.4's two prerequisites identified in the prior session's
ledger note: loading the staged historical Statement 6 (item 5.2) and Treasury PBS
(item 5.3) facts into `data/facts.db`. The second prerequisite - the actual exact-only
crosswalk edges - remains open; see "Remaining work" below.

## Critical finding

Both the Statement 6 mapping YAMLs (from item 5.2, marked `deployment_status:
adapter_only_pending_graph_visibility`) and the item-5.3 PBS extractor's natural mapping
used `measure_type: budget_estimate`, matching the *same* `compatibility_group:
budget_expense` as every other budget-basis fact. `src/backend/routers/v2/dashboard.py`'s
`_fact_rows()` selects mode='budget' base facts with a bare
`WHERE m.compatibility_group = 'budget_expense' AND ... AND f.financial_year = ?` and
**no per-source de-duplication or canonical restriction** - it additively sums every
matching fact from every loaded source for that year.

Statement 6 (function-level) and Treasury PBS (entity/program-level) both represent
near-complete views of the *same* underlying commonwealth expenditure for a given year.
Loading either family this way, verified independently on a disposable database copy:

| Change tested | `federal_budget_2022_23` root total | `federal_budget_2023_24` root total |
| --- | ---: | ---: |
| Baseline (reviewed fixture) | $1,629,222,000 | $1,818,520,572,000 |
| + PBS only | $714,112,682,000 | $2,552,022,474,000 |
| + Statement 6 only | $2,336,563,222,000 | $4,125,807,572,000 |
| + both (original attempt) | $3,049,046,682,000 | $4,859,309,474,000 |

This is a direct violation of the plan's non-negotiable rule "Never sum incompatible
categories, compatibility groups, accounting bases, measures, vintages, or units" -
loading either historical family under `budget_expense` would have silently ~2-3x'd the
displayed federal budget total for real users. This defect was caught entirely on a
disposable copy before touching the live database, per this program's required database
discipline.

Root cause investigation: `compatibility_group` segregation is the actual mechanism that
keeps every other family-specific measure (e.g. `vic_afs_expense`, `tas_ggs_expense`)
from leaking into federal modes today - not any node-name or source-key exclusion. The
one exception, historical FBO (item 4.2), stays safe under `mode='actuals'` by an
entirely different route (edge-based `attach_related_to_tree`), which `mode='budget'`
does not call at all today.

## Fix

Added migration `018_historical_related_evidence_measures.sql`, registering two new
measures with their own compatibility groups (matching the established one-measure-one-
group convention from migration 016's `vic_output_total_cost`):

- `historical_bp1_statement6_expense` (Statement 6 rows)
- `historical_treasury_pbs_program_expense` (PBS rows)

Both set `additive_across_nodes = 0` and `root_total_allowed = 0`, and neither shares a
compatibility group with any mode currently queried by `_fact_rows` (`actual_expense`,
`budget_expense`, `gfs_liability`, `gfs_revenue`, `gdp`). This makes them structurally
invisible to every existing mode's raw fact walk while remaining reachable by node ID for
a future exact-only `related_breakdown` edge set (`breakdown_graph.fact_for_node_year`
orders by compatibility-group preference but does not exclude other groups - verified by
reading its query directly).

Updated all six mapping YAMLs (3 Statement 6 from item 5.2, 3 PBS from item 5.3) to use
the new measure types, and changed their `deployment_status` from
`adapter_only_pending_graph_visibility` to `related_evidence_exact_only`.

## Validation

- Disposable-copy dry run (before touching the live database): all 6 mappings loaded
  710/675/620/765/616/765 facts respectively, 0 quarantined; a second run confirmed
  idempotency (fact count unchanged: 289,268); `canonical_dataset_id` stayed null for all
  6 sources; `task9_sql_integrity_checks.py` reported 0 hard failures;
  `dashboard_depth_audit.py --check-fixture` reported **byte-identical** results to the
  reviewed golden fixture for all 10 required projections (root totals, depths, branch
  counts, citations - everything) except the `database` path field itself.
- Live deployment: `scripts/ops/backup_facts_db.py` snapshot taken first
  (`/home/vibe-server/backups/ausgov-budget-tracker/facts-20260811T175309Z.db`,
  baseline 285,117 facts). Migration 018 applied cleanly (checksum-tracked, idempotent).
  All 6 mappings loaded live: 285,117 → 289,268 facts (+4,151, exactly matching the
  disposable-copy delta). `task9_sql_integrity_checks.py`: 0 hard failures.
  `dashboard_depth_audit.py --check-fixture`: **`fixture_matches: true`**, 0 hard
  failures - the live dashboard projection is unchanged in every respect.
- New regression suite: [`tests/api/test_historical_related_evidence_isolation.py`](../../tests/api/test_historical_related_evidence_isolation.py),
  5 passed - asserts the new measure types can never anchor a root total (schema-level),
  that the 6 new sources carry zero canonical-dataset assignment, and that a live API call
  to `/v2/dashboard/tree?mode=budget&level=federal&year=2022-23` (and `2023-24`) returns
  exactly the pre-existing root total.
- Full backend suite before and after live deployment: 617 passed both times, 0
  regressions.

## Data impact

`data/facts.db`: +2 `measure_definitions` rows, +4,151 facts (all under the two new,
mode-invisible compatibility groups), 0 changes to any existing fact, edge, or canonical
assignment. Backup taken before the write; before/after counts and dashboard-projection
fixture comparison both confirmed byte-for-byte parity outside the intended new rows.

## Remaining work

The facts are now safely loaded but **not yet reachable from the dashboard** - by design,
their compatibility groups make them structurally inert until an explicit edge set
attaches them. Completing item 5.4 requires:

1. A declarative `related_breakdown` edge set (mirroring `config/breakdowns/edge_sets.yaml`'s
   existing conventions) matching specific Statement 6 function/subfunction nodes to their
   corresponding historical PBS program nodes, by exact node name and year - not the
   substring/heuristic portfolio-to-function guess table used by the existing *current*-edition
   `scripts/ingest/extractors/pbs_programs_s6_bridge.py` bridge, which the plan's "never infer
   missing hierarchy from label similarity alone" rule argues against reusing for new work.
2. Extending `src/backend/routers/v2/dashboard.py::dashboard_tree()` to call
   `attach_related_to_tree` (or an equivalent) for `mode == "budget"`, since today it only
   calls `apply_edge_cascade_to_budget_tree` (same_group only) for that mode -
   `attach_related_to_tree` itself is generic and edge-registry-driven, but wiring it into the
   budget-mode code path is a live-API behavior change requiring its own test coverage.
3. Per the plan's Wave 3 exit gate, this can be scoped to one verified 2022-23 and one
   2023-24 representative function/program route rather than full portfolio coverage.

Not yet started; recorded as the immediate next item in the progress ledger.
