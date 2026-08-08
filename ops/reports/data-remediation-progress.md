# Data remediation progress

Execution branch: `main`

Starting revision: `76d37f3`

Started: 2026-08-07

This is the persistent execution ledger for `ops/data_remediation_plan.md`. Statuses describe repository implementation, not source acquisition alone.

| Plan item | Status | Evidence | Commit/change | Remaining work |
| --- | --- | --- | --- | --- |
| 2.1 Golden projection fixtures | complete | `tests/fixtures/dashboard_projection/baseline.json`; required ten projections | `b6f5c1e` | Review fixture only when semantics intentionally change |
| 2.2 Depth/visibility audit | complete | `dashboard-depth-audit-20260807T232555Z.{md,json}`: 10 projections, 0 hard failures | `b6f5c1e` | Keep the audit in regression use |
| 2.3 Graph integrity checks | complete | Audit covers NULL-safe duplicates, cycles, projected compatibility/unit transitions, fallback metadata, related inheritance and citations; registry rejects ambiguous and unmanifested authoritative sets | `be1f25b` | Keep audit in regression use |
| 1.1 Relationship/projection API contract | complete | Every non-root dashboard node has typed relationship metadata; roots have projection summaries; rollback flag covered | `de70595` | Frontend consumption remains in renderer/depth UX milestones |
| 1.2 Declarative edge-set policy | complete | `config/breakdowns/edge_sets.yaml`; source selection, fallback, branch semantics, presentation and merge policy are registry-driven | `be1f25b` | Extend registry only with tested source packs |
| 1.3 Projection builder | in_progress | Pure relationship/depth helpers plus declarative graph traversal and merge stages are implemented | `de70595`; `be1f25b` | Finish extraction while implementing pagination/explorer projection stages |
| 3.1 Truthful ring values and units | complete | Layout weights are isolated from reported values; all chart text is unit-aware; related percentages and mixed-semantic folding are guarded by executable tests | `e106772` | Browser depth/badge controls remain in item 4.4 |
| 3.2 Per-year availability | complete | 30 federal actual years exposed; basis is selected per year; availability metadata drives labels/warnings; every returned year is queryable | `34a36bc` | Generate future coverage prose from this endpoint in item 3.6 |
| 3.3 Edge-cascade merge safety | complete | Preflight found 719 suppressed path children; validation retains all 719 with zero root-total delta and zero semantic failures | `be1f25b` | Keep authoritative replacement gated by a completeness manifest |
| 3.4 Flat tree pagination/totals | complete | Flat shape is explicit; totals are scope-wide; publishability filtering and deterministic cursor traversal are tested | `dde1c08` | Hierarchical explorer remains separate in item 6.1 |
| 3.5 Edge uniqueness/idempotency | complete | Unique expression index applied with 0 duplicate deletions; all writers conflict-safe; every registered pack delete/rebuild path exercised on a copy | pending | Live reconciliation of surfaced emitter drift requires a separate reviewed deployment |
| 3.6 Lineage/registry consistency | not_started | Atlas records revenue/FBO/canonical-ID and alias inconsistencies | — | Correct configs, backfill, invariants and generated ranges |
| 3.7 Source-aware fiscal-year validation | not_started | `2099-00` QGIP/state actual outlier confirmed | — | Trace source, add bounded validation/quarantine |
| 4.1 Historical FBO preflight | not_started | 415 archive facts already loaded | — | Exact-year semantic/crosswalk/citation audit |
| 4.2 Historical FBO graph pack | not_started | No archive edge set exists | — | Add reversible/idempotent exact-only pack |
| 4.3 Historical traversal regression | not_started | 2022-23/2023-24 stop at two rings | — | Assert totals, years, branches and citations |
| 4.4 Safe-depth/branch UX | not_started | UI starts at depth two and infers branch semantics | — | Implement semantic controls/badges/disclosure |
| 5 Historical Statement 6/PBS editions | not_started | Required editions need repository/source inventory | — | Acquire/register, bounded adapters, crosswalks, NDIA repair |
| 6.1 Reusable explorer API | not_started | Family-specific APIs and flat generic endpoint exist | — | Add registry, hierarchy, facets, search and cursor APIs |
| 6.2 Reusable explorer shell | not_started | Existing explorer pages are family-specific | — | Add generic shell and shared evidence components |
| 6.3 Contracts/PBS/grants/VIC/ACT/QGIP migrations | not_started | Several families loaded but hidden/flat | — | Migrate in plan order; QGIP after repair |
| 7.1 MFS sibling workbooks | not_started | Five acquired structured siblings lack adapters | — | Implement per-workbook measures, fixtures and MFS tabs |
| 7.2 QLD QGIP repair | not_started | Loaded corpus has amount/subprogram/year defects | — | Reconcile, repair, validate, then explorer |
| 7.3 State borrowing gaps | not_started | Six missing and three broken acquired sources | — | Common contract and source adapters |
| 7.4 QLD Consolidated Fund | not_started | 46 acquired PDFs; no product model | — | Cash/vintage model, adapters and explorer |
| 7.5 QLD on-time payments | not_started | 42 acquired CSVs; no pipeline/product | — | Typed compliance measures, adapter and explorer |
| 7.6 VIC deferred sheets/KPIs | not_started | Structured sheets/KPI rows deliberately deferred | — | Separate typed products and surfaces |
| 8.1 Pre-2019 FBO parsers | not_started | Acquired text-extractable PDFs; broad parser unsafe | — | Three generation-bounded parser families |
| 8.2 1985-87 acquisition | not_started | Atlas reports sources external | — | Verify official source or mark blocked with evidence |
| 16 Final completion audit | not_started | — | — | Complete every actionable row and issue final report |

