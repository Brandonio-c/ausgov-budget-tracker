# Dashboard semantic defect — baseline and root cause (Tasks 1–2)

## Task 1 — reproduction

Production audit artifacts already committed at
`ops/reports/dashboard-api-audit-20260803T174511Z.{json,md}` (against
`https://ausgov-budget-api.vibefactory.app`) show the mechanically-clean
but semantically-defective result described in the mission: 6 paths,
16,609 visited nodes, 12,595 citation checks, 0 citation failures, 7/7 PBS
crosswalk cases "reachable".

Confirmed production and the current local `data/facts.db` are the same
underlying data: the 7 PBS crosswalk `fact_id`s and their exact
`sample_child` text in the committed production JSON
(257892/257838/258258/257718/257790/258178/257850) are byte-identical to
local. Re-running the audit against production was started
(`https://ausgov-budget-api.vibefactory.app`, confirmed reachable, HTTP 200
on `/api/health`) but the full 16,609-node remote traversal takes a long
time over the network; local reproduction below is used as ground truth
for root-causing, with production re-confirmed at Task 10.

New script `scripts/ops/dashboard_defect_baseline.py` walks the real API
tree for `federal_actuals_2024_25`, `qld_state_actuals_2024_25`, and
`local_government_actuals_2024_25`, cross-referencing every visited
`fact_id` directly against `facts.db` (source_key, government_level,
jurisdiction, financial_year, measure_type, compatibility_group,
estimate_status) - not just trusting the API's own labels. Output:
`ops/reports/dashboard-defect-baseline-20260803T193102Z.{csv,md}`
(15,559 nodes visited, 13,634 with a suspected defect).

Defect class counts (local reproduction):

| class | count |
|---|---:|
| `cross_government_leak` | 12,098 |
| `cross_year_silent_mismatch` | 11,769 |
| `label_quality_header_or_financial_statement_line` | 3,698 |
| `label_quality_concatenated_numeric_row` | 1,677 |
| `additive_over_100pct` | 1,015 |
| `cross_jurisdiction_leak` | 877 |

(A first draft of this script double-counted "cross_jurisdiction_leak" by
walking the *entire* multi-jurisdiction state-tree response under a single
requested-jurisdiction label - `/dashboard/tree?level=state` legitimately
returns every state as a top-level sibling in one response, it is not a
per-jurisdiction endpoint. Fixed by scoping the walk to the matching
top-level branch before counting; the numbers above are post-fix.)

## Task 2 — root cause

**Manually reproduced the exact production example**: querying
`/v2/dashboard/tree?mode=actuals&level=local&year=2024-25` locally shows,
under *every one* of the 7 states' `Economic affairs` branch, the
identical figures Immigration=$3,758,000,000, Industrial
relations=$1,044,000,000, Labour market assistance to job seekers and
industry=$2,268,000,000 - not per-state local figures, the exact same
national dollar amounts repeated seven times.

**Root cause 1 (primary, confirmed): `resolve_related_parent_node_id()`
in `src/backend/breakdown_graph.py` has no government-level or
jurisdiction scoping at all.**

```python
def resolve_related_parent_node_id(conn, node_name, fact_id):
    ...
    if fact_id:
        nid = primary_node_id(conn, int(fact_id))
        if nid is not None and child_edges(conn, nid, "related_breakdown"):
            return nid          # (A) node's own edges - correctly scoped
    ...
    for cand in candidates:
        row = conn.execute("""
            SELECT n.id FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            JOIN breakdown_edges e ON e.parent_node_id = n.id
              AND e.edge_kind = 'related_breakdown'
            WHERE d.source_key LIKE 'abs_gfs_commonwealth%'   -- (B) always federal
              AND n.name = ?
            LIMIT 1
        """, (cand,)).fetchone()
        if row:
            return int(row[0])   -- fires regardless of caller's level/jurisdiction
```

Called from `attach_related_to_tree()`'s `walk()` in the same file, for
*any* node at *any* level (federal/state/territory/local) whose leaf path
name matches one of `ABS_PURPOSE_RELATED_TARGETS` ("Health", "Education",
"Economic affairs", "Defence", etc.). For a genuine local-government
"Economic affairs" leaf: step (A) fails (a local council's own facts have
no `related_breakdown` edges of their own), so the function falls through
to step (B), which searches unconditionally for a `abs_gfs_commonwealth%`
node named "Economic affairs" - the *federal* Commonwealth GFS purpose
node - with zero awareness that the caller is rendering a local-government
tree for a specific state. It always finds one (Commonwealth Economic
affairs always exists), and `_attach(node, nid, as_folders=False)` then
overwrites the local leaf's children with the federal node's
`related_breakdown` children (Immigration, Industrial relations, Labour
market assistance - real Commonwealth "Other economic affairs"
subfunctions) and its FBO Appendix A children. This is why the exact same
national dollar figures repeat identically under every state.

This is a **pre-existing bug**, not introduced by the PBS → Statement 6
crosswalk milestone - it lives in the original `attach_related_to_tree` /
`resolve_related_parent_node_id` mechanism (used to link ABS-GFS purpose
nodes to Statement 6 and FBO Appendix A detail), which has always lacked
scope awareness. The PBS crosswalk's own edges are not implicated in this
specific contamination (they attach directly to individual PBS program
nodes with a real government_level/jurisdiction of their own - federal -
and are only reached from federal Statement 6 nodes).

Matches directive option: **"API child resolution selects a fact from the
wrong source or level."**

**Root cause 2 (confirmed, secondary): the audit script itself does not
distinguish additive from related children before computing percentages.**

`scripts/ops/dashboard_api_audit.py`'s `_walk()` computed
`pct_of_parent = value / parent_value` for *every* visited node
unconditionally, never inspecting `node.get("breakdown")` (which the API
already returns, including `breakdown.kind == "related_breakdown"` for
non-additive children). This is why "0 citation failures" coexisted with
">100% of parent" and cross-government contamination going undetected:
the audit's own traversal treated every child - additive or related - the
same way. Matches directive option: **"the audit traverses related
navigation as additive hierarchy."**

**Root cause 3 (found while validating the baseline, real and distinct):
`build_same_group_subtree()`'s `allow_nearest_fy=True` path can select a
*later* financial year than the one requested when the exact year is
unpublished for a node** - e.g. a 2024-25 Federal Actuals tree showing a
child fact from 2025-26. Confirmed via 11,769 same_group nodes in the
baseline where `child_financial_year > parent_financial_year` for a
same-family additive edge. This is the "no future-year fallback" rule
Task 7 names, and it affects the underlying Statement 6/PBS same_group
cascade broadly, not only newly-added PBS content.

None of these three causes were patched around at the symptom level (e.g.
by excluding "Economic affairs" from the audit, or by clamping percentages
to 100%) - the underlying `resolve_related_parent_node_id` scope gap, the
audit's edge-kind blindness, and the year-fallback direction are the exact
mechanisms fixed in the commits that follow.
