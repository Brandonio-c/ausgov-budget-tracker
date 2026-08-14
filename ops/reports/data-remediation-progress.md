# Data remediation progress

Execution branch: `main`

Starting revision: `76d37f3`

Started: 2026-08-07

This is the persistent execution ledger for `ops/data_remediation_plan.md`. Statuses describe repository implementation, not source acquisition alone.

> **CRITICAL, not part of the plan's own items, requires an explicit human decision:**
> the public production API (`https://ausgov-budget-api.vibefactory.app`) is running a
> backend container built from before commit `dde1c08` (item 3.4) - it does not have the
> `/v2/tree` pagination fix, and by extension none of items 3.4 through the present entry
> in this ledger are visible to real users. Data/config-only fixes reach production
> immediately via the bind mount; every *Python code* change since does not, until the
> container is rebuilt and redeployed. See
> [`contracts-pagination-fix-20260812T030352Z.md`](contracts-pagination-fix-20260812T030352Z.md#critical-finding-the-public-production-api-has-not-been-redeployed)
> for the evidence. This autonomous loop deliberately did not trigger a deploy (a live,
> user-facing, comparatively hard-to-reverse action) without an explicit decision to do so.

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
| 3.5 Edge uniqueness/idempotency | complete | Unique expression index applied with 0 duplicate deletions; all writers conflict-safe; every registered pack delete/rebuild path exercised on a copy | `754c669` | Live reconciliation of surfaced emitter drift requires a separate reviewed deployment |
| 3.6 Lineage/registry consistency | complete | Revenue/FBO identities corrected; 22,196 canonical facts assigned with 0 mismatches; TAS/QLD aliases and API-derived UI ranges validated | `af0294b` | Maintain ownership registry as canonical families expand |
| 3.7 Source-aware fiscal-year validation | complete | QGIP amount/year column collision fixed; 4,198 horizon outliers recoverably quarantined; 0 remain published | `9dd056f` | Correct and reattribute quarantined QGIP years in item 7.2 |
| 4.1 Historical FBO preflight | complete | 415 facts; 0 semantic failures; 50/50 mapped comparisons; official locator years exact; retrieval attribution defect explicit | `ed3567f` | Repair per-edition retrieval/cached-copy provenance before graph deployment |
| 4.2 Historical FBO graph pack | complete | 415/415 exact-year citations; 75 source-native + 11 related edges; stable rebuild; ABS totals unchanged | `3d48680` | Freeze 2022-23/2023-24 traversal regressions in item 4.3 |
| 4.3 Historical traversal regression | complete | Reviewed fixture: unchanged roots, 11 mapped routes/year, exact audited branches, 69/69 leaf citations, explicit exceptions | `468eed2` | Surface available related depth and branch choices in item 4.4 |
| 4.4 Safe-depth/branch UX | complete | Canonical-default branch chips; selected/available safe depth; semantic/year/basis/status badges; production build clean | `d3446b3` | Begin Wave 3 historical edition manifest/acquisition |
| 5.1 Historical edition acquisition | complete | Three edition-specific Statement 6 sources and three Treasury PBS representatives acquired with official URLs/checksums; March/October remain distinct | `3ec6d55` | Build bounded Statement 6 edition adapters in item 5.2 |
| 5.2 Historical Statement expense adapters | complete | Edition-bounded Statement 5/6 appendix + 13 component tables each; 2,146 rows preflighted twice with zero quarantine; live projection unchanged | `4adcbcc` | Add historical PBS fixtures/adapters in item 5.3 |
| 5.3 Historical Treasury PBS adapter | complete | Extractor fixed (4 root-cause defects) and validated on all 3 real editions: 0 exceptions, 0 duplicate keys, program-row counts exactly match programs×5yr, component sums reconcile to published program totals except 3 rows within documented $1,000 rounding; 12 new regression tests passed | `2553851` | Build crosswalk beneath matched Statement 6 nodes and deploy exact-only related edges in item 5.4 |
| 5.4 Historical PBS/Statement 6 crosswalk | complete | Facts loaded (critical additivity defect found/fixed first); 82 exact-only `related_breakdown` edges deployed (Treasury portfolio, March 2022-23 + 2023-24, 43+39 programs); reachable via `/v2/dashboard/item/{id}/children`, zero root-total impact, zero fallback leakage; 19 new tests passed | `474cdd7` | Extend to more portfolios/editions in a follow-up; not required by the Wave 3 exit gate |
| 5.5 NDIA repair / current-PBS coverage | complete | NDIA repaired (`b4504c8`); coverage report refreshed (`12ceead`); classifier precision fixed (2 new rejection signals + 6 new vocabulary terms, isolated diff proves 0 new false-positive acceptances and catches 158 previously mis-accepted garbled "program" labels); quarantine precision review evidence-based, 0 bulk promotions | `a7aad12` | Per-individual-document origin breakdown for the "mapped" bucket remains a minor follow-up; NEW distinct finding: `federal_pbs_programs_all` live facts are stale vs current code (17,482 vs 33,291 if reloaded) — reload needs its own dedicated, reviewed milestone, tracked separately below |
| 5.5b `federal_pbs_programs_all` stale-corpus reload | complete | Reload + `cleanup_stale_pbs_nodes.py` deployed live with backup: fact-key analysis showed net effect was -682 facts (0 added, all removals of the same 158 garbled labels item 5.5 already verified), 158 stale crosswalk edges to nodes/412 edges cleaned; found and fixed an independent `task9_sql_integrity_checks.py` `--db`-ignored bug along the way; 0 hard failures after, fixture updated, full suite 643 passed | `1ec8b68` | Follow the same reload+cleanup pairing for any future classifier precision work on this source |
| 6.1 Reusable explorer API | complete | Full backend contract per the plan's own list: registry (5 families), `GET /v2/explorers`, `.../availability`, `.../tree` (cursor pagination, truthful totals, registry-validated estimate_status, honest 400 for `path` - verified via direct DB inspection that no family has real `node_edges` hierarchy, so none is fabricated), `.../facets` (year/status/source/measure), `.../item/{fact_id}` (family-boundary enforced even for a real cross-family fact_id), plus server-side `search` added to `/v2/tree` itself; 28 new tests across this and the prior increment, 676 total passed, 0 regressions; verified live against a freshly-confirmed uvicorn process, not only TestClient | `d7717fb`, `26dd135`, `14eede9`, `42a05c9` | Frontend migration onto the registry is deliberately item 6.2/6.3 work, not redone twice; path browsing has no data to serve until a family gains real hierarchy |
| 6.3 Contracts 200-row truncation | complete | Frontend-only fix reusing item 3.4's already-built `/v2/tree` cursor pagination; verified live in a real browser (Playwright): truthful "9,036 contracts... 200 loaded", working Load-more, atomic year switch, 0 console errors | `9b3e675` | Hierarchical agency/category/supplier/notice depth and server-side search remain part of the larger item 6.1 explorer API, not this fix |
| 6.3 VIC output performance surfacing | complete | 14 already-loaded facts (7 outputs x actual/budget) had zero frontend reachability; new explorer page reuses the existing `/v2/tree` endpoint (no backend change), verified live in a real browser: all 7 rows correct, full citations, 0 console errors | `e0fb807` | The 70 non-dollar KPI rows from the same workbook remain deliberately deferred, unchanged from the original 2026-08-07 implementation |
| 6.3 Grants explorer | complete | 2,486 already-loaded GrantConnect award facts had zero frontend reachability; new explorer page mirrors the contracts pagination pattern (same `/v2/tree` compatibility_group, different estimate_status), verified live in a real browser: truthful totals, working Load-more, 0 console errors | `bb4fa3b` | Hierarchical portfolio/program -> award/recipient depth and server-side search remain part of the larger item 6.1 explorer API |
| 6.3 ACT invoices explorer | complete | 46,714 already-loaded ACT notifiable invoice facts (13 years) had zero frontend reachability; confirmed `cash_outflow` group is shared with an unrelated source but `estimate_status=invoice` correctly scopes to ACT only; verified live in a real browser: truthful totals, working Load-more, 0 console errors | `e9bb39a` | True agency->supplier->invoice drill-down hierarchy and server-side search remain part of the larger item 6.1 explorer API |
| 6.3 PBS explorer | complete | 16,800 already-loaded `federal_pbs_programs_all` facts had zero frontend reachability; added an optional `source_key` filter to `/v2/tree` (new test proves it narrows a real shared compatibility triple and preserves unfiltered behaviour when omitted) so the page shows PBS facts only, not co-scoped state/other-PBS sources; verified live in a real browser across year/estimate_status switches, 0 console errors | `d7717fb` | Hierarchical edition->portfolio/entity->outcome/program/component depth and server-side search remain part of the larger item 6.1 explorer API |
| Contracts jurisdiction-mix disclosure (found scoping 6.1) | complete | Discovered the "Contracts explorer" scope for 2024-25 is 100% NSW/NT/QLD state data, 0% federal AusTender, undisclosed; added a `source_breakdown` facet to `/v2/tree` (2 new tests, exact-match against direct SQL) and surfaced it with a disclosure sentence and per-jurisdiction counts on the page; verified live in a real browser, 0 console errors | `26dd135` | Splitting into true per-jurisdiction family pages remains a legitimate item 6.1/6.3 scope boundary, not required by the exit gate |
| 6.2 Reusable explorer shell | complete | `ExplorerShell.tsx` + `explorerApi.ts` + `app/explorers/family/[family]/page.tsx`, registry-driven end to end (year selector/estimate-status/additive-note banner/source_breakdown all derived from `/v2/explorers` responses, zero per-family hardcoding); verified live for all 5 registered families (zero console errors), server-side search, honest 404/no-data-year states, and zero regression to the 2 existing dedicated pages spot-checked; a real defaulting bug (latest-year default landing on sparse years) was found and fixed during live verification | `4f76350` | Family migration (item 6.3) intentionally not done in this pass; dynamic route placed at `/explorers/family/{id}` rather than the plan's literal `/explorers/[family]` since that slug is still shadowed by the 5 unmigrated static pages |
| 6.3 Contracts/PBS/grants/VIC/ACT/QGIP migrations | complete | All 5 plan-listed families migrated onto the item 6.1/6.2 generic shell at their existing URLs (each page now a thin `<ExplorerShell familyId="..." />` wrapper instead of ~170-200 lines of bespoke fetch/state logic); live-verified zero regressions to any of the 5 real totals, `DebtNav`/GFS cross-link preserved on contracts via a new `extraContent` shell slot; eslint baseline genuinely improved (25 -> 24 errors) by deleting duplicated code; QGIP still correctly blocked behind item 7.2 repair | `c115219` | QGIP explorer after item 7.2 repair |
| 7.1 MFS sibling workbooks | in_progress | Workbook 2/5 (Note 3, Total expense by function) done: 20 new measure_types, +4,413 facts live, 0 backend/frontend code change needed (API/UI already registry-driven); found and fixed 2 real header-shape quirks via a new shared mfs_common.py module; found and resolved 43 duplicate-fact false positives; 16 new tests, 692 total passed, 0 regressions, 0 canonical-tree impact. Workbook 3/5 (Operating Statement) investigated and deliberately deferred: found at least 3 structurally distinct generations (not a richer version of Note 3's flat shape) including a genuine same-label, different-section, different-value collision ("Actuarial revaluations") - evidence and a recommended per-generation approach recorded, no code written | `31c8b4d` | Operating Statement needs a dedicated future pass (see scoping report); Balance Sheet, Tax Notes 1/2, Monthly Profiles remain untouched |
| 7.2 QLD QGIP repair | complete | All 3 named defects root-caused via direct inspection of all 14 real files and fixed: financial_year now derived only from filename (was picking up a dollar-amount column, "Previous financial year", as a year - root cause of the "2099-00" observation; also fixed a filename-regex gap that silently misattributed 5 real years' data to a hardcoded "2024-25"); amount-column now prefers per-year "Financial year expenditure" over "Total funding under this agreement" regardless of file column order, with the 2 years lacking a per-year column tagged with a distinct estimate_status so they can never blend with genuine single-year figures; subprogram structure now captured (was silently dropped for 11/14 files). Facts 176,719 -> 203,899 via replace_on_reload; 63,763 stale old nodes cleaned up (same method as the PBS reload); 0 hard failures, 0 canonical-tree impact, idempotent; 7 new tests, 699 total passed | `26522e2` | Dedicated QGIP explorer not yet built, per the plan's own "then expose..." sequencing; fact_key overwrite-not-sum collision risk on identical agency/program/subprogram text is pre-existing and flagged for a future pass, not fixed here |
| 7.3 State borrowing gaps | in_progress | Investigated before writing any adapter code: the "three broken" sources are NOT broken - `orphan-node-investigation-20260804T180700Z.md` already resolved them as intentionally retired legacy duplicates (superseded by already-loaded canonical sources); reloading them would double-count debt. Real remaining gap is 8 acquired-but-unadapted sources (5 PDF, 1 XLSX, 1 CSV, 1 unchecked), one of which (`vic_tcv_benchmark_bond_outstandings`) was found to substantially overlap already-loaded data and needs non-additive treatment, not a plain adapter. A separate, larger federal AOFM debt-instrument family (12 sources) was also found, out of this item's "state borrowing" scope | `ecb6546` | Ledger correction is the concrete deliverable this pass; each of the 5 PDF sources needs its own evidence-first inspection before any adapter is written (see scoping report) |
| 7.4 QLD Consolidated Fund | not_started | 46 acquired PDFs; no product model | — | Cash/vintage model, adapters and explorer |
| 7.5 QLD on-time payments | complete | 8 typed measure_types (count/cash/days/percent) live for 29 agencies; 794 facts loaded, idempotent, 0 hard failures, `fixture_matches: true` on live | `209d65f` | Dedicated compliance explorer not yet built, per the plan's own sequencing |
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

## Milestone: Canonical lineage and truthful source coverage

### Item

Plan section 3.6.

### Previous behavior

The revenue canonical declaration pointed at the expense source, “full” FBO coverage used a broad prefix that could imply historical completeness, every row-level canonical ID was null, TAS/QLD duplicate acquisitions appeared as separate backlog items, and specialist explorer coverage prose embedded static year ranges.

### Root cause

Canonical lineage existed only as report configuration and was not integrated into fact publication. Coverage heuristics could override dataset-level intent, duplicate acquisition IDs lacked normalized alias direction, and the frontend repeated availability already present in API series data.

### Changes

- Corrected the ABS revenue source identity and split current FBO Appendix A from the partial historical archive.
- Added validated, single-owner canonical lineage lookup and integrated it into shared fact upserts.
- Added a preview-by-default transactional backfill and populated all configured live facts while clearing non-canonical stale assignments.
- Made declared exact-source canonical coverage authoritative over generic audit heuristics.
- Normalized TAS/QLD duplicate aliases and handoff repository targets, then regenerated both coverage report families.
- Replaced displayed static specialist year/vintage ranges with API-response-derived availability summaries and executable frontend coverage.

### Validation

- [`lineage-registry-validation-20260808T162028Z.md`](lineage-registry-validation-20260808T162028Z.md) records per-dataset assignments and disposition evidence.
- 22,196 canonical facts assigned; 267,119 specialist facts null; 0 mismatches; second backfill changed 0 rows.
- Focused canonical/registry suite: 15 passed; shared loader/API suite: 48 passed; full backend suite: 586 passed.
- Frontend unit, TypeScript, accepted lint baseline and production build passed.

### Data impact

Only `facts.canonical_dataset_id` changed in the ignored live database. No fact content or graph topology changed.

### Remaining risks

Future bespoke loaders for newly canonicalized families must call the shared lineage lookup or the backfill command; the real-database invariant will fail if assignments drift. Historical FBO remains correctly partial until later archive work completes.

### Next item

Plan section 3.7: investigate the `2099-00` outlier and add source-declared publication-horizon validation/quarantine.

## Milestone: Source-declared fiscal-year horizons

### Item

Plan section 3.7.

### Previous behavior

Validation accepted any syntactically shaped fiscal year. The QGIP exporter could mistake `Financial year expenditure` for the actual year column, turning amounts such as 2,099 into FY `2099-00` and publishing them.

### Root cause

Fuzzy year-column matching did not exclude monetary columns, and validation had no source-specific publication boundary. A global maximum would hide the immediate symptom but incorrectly reject legitimate long-horizon sources.

### Changes

- Corrected QGIP year-column selection and added a regression for amount 2,099 versus real FY2022-23.
- Added optional mapping-declared minimum/maximum financial years to the generic validation gate.
- Added machine-readable source-horizon quarantine reasons without imposing a global cap.
- Added a preview-by-default transactional remediation command that preserves full provenance and cleans only newly orphaned source nodes.
- Moved all existing out-of-horizon QGIP facts to recoverable quarantine.

### Validation

- [`source-horizon-validation-20260808T163200Z.md`](source-horizon-validation-20260808T163200Z.md) records root-cause samples and exact data impact.
- Preflight 4,198 outliers across 80 years; postflight 0 published outliers; second apply changed 0 rows.
- Focused suite: 9 passed; registry suite: 11 passed; full backend suite: 591 passed.
- Graph/data integrity audit: 0 hard failures and 0 orphans; SQLite integrity `ok`.

### Data impact

4,198 invalid QGIP facts were moved from publication to `facts_pending_attribution`; 3,522 exclusive orphan nodes were removed. All moved facts retain source provenance and a deterministic reason.

### Remaining risks

Some in-horizon QGIP years may still require source-file-based reattribution; the horizon prevents impossible publication but does not replace the comprehensive QGIP reconciliation in item 7.2.

### Next item

Plan section 4.1: run the no-write semantic and reconciliation preflight for the 2019-20 through 2023-24 historical FBO archive.

## Milestone: Historical FBO no-write preflight

### Item

Plan section 4.1.

### Result

Conditional pass. The already-loaded archive is semantically suitable for an exact-only related graph pack, but its shared retrieval/cached-copy attribution must be repaired before edge deployment.

### Evidence

- [`fbo-archive-crosswalk-20260808T163747Z.md`](fbo-archive-crosswalk-20260808T163747Z.md) and its JSON companion enumerate all 415 facts across FY2019-20 through FY2023-24.
- Every edition contains 83 facts: 71 source-native function/subfunction rows and 12 reported totals.
- All facts are `actual_accrual_expense / accrual / audited_actual`; semantic failures are zero.
- The existing COFOG crosswalk supplies evidence for all ten mapped budget functions in all five years: 50/50 comparisons, with differences retained strictly as non-additive evidence.
- `Agriculture, forestry and fishing`, `labour and employment affairs`, and `Other purposes` remain explicit unmapped FBO classifications.
- Twelve exact-label additions/removals are typographic variants across three subfunction labels; there are no substantive classification changes.

### Citation finding

All 415 fact locators, landing URLs and official resource URLs identify their exact fact year. However, every fact shares one retrieval row: its resolved URL identifies 2019-20 and its local path identifies the 2023-24 PDF. Locator cached paths likewise identify 2023-24 for every fact. Consequently zero facts currently satisfy all six exact-year citation signals.

### Validation

- Audit unit suite: 4 passed.
- Full backend suite: 595 passed, one dependency deprecation warning.
- Ruff and diff checks passed.
- A repeated full audit left the ignored live database byte-identical: SHA-256 `6a3ffc8fd8046a437c5f8104067f6fd5f5613243cdf00a84aafdf54eb7f3a17d` before and after.

### Data impact

None. The audit opens the database with SQLite `mode=ro`.

### Next item

Plan section 4.2: first repair exact per-edition retrieval/cached-copy attribution, then add the reversible, idempotent, exact-only historical FBO graph pack.

## Milestone: Historical FBO exact-only graph pack

### Item

Plan section 4.2.

### Changes

- Added per-financial-year cached-file attribution and corrected stale same-content retrieval metadata during ingestion.
- Reingested the same 415 facts with five exact source retrievals and zero quarantine or duplication.
- Registered separate historical FBO related and source-native edge sets, both augmenting and exact-only.
- Added a reversible rebuilder that attaches ten mapped budget functions while retaining three unmapped classifications as explicit exceptions.
- Enabled factless related navigation nodes only when exact-year fact descendants exist.
- Excluded related navigation folders from additive totals using typed relationship metadata.

### Validation

- [`historical-fbo-edge-pack-20260808T165500Z.md`](historical-fbo-edge-pack-20260808T165500Z.md) records exact counts and live/disposable rebuild evidence.
- Exact-year citation coverage: 415/415 across all six audited signals.
- Stable live second rebuild: 75 source-native edges and 11 related edges.
- Dashboard audit: zero hard failures, unchanged FY2022-23/FY2023-24 roots, no fallback facts and complete leaf citations.
- Graph/data audit: zero hard failures and zero orphans; SQLite integrity `ok`.

### Data impact

Only retrieval attribution, source-native navigation nodes and the two explicitly scoped historical FBO edge sets changed in the ignored live database. Facts and canonical totals are unchanged.

### Next item

Plan section 4.3: freeze historical traversal totals, branch/year semantics, citations and explicit unmapped exceptions as executable regressions.

## Milestone: Historical FBO traversal regression

### Item

Plan section 4.3.

### Changes

- Updated the reviewed dashboard projection fixture for the intentionally deployed historical FBO edges.
- Added API regressions for FY2022-23 and FY2023-24 root totals, first-ring count, safe-depth contract, FBO branch summaries, exact years, accrual/audited semantics and non-additive relationship inheritance.
- Added a database regression proving the three documented unmapped FBO classifications are not silently wired.

### Validation

- [`historical-fbo-traversal-20260808T170000Z.md`](historical-fbo-traversal-20260808T170000Z.md) and JSON: fixture match, zero hard failures, zero duplicate semantic edges and zero cycles.
- FY2022-23 root remains $639.703b; FY2023-24 remains $687.277b.
- Both years retain eleven canonical first-ring functions, gain eleven exact-only FBO routes, use zero fallback facts and have 69/69 cited fact-bearing leaves.
- API safe visible depth remains 2 pending item 4.4; typed branch metadata reports audited FBO related depth 2 without claiming a third FBO semantic ring.
- Focused traversal suite: 10 passed; full backend suite: 598 passed, one dependency deprecation warning.
- Ruff and diff checks passed.

### Data impact

None beyond item 4.2. This milestone freezes the reviewed deployed projection behavior.

### Next item

Plan section 4.4: expose safe versus available depth and related branch families without changing canonical totals.

## Milestone: Safe-depth and branch UX

### Item

Plan section 4.4.

### Changes

- Replaced automatic related-pack preference with canonical-default, user-selected branch families.
- Renamed frontend maximum traversal depth to visible depth and kept additive depth as separate API metadata.
- Added selected/available/default safe-level controls and a Show maximum action.
- Added Additive/Related, Navigation/Data, selected/source year, basis and estimate-status disclosures to hover/click interaction.
- Added the same explicit branch selection behavior to Combined and retained canonical behavior for debt.

### Validation

- [`safe-depth-branch-ux-20260808T170500Z.md`](safe-depth-branch-ux-20260808T170500Z.md) records safeguards and executable checks.
- Chart semantic unit suite and TypeScript passed.
- Accepted lint baseline remained 25 errors / 13 warnings.
- Production build passed with 12 static pages.

### Data impact

None. Canonical totals, API responses, graph edges and citations are unchanged.

### Next item

Plan section 5.1: inventory/register the required 2022-23 and 2023-24 Statement 6/PBS editions with checksums and original URLs before building a genuine historical third ring.

## Milestone: Historical Statement 6/PBS edition acquisition

### Item

Plan section 5.1.

### Changes

- Registered separate source identities for March 2022-23, October 2022-23 and 2023-24 Budget Paper No. 1/Statement 6 editions.
- Registered a directly archived Treasury PBS representative for each target vintage.
- Acquired all six official PDFs through the standard procurement snapshot pipeline with original URLs and SHA-256 manifests.
- Reused the already-deployed historical FBO acquisitions rather than duplicating them.
- Added registry regressions that prevent March and October 2022-23 from collapsing into one source identity.

### Validation

- [`historical-budget-edition-acquisition-20260808T170741Z.md`](historical-budget-edition-acquisition-20260808T170741Z.md) records all six URLs, byte counts, page counts and checksums.
- Procurement run: 6 downloaded, 0 failed; all PDFs readable; 2,409 pages total.
- Registry loaded 373 unique sources.

### Scope boundary

The archive pages expose direct Treasury PBS files but only name the other portfolios as externally hosted at release. This milestone does not claim complete all-portfolio coverage; unresolved portfolios require verified official URLs and separate edition-bearing identities.

### Data impact

Raw acquisition only. No facts, edges, totals or API behavior changed.

### Next item

Plan section 5.2: add edition fixtures and bounded Statement 6 adapters before extracting any historical rows.

## Milestone: Historical Budget Paper expense adapters

### Item

Plan section 5.2.

### Changes

- Added one edition-configured adapter for March 2022-23 Statement 5/Table 5A.1 and the October 2022-23/2023-24 Statement 6/Table 6A.1 layouts.
- Extracted function, subfunction and all 13 published component tables per edition with exact page/table/year/vintage locators.
- Excluded historical actual columns from the budget-estimate mappings; audited actual coverage remains in FBO.
- Added three source-specific mappings and executable published-total/layout regressions.

### Validation

- [`historical-statement-expense-adapters-20260808T172116Z.md`](historical-statement-expense-adapters-20260808T172116Z.md) records edition contracts, counts and totals.
- 2,146 rows loaded twice on an isolated database copy: zero quarantine, 2,146 distinct fact keys, one retrieval/checksum per edition, integrity `ok`.
- Real-PDF regression suite: 5 passed.
- Full backend regression suite: 605 passed, one dependency deprecation warning.
- Live probe exposed flat additive projection risk; exact probe rows were removed and the restored dashboard fixture matches with zero hard failures.

### Data impact

Acquired PDFs and reproducible staging CSVs only. Historical mappings are marked adapter-only pending graph visibility; no historical Statement expense facts remain deployed in `data/facts.db` and dashboard behavior is unchanged.

### Next item

Plan section 5.3: historical Treasury PBS edition fixtures/adapters, still withheld from dashboard deployment until item 5.4.

## Milestone: Historical Treasury PBS adapter

### Item

Plan section 5.3.

### Previous behavior

An uncommitted-to-the-ledger extractor (`scripts/ingest/extractors/historical_treasury_pbs.py`, commit `4efd5e8`) existed for the three acquired Treasury PBS editions but had never run successfully: every edition raised `duplicate year/category/status rows` on first execution, with no test or report.

### Root cause

Four distinct defects, each verified against the raw PDF text before being changed: (1) the "Outcome N Totals by appropriation type" cross-program reconciliation table was misattributed to the last-seen program; (2) multi-item appropriation-type headings (e.g. "Ordinary annual services") only reached their first child line, leaving siblings under an unqualified label; (3) two ATO programs' five year-columns were split by pypdf across 2-3 physical lines and silently dropped entirely; (4) a three-line label wrap left its bare numeric line orphaned, and a separate "Movement of administered funds between years" memo table reused the program-header pattern and corrupted Treasury Program 1.9.

### Changes

- Added `OUTCOME_TOTALS_RE` and a "Movement of administered" boundary to stop attributing reconciliation-table rows to a program.
- Added persistent `heading` state (`KNOWN_HEADINGS`, `STANDALONE_LABEL_PREFIXES`) so multi-item appropriation-type headings apply to every sibling, not just the first.
- Added a bounded `_merge_wrapped_amount_lines` pre-pass that reassembles rows whose amount columns pypdf split across lines, provably only touching lines that do not already match the standard five-token pattern.
- Allowed `_amount_line` to recognise a label-free, fully numeric line so an already-buffered multi-line label is not orphaned from its amounts.
- Added `tests/ingest/test_historical_treasury_pbs.py` (12 tests): layout/count fixtures per edition, uniqueness, vintage distinctness (March vs October 2022-23), component-sum-to-published-total reconciliation with an explicit, reviewed rounding-exception whitelist, exclusion of reconciliation-table content, and exact-year citation/locator completeness.

### Validation

- [`historical-treasury-pbs-adapter-20260811T173656Z.md`](historical-treasury-pbs-adapter-20260811T173656Z.md) records full per-edition evidence.
- All three editions extract with zero exceptions: 710/675/620 rows; program-row counts exactly equal programs×5 years (215/215/195); component sums reconcile to every published program total except 3 rows (Treasury 1.1, March edition) within the documents' own documented $1,000 rounding.
- New suite: 12 passed. Full backend/ingest suite: 617 passed (605 baseline + 12 new), 0 failures, 0 regressions. `ruff check` on extractor and test file: passed.
- Real-PDF regression only; no facts.db or graph write performed.

### Data impact

Staging only. Wrote `data/staging/breakdowns/federal_pbs_2022_23_{march,october}_treasury.csv` and `federal_pbs_2023_24_treasury.csv` (gitignored, not part of `data/facts.db`). No fact, edge, canonical lineage or dashboard-visible content changed; root totals and existing PBS graph are untouched.

### Remaining risks

Per the 5.2 milestone's boundary and Wave 3 sequencing, these rows remain deliberately withheld from `data/facts.db`/graph deployment until item 5.4 builds the Statement 6 crosswalk and exact-only related edges. Item 5.5 (NDIA repair, current-PBS coverage-by-portfolio report, quarantine precision review) remains not started.

### Next item

Plan section 5.4: crosswalk historical PBS program detail beneath matched Statement 6 nodes and expose it as an exact-only related branch. Investigation for this milestone found that item 5.4 has two prerequisite steps neither 5.2 nor 5.3 performed (both were deliberately staging-only):

1. **Historical fact loaders.** Neither the historical Statement 6 rows (`data/staging/breakdowns/federal_budget_statement_6_2022_23_{march,october}.csv`, `federal_budget_statement_6_2023_24.csv`, from item 5.2) nor the historical PBS rows (`federal_pbs_2022_23_{march,october}_treasury.csv`, `federal_pbs_2023_24_treasury.csv`, from item 5.3) are in `data/facts.db` yet. A loader for each is needed, following this repository's established idempotent/conflict-safe upsert pattern and the canonical-lineage rule from item 3.6 (these are related evidence, so `canonical_dataset_id` must stay null, never assigned as if they were canonical annual facts).
2. **Exact-year crosswalk, not the existing year-agnostic one.** `scripts/ingest/pbs_s6_crosswalk.py` / `config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml` already link the *current* PBS edition under Statement 6 with year-agnostic, portfolio-level `related_breakdown` edges. That pattern cannot be reused as-is for the historical editions: per the plan's non-negotiable rules and the historical FBO precedent (item 4.2), historical PBS-under-Statement-6 edges must be `fallback_policy: exact_only` and carry exact publication-edition/vintage metadata, not year-agnostic linkage — March and October 2022-23 must remain distinct, unmerged crosswalk targets.

Given the plan's Wave 3 exit gate only requires "at least one 2022-23 and one 2023-24 representative function" with a verified route, the next iteration should scope 5.4 to one or two representative Treasury programs/functions end-to-end (loader + exact-only edge set + regression test + validation report) rather than a full-portfolio rollout, then expand coverage in a follow-up once the pattern is proven.

## Milestone: Historical fact loading and a critical additivity defect

### Item

Plan section 5.4, prerequisite 1 (historical fact loaders), plus a defect found and fixed before any deployment.

### Previous behavior

Historical Statement 6 (item 5.2) and PBS (item 5.3) rows existed only as staged CSVs. Their natural mapping configuration used `measure_type: budget_estimate`, the same `compatibility_group: budget_expense` used by every other budget-basis fact.

### Root cause

`src/backend/routers/v2/dashboard.py::_fact_rows()` selects `mode='budget'` base facts with a bare `WHERE m.compatibility_group = 'budget_expense' AND ... AND financial_year = ?` and no per-source de-duplication. Statement 6 (function-level) and PBS (program-level) both represent near-complete, overlapping views of the same underlying expenditure; loading either family under `budget_expense` was verified on a disposable database copy to inflate the `federal_budget_2022_23`/`2023_24` root totals by roughly 400-3,000x (e.g. $1.63b → $2.34 trillion from Statement 6 alone) - a direct violation of the "no cross-compatibility-group/incompatible summation" invariant. Caught entirely on a disposable copy before the live database was touched.

### Changes

- Added migration `018_historical_related_evidence_measures.sql`: two new measures (`historical_bp1_statement6_expense`, `historical_treasury_pbs_program_expense`), each with its own compatibility group, `additive_across_nodes=0`, `root_total_allowed=0` - structurally invisible to every existing mode's raw fact walk, per the established one-measure-one-compatibility-group convention (migration 016).
- Updated all 6 mapping YAMLs (3 Statement 6, 3 PBS) to the new measure types; `deployment_status` changed from `adapter_only_pending_graph_visibility` to `related_evidence_exact_only`.
- Loaded all 6 mappings into the live `data/facts.db` after full disposable-copy validation and a live backup.
- Added `tests/api/test_historical_related_evidence_isolation.py` (5 tests): schema-level guard that the new measure types can never anchor a root total, canonical-lineage-null guard, and a live API regression asserting `mode=budget` root totals for 2022-23/2023-24 are byte-identical to the pre-existing baseline.

### Validation

- [`historical-related-evidence-measures-20260811T180000Z.md`](historical-related-evidence-measures-20260811T180000Z.md) records the full defect investigation and before/after evidence.
- Disposable copy: 6 mappings loaded 4,151 facts total, 0 quarantined; idempotent second run; 0 canonical assignment; `task9_sql_integrity_checks.py` 0 hard failures; `dashboard_depth_audit.py --check-fixture` byte-identical to the reviewed golden fixture for all 10 required projections.
- Live deployment: backup taken first (`facts-20260811T175309Z.db`, baseline 285,117 facts); migration applied idempotently; facts 285,117 → 289,268 (+4,151, exact match to the disposable-copy delta); `task9_sql_integrity_checks.py` 0 hard failures; `dashboard_depth_audit.py --check-fixture`: **`fixture_matches: true`**.
- New suite: 5 passed. Full backend suite before and after live deployment: 617 passed both times, 0 regressions. `ruff check`: passed.

### Data impact

`data/facts.db`: +2 `measure_definitions` rows, +4,151 facts under the two new mode-invisible compatibility groups. 0 changes to any existing fact, edge, or canonical assignment.

### Dashboard impact

None observable. The new facts are loaded but structurally unreachable from any current mode/route until an explicit edge set attaches them (item 5.4's remaining work).

### Remaining risks

The facts are safely loaded but not yet reachable from the dashboard by design. Completing item 5.4 still requires: (1) a declarative exact-only `related_breakdown` edge set matching specific Statement 6 nodes to their historical PBS program nodes by exact name/year (not the existing current-edition bridge's portfolio-substring heuristic, which the plan's "never infer missing hierarchy from label similarity alone" rule argues against reusing), and (2) extending `dashboard_tree()` to call `attach_related_to_tree` (or equivalent) for `mode == "budget"`, since today only `mode == "actuals"` does - a live-API behavior change requiring its own dedicated test coverage.

### Next item

Plan section 5.4, prerequisite 2: build the exact-only edge set and extend `dashboard_tree()`'s budget-mode branch, scoped to one verified 2022-23 and one 2023-24 representative route per the Wave 3 exit gate.

## Milestone: Historical Treasury PBS program detail under Statement 6 (item 5.4 complete)

### Item

Plan section 5.4, prerequisite 2.

### Discovery that changed the plan

Investigating how to expose the edges revealed `dashboard_tree()` calling `attach_related_to_tree` only for `mode == "actuals"`, never `mode == "budget"` - the router extension flagged as required in the prior milestone. Reading the router further found a *second*, mode-agnostic route, `dashboard_item_children` (`/v2/dashboard/item/{fact_id}/children`), which already resolves `related_breakdown` edges for any node by id regardless of mode - this is how the frontend's lazy-loaded drill-down already works, and it already carries the existing (currently dormant) current-edition `pbs_programs_all_under_s6` edges. No router code change was needed at all; only the edge set itself.

### Changes

- Added `config/breakdowns/crosswalks/historical_pbs_treasury_under_statement6.yaml`: two edition-locked pairings (March 2022-23, 2023-24), reusing the already-reviewed "Treasury -> General public services" portfolio-ownership assessment from the current-edition crosswalk rather than the unreviewed substring-heuristic bridge extractor.
- Registered the `historical_pbs_treasury_under_statement6` policy in `config/breakdowns/edge_sets.yaml`: `related_breakdown`, `augment`, `fallback_policy: exact_only`.
- Added `scripts/ingest/historical_pbs_s6_crosswalk.py`, an idempotent edge builder (dry-run by default, `--apply` to commit).
- Found and fixed a program-node selection defect: a literal `NOT LIKE '%/ Administered /%'` filter let 3 mis-scoped National Housing Finance and Investment Corporation component rows (published under `scope="Unscoped"`) through as if they were whole programs (42 vs the correct 39 for 2023-24). Fixed by matching the extractor's fixed path-segment count instead of specific scope literals.
- Deployed 82 edges live (43 March-2022-23 + 39 2023-24 Treasury programs).
- Updated the reviewed `tests/fixtures/dashboard_projection/baseline.json` (`graph.edge_count`: 14,253 -> 14,335 - the sole, reviewed delta).
- Added `tests/api/test_historical_pbs_s6_crosswalk.py` (7 tests).

### Validation

- [`historical-pbs-s6-crosswalk-20260811T221243Z.md`](historical-pbs-s6-crosswalk-20260811T221243Z.md) records full evidence.
- Disposable-copy dry run, apply, and idempotent re-apply (0 new edges second time); live API check via FastAPI `TestClient` confirmed all 43/39 children resolve with `fallback_reason: exact_year_match`, `is_year_fallback: false`, correct source/compatibility metadata, and a non-additive banner; a year present in neither source returned empty with **no** fallback.
- `mode=budget` root totals for FY2022-23/2023-24 confirmed unchanged after edge deployment.
- Live deployment: backup taken first; 82 edges applied; second `--apply` inserted 0; `task9_sql_integrity_checks.py` 0 hard failures; `dashboard_depth_audit.py --check-fixture` true after the reviewed fixture update.
- New suite: 7 passed. Full backend suite: 629 passed (622 + 7), 0 regressions. `ruff check`: passed.

### Data impact

`data/facts.db`: +82 `breakdown_edges` rows only; no fact, node, or existing edge changed. `tests/fixtures/dashboard_projection/baseline.json`: `graph.edge_count` updated.

### Dashboard impact

Drilling into the March 2022-23 or 2023-24 Statement 6 "General public services" function now surfaces the Treasury portfolio's individual program totals as clearly-labeled, non-additive related evidence with exact-year citations. No other function or portfolio gained depth from this milestone; canonical Statement 6 totals are unchanged.

### Remaining risks

Scope is Treasury-only, two editions, function-level, deliberately satisfying the Wave 3 exit gate rather than a full rollout. Extending to more portfolios/editions is future work using the same edition-locked pattern. Item 5.5 (NDIA repair, current-PBS coverage-by-portfolio report, quarantine precision review) remains not started.

### Next item

Plan section 5.5: NDIA repair, current-PBS coverage-by-portfolio report, and quarantine precision review - or continue to Wave 4 (reusable explorer platform) per priority order.

## Milestone: NDIA PBS repair (item 5.5, part 1 of 4)

### Item

Plan section 5.5, sub-item 1: "Repair `federal_pbs_2026_27_ndia` with a source-specific fixture."

### Previous behavior

A real, acquired 22-page NDIA PBS PDF published zero facts via the generalized `pbs_programs_all.py` adapter, recorded as `adapter_broken` across several prior reports.

### Root cause

Two defects: (1) the generalized extractor's multi-portfolio Table 2.1 layout assumptions do not match this document's single-entity, "Revenue from Government"/"Total for Program N" structure; (2) `main()`'s cross-document dedupe key `(portfolio, program_label, fy, status, amount)` has no source_id component, and NDIA is assigned the same portfolio label ("Health Disability and Ageing") as an unrelated, larger, separately-loaded document - even the 86 rows the generalized extractor *could* parse were silently discarded as apparent duplicates.

### Changes

- Added `scripts/ingest/extractors/federal_pbs_2026_27_ndia.py`, a bounded source-specific adapter (1 entity, 1 outcome, 2 programs, Table 2.1.1), excluding the "Outcome 1 totals by resource type" reconciliation section using the same pattern fixed for Treasury in item 5.3.
- Found and fixed a second, more serious defect before deployment: NDIA's "Payment from related entities" revenue (~$38-40b) overlaps with the portfolio department's own already-loaded "Program 3.2 – National Disability Insurance Scheme" administered expense (~$34-38b) under `federal_pbs_programs_all` - confirmed directly against the live database. Loading NDIA under the shared `budget_estimate` measure was verified on a disposable copy to add NDIA's entire $56.5b FY2029-30 outcome total on top of the existing root total.
- Added migration `019_ndia_pbs_measure.sql`, isolating NDIA facts under their own `federal_pbs_2026_27_ndia_expense` measure/compatibility group (`additive_across_nodes=0`, `root_total_allowed=0`), the same pattern established in item 5.4.
- Added `tests/ingest/test_federal_pbs_2026_27_ndia.py` (5 tests) and `tests/api/test_ndia_pbs_isolation.py` (3 tests).

### Validation

- [`ndia-pbs-repair-20260811T230253Z.md`](ndia-pbs-repair-20260811T230253Z.md) records full evidence.
- Extractor: 50 rows (40 component + 10 program), component sums reconcile exactly (0 mismatches, no rounding needed) to every published "Total for Program N" row.
- Disposable-copy dry run under the naive measure type reproduced the $56.5b inflation (proof of the defect); the corrected isolated measure type left every one of the 10 required projections byte-identical to the reviewed baseline.
- Live deployment: backup taken first; 50 facts loaded (289,268 → 289,318); idempotent second run; `task9_sql_integrity_checks.py` 0 hard failures; `dashboard_depth_audit.py --check-fixture`: **true**.
- New suites: 8 passed. Full backend suite: 637 passed (629 + 8 new), 0 regressions. `ruff check`: passed.

### Data impact

`data/facts.db`: +1 `measure_definitions` row, +50 facts under the new mode-invisible compatibility group. No existing fact, node, edge, or canonical assignment changed.

### Dashboard impact

None observable - NDIA facts are correctly extracted and safely loaded but, like historical Statement 6/PBS before its crosswalk, remain structurally unreachable until a future related_breakdown edge deliberately attaches them.

### Remaining risks

Only sub-item 1 of item 5.5's four sub-asks is complete. Still open: current-PBS coverage-by-portfolio report, malformed-label classifier precision improvements (documented recurring across many portfolios in `ops/reports/pbs-semantic-quality-audit-20260803T200915Z.md`, a substantial separate task against the 597-line generalized extractor), and quarantine precision review (page/table-evidence-only, never bulk promote).

### Next item

Plan section 5.5, sub-items 2-4: current-PBS coverage-by-portfolio report, classifier precision improvements, quarantine precision review.

## Milestone: Current-PBS coverage-by-portfolio report (item 5.5, part 2 of 4)

### Item

Plan section 5.5, sub-item 2: "Produce current unmapped-node coverage by source origin and portfolio."

### Changes

None to code. Re-ran the existing `scripts/ingest/pbs_s6_crosswalk.py --report-only` (already scoped exactly to this ask - a portfolio-level mapped/ambiguous/unmapped breakdown against `pbs_programs_all_under_s6.yaml`) against the live database, refreshing it after the NDIA repair.

### Result

[`pbs-statement6-crosswalk-coverage-20260811T230702Z.md`](pbs-statement6-crosswalk-coverage-20260811T230702Z.md)/`.csv`: 2,957 live PBS program nodes; 2,413 mapped (14,396 facts); 372 ambiguous (portfolio spans multiple Statement 6 functions with no dominant destination - deliberately left unmapped rather than guessed, per the crosswalk's own evidence-tier design); 172 unmapped. All 172 unmapped nodes trace to 9 documents in the parliamentary-services family (Senate, House of Representatives, Parliamentary Budget Office, Department of Parliamentary Services across editions) whose `_portfolio_from_source()` label is effectively their own document identity rather than a real government portfolio - i.e. the portfolio column already functions as a source-origin identifier for exactly the rows that matter (the unmapped ones).

### Remaining risks

A true per-individual-document origin column for the 2,413 *mapped* nodes (there are ~63 distinct PBS PDFs feeding the combined `federal_pbs_programs_all` source) is not built - the existing `_facts_by_origin()` mechanism in `ingestion_coverage_audit.py` could supply it but has not been joined into this report. Not attempted in this session; recorded as a scoped follow-up rather than claimed complete.

### Next item

Plan section 5.5, sub-items 3-4 (classifier precision on malformed labels; quarantine precision review) - each a substantial, separate task against the 597-line generalized `pbs_programs_all.py` extractor and the ~40,600-row PBS/bridge quarantine set respectively. Deliberately deferred to a dedicated session rather than rushed; not attempted here. Continue to these, or to Wave 4 (reusable explorer platform, item 6.1) per the plan's priority order.

## Milestone: PBS classifier precision and quarantine review (item 5.5 complete)

### Item

Plan section 5.5, sub-items 3-4: classifier precision on malformed labels; quarantine precision review with page/table evidence, no bulk promotion.

### Previous behavior

`pbs_label_classifier.py`'s `unknown`/`no_confident_signal` bucket (572 of 35,601 quarantined `federal_pbs_programs_all` rows) contained real, unaddressed precision gaps. More seriously, undiscovered until this investigation: 158 unique genuinely garbled, multi-column-flattened Section 3 fragments (699 row instances across years) were being **incorrectly accepted** as real `program` facts and published.

### Root cause

Two structural signals the classifier had no rule for: (1) standard GFS/AASB single-word revenue/asset vocabulary ("Taxes", "Fees", "Fines", "Loans", "Leases", "Land") missing from the curated `FINANCIAL_STATEMENT_LINE_ITEMS` set; (2) two embedded dollar values plus an accounting-heading keyword, and a run of three or more bare `-`/soft-hyphen placeholder tokens, both strong concatenated-row signals with no existing detector.

### Changes

- `scripts/ingest/pbs_label_classifier.py`: added the 6 vocabulary terms; added `BARE_DASH_RUN` detection (`embedded_bare_dash_run`) and a `two_embedded_value_tokens_with_heading` check, both inserted in the existing "malformed" precedence tier.
- `tests/ingest/test_pbs_label_classifier.py`: 6 new tests (29 total) pinning real, verbatim quarantined label strings, including explicit guards that the new rules do not over-fire (single bullet dash, two values with no heading keyword).

### Validation

- [`pbs-classifier-precision-20260812T025148Z.md`](pbs-classifier-precision-20260812T025148Z.md) records the full methodology and evidence.
- Isolated the classifier-only effect from unrelated corpus staleness by classifying the exact same 103,945-row extracted label set with pre-change and post-change code and diffing: **zero** labels newly became `program`/`outcome`/`component` (publishable set can only shrink); 158 unique labels moved `program` -> `malformed_concatenated_row`, individually reviewed and confirmed every one is genuinely garbled, not a real program name.
- New suite: 6 passed. Full backend suite: 643 passed (637 + 6), 0 regressions. `ruff check`: passed.
- No live database write; `federal_pbs_programs_all` fact count confirmed unchanged (17,482) throughout.

### Data impact

None. All validation ran against a disposable copy or pure in-memory classification.

### Dashboard impact

None yet - the fix is validated but not deployed (see "New finding" below).

### Quarantine review disposition

Reviewed `federal_pbs_programs_all`'s full `unknown` bucket and the classifier-diff-identified transitions against real page/table locator evidence; 0 bulk promotions; remaining quarantined material re-categorized more precisely, not released. `qld_qgip_expenditure` (item 3.7/7.2) and `federal_pbs_programs_s6_bridge` (legacy derived product) explicitly out of scope with rationale recorded.

### Remaining risks

New finding, tracked as plan item 5.5b: the live `federal_pbs_programs_all` corpus is stale relative to current code (would nearly double published facts if reloaded) - this predates this session and is not caused by it, but deploying it is a separate, larger, dedicated decision deliberately not folded into this fix.

### Next item

Plan item 5.5b (`federal_pbs_programs_all` stale-corpus reload) - or continue to Wave 4 (reusable explorer platform, item 6.1) per the plan's priority order, since 5.5's four named sub-items are now genuinely closed.

## Milestone: Contracts explorer truthful pagination (Wave 4 started)

### Item

Plan section 6.3, first migration ("Contracts — remove the 200-row truncation"), toward the Wave 4 exit gate.

### Previous behavior

The contracts explorer page fetched a hardcoded `limit: 200` and presented that single page as if it were the complete contract list, with no indication more existed.

### Root cause

The frontend page pre-dated item 3.4's `/v2/tree` cursor-pagination/truthful-totals work and was never updated to consume it, even though the backend capability already existed.

### Changes

- `src/frontend/app/explorers/contracts/page.tsx`: consumes `total_count`/`total_value`/`next_cursor` from the existing `/v2/tree` endpoint; shows the true scope-wide total alongside the loaded count; adds a "Load next 200" button; state updates happen atomically in the fetch callback (avoids a new `react-hooks/set-state-in-effect` lint violation).

### Validation

- [`contracts-pagination-fix-20260812T030352Z.md`](contracts-pagination-fix-20260812T030352Z.md) records full evidence.
- `tsc --noEmit`, `lint:ci` (unchanged baseline), `build` (12 static routes), `test:unit`: all passed.
- Live browser verification via Playwright against `next dev` + a local backend bound to the real `data/facts.db`: confirmed the true total ("9,036 contracts for 2024-25, total value $39,337,071,294 — 200 loaded"), a working Load-more (400 loaded, total unchanged), an atomic year switch (2023-24: "2,836 contracts... $25,994,214,805"), and zero console errors.

### Data impact

None - frontend-only change, no backend/API/database change.

### Dashboard impact

Once deployed (see the critical finding below), users can see and reach every contract for a year, not just the first 200, with a truthful total always visible.

### Critical finding

While validating this fix, discovered the **public production API has not been redeployed since before item 3.4** (commit `dde1c08`) - see the callout at the top of this ledger and the milestone report's "Critical finding" section for full evidence. Every backend code change made across this entire remediation program (items 3.4 onward) is committed and tested on `main` but not yet live for real users. Deliberately not deployed as part of this autonomous loop; flagged for an explicit human decision.

### Remaining risks

Hierarchical agency/category/supplier/notice depth and true server-side search remain part of the larger item 6.1 reusable explorer API. The production deployment lag above is the single most consequential open item in this program.

### Next item

Item 6.1 (reusable explorer API/registry) for the remaining Wave 4 families, or resolve the production deployment lag first (a decision for the user, not this loop, given its live/hard-to-reverse nature).

## Milestone: VIC Output Performance explorer surfacing

### Item

Plan section 6.3: "VIC output performance — immediate surfacing of the seven already-loaded output nodes."

### Previous behavior

14 facts (7 outputs x actual/budget) have been loaded and live since 2026-08-07 (`ops/reports/vic-output-performance-implementation-20260807T173750Z.md`), reachable via the generic `/v2/tree` endpoint, but zero frontend page existed to surface them - confirmed by a repository-wide search.

### Changes

- Added `src/frontend/app/explorers/vic-output-performance/page.tsx`: fetches both `actual` and `budget` estimate statuses from the existing `/v2/tree` endpoint (no backend change) and merges them by output name into an Output / Actual / Target / Variance table with a citation panel.
- Registered in `src/frontend/app/explorers/page.tsx`'s index.

### Validation

- [`vic-output-performance-explorer-20260812T034520Z.md`](vic-output-performance-explorer-20260812T034520Z.md) records full evidence.
- `tsc --noEmit`, `lint:ci` (unchanged baseline), `build` (13 static routes), `test:unit`: all passed.
- Live browser verification via Playwright: all 7 rows rendered correctly (first row "Budget and Financial Advice $46,300,000 $39,000,000 $7,300,000" matches the database exactly), citation panel populated with full workbook/sheet/cell locator on click, zero console errors.

### Data impact

None. No backend, database, or API contract change.

### Dashboard impact

Once deployed (see the production-deployment-lag finding), all seven Victorian departmental outputs' actual-vs-target total cost become reachable and citable for the first time, clearly separated from the annual additive tree.

### Remaining risks

The 70 non-dollar KPI rows from the same workbook remain deliberately deferred, unchanged from the original implementation. Only FY2024-25 is shown since it is the only loaded year; no year selector was added to avoid dead UI or inviting a future-year fallback.

### Next item

Item 6.1 (reusable explorer API/registry), or the remaining item 6.3 family migrations (PBS, grants, ACT invoices).

## Milestone: Grants explorer

### Item

Plan section 6.3, second migration: "Grants — portfolio/program -> award/recipient, never additive to expenditure."

### Previous behavior

2,486 GrantConnect award facts have been loaded and live, but no frontend page existed to surface them.

### Changes

- Added `src/frontend/app/explorers/grants/page.tsx`, mirroring the contracts explorer's pagination pattern (same `compatibility_group`/`accounting_basis`, `estimate_status: award` instead of `contract` - the same `/v2/tree` endpoint applies with no backend change).
- Registered in `src/frontend/app/explorers/page.tsx`'s index.
- Page copy explicitly states grant awards are never additive to expenditure, matching the plan's exact wording.

### Validation

- [`grants-explorer-20260812T035705Z.md`](grants-explorer-20260812T035705Z.md) records full evidence.
- `tsc --noEmit`, `lint:ci` (unchanged baseline after fixing one new violation introduced by copying an unnecessary resync effect), `build` (14 static routes), `test:unit`: all passed.
- Live browser verification via Playwright: truthful total ("2,486 grant awards for 2024-25, total value $35,965,945,219 — 200 loaded"), working Load-more (400 loaded), correct citation, zero console errors.
- Full backend suite: 643 passed, 0 regressions (frontend-only change).

### Data impact

None. No backend, database, or API contract change.

### Dashboard impact

Once deployed, all 2,486 FY2024-25 grant awards become reachable and truthfully paginated, explicitly labeled non-additive to expenditure.

### Remaining risks

Hierarchical portfolio/program -> award/recipient depth and server-side search remain part of the larger item 6.1 explorer API.

### Next item

Item 6.1 (reusable explorer API/registry), or the remaining item 6.3 family migrations (PBS, ACT invoices).

## Milestone: ACT notifiable invoices explorer

### Item

Plan section 6.3, fifth migration: "ACT invoices — agency -> supplier/invoice cash-outflow product."

### Previous behavior

46,714 `act_notifiable_invoices` facts (13 financial years, 2005-06 through 2026-27) have been loaded and live, but no frontend page existed.

### Changes

- Added `src/frontend/app/explorers/act-invoices/page.tsx`, the same proven `/v2/tree`-backed pagination pattern used for contracts and grants (no backend change). Node labels are already published as `AGENCY / SUPPLIER-OR-DESCRIPTION`.
- Registered in `src/frontend/app/explorers/page.tsx`'s index.
- Verified before writing the page that `cash_outflow` is shared with an unrelated source (`bp1_outlays_by_function_pre_fbo`) but a different `estimate_status`, so `estimate_status=invoice` correctly scopes queries to ACT invoices only.

### Validation

- [`act-invoices-explorer-20260812T041103Z.md`](act-invoices-explorer-20260812T041103Z.md) records full evidence.
- `tsc --noEmit`, `lint:ci` (unchanged baseline), `build` (15 static routes), `test:unit`: all passed.
- Live browser verification via Playwright: truthful total ("4,742 invoices for 2024-25, total value $1,004,198,107 — 200 loaded"), working Load-more (400 loaded), correct citation, zero console errors.
- Full backend suite: 643 passed, 0 regressions (frontend-only change).

### Data impact

None. No backend, database, or API contract change.

### Dashboard impact

Once deployed, all ACT notifiable invoices across all 13 loaded years become reachable and truthfully paginated.

### Remaining risks

A true agency -> supplier -> invoice drill-down hierarchy and server-side search remain part of the larger item 6.1 explorer API.

### Next item

Item 6.1 (reusable explorer API/registry), or item 6.3's remaining migration (PBS - blocked behind resolving item 5.5b's stale corpus first for a correct fact count), or item 5.5b itself.

## Milestone: federal_pbs_programs_all corpus reload (item 5.5b) and a --db validation-tooling bug

### Item

Plan item 5.5b: reload the stale `federal_pbs_programs_all` corpus, found while validating item 5.5.

### Previous behavior

Live facts (17,482) predated item 5.5's classifier precision fix by several days.

### Root cause

The corpus had not been reloaded since 2026-07-31, so the classifier fix's rejection of 158 genuinely garbled labels had never been applied to the live database.

### A second, independent bug found and fixed first

While validating on a disposable copy, `task9_sql_integrity_checks.py --db <copy>` kept reporting the same 254 hard failures regardless of changes made to the copy. Root cause: `main()` had no `argparse` at all and never read `sys.argv` - every `--db` flag ever passed to this script anywhere in this repository was silently ignored, always checking the hardcoded live `data/facts.db`. Fixed by adding a real `--db` argument and `argv` parameter (matching this repo's established CLI pattern), updating the 4 existing `main()`-calling tests to pass `main([])` explicitly, and adding a new dedicated regression test proving `--db` overrides the module default. This means every prior *pre-flight* task9 check with `--db` in this session was a no-op (re-checking the already-known-good live db); post-deployment checks (no `--db`, correctly defaulting to live) remained valid throughout, so no incorrect deployment resulted, but the pre-flight step itself was silently vacuous until this fix.

### Changes

- `scripts/ops/task9_sql_integrity_checks.py`: added `--db`/`argv` support.
- `tests/ops/test_task9_sql_integrity_checks.py`: fixed 4 existing tests' `main()` calls, added `test_main_db_flag_overrides_module_default`.
- Ran `scripts/ingest/reload_pbs_programs_all.py` then `scripts/ops/cleanup_stale_pbs_nodes.py` (an existing, tested "Task 8" tool built for exactly this scenario) against the live database, backup taken first.
- Updated the reviewed dashboard-projection fixture and two tests with hardcoded pre-reload FY2023-24 root totals, both with inline explanations.

### Validation

- [`pbs-corpus-reload-20260812T044311Z.md`](pbs-corpus-reload-20260812T044311Z.md) records full evidence.
- Exact `fact_key`-set comparison between the pre-reload backup and the post-reload database: -682 facts, **0 added**, 16,800 unchanged - the reload's entire net effect was removing the same 158 garbled labels item 5.5 already verified, not adding new coverage (correcting this milestone's original "would nearly double published facts" framing, which conflated row-level and deduplicated-fact counts).
- `cleanup_stale_pbs_nodes.py`: 158 newly-orphaned nodes (exactly matching item 5.5's count - independent cross-validation), 412 stale edges removed.
- `task9_sql_integrity_checks.py` (now correctly `--db`-aware): 254 hard failures -> 0, on both the disposable copy and, after live deployment, live itself.
- `dashboard_depth_audit.py`: `federal_actuals_*` (canonical GFS tree) completely unchanged; `federal_budget_2023_24/2024_25/latest` root totals decreased by explained amounts (e.g. FY2023-24: -$31,083,239,000); citation completeness 100% before and after. Fixture updated and re-verified.
- Full backend suite: 643 passed, 0 unexplained regressions (2 hardcoded-total updates resolved with documented justification).

### Data impact

`data/facts.db`: -682 facts, -158 nodes, -412 edges, confined to `federal_pbs_programs_all` and its crosswalk. Backup taken first (`facts-20260812T041605Z.db`).

### Dashboard impact

The federal "budget" mode no longer presents 158 garbled label fragments as real PBS facts, and the already-live PBS-under-Statement-6 crosswalk no longer exposes them as related detail. Canonical GFS actuals unaffected.

### Remaining risks

None identified for this reload specifically. Future classifier precision work on this source should follow the same reload+cleanup pairing established here.

### Next item

Item 6.3's remaining migration (PBS explorer, now unblocked with a correct, cleaned-up fact count), or item 6.1 (reusable explorer API/registry).

## Milestone: PBS explorer and a source_key filter for /v2/tree

### Item

Plan section 6.3, sixth migration: "PBS — edition -> portfolio/entity -> outcome/program/component, with quarantine-safe search."

### Previous behavior

16,800 `federal_pbs_programs_all` facts (post item 5.5b's reload) were loaded and live, but no frontend page existed. The `budget_expense / accrual / <status> / <year>` compatibility triple this source uses is shared with other sources (state budget statements, other PBS-derived extractors), so a naive reuse of the existing `/v2/tree` pattern would mix unrelated sources into "the PBS explorer."

### Changes

- `src/backend/routers/v2/query.py`: added an optional `source_key` filter to `GET /v2/tree`, applied as an exact `source_documents.source_key` match. Omitted by every pre-existing caller, preserving their behaviour exactly (proven by a dedicated regression test).
- `tests/api/test_v2_tree_pagination.py`: two new tests proving the filter narrows a real shared triple (matches direct SQL) and that omitting it changes nothing for existing callers.
- Added `src/frontend/app/explorers/pbs/page.tsx`, reusing the proven flat cursor-pagination pattern, scoped with `source_key=federal_pbs_programs_all` plus year/estimate_status controls. Registered in the explorers index.

### Validation

- [`pbs-explorer-20260812T054703Z.md`](pbs-explorer-20260812T054703Z.md) records full evidence, including a debugging note about a stale local dev server process (not a code defect - two earlier "restarts" had not actually replaced the running PID).
- `tsc --noEmit`, `lint:ci` (unchanged baseline), `build` (14 static routes including `/explorers/pbs`), `test:unit`: all passed.
- Live browser verification via Playwright against a confirmed-fresh backend process: truthful totals across year/estimate_status switches (including a correct 0-row result for a forward year's `actual` status), working citation panel, working client-side filter, zero console errors.
- Full backend suite, run in the project's dedicated conda environment: 646 passed, 0 regressions.

### Data impact

None. No database write; `source_key` is a new, optional, backward-compatible parameter.

### Dashboard impact

Once deployed, all 16,800 live `federal_pbs_programs_all` facts become reachable through a correctly-scoped explorer that never mixes in other sources sharing the same compatibility triple.

### Remaining risks

Hierarchical edition -> portfolio/entity -> outcome/program/component depth and server-side search remain part of the larger item 6.1 explorer API. The production deployment lag (top-of-file callout) continues to apply.

### Next item

Item 6.1 (reusable explorer API/registry) - the last remaining Wave 4-adjacent item now that every plan-listed 6.3 family except QGIP (blocked behind item 7.2's repair) has an explorer.

## Milestone: contracts jurisdiction-mix disclosure and a source_breakdown facet for /v2/tree

### Item

Discovered while scoping item 6.1's family registry (plan 6.1 requires a "jurisdiction" facet). Not a numbered plan item; a truthfulness finding fixed immediately per the standing rule against deferring findings that fit current scope.

### Previous behavior

The contracts explorer's `commitment/commitment/contract` scope is shared by federal AusTender plus three state contract-disclosure sources. For its default year, 2024-25, the scope was 100% NSW/NT/QLD state data - **0% federal AusTender** - with no disclosure of this on a page titled plainly "Contracts explorer," unlike every sibling family page.

### Changes

- `src/backend/routers/v2/query.py`: `/v2/tree` now always returns `source_breakdown`, a `GROUP BY source_key` list of `{source_key, count, value}` over the full scope, independent of page `limit`.
- `tests/api/test_v2_tree_pagination.py`: two new tests proving the breakdown is exact against direct SQL for both a real multi-source scope and a single-source scope.
- `src/frontend/app/explorers/contracts/page.tsx`: renders the breakdown with readable jurisdiction labels and states plainly in the header that the scope is not federal-only.

### Validation

- [`contracts-jurisdiction-disclosure-20260812T061849Z.md`](contracts-jurisdiction-disclosure-20260812T061849Z.md) records full evidence.
- `tsc --noEmit`, `lint:ci` (unchanged baseline), `build` (14 routes, unchanged): all passed.
- Live browser verification via Playwright: summary total unchanged, breakdown line and disclosure sentence both present, zero console errors.
- Full backend suite: 648 passed (2 new tests), 0 regressions.

### Data impact

None. `source_breakdown` is a new, always-present, additive response field.

### Dashboard impact

The contracts explorer now discloses its true jurisdiction mix. No other live family's reported totals change (all others already confirmed single-source).

### Remaining risks

Splitting into true per-jurisdiction pages remains a legitimate item 6.1/6.3 scope boundary, not required by the plan's exit gate. The production deployment lag continues to apply.

### Next item

Item 6.1's fuller reusable explorer API/registry (family registry config, `/v2/explorers` endpoints, generic frontend shell) remains open.

## Milestone: explorer family registry and availability API (item 6.1, first increment)

### Item

Plan section 6.1: family registry plus `/v2/explorers` endpoints.

### Previous behavior

Each of the five completed family pages hardcoded its own compatibility triple/`source_key` in its own `page.tsx`, with no single source of truth and no way to discover which years/statuses have live data without querying `/v2/tree` per candidate.

### Changes

- `config/explorers/families.yaml`: declarative registry of all 5 completed families (compatibility triple, allowed estimate statuses, `source_key` where required, additive note), same `version: 1` + fail-fast validation pattern as `config/breakdowns/edge_sets.yaml`.
- `src/backend/explorer_registry.py`: loader mirroring `edge_set_policy.py`'s structure and validation discipline.
- `src/backend/routers/v2/explorers.py`: `GET /v2/explorers` (list families) and `GET /v2/explorers/{family_id}/availability` (per year × estimate_status live counts/values, honoring `source_key`; 404 for unknown family).
- 12 new tests (`tests/unit/test_explorer_registry.py`, `tests/api/test_v2_explorers.py`), including proof that contracts' availability (no `source_key`) matches `/v2/tree`'s multi-jurisdiction total exactly - the registry does not silently narrow a legitimately multi-source family.

### Validation

- [`explorer-registry-20260812T064145Z.md`](explorer-registry-20260812T064145Z.md) records full evidence.
- Full backend suite: 660 passed (12 new), 0 regressions. No frontend change in this increment - deliberately scoped as a backend-only first step.

### Data impact

None. Both endpoints are read-only.

### Dashboard impact

None yet - no frontend page consumes these endpoints in this increment.

### Remaining risks

Migrating the five existing pages onto the registry, the plan's remaining 6.1 endpoints (hierarchical `tree?path=`, `facets`, `search`, `item/{fact_id}`), and item 6.2's generic frontend shell all remain open, deliberately deferred to keep this increment reviewable. The production deployment lag continues to apply.

### Next item

Continue item 6.1 (migrate pages onto the registry, or add facets/search) before item 6.2's generic shell, or assess remaining plan items for higher-priority gaps.

## Milestone: item 6.1 completion - full explorer backend contract

### Item

Plan section 6.1, closing the gap left open by the prior "first increment" milestone: `tree`, `facets`, `item/{fact_id}`, and `search`.

### Previous behavior

Registry, `GET /v2/explorers`, and `GET /v2/explorers/{family}/availability` existed. `tree`, `facets`, `item`, and `search` (the plan's own explicitly named capability) did not exist anywhere in the API, including on the pre-existing `/v2/tree`.

### Gap analysis

Before writing any hierarchy-handling code, checked directly against `data/facts.db` whether any of the five completed families have real `node_edges` beneath their nodes. **None do** - every family's nodes are single formatted-string labels with zero graph edges. This ruled out label-splitting as a way to fake `tree?path=` browsing (would violate the standing rule against inferring hierarchy from label structure) and settled the design as an honest 400 rejection instead.

### Changes

- `src/backend/routers/v2/query.py`: extracted `/v2/tree`'s query body into a shared `build_flat_tree_response()`, now used by both `/v2/tree` and the new per-family tree endpoint (no parallel query logic to drift out of sync); added an optional, backward-compatible `search` parameter with proper LIKE-wildcard escaping.
- `src/backend/routers/v2/explorers.py`: added `GET /v2/explorers/{family}/tree` (registry-driven, estimate_status validated against the family's registered list, `path` honestly rejected, `q` search param), `GET /v2/explorers/{family}/facets` (year/status/source/measure breakdowns), `GET /v2/explorers/{family}/item/{fact_id}` (family-boundary-enforced citation lookup - a real fact_id valid in a different family still 404s).
- 16 new tests (4 in `test_v2_tree_pagination.py` for `search`, 12 in `test_v2_explorers.py` for the three new endpoints), including a dedicated test proving family-boundary enforcement survives a real cross-family fact_id.

### Validation

- [`explorer-platform-6.1-completion-20260813T022217Z.md`](explorer-platform-6.1-completion-20260813T022217Z.md) records the full gap analysis and evidence.
- Full backend suite: 676 passed (16 new), 0 regressions.
- Live-verified against a freshly-confirmed `uvicorn` process (PID checked before/after, per this session's earlier debugging lesson): search, path-rejection, facets, and cross-family item-boundary all confirmed via direct `curl`, not only `TestClient`.

### Data impact

None. All new endpoints are read-only; `search` is optional and additive.

### Dashboard impact

None yet - no frontend page consumes these endpoints. The backend explorer contract the plan describes for item 6.1 is now complete for all five registered families.

### Remaining risks

Frontend migration onto the registry remains item 6.2/6.3 territory, not redone twice ahead of the shell that would consume it. Hierarchical path browsing has no real data to serve until some family gains actual `node_edges` structure. A pre-existing, unrelated data-quality artifact (`financial_year = "2022-20"` in the contracts source data) surfaced while spot-checking `/facets` - left visible rather than silently filtered, flagged for a future pass. The production deployment lag continues to apply.

### Next item

Item 6.1 is complete against the plan's explicit list. Item 6.2 (generic frontend explorer shell) is next, followed by migrating the five existing family pages onto it per the plan's established order.

## Milestone: item 6.2 completion - generic frontend explorer shell

### Item

Plan section 6.2: the generic explorer page/component consuming item 6.1's registry-backed API.

### Previous behavior

`ExplorerShell.tsx`, `explorerApi.ts`, and any `[family]` route did not exist (confirmed via `find` before writing anything). The five family pages each still hard-coded their own scope and duplicated citation/pagination/search logic.

### Changes

- `src/frontend/lib/explorerApi.ts`: typed client for every item-6.1 endpoint.
- `src/frontend/components/ExplorerShell.tsx`: the generic shell - registry-driven year selector (only years with real data, with counts), estimate-status selector (only rendered when a family actually has more than one), the registry's `additive_note` as a generic source/semantic banner, the family-scoped `source_breakdown` always shown, server-side debounced search, an honestly minimal breadcrumb (no fabricated hierarchy - re-confirmed no family has real `node_edges`), and explicit unknown-family/no-data-year/empty/error states.
- `src/frontend/app/explorers/family/[family]/page.tsx`: the dynamic route, deliberately placed off the plan's literal suggested path because the 5 existing pages already shadow it; `generateStaticParams()` reads the actual `config/explorers/families.yaml` registry file via a narrow regex rather than a hard-coded id list, so the static-export build target cannot drift from the real registry.
- `src/frontend/app/explorers/page.tsx`: added a registry-driven section linking to the shell for every family, alongside the untouched existing links.
- Found and fixed a real defaulting bug during live verification: picking the *latest* year (rather than the *most-populated* one) landed several families on sparse edge years (contracts: 21 vs 9,036 rows; PBS: 603/$2.6T vs 1,980/$5.9T) - fully disclosed, nothing hidden, but a misleading first view. Also surfaced further evidence of the pre-existing malformed-`financial_year` data-quality pattern (PBS: `"2025-20"`, `"2026-29"`, etc.), consistent with contracts' already-flagged `"2022-20"`.

### Validation

- [`explorer-shell-6.2-20260813T163357Z.md`](explorer-shell-6.2-20260813T163357Z.md) records full evidence.
- `tsc --noEmit` clean (empirically confirmed this Next.js version's async dynamic-route `params` convention rather than guessing, per `AGENTS.md`'s warning that this version has training-data-diverging breaking changes); `lint:ci` back to baseline after fixing 2 `react-hooks/set-state-in-effect` violations; `build` succeeded with exactly the 5 real families statically generated; `test:unit` passed.
- Live Playwright verification against freshly-confirmed backend/frontend processes: all 5 families correct with zero console errors, server-side search working, honest 404/no-data-year states, contracts' full jurisdiction disclosure reproduced generically, and the 2 already-verified dedicated pages re-checked byte-for-byte unaffected.
- No backend files touched this pass (`git status` confirms frontend-only diff).

### Data impact

None.

### Frontend impact

A new generic, registry-driven explorer surface exists at `/explorers/family/{id}` for all 5 completed families, alongside their still-untouched dedicated pages.

### Remaining risks

Family migration (item 6.3) is intentionally not done here. Hierarchical path browsing remains unavailable until a family gains real graph structure. The malformed-`financial_year` pattern now has two independent pieces of evidence (contracts, PBS) and deserves a dedicated data-quality pass. The production deployment lag continues to apply.

### Next item

Item 6.3: migrate contracts, PBS, grants, VIC output performance, and ACT invoices onto the shell in that order (QLD QGIP only after Wave 5 repair), per the plan's established migration order and exit gate.

## Milestone: item 6.3 completion - migrate the five family pages onto the generic shell

### Item

Plan section 6.3's literal migration instruction, as distinct from the earlier-satisfied Wave 4 exit gate.

### A discrepancy found and resolved

The task opening this session claimed item 6.3 was already complete. This ledger's own last-written line said the opposite ("Family migration (item 6.3) is intentionally not done here... is next"). Trusting the repository's own evidence over the assumed premise, the gap was verified real and closed in this pass. The five earlier "6.3 X explorer complete" rows above refer to a different, already-satisfied claim - the plan's literal exit gate (reachable, non-additive, truthful pagination) - not the stronger "one reusable explorer framework" instruction in the same plan section, which was not yet true until this pass.

### Previous behavior

Each of the five family pages contained its own full fetch/state/pagination implementation (~170-200 lines each) with hard-coded scope and bespoke disclosure prose - the duplication item 6.1/6.2 were built to eliminate.

### Changes

- `ExplorerShell.tsx`: added an optional `extraContent` slot for family-specific supplementary navigation the generic shell shouldn't need to know about.
- All five pages rewritten as thin `<ExplorerShell familyId="..." />` wrappers at their unchanged URLs; `contracts/page.tsx` passes `DebtNav` + the GFS-liabilities link as `extraContent` (the one real family-specific addition among the five).
- `explorers/page.tsx`: removed the now-redundant 6.2-era "preview" section.
- `.eslint-baseline.json`: lowered `max_errors` 25 -> 24, a genuine improvement from deleting duplicated code (flagged and confirmed by the baseline tool itself).

### Validation

- [`explorer-shell-migration-6.3-20260813T172550Z.md`](explorer-shell-migration-6.3-20260813T172550Z.md) records full evidence.
- `tsc`/`lint:ci`/`build`/`test:unit` all passed; route list unchanged (implementations changed, not routes).
- Live Playwright verification of all 5 migrated pages at their original URLs: identical real totals to every prior milestone report for these same scopes, zero console errors, `DebtNav`/GFS link preserved on contracts. Searched e2e/backend tests for references to the old bespoke page copy/components first - none found, so nothing needed updating.
- Full backend suite: 676 passed, 0 regressions (no backend files touched).

### Data impact

None.

### Frontend impact

Five family pages now genuinely share one implementation at their existing URLs; several gained real capabilities they lacked as bespoke pages (server-side search, availability-aware year selector, generic `source_breakdown`).

### Remaining risks

QLD QGIP migration remains correctly blocked behind item 7.2 repair. The production deployment lag continues to apply.

### Next item

Wave 5 (structured-family repairs and new products): MFS sibling workbooks, QLD QGIP repair, state borrowing adapter repairs, QLD Consolidated Fund/CFFR, QLD on-time payment, remaining VIC AFS structured sheets - per the plan's own next heading.

## Milestone: MFS Note 3 (Total expense by function) - item 7.1, workbook 2 of 5

### Item

Plan section 7.1: implement the MFS sibling workbooks one at a time. `federal_mfs_aggregates` (workbook 1) was already complete; this closes Note 3 - Total expense by function (workbook 2).

### Previous behavior

The Note 3 `.xlsx` was acquired (21 sheets, FY2005-06..FY2025-26, checksummed) but had zero extractor or loader.

### Changes

- Factored shared header/footnote-row parsing out of `mfs_aggregates.py` into a new `scripts/ingest/extractors/mfs_common.py` (3 more sibling workbooks will need the identical parsing - real, not speculative, duplication). Verified behavior-preserving: `mfs_aggregates.py`'s existing tests pass unchanged and a fresh dry-run against the live database still idempotently matches all 3,354 existing facts.
- Found and fixed two real structural quirks while building the shared module, both verified directly against the real file before assuming anything: an internal-whitespace-before-month header token (FY2013-14..FY2015-16), and a genuinely different header shape - the header spread across four separate physical rows instead of one combined cell (FY2005-06..FY2011-12), detected per-sheet and normalized into the same parsing path.
- New `mfs_note3_function.py` extractor; 20 new `mfs_note3_*` measure types in `config/measure-semantics/mfs.yaml` (13 COFOG functions + 5 "Other purposes" items + Asset Sales, `only_published_financial_years`-gated to its real FY2005-06..FY2007-08 window + Total expenses, always the source's own stated cell, never computed); migration `020_mfs_note3_measures.sql`; new `load_mfs_note3_function.py` loader mirroring the Aggregates loader's revision-conflict discipline exactly.
- Investigated 43 duplicate-fact candidates surfaced on a disposable copy before touching live: all three lumpy/irregular-flow measures (Contingency reserve, Natural disaster relief, Nominal superannuation interest) genuinely flat across consecutive months in real years - verified directly against the raw workbook, same false-positive class already documented for Aggregates. All 43 added to `config/audit/reviewed_duplicate_facts.yaml` with full evidence.

### Validation

- [`mfs-note3-function-20260813T212037Z.md`](mfs-note3-function-20260813T212037Z.md) and [`mfs-note3-duplicate-fact-investigation-20260813T180000Z.md`](mfs-note3-duplicate-fact-investigation-20260813T180000Z.md) record full evidence.
- 16 new tests; full suite 692 passed, 0 regressions.
- Disposable-copy-first: dry-run, apply, second apply (idempotent, 0 new inserts), `task9_sql_integrity_checks.py` (0 hard failures after the reviewed-duplicates update), `dashboard_depth_audit.py --check-fixture` (only the `database` path/timestamp differed from the golden fixture; manual diff confirmed `projections`/`graph` content byte-identical) - only then applied to live.
- Live: backup taken first. Facts 288,636 -> 293,049 (+4,413, exact match), nodes +20. Second live apply: 0 new inserts. `task9`/`dashboard_depth_audit` on live: 0 hard failures, `fixture_matches: true`.
- Zero backend or frontend code changes needed for reachability: `/v2/mfs/measures` and the existing MFS explorer page are both already registry/API-driven. Live-verified via Playwright: 35 measures in the dropdown (up from 15), "MFS Note 3: Defence" selectable and charts real data, 0 console errors.

### Data impact

`data/facts.db`: +4,413 facts, +20 nodes, +1 source_document, 0 changes to any existing source. Backup: `facts-20260813T175305Z.db`.

### Dashboard impact

None on the canonical annual tree (confirmed). The dedicated MFS explorer gains 20 new selectable series.

### Remaining risks

Four MFS sibling workbooks remain: operating statement, balance sheet, tax Notes 1/2, monthly profiles. Production deployment lag continues to apply to code (data is live immediately via the bind mount).

### Next item

Continue item 7.1 (Operating Statement, next in the plan's stated order), or item 7.2 (QLD QGIP repair) as an independent, parallel-eligible Wave 5 effort.

## Milestone: MFS Operating Statement scoping investigation - deferred with evidence

### Item

Plan section 7.1, third MFS sibling workbook in the stated order.

### Previous behavior

`federal_mfs_operating_statement` acquired but unadapted, same as the other three remaining siblings.

### Investigation and finding

Direct inspection of all 21 sheets before writing any code found at least three structurally distinct generations, not one richer version of Note 3's flat single-table shape: FY2005-06/06-07 ("Income Statement", 9-13 high-level items plus a separate second reconciliation table on the same sheet); FY2007-08 (transitional `GFS revenue`/`GFS expenses` wording, plus a unique line-wrap defect splitting one label across two physical rows); FY2008-09..FY2025-26 (the modern, richly-sectioned statement) - and even within this "modern" 18-year span, the Other-economic-flows/equity subsection alone has cycled through at least four distinct vocabularies. A genuine section collision was confirmed: `"Actuarial revaluations"` appears twice per sheet from FY2013-14 onward, under two different sections, with different values - mapping on row label alone (as Note 3 safely could) would silently conflate two different GFS concepts here.

### Disposition

**Deferred, not attempted.** Building a correct mapping across this many under-resolved era boundaries in one pass would mean guessing which vocabulary a given year's row belongs to - exactly what this program's rules forbid. No code was written; nothing to roll back. Full evidence and a recommended per-generation approach for a future dedicated pass: [`mfs-operating-statement-scoping-20260813T220000Z.md`](mfs-operating-statement-scoping-20260813T220000Z.md).

### Next item

Redirecting this session's Wave 5 effort to item 7.2 (QLD QGIP repair) - an independent item with its own already-documented, differently-shaped defects, rather than rushing Operating Statement's real complexity.

## Milestone: QLD QGIP repair (item 7.2)

### Item

Plan section 7.2: identify/correct the amount-column defect, recover/validate subprogram structure, investigate the 2099-00 observation, publish a before/after reconciliation report, rerun citations/idempotency - all before any UI work.

### Previous behavior

176,719 `qld_qgip_expenditure` facts loaded via `m7_qld_procurement.py`'s `export_qgip()`. Financial year, amount, and category columns were all auto-detected by generic substring heuristics with no per-file verification.

### Root causes (all verified directly against the 14 real acquired files)

1. `"Previous financial year"` - a column that actually holds a **dollar amount** - was being matched as the year column for 2012-13/2013-14; when an amount coincidentally resembled `20\d{2}`, the code fabricated a bogus future year (e.g. "2037-38") - the exact mechanism behind the "2099-00" observation. Separately, the filename-year regex required a 4-digit "20XX" and failed on 5 real files using a bare two-digit pattern, silently dumping tens of thousands of rows from FY2017-18..FY2021-22 into a hardcoded "2024-25" (confirmed: those 5 years held only 2-9 facts each before this fix, vs 14,209/18,513 for correctly-attributed neighbouring years).
2. The amount column was the first file-order match against generic substrings, picking "Total funding under this agreement" (whole-of-agreement total) over "Financial year expenditure" (correct single-year figure) for the 2014-15 file purely by column position.
3. "Sub-program title" (present in 11/14 files) was silently dropped - the category heuristic always picked "Program title" first.

### Changes

- `m7_qld_procurement.py`: `export_qgip()` rewritten - filename-only financial year (handles both 2-digit and 4-digit patterns, skips files with no determinable year rather than defaulting); amount column always prefers the true per-year figure; subprogram captured as a distinct dimension.
- `config/mappings/qld_qgip_expenditure.yaml`: `estimate_status` now a per-row column (2012-13/2013-14's whole-of-agreement-total rows get `actual_cumulative_agreement_total`, never blended with genuine single-year `actual` figures); `replace_on_reload: true`.
- `scripts/ingest/migrations/021_qgip_agreement_total_estimate_status.sql`: full `facts` table rebuild (SQLite has no `ALTER TABLE ... ADD CHECK`) adding the new estimate_status value; every column/row/index preserved, verified byte-for-byte on a disposable copy first.
- 7 new regression tests.

### Validation

- [`qgip-repair-20260814T134952Z.md`](qgip-repair-20260814T134952Z.md) records the full before/after reconciliation table and evidence.
- Disposable-copy-first throughout: migration, reload (idempotent - verified via a second run producing identical facts), and stale-node cleanup (reusing `cleanup_stale_pbs_nodes.py --source-key qld_qgip_expenditure` unmodified, same before/after-snapshot method already proven for the PBS reload) all tested on a copy before live.
- `task9_sql_integrity_checks.py`: 0 hard failures on live after cleanup. `dashboard_depth_audit.py --check-fixture`: `fixture_matches: true` (QGIP is not part of the primary GFS-preferred annual tree, so zero canonical impact, as expected).
- Facts 176,719 -> 203,899; QGIP-specific nodes 149,161 -> 170,264 (net +21,103 from genuinely finer subprogram structure), 63,763 stale old nodes removed.
- Full backend suite: 699 passed (692 + 7 new), 0 regressions.

### Data impact

`data/facts.db`: QGIP facts replaced via `replace_on_reload`; net node count change reflects real added structure, not double-counting. Backup taken first: `facts-20260814T134320Z.db`.

### Dashboard impact

None on the canonical tree. No dedicated QGIP explorer yet (deliberately deferred per the plan's own sequencing).

### Remaining risks

`upsert_fact()`'s `ON CONFLICT ... DO UPDATE SET amount_aud = excluded.amount_aud` overwrites rather than sums when multiple raw rows share identical node identity - pre-existing pipeline behaviour, reduced but not eliminated by adding subprogram granularity; a full fix needs a stable per-recipient identity (e.g. ABN) in the node/fact_key, flagged for a future dedicated pass. The production deployment lag continues to apply to code (data is live immediately via the bind mount).

### Next item

Dedicated QGIP program/project explorer (the plan's explicit next step for this item), or continue Wave 5 with state borrowing repair, QLD Consolidated Fund, QLD on-time payments, or remaining VIC AFS work.

## Milestone: state borrowing (item 7.3) - status correction and scoping

### Item

Plan section 7.3: repair/add adapters for missing/broken state borrowing sources.

### Finding: the ledger's own "three broken" characterization was stale and would have caused a real mistake

Before writing any adapter code, re-ran all three "broken" sources (`nsw_tcorp_weekly_bonds`, `qld_qtc_benchmark_bonds`, `qld_qtc_weekly_outstandings_2026_07_17`) - all extract and load cleanly today (tested on a disposable copy). But an earlier milestone report (`orphan-node-investigation-20260804T180700Z.md`, 2026-08-04) had already determined these are **intentionally retired legacy duplicates**, superseded by already-loaded canonical sources (`nsw_tcorp_bonds_on_issue`, `qld_qtc_aud_bond_outstandings`). Reloading them would double-count the same NSW/QLD debt under two source_keys - exactly what this program's rules forbid. The atlas/backlog reports' "three broken" framing was outdated and, read at face value, would have led to a wrong reload.

### Further finding: at least one "missing" candidate overlaps already-loaded data

Direct inspection of `vic_tcv_benchmark_bond_outstandings.csv` (one of 8 real acquired-but-unadapted state sources found) shows its current-date figures match an already-loaded security in `vic_tcv_amount_on_issue` almost exactly - the same bond population, mostly not new information. Flagged as needing careful non-additive treatment, not a plain adapter.

### Disposition

Ledger corrected (a real, load-bearing fix preventing a future wrong action). Full evidence and an 8-source inventory (plus a separately-flagged, out-of-scope 12-source federal AOFM family) in [`state-borrowing-scoping-20260814T140019Z.md`](state-borrowing-scoping-20260814T140019Z.md). No adapter code written - each of the 5 remaining PDF sources needs its own evidence-first inspection first, matching the discipline already demonstrated for MFS Operating Statement.

### Next item

Redirecting to item 7.5 (QLD on-time payments) - a more homogeneous, single-publisher CSV family, for concrete forward progress this pass.

## Milestone: QLD on-time payments (item 7.5)

### Item

Plan section 7.5: build an extractor/loader for the QLD Government On-Time Payment (small business) quarterly compliance reports (42 acquired CSVs, one per agency per acquisition batch) with typed measures for counts, percentages, days and payment values.

### Previous behavior

No pipeline existed for this source; 0 facts loaded.

### Build approach and defects avoided by design, not found after the fact

- 42 real files inspected directly before writing any mapping code: a stable 9-column shape, but 5 real wording variants for one column plus 1 file missing it entirely; inconsistent numeric formatting (`$X,XXX`, padded whitespace, `"Nil"` as a literal zero, blank as a genuinely missing observation); agency identity and financial year present only in the filename, not the CSV data, and for several files not confidently determinable at all.
- Extractor (`scripts/ingest/extractors/qld_on_time_payments.py`) normalizes the 5 header-wording variants, handles one file's embedded-newline `"2025-26\nQuarter"` header cell, and skips (never guesses) any file whose agency code or financial year can't be confidently derived from its filename - the plan's standing rule against inferring identity from label similarity alone.
- 8 dedicated `qld_otp_*` measure_types (migration `022_qld_on_time_payment_measures.sql`), each its own `compatibility_group`, none sharing a group with any expenditure/procurement measure. Count/day/percentage measures write to `facts.quantity`; only the two genuine dollar measures (`penalty_interest_paid`, `value_paid_late`) write to `amount_aud`.
- Loader (`scripts/ingest/load_qld_on_time_payments.py`) maps QLD's Q1=Jul-Sep..Q4=Apr-Jun financial-year quarter convention to real calendar `period_start`/`period_end` dates; agency node identity is the literal filename-derived code, never expanded to a guessed department name (QLD agencies undergo frequent machinery-of-government renames).

### Two real bugs found and fixed along the way

1. **Extractor**: `pandas` represents a blank CSV cell as `float('nan')`, not Python `None`, even with `dtype=str` - `str(float('nan'))` is the non-empty string `"nan"`, which silently survived the original `raw is None` check and round-tripped back into a real NaN via `float("nan")`, reaching the `facts` table's `amount_aud IS NOT NULL OR quantity IS NOT NULL` CHECK constraint as neither a valid number nor SQL NULL. Fixed with an explicit `pd.isna()` check; extraction dropped from 840 to 794 genuine rows (the 46 difference were all-blank rows, correctly excluded, not lost data).
2. **Shared infrastructure**: `task9_sql_integrity_checks.py`'s `duplicate_facts()` grouped strictly on `f.amount_aud`, so this was the first load in the database's history to produce `quantity`-only facts (`amount_aud IS NULL`) - every one of them fell into a single NULL-amount_aud SQL group, and `partition_duplicate_facts()` crashed outright (`TypeError: float(None)`) the first time it tried to process one. Fixed by grouping on `COALESCE(f.amount_aud, f.quantity)` in both the SELECT and GROUP BY, while keeping the returned dict's `"amount_aud"` key name for backward compatibility with all 49 pre-existing registry entries. 2 new regression tests added (quantity-only duplicate detection without crashing; quantity-only facts with genuinely different values correctly not conflated).

### Duplicate-fact investigation

87 `unresolved_duplicate_facts` groups surfaced after the COALESCE fix - the same structural false-positive class already documented for MFS: `duplicate_facts()` groups by value but not quarter/period, so two genuinely different quarters for one agency/measure that happen to report an identical value (very common for small agencies reporting `0` eligible claims/penalty interest quarter after quarter) are flagged as if duplicates. All 87 verified directly against the extracted staging CSV (not database metadata alone) and added to `config/audit/reviewed_duplicate_facts.yaml` (49 -> 136 entries). Full evidence in [`qld-on-time-payments-duplicate-fact-investigation-20260814T150000Z.md`](qld-on-time-payments-duplicate-fact-investigation-20260814T150000Z.md), including a `133`-vs-`136` reconciliation: all 87 new entries matched cleanly; the gap was 3 stale, already-precedented `qld_qgip_expenditure` entries whose underlying duplicate pairs no longer exist after the earlier item 7.2 QGIP repair (a benign side effect of that unrelated fix, not a defect here).

### Validation

- Disposable-copy-first throughout: extraction, migration, first apply (794 inserted, 29 nodes, 0 conflicts) and a second apply (794 idempotent skips, 0 new inserts) all proven on a copy before touching live.
- 32 new regression tests (30 extractor/loader, 2 task9 COALESCE fix); full backend suite 731 passed, 0 regressions.
- `task9_sql_integrity_checks.py`: 0 hard failures on live after the registry update.
- `dashboard_depth_audit.py --check-fixture` on live (no `--db` override, the definitive check): `fixture_matches: true`, `hard_failure_count: 0` - zero canonical-tree impact, as expected (8 entirely new, isolated compatibility groups).

### Data impact

`data/facts.db`: facts 320,229 -> 321,023 (+794, exact match to `facts_to_insert`); nodes 240,900 -> 240,929 (+29 agency nodes, exact match). Backup taken first: `facts-20260814T190319Z.db`.

### Dashboard impact

None on the canonical tree (new, isolated compatibility groups; confirmed via fixture match). No dedicated compliance explorer yet, per the plan's own "then expose..." sequencing already established for QGIP.

### Remaining risks

The production deployment lag (see the CRITICAL note at the top of this ledger) continues to apply to code; this item's data is live immediately via the bind mount. 13 of the 42 real files were quarantined at extraction (11 undeterminable financial year, 2 undeterminable agency code) - never guessed, consistent with this program's standing rule; a human reviewer could potentially resolve some of these from the source publication pages, but that is out of scope for this pass.

### Next item

Continuing Wave 5: item 7.4 (QLD Consolidated Fund, 46 acquired PDFs, no product model), the remaining MFS sibling workbooks (Balance Sheet, Tax Notes 1-2, Monthly Profiles, and the deferred Operating Statement), or the 5 remaining state-borrowing PDF sources scoped in item 7.3's report.