## Baseline

- Branch: `main`.
- Starting HEAD: `76d37f3`, equal to `origin/main` after fetch.
- Starting uncommitted work: `ops/data_remediation_plan.md` only; this is user-provided authoritative work and must be preserved.
- Current database snapshot and dashboard-depth baseline: [`current-data-atlas-20260807T195412Z.md`](current-data-atlas-20260807T195412Z.md).
- First selected milestone: Wave 0 projection signatures, depth audit, and graph integrity contract.

## Milestone: Wave 0 projection baseline and audit

### Item

Plan sections 2.1, 2.2, and the policy-independent portion of 2.3.

### Previous behavior

The repository had a semantic traversal audit, but no deterministic normalized projection fixtures for the required federal years and no single audit that reproduced visible ring depth, separated additive/related depth, counted presentation folding/rejections, and compared the result with a reviewed golden signature.

### Root cause

Projection behavior was distributed between backend tree construction and frontend sunburst rules. Existing reports recorded point-in-time observations rather than an executable regression contract.

### Changes

- Added `scripts/ops/dashboard_depth_audit.py`, a read-only in-process API audit.
- Added `tests/fixtures/dashboard_projection/baseline.json` for ten required representative projections.
- Added `tests/ops/test_dashboard_depth_audit.py` for relationship depth, future-year rejection, NULL-safe duplicate/cycle detection, and the real-database golden comparison.
- Added `ops/reports/dashboard-depth-audit-20260807T232555Z.{md,json}` as the reviewed baseline output.

### Validation

- Pre-change full suite in the configured conda environment: **553 passed**, one dependency deprecation warning.
- Focused new tests: **4 passed**, one dependency deprecation warning.
- Post-change full suite: **557 passed**, one dependency deprecation warning.
- Ruff on new Python files: passed.
- Audit: ten projections, **0 hard failures**, **0 duplicate semantic edges**, **0 cycles**, complete citations for every fact-bearing terminal node in scope.

### Data impact

None. The audit opens `data/facts.db` read-only and does not run loaders or migrations.

### Dashboard impact

None. This milestone freezes current behavior. It confirms federal actual safe visible depth of 2 for 2022-23, 2 for 2023-24, and 4 for 2024-25, with unchanged root totals of $639.703b, $687.277b, and $745.030b respectively.

### Remaining risks

Policy-aware checks for authoritative completeness and per-edge-set fallback cannot be final until the declarative edge-set registry exists. This is why plan item 2.3 remains `in_progress` rather than being overstated as complete.

### Next item

Plan section 1.1: add the backward-compatible relationship/projection API contract, then use it as the basis for declarative edge policy.

## Milestone: Relationship and projection API contract

### Item

Plan section 1.1 and the metadata-propagation foundation of section 1.3.

### Previous behavior

Only related/fallback nodes had the legacy `breakdown` object. Consumers inferred navigation folders from labels, could not distinguish a same-group edge inside a related branch, and had no root metadata describing safe versus additive depth.

### Root cause

Edge kind, inherited branch semantics, source provenance, presentation role and requested/fact year were conflated in one optional compatibility object. Canonical leaves were historically stamped as related when related children were attached.

### Changes

