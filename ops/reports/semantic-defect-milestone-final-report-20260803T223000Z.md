# Semantic-defect milestone — final report

Timestamp: 2026-08-03T22:30:00Z

## 1. Root causes found

1. **Cross-government/local contamination** — `resolve_related_parent_node_id()` /
   `attach_related_to_tree()` (`src/backend/breakdown_graph.py`) correctly
   resolved each node's own `related_breakdown` edges (each jurisdiction's
   local/state "Economic affairs" etc. has its own edges to federal
   Statement 6/FBO reference data, by design), **but `build_related_subtree()`
   only stamped `breakdown.kind` on some of the resulting nodes** — a
   related child with no year fallback of its own, and any `same_group`
   descendant nested beneath it, were emitted with `breakdown: null`. Since
   each node is serialized independently (one tree walk, and separately
   every standalone `/item/{fact_id}/children` call with no parent to
   inherit from), that made a federal fact under a local-government path
   indistinguishable from a real additive fact of that jurisdiction.
2. **The audit itself was blind to edge kind** — `scripts/ops/dashboard_api_audit.py`
   computed `pct_of_parent` and flagged missing depth without ever checking
   `breakdown.kind`, so `related_breakdown` content was evaluated as if it
   were additive.
3. **Future-year fallback** — `fact_for_node_year()`'s nearest-year
   fallback preferred a *later* year over an *earlier* one whenever both
   existed, regardless of distance (confirmed via 11,769 real nodes where
   the served child year was after the requested/parent year).
4. **PBS label quality** — no classification stage existed between PDF
   extraction and publication; the generic ingest gates (`validate.py`
   Gates 1-6) check schema/citation completeness, never label content, so
   table headers, financial-statement lines, and concatenated
   extraction-fragment rows were published as if they were program names.
5. **Two separate PBS ingest paths** — `federal_pbs_programs_all` (this
   session's own crosswalk) and `federal_pbs_programs_s6_bridge` (an older,
   separate ingest path pre-dating it) both exhibited the same label-quality
   problem; only the first was in scope until Task 9's SQL checks surfaced
   the second live on production.
