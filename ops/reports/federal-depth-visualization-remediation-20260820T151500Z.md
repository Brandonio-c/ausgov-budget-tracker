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

## Loop 2 — P0: "Canonical actual" silently absorbing related sunburst children (fixed, not yet deployed)

Commit: `2bddc08`

### Observe

With Loop 1's crosswalk fix live locally, "Social security and welfare" became reachable
for the first time — but reachable data is not the same as *correctly labeled* data.
Inspecting `additiveChildren()` in `src/frontend/lib/sunburstTree.ts` showed it gated
exclusion of related data on a folder-shape / `presentation_role` heuristic ("does this
node look like a navigation folder?"), not on `branch_kind` itself. `Social security and
welfare`'s Statement 6 children are attached as **bare siblings directly on the leaf** (no
wrapping folder) — the exact shape `attach_related_to_tree()`'s "leaf exposes first
declared related family directly" branch produces when a GFS purpose has zero native
additive sub-breakdown. That shape passed the old folder-shape check and would have
rendered as if it partitioned the canonical additive total, with `scaleToSum()` forcing the
children's raw dollar sum to visually equal the parent — a false quantitative partition of
data that is not, in fact, additive.

### Diagnose

Read `attach_related_to_tree()` (`src/backend/breakdown_graph.py:840+`) end to end to
confirm the bare-sibling shape is deliberate backend behavior for purposes with no native
additive breakdown (not a mistagging bug to fix upstream). Confirmed via a fixture-driven
unit test that the *old* `additiveChildren()` returned these bare `branch_kind: "related"`
siblings as if additive, and that naively excluding all related nodes without also fixing
`relatedFolderChildren()` would make this same data completely unreachable via the related
branch selector — a regression, not a fix.

### Implementation

`src/frontend/lib/sunburstTree.ts`:
- `additiveChildren()`: excludes any child with `branch_kind === "related"`
  unconditionally (plus the pre-existing legacy `related_breakdown` check), regardless of
  folder shape or `presentation_role`.
- `relatedFolderChildren()`: rewritten to recognize both folder-wrapped related data
  (existing behavior) **and** bare-sibling related data attached directly on a leaf (new),
  so tightening `additiveChildren()` does not orphan this data from the related branch
  selector.
- `unwrapSameName()`: gained a `childrenOf` parameter (default `additiveChildren`, used by
  the canonical call site) because it is also called from the related cascade in
  `nestableChildren()`, which must not re-exclude a node it already knows is
  `branch_kind: "related"`. Related call site now passes a new `positiveChildren()` helper
  (filters on `value > 0` only).

### Tests

`src/frontend/scripts/test-chart-semantics.mjs`: two new assertions using a fixture
purpose ("Social protection", $286,605, two bare `branch_kind: "related"` /
`branch_family: "statement_6"` children) proving (a) canonical mode renders it as a leaf
with `children === undefined` — no fabricated additive depth — and (b) the `statement_6`
related branch still returns both children, correctly labeled `branch_kind: "related"`.
`npm run test:unit`: all cases pass, including the pre-existing `fboRings` case that
exercises the same `unwrapSameName()` path (this caught the `childrenOf` regression during
development — see below). `npx tsc --noEmit -p .`: clean. `npm run build`: succeeds.
`npm run lint:ci`: 25 errors / 13 warnings, confirmed via `git stash` / `git stash pop` to
be pre-existing baseline drift (24-error baseline) unrelated to this change — all errors
are in files this fix does not touch (`FactCitationViewer.tsx`, `GlobalSearchBar.tsx`,
`SpendingChart.tsx`, two unrelated `tests-e2e/*.spec.ts` files).

Caught during development: the first version of the `additiveChildren()` fix alone broke
the existing `fboRings` test (`fboRings.data[0].children[0].name` returned `"Health"`
instead of `"Audited subfunction"`) because `unwrapSameName()` always called
`additiveChildren()` internally regardless of which branch called it — harmless under the
old loose check, but wrong once the check correctly started excluding related leaves. Fixed
by parameterizing `unwrapSameName()`'s child-selection function per call site, then
re-ran the full unit suite to confirm the regression was resolved.

### Browser verification

Rebuilt the frontend (`next build`, `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8099`) and
served the static export from a correctly-symlinked `ausgov-budget-tracker/` path (Next's
`basePath` requires the app be reached at `/ausgov-budget-tracker/`, not the server root —
serving from the parent directory and navigating to that path was the fix for an earlier
`ERR_ABORTED`/hydration failure). Ran against a fresh local backend on port 8099 (never the
production container). Playwright + full-page screenshots for FY2025-26:

- **Canonical actual** (default branch): "Social security and welfare" renders as a single
  wedge with "Safe levels: of 1 · default 1" — confirming it is correctly reported as a
  leaf with no fabricated additive depth.
- **Budget Statement 6** (related branch, selected via the "Ring branch" button group):
  same top-level view, but "Safe levels" changes to "of 3 · default 3" — confirming real,
  reachable depth exists and is now correctly exposed only under the related branch, not
  folded into canonical.
- 0 browser console errors in both states.

### Data/graph impact

None — pure frontend code fix. No migration, no facts.db mutation, no backend change.

### Deployment status

**Not yet deployed.** Same standing constraint as Loop 1: this is a frontend static-export
change requiring an authorized rebuild/redeploy of the production frontend, which this
program continues to treat as a human-authorized action. Verified end-to-end against a
disposable local static export + local backend only.

### Next

Continue the loop into the next P0 item: replace the single global `maxVisibleDepth()`
number with per-function depth metrics (canonical additive max depth, related max depth,
spend-weighted median depth, coverage thresholds) so no single number is presented as if
every wedge in the chart shares it.

## Loop 3 — P0: single aggregated "Safe levels" number implying uniform depth (fixed, not yet deployed)

Commit: `0bc6850`

### Observe

`RingDepthControl`'s "Safe levels ... of N" is fed by `maxRingDepth = Math.max(1,
maxVisibleDepth(rawChildren, activeBranchChoice))` in `HomeClient.tsx` — the deepest path
reachable *anywhere* among the current level's siblings, combined into one number. This is
a legitimate rendering necessity (an ECharts sunburst nests all rings to one shared depth,
so the chart genuinely cannot draw more rings than the deepest branch supports), but
presented alone it invites reading "of 3" as "every wedge here has 3 levels" — exactly the
directive's named failure mode ("Six reported rings are not success if Social Security
stops at the first ring").

### Diagnose

Confirmed live, for FY2025-26 under the "Budget Statement 6" related branch: the
aggregated number is 3, but of the 17 federal top-level functions, 10 are leaves at depth
1, 5 reach depth 2, and only Health and Social security and welfare actually reach depth
3. Under "Canonical actual" for the same year, all 17 functions are genuinely depth-1
leaves — no native additive sub-purpose breakdown exists in this dataset at all; only the
related branches carry deeper structure. Both facts needed to be true and disclosed, not
one asserted as if it applied everywhere.

### Implementation

`src/frontend/lib/sunburstTree.ts`: new `perFunctionDepth(nodes, branchChoice)`, returning
each top-level node's own depth (not the aggregate) under the currently active branch, by
calling the existing `nestableChildren`/`maxVisibleDepth` per node instead of across all of
them combined. `src/frontend/app/HomeClient.tsx`: wired into a `<details>` disclosure
rendered next to the branch-note text, listing every top-level function's own depth
("Health: 3 levels", "Social security and welfare: 3 levels", "Defence: 1 (leaf)", ...) —
shown only when `functionDepths` actually vary, so it adds nothing when there is nothing
uneven to disclose (verified: correctly absent under "Canonical actual").

### Tests

New case in `test-chart-semantics.mjs`: a 2-node fixture (one leaf, one 3-deep chain)
asserts `perFunctionDepth` returns each node's own depth, not the aggregate. `npm run
test:unit`, `tsc --noEmit`, `next build` all pass/succeed. `lint:ci` 25/24 baseline drift
confirmed pre-existing/unrelated via `git stash` (identical problem list before and after).

### Browser verification

Same fresh local backend + production-style static export setup as Loops 1-2. FY2025-26,
"Budget Statement 6" branch: screenshot confirms the expanded disclosure lists all 17
federal functions with their true individual depths (10 leaves, 5 at 2 levels, 2 at 3
levels) directly beneath the "Safe levels ... of 3 · default 3" control it qualifies. Under
"Canonical actual" the disclosure is correctly absent (all functions genuinely depth-1).
0 console errors in both states.

### Data/graph impact

None — pure frontend code fix. No migration, no facts.db mutation, no backend change.

### Deployment status

**Not yet deployed.** Same standing constraint as Loops 1-2.

### Next

P0 items 1-4 from the reopened directive are now addressed (crosswalk resolution, canonical
sunburst purity, related-data visual/structural distinction via the branch selector, and
per-function depth disclosure replacing the misleading single number). Continue into the P1
items in priority order: top-level folding (never fold the first ring for federal
functions), "Other" synthetic-depth-as-real-hierarchy, persistent chart labeling, stable
semantic per-function colors, stale selected-node metadata on year/mode/branch changes,
explicit/exclusive related-branch selection with coverage disclosure, taxonomy/basis-change
disclosure (FY2024-25 GFS/COFOG vs FY2025-26 accrual/Commonwealth function classification),
and FY2025-26 golden regression fixtures — before moving to the data-depth ingestion
mission and the high-value dead-end audit.

## Loop 4 — P1: top-level folding hid real named functions behind "Other" (fixed, not yet deployed)

Commit: `0070d35`

### Observe

`foldToTopN()` (`lib/colors.ts`) applies uniformly at every ring, including the outermost
ring of an undrilled view. For FY2025-26 Federal Actuals (17 real COFOG/budget functions),
both pie and rings modes showed only the top 7 by value plus one opaque "Other (10)"
bucket — hiding 10 real named categories (Agriculture, Fuel and energy, General public
services, Housing, Mining/manufacturing/construction, Natural disaster relief, Nominal
superannuation interest, Other economic affairs, Public debt interest, Recreation and
culture) at the single most important level of the chart, where every function is a
well-known, bounded, always-meaningful category — not a genuinely long unbounded tail.

### Diagnose

Traced folding to two independent call sites that both needed the same fix: (1)
`displayedChildren` in `HomeClient.tsx`/`combined/page.tsx`/`DebtViewer.tsx` (feeds pie/bar,
calls `foldToTopN(additiveChildren(rawChildren))` unconditionally regardless of drill
depth), and (2) `buildLevel()` in `sunburstTree.ts` (feeds rings, calls `foldToTopN()` at
every recursion level including `currentDepth === 1`). Confirmed folding was already
correctly presentation-only with respect to depth math — `maxVisibleDepth`/`nestableChildren`
never called `foldToTopN` in the first place, so no semantic-depth corruption existed; only
the visual hiding of named categories needed fixing.

### Implementation

`sunburstTree.ts`: `buildSunburst()` and `buildLevel()` gained a `foldFirstRing` parameter
(default `true`, preserving existing behavior everywhere folding was already correct);
folding is skipped only when `currentDepth === 1 && !foldFirstRing` — every deeper ring
folds exactly as before. `SpendingChart.tsx` gained a matching `foldFirstRing` prop.
`HomeClient.tsx`, `combined/page.tsx`, `DebtViewer.tsx`: `displayedChildren` skips
`foldToTopN()` when `drillPath.length === 0`; all three pass `foldFirstRing={drillPath.length > 0}`
to `<SpendingChart>`.

### Tests

New case in `test-chart-semantics.mjs`: 9 synthetic top-level functions — `foldFirstRing:
false` (undrilled) keeps all 9 with zero "Other"; `foldFirstRing: true` (drilled/default)
folds to 8 with one "Other" bucket, exactly matching prior behavior. `npm run test:unit`,
`tsc --noEmit`, `next build` all pass/succeed. `lint:ci` 25/24 baseline drift confirmed
pre-existing via `git stash` (identical problem list before/after across all 6 touched
files).

### Browser verification

Same fresh local backend + production-style static export setup as Loops 1-3. FY2025-26,
Federal Actuals, undrilled: both pie and rings screenshots confirm all 17 named functions
render individually with zero "Other" bucket (previously 7 + "Other (10)"). Drilled into
"Social security and welfare" (a genuine canonical leaf per Loop 2's fix): navigation,
citation panel, and source-data table all continue to render correctly, confirming the
fold change did not regress drill-down. 0 console errors throughout.

### Data/graph impact

None — pure frontend code fix. No migration, no facts.db mutation, no backend change.

### Deployment status

**Not yet deployed.** Same standing constraint as Loops 1-3.

### Next

Continue into the remaining P1 items: "Other" synthetic-depth-as-real-hierarchy (a folded
bucket must never be counted as if it were a real hierarchy level), persistent chart
labeling, stale selected-node metadata on year/mode/branch changes, explicit/exclusive
related-branch selection with coverage disclosure, taxonomy/basis-change disclosure, and
FY2025-26 golden regression fixtures.

## Loop 5 — P1: chart colors reassigned by sort position instead of function identity (fixed, not yet deployed)

Commit: `19cad2c`

### Observe

Loop 4's own fix exposed a fresh, concrete correctness problem: `colorsFor()` assigned
color via `palette[i % palette.length]` on the value-sorted array. With folding removed at
the undrilled top level, 17 real federal functions are now shown against only a 7-hue
palette — positions 0/7/14, 1/8/15, and 2/9/16 all receive the identical hex value by
construction (`17 % 7` wraps twice), so up to 3 unrelated functions could render in the
exact same color simultaneously. Independent of collision, position-based assignment also
meant a single function's color silently reassigns whenever value-based sort order changes
across years, modes, or branches — the opposite of the "stable semantic colors, fixed per
canonical function" requirement.

### Diagnose

Confirmed the collision arithmetically: `Array.from({length:17}, (_,i) => i % 7)` produces
`[0,1,2,3,4,5,6,0,1,2,3,4,5,6,0,1,2]` — three colors repeat exactly 3 times each. This is
inherent to a 7-color palette applied to more than 7 categories (pigeonhole), not something
introduced by a rendering bug — it existed the moment 17 functions became simultaneously
visible, which Loop 4 caused.

### Implementation

`colors.ts`: `colorsFor()` now derives each node's palette index from a deterministic hash
of its own `name` (`stableColorIndex`), not its position in the (sorted) input array.
Deeper rings are unaffected — `buildLevel()` in `sunburstTree.ts` already derives their
color by lightening the parent's (now-stable) color, not by a separate position-based call.

### Tests

New case in `test-chart-semantics.mjs`: `colorsFor()` on the same 3 named nodes
(Health/Defence/Social security and welfare) in ascending vs descending value order
produces byte-identical hex values per name (`assert.deepEqual`, exact string equality —
not visual inspection). `npm run test:unit`, `tsc --noEmit`, `next build` all pass/succeed.
`lint:ci` 25/24 baseline drift confirmed pre-existing via `git stash`.

### Browser verification

Fresh local backend + production-style static export. Navigated FY2025-26 Actuals → Debt
mode → back to Actuals → FY2024-25 Actuals (three different value orderings and, for
FY2024-25, a different GFS-basis category set entirely) with 0 console errors and no
crashes; drill-down and citation panel continued working. Exact color-identity proof for
this fix rests on the unit test above (string equality), which is more reliable than
comparing hues by eye across PNG screenshots.

Incidentally observed during this check, out of scope for this fix: FY2024-25's rings view
shows overlapping/illegible labels ("Health" and "General public services" text
collide) — a pre-existing legibility defect, tracked under the still-open "persistent chart
labeling" P1 item below, not fixed here.

### Data/graph impact

None — pure frontend code fix. No migration, no facts.db mutation, no backend change.

### Deployment status

**Not yet deployed.** Same standing constraint as Loops 1-4.

### Disclosed limitation (not fixed, by design)

With only 7 palette hues and up to 17 named federal functions, some hue reuse remains
mathematically unavoidable without growing the palette (a design decision affecting the
site's visual identity, not made unilaterally in this remediation loop). This fix
guarantees **stability** (the same function always renders in the same color, in every
view) — it does not guarantee **zero collision** between different functions. If
zero-collision is required, expanding `CATEGORICAL_LIGHT`/`CATEGORICAL_DARK` past 7 entries
is a separate, disclosed follow-up item, left for explicit product/design sign-off.

### Next

Continue into the remaining P1 items: "Other" synthetic-depth-as-real-hierarchy, persistent
chart labeling (including the FY2024-25 label-overlap defect just observed), stale
selected-node metadata on year/mode/branch changes, explicit/exclusive related-branch
selection with coverage disclosure, taxonomy/basis-change disclosure, and FY2025-26 golden
regression fixtures.

## Loop 6 — P1: chart labels illegible/overlapping, no persistent list (fixed, not yet deployed)

Commit: `cf5ecba`

### Observe

ECharts sunburst/pie labels are drawn on-canvas with layout dependent on wedge angle.
Confirmed live at FY2024-25 (fewer, unevenly-sized GFS categories than FY2025-26's 17): the
rings view's "Health" and "General public services" labels visually overlapped and became
illegible. Loop 4's own fix (stop folding the top-level ring) made the underlying problem
worse by exposing more simultaneously-visible, variously-sized wedges all needing labels at
once, with no built-in overlap avoidance for ECharts' sunburst series (unlike its pie
series, which already sets `avoidLabelOverlap: true`).

### Implementation

New `components/ChartLegend.tsx`: a plain-DOM `<ul>` listing the current top-level
category names, color swatches (via Loop 5's now name-stable `colorsFor()`), and formatted
values — legible regardless of wedge size, entirely independent of ECharts' label layout.
Each entry is a button that drills exactly like clicking its wedge (reuses the same
`onNodeClick`/`handleNodeClick` handler). Wired into `HomeClient.tsx`, `combined/page.tsx`,
`DebtViewer.tsx` using each file's existing `displayedChildren` (the same list already
feeding pie/bar), so the legend is guaranteed to match what the current view actually draws
— including going correctly empty when the current node is a canonical leaf (Loop 2), never
showing a stale list.

### Tests

No new pure-logic unit test needed (the component has no computation beyond the
already-tested `colorsFor`/`formatMeasureValue`); verified via live browser interaction
instead. `tsc --noEmit`, `next build` both pass/succeed. `npm run test:unit` unaffected
(no changes to tested modules). `lint:ci` 25/24 baseline drift confirmed pre-existing;
`ChartLegend.tsx` itself lints with zero errors in isolation.

### Browser verification

Fresh local backend + production-style static export, FY2025-26 Federal Actuals: legend
lists all 17 functions with correct names, swatches visually matching their pie wedges, and
correctly formatted dollar values (screenshot confirmed). Clicking "Health" in the legend
drilled exactly as clicking its wedge would; the legend then correctly rendered empty
(returns `null` for zero nodes) since Health is a canonical leaf per Loop 2's fix — the
legend's emptiness matches the chart's own emptiness, never contradicting it. 0 console
errors.

### Data/graph impact

None — pure frontend code, new presentational component only.

### Deployment status

**Not yet deployed.** Same standing constraint as Loops 1-5.

### Remaining labeling gap (not fixed here, disclosed)

This fix addresses first-level (top-of-view) labeling only. The master directive also asks
for second-level category labels and a full legend/table option; the on-canvas overlap for
deeper rings (e.g. within a drilled multi-ring view) is unaddressed by this loop and remains
open under the same P1 item.

### Next

Continue into the remaining P1 items: "Other" synthetic-depth-as-real-hierarchy, second-level
persistent labeling, stale selected-node metadata on year/mode/branch changes,
explicit/exclusive related-branch selection with coverage disclosure, taxonomy/basis-change
disclosure, and FY2025-26 golden regression fixtures.

## Loop 7 — P1: selected-node metadata badge/citation survived mode/level/year/branch changes (fixed, not yet deployed)

Commit: `e928ed9`

### Observe

Selecting a node populates a relationship badge ("Additive/Related, Data/Navigation,
Selected FY · Source FY, BASIS · estimate_status") and a citation panel. Confirmed live:
none of `HomeClient.tsx`'s `handleModeChange`/`handleLevelChange`/`handleYearChange`, nor
the "Ring branch" buttons' inline `onClick={() => setBranchChoice(choice)}`, ever reset
`selectedNode` — only `selectedItemId` was cleared in some of them, and `handleModeChange`
cleared neither. Switching mode/level/year/branch after selecting a node left the badge
showing the *previous* selection's relationship metadata, which may no longer describe
anything real in the newly-fetched tree.

### Implementation

`HomeClient.tsx`: added a shared `resetSelection()` (clears `selectedNode`,
`selectedItemId`, resets `sourcePrompt`) called from all four change paths; added a new
`handleBranchChoiceChange` (the branch buttons previously had no handler function, just an
inline `setBranchChoice`). Drill position (`drillPath`) is deliberately left untouched on
branch change — the same node exists regardless of which branch is being viewed, so only
the branch-specific relationship metadata needs to reset, not navigation position.

`combined/page.tsx` had the identical gap for its mode-switch and branch-switch buttons
(`selectedItemId` never reset on either, feeding a stale citation panel) — fixed the same
way. Its level (`toggleLevel`) and year-change handlers already reset `selectedItemId`
correctly and needed no change. `DebtViewer.tsx` has no relationship badge and its
level/year handlers already reset `selectedItemId` correctly — confirmed no change needed
there.

### Tests

No new pure-logic unit test (this is state-reset wiring, not a computable function);
verified via live browser interaction. `tsc --noEmit`, `next build` pass/succeed. `npm run
test:unit` unaffected. `lint:ci` 25/24 baseline drift confirmed pre-existing.

### Browser verification

Fresh local backend + production-style static export, FY2025-26: selected "Social security
and welfare" via the Loop 6 legend under the "Budget Statement 6" branch, confirmed the
relationship badge showed real content ("Additive, Data, Selected FY 2025-26 · Source FY
2025-26, ACCRUAL · actual") and the citation panel showed the real Statement 6 source table.
Switched back to "Canonical actual": confirmed the badge disappeared entirely (0 matching
elements) rather than showing stale Statement 6 metadata, and the citation panel correctly
reverted to its empty-state prompt, matching the chart's own correct leaf/empty state
(Loop 2). 0 console errors.

### Data/graph impact

None — pure frontend state-management fix. No migration, no facts.db mutation, no backend
change.

### Deployment status

**Not yet deployed.** Same standing constraint as Loops 1-6.

### Next

Continue into the remaining P1 items: "Other" synthetic-depth-as-real-hierarchy, second-level
persistent labeling, explicit/exclusive related-branch selection with coverage disclosure,
taxonomy/basis-change disclosure, and FY2025-26 golden regression fixtures.

## Loop 8 — P1: related-branch selection required a blind click, no coverage disclosed first (fixed, not yet deployed)

Commit: `cae788e`

### Observe

Branch selector buttons ("Contracts", "Grants", "PBS programs", "Budget Statement 6", ...)
showed only a name — no indication of how much of the current view actually has data under
that branch before clicking. Loop 3 already disclosed this *after* selecting a branch (the
"Depth varies by function" list); the master directive specifically calls for coverage to be
disclosed *before* clicking.

### Diagnose / self-caught regression during implementation

First implementation computed coverage directly (`additiveChildren(rawChildren)` +
`nestableChildren(node, family)` per node), independent of Loop 3's `perFunctionDepth()`.
Live verification caught a real disagreement: for FY2025-26 under Statement 6, this
computed "10/17" while Loop 3's own depth-disclosure list showed exactly 8 non-leaf
functions. Root cause: `perFunctionDepth`/`ringRootChildren` route top-level nodes through
`prepareRingNodes` (`collapseSameNameChain`) before calling `nestableChildren`; the fresh
reimplementation skipped that step, so for any top-level node with a same-name wrapper
chain, it saw the wrong (unwrapped) children and disagreed with the already-shipped depth
disclosure describing the identical view. Caught by cross-checking the two numbers in the
live browser check rather than trusting the new code by inspection — the same discipline
applied throughout this session.

### Implementation

`branchCoverage` in `HomeClient.tsx` and `combined/page.tsx` is now derived directly from
`perFunctionDepth(rawChildren, family)` (`covered = depths.filter(d => d.depth > 1).length`),
guaranteeing the coverage count and the depth-disclosure list can never disagree — they
share one code path. Coverage renders as `" (covered/total)"` appended to each branch
button's label, with a `title` tooltip spelling it out. `DebtViewer.tsx` has no branch
selector (Government debt has no related branches) and needed no change.

### Tests

No new pure-logic unit test (this reuses the already-tested `perFunctionDepth`); verified
via live browser cross-check instead. `tsc --noEmit`, `next build` pass/succeed. `npm run
test:unit` unaffected. `lint:ci` 25/24 baseline drift confirmed pre-existing.

### Browser verification

Fresh local backend + production-style static export, FY2025-26 Federal Actuals: buttons
read "Contracts (1/17)", "Grants (1/17)", "PBS programs (0/17)", "Recipients (0/17)",
"Budget Statement 6 (8/17)" — PBS programs and Recipients genuinely cover nothing at the
top level (their detail is nested deeper, only reachable after drilling into a specific
sub-item), which a user could not have known before this fix without clicking blind.
Cross-checked "Budget Statement 6 (8/17)" against the Depth-varies-by-function list's own
non-leaf count for the identical view: exact match (screenshot confirmed). 0 console
errors.

### Data/graph impact

None — pure frontend code fix. No migration, no facts.db mutation, no backend change.

### Deployment status

**Not yet deployed.** Same standing constraint as Loops 1-7.

### Next

Continue into the remaining P1 items: "Other" synthetic-depth-as-real-hierarchy, second-level
persistent labeling, taxonomy/basis-change disclosure, and FY2025-26 golden regression
fixtures.

## Loop 9 — P1: basis note didn't say a basis change means a different taxonomy (fixed, not yet deployed)

Commit: `485212a`

### Observe

The existing FY basis note ("FY 2025-26 uses ACCRUAL...", "FY 2024-25 uses GFS
(preferred)...") disclosed the accounting basis but left the reader to infer that this also
means a completely different category classification — GFS-basis years use ABS/COFOG
purpose categories; accrual-basis years use the Department of Finance's own Commonwealth
function classification.

### Diagnose (and a false alarm resolved along the way)

Confirmed live via direct API calls and screenshots: GFS FY2024-25 shows 11 categories
(Health, Defence, Economic affairs, Environmental protection, Housing, Education, General
public services, Public order and safety, Recreation/culture/religion, Social protection,
Transport) with materially different groupings from accrual's same-named buckets — e.g.
GFS's "General public services" totals $159B vs accrual FY2025-26's $29B for a
similarly-named category; the two systems bundle differently, not just rename. Accrual
FY2025-26 shows a distinct 17-category set (fully visible for the first time since Loop 4).

While building the live verification test, a first-pass wait condition (waiting only for
"Loading…" to disappear after a year change) produced a screenshot that appeared to show
FY2024-25 rendering FY2025-26's exact data — investigated as a possible serious stale-data
bug in the year-change flow. Root cause of the *false alarm*: "Loading…" only renders when
`tree` is `null`; switching years leaves the previous year's tree non-null while the new
fetch is in flight, so waiting for "Loading…" to disappear is trivially already satisfied
before the new data arrives. Re-tested by polling for FY2024-25-specific content
("Economic affairs", which does not exist in FY2025-26's data) instead — confirmed the
underlying year-change fetch and render flow is correct; only the disclosure text needed
this fix, not the data flow.

### Implementation

`HomeClient.tsx`: new module-level `CLASSIFICATION_BY_BASIS` mapping `gfs`/`accrual` to a
plain-language classification name, appended as a clause to every branch of the existing
`availabilityNote` computation.

### Tests

No new pure-logic unit test (this is presentation text derived from already-fetched data);
verified via live browser check. `tsc --noEmit`, `next build` pass/succeed. `npm run
test:unit` unaffected. `lint:ci` 25/24 baseline drift confirmed pre-existing.

### Browser verification

Fresh local backend + production-style static export: FY2025-26 note now reads "...Category
names and depth follow the Dept of Finance Commonwealth function classification and will
differ from other bases."; FY2024-25 reads "...ABS GFS/COFOG purpose classification...".
Screenshots confirm the legend's actual category lists visually back up the claim (11 vs 17
differently-named categories). 0 console errors.

### Data/graph impact

None — pure frontend presentation-text fix. No migration, no facts.db mutation, no backend
change.

### Deployment status

**Not yet deployed.** Same standing constraint as Loops 1-8.

### Disclosed gap (not fixed here)

`combined/page.tsx` and `DebtViewer.tsx` do not fetch per-year basis availability data at
all and have no equivalent note. Extending this disclosure there would require fetching new
data (a genuinely separate, larger change), left as a disclosed follow-up rather than
scope-creeping into this fix.

### Next

Continue into the remaining P1 items: "Other" synthetic-depth-as-real-hierarchy, second-level
persistent labeling, and FY2025-26 golden regression fixtures.