- Added typed `RelationshipMeta`, `ProjectionMeta`, and branch-summary schemas plus matching frontend types.
- Added the pure `dashboard_projection.py` metadata/summary module.
- Added a `relationship` object to every non-root dashboard node and root `projection` metadata.
- Preserved `breakdown` as a deprecated compatibility alias.
- Preserved actual edge kind while propagating `branch_kind=related` through descendants.
- Marked jurisdiction and repeated source-function bridges as navigation where they are not semantic levels.
- Kept canonical ABS parents additive even when related Statement 6/FBO children are attached.
- Added temporary `DASHBOARD_PROJECTION_V2` rollback control, enabled by default.
- Updated the projection audit to use explicit edge-set identity and semantic depth.

### Validation

- Focused API/unit/graph tests: **22 passed**.
- Full backend suite: **563 passed**, one dependency deprecation warning.
- Frontend `lint:ci`: passed at the unchanged accepted baseline of 25 errors / 13 warnings.
- TypeScript `tsc --noEmit`: passed.
- Frontend production build: passed, 12 static routes.
- Ruff and diff checks: passed.
- [`dashboard-depth-audit-20260807T234053Z.md`](dashboard-depth-audit-20260807T234053Z.md): fixture match, zero hard failures, zero duplicate semantic edges, zero cycles, zero missing terminal citations.

### Data impact

None. No schema migration, loader or database write was performed.

### Dashboard impact

The wire contract is richer but tree values and reachability are unchanged. Federal actual root totals remain $639.703b (2022-23), $687.277b (2023-24), and $745.030b (2024-25); safe visible depths remain 2, 2 and 4. The 2024-25 root now explicitly reports additive depth 2, related depth 4 through the audit, 11 canonical nodes with related children, and source/basis/year/unit metadata on projected nodes.

### Remaining risks

Branch-family labels still reflect current source families until the declarative edge-set policy supplies product-level families such as `statement_6`, `fbo`, `contracts` and `grants`. The existing frontend has not yet migrated from `breakdown` to `relationship`; that is intentionally isolated from this API contract commit.

### Next item

Plan section 1.2 and section 3.3 preflight: add the declarative edge-set policy and audit path-versus-edge suppression before changing cascade behavior.

## Milestone: Declarative edge policy and cascade merge safety

### Items

Plan sections 1.2, 2.3, and 3.3, plus the graph-policy portion of section 1.3.

### Previous behavior

`attach_related_to_tree` classified Statement 6 and FBO branches with source-key prefixes, every related branch allowed nearest-year fallback, and the federal budget cascade unconditionally replaced path-derived children whenever any same-group edges existed.

### Root cause

`breakdown_edges` stored topology but had no declarative projection, fallback, branch-family or presentation policy. SQLite edge presence was therefore treated as proof of completeness even though the deployed edge sets are partial.

### Preflight evidence

- [`budget-edge-cascade-preflight-20260807T234606Z.md`](budget-edge-cascade-preflight-20260807T234606Z.md) compares all 15 federal budget years before the behavior change.
- It found 26 parent/year projections with path-only children and **719 path-only children** that unconditional replacement would suppress.
- The old replacement behavior changed the raw path root total in six years; those emitted replacement totals were captured as the compatibility baseline for the postflight check.

### Changes

- Added `config/breakdowns/edge_sets.yaml` and a validated registry for edge-set identity, physical edge kind, inherited branch kind, source-family scope, augment/authoritative projection, exact/nearest fallback, presentation role, folder label and deterministic order.
- Split the shared `cofog_to_budget_function` crosswalk into explicit Statement 6 and FBO policies; historical/audited FBO remains exact-year only.
- Removed source-prefix classification from related-tree attachment and grouped related branches by registry metadata.
- Made cross-measure contract, grant and recipient drills explicitly related even where legacy storage uses a physical `same_group` edge.
- Changed federal budget cascading to augment by default, recursively deduplicate by node ID/canonical key/normalized label, and order deterministically.
- Preserved pre-change projected parent/root amounts while retaining non-authoritative path evidence; cross-measure path additions are tagged related and excluded from additive reconciliation.
- Gated authoritative replacement on registry validation requiring a named completeness manifest.
- Added focused policy and pure merge tests plus a repeatable read-only cascade audit.

### Validation

- Focused graph/policy/API suite: **24 passed**, then projection-contract regression suite passed after intentional edge-set identity updates.
- Full backend suite: **572 passed**, one dependency deprecation warning.
- Ruff and diff checks: passed.
- [`budget-edge-cascade-validation-20260808T001300Z.md`](budget-edge-cascade-validation-20260808T001300Z.md): all **719** at-risk path-only children retained; no year differs from the captured replacement root total.
- [`dashboard-depth-audit-edge-policy-final-20260808T001300Z.md`](dashboard-depth-audit-edge-policy-final-20260808T001300Z.md): reviewed fixture match, **0 hard failures**, 0 duplicate semantic edges, 0 cycles and complete terminal citations.