6. **First-split vs last-split label inconsistency** — the reload's label
   gate classified a node_name's first-`" / "`-split remainder, while the
   real UI displays the *last* segment (`display_name()`'s rsplit rule);
   a node_name with more than one `" / "` (e.g. `"Defence / Key cost
   category / workforce"`) could pass the gate on the first-split text
   while still displaying an unclassifiable bare fragment, and that exact
   node was reachable via a live PBS → Statement 6 crosswalk edge.

## 2. Files changed

**Backend:** `src/backend/breakdown_graph.py` (non-additive tagging at
every depth, cross-year fallback policy, bubble-up fallback_reason
correctness), `src/backend/schemas.py` (BreakdownMeta year-fallback
fields).

**Frontend:** `src/frontend/app/HomeClient.tsx` (per-node year-fallback
disclosure), `src/frontend/lib/types.ts` (BreakdownMeta fields) — plus
`src/frontend/lib/*` (9 more files) newly tracked after fixing a
pre-existing `.gitignore` bug that had silently excluded the entire
directory from git since it was created.

**Ingest/ops (new):** `scripts/ops/dashboard_api_audit.py` (rewritten:
per-node scope/jurisdiction/edge-kind/year/citation metadata, 8 hard-failure
buckets, non-zero exit code), `scripts/ingest/pbs_label_classifier.py`
(Task 5 classifier), `scripts/ops/pbs_semantic_quality_audit.py` (Task 6
corpus audit), `scripts/ingest/reload_pbs_programs_all.py`,
`scripts/ops/cleanup_stale_pbs_nodes.py`,
`scripts/ops/cleanup_pbs_s6_bridge_labels.py`,
`scripts/ops/task9_sql_integrity_checks.py`,
`scripts/ops/dashboard_defect_baseline.py`.

**`.gitignore`:** scoped the Python-packaging `lib/`/`lib64/`/`build/`
rules to the repo root (`/lib/` etc.) — the unscoped version was silently
matching `src/frontend/lib/`.

**Tests (new):** `tests/ops/test_dashboard_api_audit.py`,
`tests/unit/test_breakdown_graph_related_tagging.py`,
`tests/unit/test_year_fallback_policy.py`,
`tests/ingest/test_pbs_label_classifier.py`,
`tests/ingest/test_reload_pbs_programs_all.py`,
`tests/ops/test_cleanup_stale_pbs_nodes.py`,
`tests/ops/test_cleanup_pbs_s6_bridge_labels.py`. **Tests updated:**
`tests/api/test_breakdown_related.py` (3 tests asserted the old,
future-year-preferring behaviour as if correct; updated to assert the
corrected, mission-required behaviour).

## 3. Database before/after counts

| metric | before | after |
|---|---:|---:|
| facts | 321,950 | 285,574 |
| nodes | 230,391 | 222,798 |
| fact_nodes | 321,950 | 285,574 |
| breakdown_edges | 33,756 | 14,183 |
| federal_pbs_programs_all facts | 53,083 | 17,508 |
| federal_pbs_programs_all nodes (total, incl. portfolio-folder navigation nodes with no fact of their own) | 9,817 | 2,999 |
| federal_pbs_programs_s6_bridge facts | 1,273 | 472 |
| PBS → Statement 6 crosswalk edges | 16,365 | 5,119 |
| quarantine (facts_pending_attribution) | 15 | 36,391 |
| non-PBS-family facts | 267,594 | 267,594 (byte-identical, verified directly) |

(Final counts reflect the last-split classifier fix and the 4-node
empty-folder cleanup from Task 9, run after the Task 8 commit's own
recorded numbers - re-verified directly against `data/facts.db` for this
report, not copied from earlier intermediate JSON snapshots.)

## 4. PBS accepted/rejected/quarantined counts

`federal_pbs_programs_all` (final classifier, last-split label rule):
34,080 published / 69,865 quarantined of 103,945 total rows classified —
program 33,426 + outcome 8 + component 646 = 34,080 accepted;
malformed_concatenated_row 26,772, table_header 20,289, financial_statement_line
10,443, narrative_fragment 6,481, subtotal 5,171, unknown 709 rejected.

`federal_pbs_programs_s6_bridge`: 472 published / 801 quarantined of
1,273 total.

Full corpus-quality audit (Task 6, `ops/reports/pbs-semantic-quality-audit-20260803T200915Z.{csv,md}`,
run read-only before any write): 17,525/53,083 (33%) accepted. The first
reload pass (Task 8, first-split label rule) published exactly 17,525
distinct facts, confirming the audit and the live gate agreed. Task 9's
follow-up fix (classify the *last* displayed segment, not the first-split
remainder - §1 item 6) then correctly re-rejected 3 further nodes whose
first-split text had passed but whose actually-displayed final segment
had not; the distinct fact count after that fix is 17,508 (§3), and the
row-level classification counts immediately above are from that final,
corrected pass.

## 5. Graph before/after counts

See §3. Additionally: 6,815 stale `federal_pbs_programs_all` leaf nodes
and 18,053 stale edges removed after the reload (Task 8); 771 stale
`federal_pbs_programs_s6_bridge` nodes and 1,509 stale edges removed; 4
further empty portfolio-folder nodes (zero facts, zero edges) removed
directly after Task 9's SQL check found them. Both PBS reload+cleanup+crosswalk
sequences were run 4 times total across this milestone to prove
idempotency; every re-run after the first inserted/removed zero facts,
nodes, or edges beyond the intended replacement.

## 6. Local audit result

Final local run: **1 hard failure** (down from 32,178 at the pre-Task-4
baseline) — a single `additive_reconciliation_failures` entry,
fact_id 337001 "Defence / Key cost category / OPERATING", 100.52% of
parent. Confirmed as a genuine PBS source-document rounding
characteristic (a real, tiny over-100% artifact in the underlying Defence
PBS table), not a scope, label, or year defect — documented as an
accepted residual rather than hidden by weakening the threshold. All
other buckets (scope, jurisdiction, edge_kind, cross_year, label_quality,
citation, transport) are zero across all 6 required paths. 7/7 PBS →
Statement 6 crosswalk cases reachable, non-additive, cited, and
amount-preserving. `pytest tests -q`: 174 passed. `npm run build`: passes.
Playwright (`src/frontend`, 16 tests across `dashboard.spec.ts`,
`pbs-s6-crosswalk.spec.ts`, `pbs-year-fallback.spec.ts`): 16 passed.

## 7. Production audit result

Identical to local: **1 hard failure**, same fact/reason, 0 everywhere
else, 7/7 crosswalk cases reachable/cited/amount-preserving. Backend
origin (Docker, behind `ausgov-budget-api.vibefactory.app`) rebuilt and
restarted; frontend deployed to `vibefactory.app/ausgov-budget-tracker`
via wrangler. All 6 named production dashboard views (Federal Actuals,
Federal Budget, QLD state actuals, local-government actuals, federal
debt, GDP/ratios) and the 7 PBS detail cases manually verified directly
against the live API — see `ops/reports/task10-production-verification-20260803T222222Z.md`.

## 8. pytest result

174 passed, 0 failed (final run, against the fully rebuilt database).

## 9. Frontend build result

`npm run build` (Next.js static export): passes, no TypeScript errors.

## 10. Playwright result

16/16 passed (7 `dashboard.spec.ts`, 7 `pbs-s6-crosswalk.spec.ts`, 2 new
`pbs-year-fallback.spec.ts`).

## 11. Reconciliation result

`ingestion_coverage_audit.py`, `ingestion_coverage_lineage.py` (updates
`federal_pbs_programs`'s tracked count from 54,431 to 18,072, reflecting
the rebuild), `quarantine_report.py`, `revenue_reconciliation.py`,
`debt_reconciliation.py`: all ran clean; all pre-existing non-PBS
reconciliation checks unaffected. New `task9_sql_integrity_checks.py`:
duplicate_breakdown_edges 0, orphan_facts 0, orphan_edges 0,
cross_government_additive_edges 0, cross_jurisdiction_additive_edges 0
(checked system-wide, not just the 6 audited paths — confirms Task 4's
fix holds globally), pbs_crosswalk_children_with_rejected_labels 0,
pbs_children_missing_source_year 0. Two **pre-existing, out-of-scope**
findings surfaced by these new checks and **not fixed** (per "do not
alter non-PBS facts"): 5 duplicate facts in
`vic_local_govt_financial`/`qld_qgip_expenditure`, and 278 orphan nodes
across several state-debt datasets (`nsw_tcorp_*`, `qld_qtc_*`,
`vic_tcv_*`, `wa_watc_*`, `sa_safa_*`, `nt_nttc_*`, `tas_tascorp_*`) —
recommended for a future, separate milestone.

## 12. Focused commits created

9 commits on `main`, not yet pushed:

1. `154899e` docs(ops): reproduce production dashboard defects and root-cause the local-government contamination (Tasks 1-2)
2. `d8c8733` test(audit): add dashboard scope and semantic invariants (Task 3)
3. `6844a65` fix(dashboard): prevent cross-government additive traversal (Task 4)
4. `86f0525` feat(ingest): classify and quarantine malformed PBS rows (Task 5)
5. `e585325` feat(ingest): audit the full PBS corpus with the label classifier (Task 6)
6. `c6f8674` fix(hierarchy): expose explicit PBS year fallback metadata (Task 7)
7. `bdebd2f` feat(ingest): back up and rebuild PBS data with the corrected classifier (Task 8)
8. `915732c` test(audit): full validation pass and a real classifier bug found via new SQL integrity checks (Task 9)
9. `72a7148` docs(ops): deploy to production and verify (Task 10)

## 13. Unresolved limitations

- One 0.52%-over-parent additive-reconciliation case remains (Defence PBS
  "Key cost category / OPERATING" same_group rollup) — a genuine
  source-document rounding characteristic, not a scope/label defect.
- Two pre-existing, out-of-scope defects found (not fixed, per "do not
  alter non-PBS facts"): 5 duplicate facts and 278 orphan nodes in
  unrelated state-debt/local-government datasets (§11).
- The PBS label classifier is deterministic and evidence-based but not
  perfect on every edge case in a 100K+-row real-world corpus; residual
  `unknown` rows (709 in `federal_pbs_programs_all`) are conservatively
  excluded from the crosswalk rather than guessed into it, per the
  mission's own instruction, and are available for manual review in
  `ops/reports/pbs-semantic-quality-audit-20260803T200915Z.csv`.
- Frontend per-child year-fallback disclosure is wired through interactive
  hover/click and search-deep-link paths; it has not been re-verified
  against every possible chart type (pie/rings/bar) individually beyond
  the Playwright coverage added.

## 14. Working tree cleanliness

Clean. `git status --short` returns nothing. `data/facts.db` was never
committed (verified via `git status`/`.gitignore` throughout).

## 15. Exact command to push `main`

```
git push origin main
```
