# Federal depth & visualization remediation — mission reopen

Generated: 2026-08-20T151500Z (started)
Repository: `ausgov-budget-tracker`, branch `main`

## Purpose

A new, much broader mission-reopen directive was issued: the ledger's "complete" status on
earlier plan items does not by itself mean the live product satisfies the actual mission.
The directive identifies specific live-product failures (Social Security appearing depth-1
while the dashboard reports "6 of 6" safe levels; canonical/related visual conflation;
misleading global depth metrics; top-level folding; unstable colours; stale hover metadata;
opaque branch coverage; taxonomy changes not disclosed) and a large follow-on data-depth
program (DSS PBS components, NDIS, Defence, Education, Health depth).

This report tracks that reopened work as it proceeds, loop by loop. It supersedes no
existing report; it is additive documentation for a genuinely new phase of work.

**Standing constraint carried over unchanged from every prior phase of this program:**
production deployment (rebuilding/restarting the live `ausgov-budget-tracker-backend-1`
Docker container, or redeploying the frontend) remains a human decision this autonomous
loop does not trigger itself, per the CRITICAL note at the top of
`ops/reports/data-remediation-progress.md`. This is unchanged by the new directive's own
deployment section - a live, user-facing, comparatively hard-to-reverse action requires an
explicit human decision, and that safety rule takes precedence.

## Loop 1: P0 — Social Security / Social Protection crosswalk resolution

### Observe

Reported symptom: FY2025-26 Federal Actuals shows "Social security and welfare" (by far one
of the largest expenditure functions) with essentially no depth, despite the dashboard's own
depth counter reporting "6 of 6" safe levels overall - implying the global maximum is being
driven by an unrelated, narrow branch while the largest function dead-ends immediately.

### Diagnose

Dispatched a read-only investigation subagent (no code edits) to trace the actual runtime
behavior before touching anything. Findings, independently reproduced below:

1. **The declarative crosswalk config is correct and complete.**
   `config/breakdowns/crosswalks/cofog_to_budget_function.yaml` maps every relevant ABS
   COFOG purpose name to its Australian Government budget-function equivalent, with an
   explicit `quality: exact` or `quality: approx` flag per mapping - including the exact
   mapping the bug report named:
   ```yaml
   - abs: Social protection
     budget: Social security and welfare
     quality: approx
   ```
   Also present: Recreation, culture and religion ↔ Recreation and culture (approx);
   Economic affairs ↔ Other economic affairs (approx); Transport ↔ Transport and
   communication (approx); Environmental protection ↔ Housing and community amenities
   (approx, alongside Housing's own exact self-mapping).

2. **The live resolver never reads this file at all.** `resolve_related_parent_node_id()`
   in `src/backend/breakdown_graph.py` (pre-fix, lines 709-715) used its own independent,
   4-entry hardcoded dict:
   ```python
   aliases = {
       "health": "Health",
       "education": "Education",
       "defence": "Defence",
       "general public services": "General public services",
   }
   ```
   Every one of these 4 happens to be a case where the ABS purpose name and the budget
   function name are already identical strings - meaning this dict was never actually
   performing crosswalk translation, only case-normalization for names that didn't need
   translation in the first place. Any function requiring a genuine APPROX crosswalk
   translation (a different string on each side) silently failed to resolve, returning
   `None`, and the caller then attached zero related children.
   `grep -rn "cofog_to_budget_function" src/` confirmed the YAML is referenced only from
   offline ingest/audit scripts (`scripts/ingest/breakdown_pack.py`,
   `scripts/ingest/breakdown_coverage.py`, `scripts/ops/fbo_archive_crosswalk_audit.py`) -
   zero references anywhere under `src/backend/` before this fix.

3. **Live confirmation against the running production container** (port 8010, before any
   fix): `GET /v2/dashboard/tree?mode=actuals&level=federal&year=2025-26` returned 0
   children for Social security and welfare, Recreation and culture, Other economic
   affairs, and Transport and communication - the exact 4 functions requiring an approx
   crosswalk translation whose ABS name differs from its budget name - while
   Health/Education/Defence/General public services (the 4 hardcoded, identically-named
   cases) all returned real related depth.

### Fix

Added a small, cached crosswalk loader to `src/backend/breakdown_graph.py`
(`_cofog_crosswalk_path()` / `_budget_to_abs_purpose()`), mirroring the exact
repo-checkout-vs-Docker-mount path-resolution pattern already established in
`src/backend/edge_set_policy.py`. It reverse-indexes the real YAML file's `mappings` list
into `{budget_name.lower(): abs_purpose_name}`, with exact-quality mappings taking priority
over approx ones when more than one ABS purpose maps to the same budget function (handles
the Environmental-protection-vs-Housing's-own-exact-self-mapping case correctly - verified
directly, see Verify below).

Replaced the 4-entry hardcoded `aliases` dict in `resolve_related_parent_node_id()` with a
single lookup into this new function. No other logic in the resolver changed -
`ABS_PURPOSE_RELATED_TARGETS` already listed every affected purpose name and did not need
changes; per-edge `match_quality` is derived from each edge's own `notes` field at walk time
(`match_quality_from_notes()`, unchanged), not from this resolver, so quality labeling was
never part of this specific defect.

### Verify

**Unit-level**, against the real config file (not a mock):
```
'defence'                       -> 'Defence'
'education'                     -> 'Education'
'general public services'       -> 'General public services'
'health'                        -> 'Health'
'housing and community amenities' -> 'Housing and community amenities'   # exact wins over the competing approx "Environmental protection" mapping
'other economic affairs'        -> 'Economic affairs'
'public order and safety'       -> 'Public order and safety'
'recreation and culture'        -> 'Recreation, culture and religion'
'social security and welfare'   -> 'Social protection'
'transport and communication'   -> 'Transport'
```

**Direct DB-level**, `resolve_related_parent_node_id()` called against the real live
`data/facts.db` (no test doubles):

| Budget function | related_children before | related_children after |
| --- | --- | --- |
| Social security and welfare | 0 | 17 |
| Recreation and culture | 0 | 10 |
| Other economic affairs | 0 | 13 |
| Transport and communication | 0 | 13 |
| Health (already worked) | 15 | 15 |
| Education (already worked) | 17 | 17 |
| Defence (already worked) | 3 | 3 |
| General public services (already worked) | 8 | 8 |
| Housing and community amenities (already worked) | 8 | 8 |

Zero change to any previously-working function; all 4 previously-broken functions now
resolve.

**Live API-level**, a fresh local backend process started from the current repo checkout
(NOT the live production container - `PYTHONPATH=src`, real `data/facts.db`, port 8099,
stopped cleanly after the check) serving the real `GET /v2/dashboard/tree` endpoint:

FY2025-26 Federal Actuals, top-level Commonwealth children (18 functions):
```
Agriculture, forestry and fishing        children=0   (not in crosswalk - genuine, no bug)
Contingency reserve                      children=0   (not in crosswalk - genuine, no bug)
Defence                                  children=1
Education                                children=8
Fuel and energy                          children=0   (not in crosswalk - genuine, no bug)
General public services                  children=1
General purpose inter-government transactions children=0  (not in crosswalk)
Health                                   children=7
Housing and community amenities          children=3
Mining, manufacturing and construction   children=0   (not in crosswalk)
Natural disaster relief                  children=0   (not in crosswalk)
Nominal superannuation interest          children=0   (not in crosswalk)
Other economic affairs                   children=6   <- FIXED (was 0)
Public debt interest                     children=0   (not in crosswalk)
Public order and safety                  children=2
Recreation and culture                   children=4   <- FIXED (was 0)
Social security and welfare              children=8   <- FIXED (was 0)
Transport and communication              children=6   <- FIXED (was 0)
```

Drilling into "Social security and welfare" in the live response shows real depth now
reachable: `Social security and welfare → Assistance to the aged → Aged care services →
Aged Care Services → {Social Support - Group, Social Support - Individual, CHSP Transport,
...}`, each with further children (11 each), down to individual funded-organization line
items (e.g. "Community Transport Services Tasmania Ltd"). This is genuine PBS/recipient-
level related detail that was already present in the graph and already correctly attached
to the "Social protection" ABS purpose node - it was purely unreachable from the budget-
function name before this fix.

The 8 functions still showing 0 children (Agriculture/forestry/fishing, Contingency
reserve, Fuel and energy, General purpose inter-government transactions,
Mining/manufacturing/construction, Natural disaster relief, Nominal superannuation
interest, Public debt interest) are **not** part of this defect - none of them appear in
the crosswalk file at all, meaning no ABS GFS purpose was ever mapped to them and no
related_breakdown edges exist for them in the graph. This is a genuine, truthful dead end
(per the mission directive's own "high-value dead-end" framework), not a resolver bug -
tracked as a separate, later investigation item, not conflated with this fix.

### Tests

New file `tests/unit/test_breakdown_graph_cofog_crosswalk.py` (5 tests): the crosswalk
loader resolves all 4 previously-broken functions, still resolves the 4
originally-working exact matches, exact-quality wins over a competing approx mapping, a
fixture-DB integration test proving `resolve_related_parent_node_id("Social security and
welfare", ...)` now returns the real "Social protection" node, and an unmapped-name
fall-through test (no silent wrong match). Full backend suite: 848 passed (843 baseline +
5 new), 0 regressions.

### Data/graph impact

None - this is a pure code fix. No migration, no facts.db mutation, no new nodes or edges.
The related_breakdown edges these 4 functions now correctly reach were already present in
the graph (loaded by earlier, already-complete milestones); this fix only corrects which
node the live API resolver looks them up under.

### Deployment status

**Not yet deployed to the live production container.** The container's compose file
(`docker-compose.vibefactory.yml`) builds the backend image from `./src/backend` - a code
change requires `docker compose -f docker-compose.vibefactory.yml up --build -d` (an image
rebuild), not merely a container restart, since `src/backend` is baked into the image while
only `config/` and the data files are bind-mounted read-only. This rebuild is the exact
"live, user-facing, comparatively hard-to-reverse action" this program has deliberately
never triggered itself since before commit `dde1c08` - continuing that same standing
constraint here. The fix is code-complete, tested, and verified against real production
data via a disposable local process; it is staged and ready for the next authorized
redeploy, alongside every other pending backend code change this program has accumulated.

### Next

Continue the loop into the next P0 item: audit "Canonical actual" filtering in
`src/frontend/lib/sunburstTree.ts` and the backend projection logic for whether related
(non-additive) branches can silently enter the canonical additive sunburst.