### Data impact

None. Both audit passes opened `data/facts.db` read-only. No schema migration, loader, edge write or fact mutation occurred.

### Dashboard impact

Federal budget root totals remain exactly compatible with the prior edge-derived projection while incomplete path rows are no longer silently removed. Cross-measure grant/contract/recipient branches now advertise related semantics instead of appearing additive. Existing Statement 6/PBS depth remains reachable.

### Remaining risks

The retained raw path corpus contains noisy historical labels; this milestone keeps valid evidence reachable without claiming those rows form an additive partition. Source-quality remediation and generic explorer filtering remain separate plan items. No edge set is authoritative today.

### Next item

Plan section 3.1: separate chart layout weight from reported fact value and make unit/percentage rendering relationship-aware.

## Milestone: Truthful chart values and semantic units

### Item

Plan section 3.1.

### Previous behavior

The sunburst recursively rescaled child `value` fields to make ECharts arcs fit their parent, then tooltips displayed that scaled value. Pie, bar, ring and center text used AUD-only formatters, ECharts percentages were shown without branch semantics, and one `Other` bucket could combine unrelated units, years and compatibility groups.

### Root cause

One numeric field served both layout and evidence. Presentation code also lacked a shared semantic tooltip/percentage contract and folded solely by rank.

### Changes

- Added exact `reportedValue`, `reportedUnit`, `reportedParentValue`, relationship and related-state fields to sunburst data while retaining `value` strictly as layout weight.
- Changed every chart tooltip, label, axis, center label and accessibility description to use `formatMeasureValue` and reported fields.
- Added real additive-cohort percent-of-parent calculation and explicit suppression/disclosure for related branches.
- Suppressed aggregate totals for mixed-unit charts.
- Made `Other` folding semantic across branch/edge kind, presentation role, unit, source year, compatibility group and accounting basis; retained typed relationship metadata on synthetic aggregates.
- Replaced active Statement 6/FBO label classification with relationship metadata while retaining a legacy fallback for rollback compatibility.
- Added a dependency-free executable TypeScript unit harness covering scaling truthfulness, semantic units, percentage rules and folding.

### Validation

- [`renderer-correctness-20260808T151835Z.md`](renderer-correctness-20260808T151835Z.md) records the acceptance evidence.
- Frontend semantic unit tests: passed.
- TypeScript: passed.
- Frontend lint baseline: unchanged at 25 errors / 13 warnings.
- Production build: passed, 12 static pages.
- Backend suite immediately before this frontend-only milestone: 572 passed.

### Data impact

None.

### Dashboard impact

Rendered arc geometry remains stable, but displayed amounts now remain identical to cited facts even when layout weights are scaled. Non-AUD measures keep their units; related branches no longer imply a percentage of an unrelated parent; mixed semantic tails cannot be hidden in one untyped `Other` wedge.

### Remaining risks

This milestone corrects chart semantics but does not yet expose branch badges, source-year badges or maximum-depth controls; those remain item 4.4. Full browser interaction coverage will be expanded with that UX milestone.

### Next item

Plan section 3.2: make federal accounting-basis selection per year and expose explicit availability metadata to the frontend.

## Milestone: Per-year accounting-basis availability

### Item

Plan section 3.2.

### Previous behavior

`/v2/dashboard/years` called `_preferred_basis` without a year. Because GFS existed anywhere in the federal actual series, the endpoint filtered the entire list to GFS and hid accrual-only years. Tree requests already selected basis using the requested year, so the list and tree contracts disagreed.

### Root cause

Basis preference was treated as a property of a government level instead of a year/measure projection. The frontend consumed only strings and could not explain which basis had been selected.

### Changes

- Added typed `DashboardAvailability` API objects with year, selected basis, available bases and source families.
- Added `/v2/dashboard/availability` and projected legacy `/years` strings from the same quality-filtered, mode-aware query.
- Applied GFS-over-accrual preference independently per actual year and reused the availability calculation for multi-level series year discovery.
- Tightened tree basis discovery to use the same quality and economy-mode filters.
- Updated the frontend selector to consume availability, label basis per year and disclose alternatives or GFS absence, with a legacy endpoint fallback for rollback compatibility.
- Added real-database tests for the 2005–06 through 2007–08 accrual window, dual-basis GFS preference and every-returned-year queryability.

### Validation

- [`dashboard-availability-validation-20260808T152859Z.md`](dashboard-availability-validation-20260808T152859Z.md) records the sample matrix and endpoint contract.
- Focused backend suite: 16 passed.
- Full backend suite: 574 passed.
- Ruff, frontend semantic unit tests, TypeScript and production build: passed.
- Frontend lint baseline remained unchanged at 25 errors / 13 warnings.

