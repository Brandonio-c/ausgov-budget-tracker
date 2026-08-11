# Historical Treasury PBS program detail under Statement 6 (item 5.4, part 2)

Generated: 2026-08-11T22:12:43Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 5.4, prerequisite 2: an exact-only `related_breakdown` edge set exposing the
now-loaded historical Treasury PBS program facts (5.3, wired into `facts.db` in the prior
milestone) beneath their matching edition's Statement 6 function node. Satisfies the Wave
3 exit gate: "at least one 2022-23 and one 2023-24 representative function has a verified
function -> subfunction/component -> PBS-program route, with exact edition metadata, no
future fallback and complete citations."

## Design

Reused the already-reviewed portfolio-ownership assessment from
`config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml` (the current-edition
crosswalk): "Treasury -> General public services, confidence: medium, evidence:
portfolio_ownership" - Commonwealth portfolio-to-COFOG-function ownership is a structural
government-classification fact, not something that changes between budget editions.
Deliberately did **not** reuse the current-edition *bridge extractor*
(`scripts/ingest/extractors/pbs_programs_s6_bridge.py`), which classifies via an
unreviewed portfolio-substring heuristic table and remaps PBS rows directly onto
Statement 6 paths as if additive - exactly the "infer missing hierarchy from label
similarity alone" pattern the plan's non-negotiable rules warn against.

New files:

- `config/breakdowns/crosswalks/historical_pbs_treasury_under_statement6.yaml`: two
  edition-locked pairings (March 2022-23 PBS <-> March 2022-23 Statement 6; 2023-24 PBS
  <-> 2023-24 Statement 6). Each PBS edition can only ever pair with its own Statement 6
  edition, even though both publish an identically-named "General public services" node -
  no cross-edition mixing is structurally possible.
- `config/breakdowns/edge_sets.yaml`: new `historical_pbs_treasury_under_statement6`
  policy - `edge_kind: related_breakdown`, `projection_policy: augment`,
  `fallback_policy: exact_only`, `presentation_role: data`, scoped by
  `source_key_prefixes` to only the two historical PBS sources.
- `scripts/ingest/historical_pbs_s6_crosswalk.py`: idempotent edge builder
  (`INSERT OR IGNORE`, default dry-run, `--apply` to commit). Attaches directly to each
  PBS *program*-level node (not a shared folder), matching the precedent set by
  `pbs_s6_crosswalk.py`, since `fact_for_node_year()` requires the related child to carry
  a real fact directly.

### A second defect found and fixed before deployment

The first program-node selection query (`NOT LIKE '%/ Administered /%' AND NOT LIKE
'%/ Departmental /%'`) returned 42 "programs" for the 2023-24 edition instead of the
expected 39. Investigation found the National Housing Finance and Investment Corporation
publishes its PBS table without the usual Administered/Departmental scope headers (using
`scope="Unscoped"` per the item-5.3 extractor), so three of its *component* rows slipped
past the literal-substring filter and would have been wired in as if they were whole
programs. Fixed by selecting on exact path-segment count (`name.count(" / ") == 3`,
matching the extractor's fixed `_rows()` category shape) instead of excluding specific
scope literals - verified to return exactly 43 and 39 program nodes for the two editions,
matching item 5.3's own validated program counts.

## Validation

- Dry run (default, rolls back): 82 edges would be inserted (43 + 39), 0 skipped.
- Disposable-copy `--apply`: 82 edges inserted; a second `--apply` run inserted 0 (fully
  idempotent). `task9_sql_integrity_checks.py`: 0 hard failures. `dashboard_depth_audit.py
  --check-fixture`: every one of the 10 required projections byte-identical to the
  reviewed baseline; only the database path and `graph.edge_count` (14,253 -> 14,335,
  exactly +82) differed.
- Live API check (FastAPI `TestClient` against the disposable copy):
  `/v2/dashboard/item/{fact_id}/children?year=2022-23` for the March-edition "General
  public services" fact returned all 43 Treasury programs, each with
  `relationship.fallback_reason == "exact_year_match"`, `is_year_fallback == False`, the
  correct `source_key`/`compatibility_group`, and a banner explicitly warning the amounts
  "must not be summed into the parent pie slice." The 2023-24 edition returned 39.
  Requesting a year present in *neither* source (`2020-21`) returned `kind: "empty"` with
  zero children - confirmed no nearest-year or future-year fallback leaks through.
- `mode=budget` root totals for FY2022-23/2023-24 confirmed unchanged
  ($1,629,222,000 / $1,818,520,572,000) - edges are only reachable via the
  drill-down `/item/{id}/children` route, never the base `/tree` walk.
- Live deployment: backup taken first (`facts-20260811T220604Z.db`). 82 edges applied;
  second `--apply` run inserted 0. `task9_sql_integrity_checks.py`: 0 hard failures.
  `dashboard_depth_audit.py --check-fixture`: confirmed the same, sole, reviewed
  `graph.edge_count` delta; fixture updated and re-verified `fixture_matches: true`.
- New regression suite:
  [`tests/api/test_historical_pbs_s6_crosswalk.py`](../../tests/api/test_historical_pbs_s6_crosswalk.py),
  7 passed - edge counts per edition, no cross-edition mixing, exact-year citations on
  every child, no-fallback-for-uncovered-year, and root-total isolation.
- Full backend suite: 622 passed both before and after this milestone (ran once with the
  fact-loading changes only, once including this crosswalk's new tests), 0 regressions.
  `ruff check` on both new Python files: passed.

## Data impact

`data/facts.db`: +82 `breakdown_edges` rows (all `edge_kind='related_breakdown'`,
`crosswalk_id='historical_pbs_treasury_under_statement6'`). No fact, node, or existing
edge changed. `tests/fixtures/dashboard_projection/baseline.json`: the single reviewed
`graph.edge_count` field updated from 14,253 to 14,335.

## Dashboard impact

For the March 2022-23 and 2023-24 Statement 6 editions' "General public services"
function, a user can now drill into the Treasury portfolio's 43 (March) or 39 (2023-24)
individual program totals as clearly-labeled, non-additive related evidence, each with
exact-year citation back to the source PBS PDF. The canonical Statement 6 function total
itself is unchanged; no other portfolio or Statement 6 function gained related detail from
this milestone.

## Remaining risks

Scope is deliberately narrow (Treasury portfolio, two editions, function-level only,
satisfying the Wave 3 exit gate's "at least one" requirement) rather than a full-portfolio
rollout. Extending coverage to other portfolios/editions, or to subfunction-level
precision, is future work and should reuse this same edition-locked pairing pattern
against the already-reviewed `pbs_programs_all_under_s6.yaml` evidence rather than
re-deriving new portfolio assignments. October 2022-23 is not yet covered (no defect - the
scope was chosen to satisfy the exit gate with two editions, not three).
