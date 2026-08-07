# Data remediation progress

Execution branch: `main`

Starting revision: `76d37f3`

Started: 2026-08-07

This is the persistent execution ledger for `ops/data_remediation_plan.md`. Statuses describe repository implementation, not source acquisition alone.

| Plan item | Status | Evidence | Commit/change | Remaining work |
| --- | --- | --- | --- | --- |
| 2.1 Golden projection fixtures | complete | `tests/fixtures/dashboard_projection/baseline.json`; required ten projections | `b6f5c1e` | Review fixture only when semantics intentionally change |
| 2.2 Depth/visibility audit | complete | `dashboard-depth-audit-20260807T232555Z.{md,json}`: 10 projections, 0 hard failures | `b6f5c1e` | Keep the audit in regression use |
| 2.3 Graph integrity checks | in_progress | Audit covers NULL-safe duplicates, cycles, projected compatibility/unit transitions, fallback metadata, related inheritance and citations | `b6f5c1e` | Add policy-aware child/completeness checks with declarative edge-set registry |
| 1.1 Relationship/projection API contract | complete | Every non-root dashboard node has typed relationship metadata; roots have projection summaries; rollback flag covered | Contract milestone working tree | Frontend consumption remains in renderer/depth UX milestones |
| 1.2 Declarative edge-set policy | not_started | Current traversal contains source/name heuristics | — | Add config and policy loader |
| 1.3 Projection builder | not_started | Projection logic is distributed across dashboard and graph modules | — | Extract pure projection stages |
| 3.1 Truthful ring values and units | not_started | Plan/current code identifies layout scaling contract defect | — | Implement after relationship contract |
| 3.2 Per-year availability | not_started | Current `/years` selects basis globally | — | Add availability endpoint and UI metadata |
| 3.3 Edge-cascade merge safety | not_started | Current budget cascade replacement requires audit | — | Preflight, augment policy, regression tests |
| 3.4 Flat tree pagination/totals | not_started | Current `/v2/tree` is limited and partial-total prone | — | Preserve compatibility and add truthful totals/cursor |
| 3.5 Edge uniqueness/idempotency | not_started | NULL-safe duplicate handling is audit-only | — | Audit, migration, scoped rebuild support |
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