### Data impact

None.

### Dashboard impact

Accrual-only historical actual years are selectable without changing GFS preference in overlapping years. The UI now tells users which basis is active and why.

### Remaining risks

Coverage prose elsewhere in the UI is still partially hard-coded; item 3.6 will generate those ranges from availability. The endpoint reports all source families available in a year, not a per-source completeness claim.

### Next item

Plan section 3.4: make the compatibility flat tree truthful with independent totals and cursor pagination.

## Milestone: Truthful flat-tree totals and cursor pagination

### Item

Plan section 3.4.

### Previous behavior

`/v2/tree` returned a limited flat list but labeled the sum of that page as the family root value. It exposed neither the full matching count nor a way to continue beyond the limit, and did not consistently apply the publication-quality filter.

### Root cause

The compatibility route combined page retrieval and aggregation in one limited query. Its response shape did not distinguish a flat fact list from a hierarchy, and citation construction reopened the facts database for every returned row.

### Changes

- Declared the route's compatibility shape as `flat` without overloading it with hierarchical explorer behavior.
- Added independent full-scope `total_count` and `total_value`; retained `value` as a truthful alias of the full total.
- Added opaque, versioned keyset cursor pagination with deterministic amount/fact-ID ordering and null handling.
- Applied the same rejected/quarantined exclusion to totals and page rows.
- Exposed `next_cursor` and added optional cursor support to the frontend client contract.
- Built citations from the page query to remove per-row database connection/query overhead.
- Added real-database tests for limit-independent totals, complete bounded traversal and invalid cursors.

### Validation

- [`flat-tree-pagination-validation-20260808T154539Z.md`](flat-tree-pagination-validation-20260808T154539Z.md) records the API contract and real-data traversal.
- Focused API/citation suite: 5 passed.
- Full backend suite: 577 passed.
- Ruff, frontend semantic unit tests, TypeScript and production build: passed.
- Frontend lint baseline remained unchanged at 25 errors / 13 warnings.

### Data impact

None.

### API impact

Existing `name`, `value` and `children` fields remain. `value` no longer misrepresents a page sum as a complete total; consumers gain explicit totals and continuation metadata.

### Remaining risks

The generic route intentionally remains a flat compatibility surface. Family registry, hierarchy, facets and search belong to the reusable explorer API in item 6.1.

### Next item

Plan section 3.5: audit and enforce NULL-safe edge uniqueness, conflict-safe writes and scoped reversible graph rebuilds.

## Milestone: NULL-safe edge identity and reversible graph packs

### Item

Plan section 3.5.

### Previous behavior

The table-level unique constraint treated NULL year/crosswalk values as distinct. Writers used manual existence checks, and graph packs had no consistent, scope-aware removal/rebuild command.

### Root cause

SQLite's NULL uniqueness semantics did not match the logical edge identity. Idempotency lived in individual loader implementations rather than the schema, while edge-set projection metadata was not reused for operational ownership.

### Changes

- Added migration 017 with defensive duplicate cleanup and a unique expression index using `COALESCE(financial_year, '')` and `COALESCE(crosswalk_id, '')`.
- Replaced every production check-then-insert edge writer with conflict-safe insertion.
- Added an edge-set/crosswalk-aware preview, delete and transactional rebuild command with explicit `--apply` mutation gating.
- Registered rebuild behavior for every current declarative edge set, including shared-crosswalk source scoping and source-native families.
- Updated integrity tests to assert that NULL-safe duplicates are rejected at insertion time.

### Validation

- [`edge-uniqueness-idempotency-validation-20260808T160231Z.md`](edge-uniqueness-idempotency-validation-20260808T160231Z.md) records the preflight, live schema verification and every disposable rebuild delta.
- Live preflight/postflight: 14,167 edges, 0 duplicate groups, 0 rows deleted, integrity check `ok`.
- Repository graph integrity audit: 0 hard failures.
- Focused suite: 60 passed; full backend suite: 581 passed.
- Ruff and diff checks passed.

### Data impact

Migration 017 is applied to the ignored live facts database. No live edge was removed or rebuilt; edge count remained unchanged. Destructive operations were validated only on disposable copies.

### Remaining risks

The disposable audit exposed deterministic rule drift in five edge sets. Those deltas are documented and were deliberately not deployed implicitly. A future graph deployment can now preview and apply each exact scope transactionally.

### Next item

Plan section 3.6: correct source identities, canonical dataset lineage, uniqueness invariants and generated coverage ranges.
