Dashboard depth remediation engineering plan

Generated: 2026-08-07T23:02:17ZRepository: Brandonio-c/ausgov-budget-trackerPlanning base: main at 76d37f3; the only change after diagnosed code revision 9652bfb is the current-data-atlas report.Scope: software-engineering and data-pipeline plan only; no production code, database, or GitHub issue changes were made.

Executive decision

Do not solve this as a single “add more rings” project. The correct target architecture has three explicit product lanes:

Canonical annual projection — comparable, additive facts only.

Related evidence branches — FBO, Statement 6, PBS, contracts, grants, recipients and other non-additive detail, with source year and semantic boundary visible at every node.

Specialist explorers — products whose dimensions, units, period semantics or vintages do not fit an annual additive sunburst.

The critical path is:

projection contract -> numerical/UI correctness -> route/graph correctness -> historical FBO bridge -> historical Statement 6/PBS -> reusable explorer platform -> remaining family adapters

The sequence matters. Adding FBO/PBS/contracts before fixing the projection and renderer contracts would increase the amount of semantically ambiguous or numerically misreported content.

Non-negotiable invariants

These remain hard gates throughout the program:

No future-year fallback.

No cross-compatibility-group summation outside an explicit reconciliation product.

No related branch may change the canonical parent total.

No release of quarantined PBS rows merely to increase depth.

No ring may be created without a source-native semantic level.

Every displayed amount must remain the published fact amount, even when a separate layout weight is needed to draw a sunburst.

Every leaf and every fallback node must retain a citation, source key, source year, requested year, accounting basis, estimate status and unit.

Historical 2022-23 March and October editions must remain separate publication vintages.

Specialist products must not silently replace ABS GFS as the annual comparison basis.

1. Target architecture

1.1 Make tree projection semantics explicit

The backend currently exposes TreeNode.breakdown only on related or fallback nodes, while the frontend infers navigation folders from names such as Statement 6 and FBO Appendix A. Replace that implicit contract with a relationship object on every non-root projected node.

Recommended backward-compatible model:

TreeNode.relationship
  edge_kind: root | same_group | related_breakdown
  branch_kind: additive | related
  presentation_role: data | navigation
  edge_set_id: string | null
  branch_family: abs_gfs | fbo | statement_6 | pbs | contracts | grants | recipients | ...
  source_key: string | null
  source_family: string | null
  compatibility_group: string | null
  accounting_basis: string | null
  estimate_status: string | null
  requested_financial_year: string | null
  fact_financial_year: string | null
  is_year_fallback: bool
  fallback_reason: string | null
  match_quality: string | null
  unit: string | null

Keep breakdown as a deprecated compatibility alias until all frontend consumers migrate.

Add optional root projection metadata:

TreeNode.projection
  requested_mode
  requested_level
  requested_financial_year
  selected_accounting_basis
  max_visible_depth
  max_additive_depth
  contains_related_branches
  branch_summaries[]

Primary files

src/backend/schemas.py

src/frontend/lib/types.ts

src/backend/routers/v2/dashboard.py

src/backend/breakdown_graph.py

1.2 Replace source-name heuristics with declarative edge-set policy

Add config/breakdowns/edge_sets.yaml, keyed by existing crosswalk_id or pack ID. Each edge set declares:

branch_family
edge_kind
projection_policy: augment | authoritative
fallback_policy: exact_only | nearest_earlier | none
presentation_role: data | navigation
folder_label
source_key_allowlist/prefixes
sort_order

This removes hard-coded source-prefix classification from attach_related_to_tree, prevents the historical FBO archive from being mislabeled as budget expense, and gives apply_edge_cascade_to_budget_tree a real rule for augmenting versus replacing path children.

Do not add an authoritative edge set unless a completeness test proves it covers all intended path children.

1.3 Treat the annual tree as a projection, not the database hierarchy

Keep breakdown_edges as the active projection relation. Do not populate generic node_edges merely to increase counts. Add a projection builder module with pure, testable steps:

select compatible base facts;

build source-native paths;

add declared edge sets;

propagate branch semantics through descendants;

validate totals, years, units and cycles;

add navigation nodes;

compute depth metadata;

serialize.

Suggested module: src/backend/dashboard_projection.py.

2. Wave 0 — freeze the semantic baseline

This wave changes no user behavior.

2.1 Add golden projection fixtures

Capture representative API trees for:

Federal actuals: 2022-23, 2023-24, 2024-25.

Federal budget: 2022-23, 2023-24, 2024-25 and latest.

State debt latest.

Local actuals latest.

Ratios latest.

Do not store the entire volatile tree. Store a normalized projection signature:

root total;

node count by depth;

maximum additive and visible depth;

selected named paths;

source year and branch kind for those paths;

child-name sets at known collision points;

citation presence.

Suggested fixture location: tests/fixtures/dashboard_projection/.

2.2 Extend the audit into a depth/visibility contract

Extend scripts/ops/dashboard_api_audit.py or add scripts/ops/dashboard_depth_audit.py to report, per mode/level/year:

base compatibility group and accounting basis;

maximum additive depth;

maximum related depth;

maximum visible depth;

number of canonical leaves with related children;

path-only, edge-only and path-plus-edge children;

nodes hidden by presentation folding;

nodes rejected by dominance/partition rules;

exact-year versus fallback descendants;

source-family and unit transitions;

citation completeness;

root-total delta versus baseline.

Emit JSON and Markdown. CI should fail only on semantic invariants; depth changes require an explicitly reviewed fixture update.

2.3 Add graph integrity checks

Add checks for:

cycles;

duplicate semantic edges;

child facts absent under declared fallback policy;

same_group edges crossing compatibility groups;

authoritative edge sets missing path children;

related descendants lacking inherited related status;

navigation nodes counted as semantic levels;

source-year metadata missing on fallback nodes.

Exit gate

The current production projection passes the new audit with zero new hard failures and has stable signatures for the required federal years.

3. Wave 1 — correctness defects before adding depth

3.1 Fix the ring-value truthfulness defect — P0

Current sunburst construction rescales child values to the parent to satisfy ECharts layout, and the tooltip displays the rescaled ECharts value. Separate reported amount from layout weight.

Change SunburstDatum to carry:

value              # layout weight only
reportedValue      # exact fact amount
reportedUnit
relationship

The tooltip, labels, hover panel and accessibility text must use reportedValue. Percentages should be:

real percentage of parent only for additive siblings;

hidden, or explicitly labeled visual share, for related branches.

Use formatMeasureValue, not AUD-only formatting, for all chart types and the center label.

Make folding semantics-aware: never fold siblings across different branch kinds, units, source years or compatibility groups into one untyped Other node. Synthetic Other nodes must retain aggregate relationship metadata.

Files

src/frontend/lib/sunburstTree.ts

src/frontend/components/SpendingChart.tsx

src/frontend/lib/colors.ts

src/frontend/lib/types.ts

Tests

Related children can be visually scaled while the tooltip shows the original fact.

A percentage/recipient-count ring never shows $.

Related branches never show a misleading percent-of-parent.

Other never mixes incompatible semantics.

3.2 Fix federal year availability — P0

/v2/dashboard/years currently chooses one preferred accounting basis for the entire level and therefore hides accrual-only federal years before the GFS window.

Change the behavior to:

query all allowed year/basis combinations;

choose preferred basis per year;

keep /years returning strings for compatibility;

add /v2/dashboard/availability returning {financial_year, selected_basis, available_bases, source_families};

have the frontend use availability metadata for labels and warnings.

Files

src/backend/routers/v2/dashboard.py

src/frontend/lib/api.ts

src/frontend/app/HomeClient.tsx

tests/api/test_dashboard.py

Acceptance

2005-06 through 2007-08 are offered when facts exist.

GFS remains preferred in years where both GFS and accrual exist.

Selecting any returned year produces a 200 tree response.

3.3 Fix partial edge-cascade suppression — P0

Before changing behavior, run a read-only comparison of path-derived and edge-derived children for every federal budget node/year.

Implement:

augment as the default edge-set projection policy;

deduplication by node ID/canonical key;

deterministic ordering;

authoritative replacement only for edge sets with a completeness manifest and test;

an audit report listing children that would have been dropped by the current unconditional replacement.

Files

src/backend/breakdown_graph.py

config/breakdowns/edge_sets.yaml

tests/api/test_breakdown_related.py

new focused unit tests for merge behavior.

Acceptance

No valid path-only child disappears when an incomplete edge set exists.

Existing Statement 6/PBS depth remains reachable.

Root and parent totals are unchanged.

3.4 Repair the flat generic tree contract — P0/P1

/v2/tree is a limited flat list, and its returned total is derived from the limited rows. Preserve it for compatibility but make the contract truthful:

return shape: flat;

compute total_count and total_value independently of page limit;

add cursor pagination;

filter rejected/quarantined facts consistently;

expose next_cursor;

stop presenting a partial page sum as the family total.

The hierarchical explorer API in Wave 4 should be separate rather than overloading this route further.

3.5 Harden edge uniqueness and idempotency

SQLite NULL behavior currently requires manual duplicate checks. Add a unique expression index using COALESCE(financial_year, '') and COALESCE(crosswalk_id, '') after a duplicate-cleanup audit. Then use conflict-safe inserts consistently.

Add an explicit pack deletion/rebuild command scoped by crosswalk_id/edge-set ID so every graph deployment is reversible.

3.6 Fix lineage and source registry inconsistencies

Correct the ABS revenue canonical source identity.

Split federal_fbo_appendix_a_2024_25 from the historical archive dataset, or rename the current canonical target so fully_ingested cannot be read as full historical coverage.

Populate facts.canonical_dataset_id for configured canonical sources during ingestion/backfill, while leaving non-canonical specialist facts null.

Add a uniqueness invariant so one fact cannot silently map to two single-valued canonical IDs.

Normalize duplicate TAS/QLD source identities and generated coverage dispositions.

Generate UI coverage ranges from API availability rather than hard-coded prose.

3.7 Add source-aware fiscal-year validation

Investigate the 2099-00 state-actual outlier. Add loader validation using source-declared publication horizon rather than a global arbitrary maximum. Unexplained outliers go to quarantine with a machine-readable reason.

Exit gate

All current semantic audits remain clean, no displayed amount differs from its cited fact, all returned years are queryable, and edge projection cannot silently remove path children.

4. Wave 2 — highest-impact federal depth using data already loaded

4.1 Preflight the 2019-20–2023-24 FBO archive

Run a no-write audit over federal_budget_archive_function_series:

enumerate function and subfunction nodes by year;

verify every fact is actual_expense / accrual / audited_actual;

map function labels to ABS GFS purposes using the existing COFOG crosswalk;

calculate function-level differences for evidence only, not for additive reconciliation;

list unmapped labels and classification changes;

verify citations and exact source years.

Deliver ops/reports/fbo-archive-crosswalk-<timestamp>.{md,json}.

4.2 Add the historical FBO graph pack

Create a pack such as:

config/breakdowns/federal_fbo_archive_function_subfunction.yaml

edge set fbo_archive_under_abs

fallback_policy: exact_only

projection_policy: augment

branch_family: fbo

presentation_role: navigation for the folder and data for descendants.

The pack should:

emit archive function -> subfunction same_group edges from source-native paths;

attach ABS function -> FBO function as related_breakdown;

use existing facts without re-extracting or duplicating them;

be idempotent and reversible by edge-set ID.

Refactor attach_related_to_tree to group related children by edge-set metadata, not hard-coded federal_fbo_ prefixes.

4.3 Add historical federal traversal tests

For 2022-23 and 2023-24, assert:

eleven canonical ABS first-ring functions remain unchanged;

every mapped function-only branch gains an audited FBO route;

FBO descendants are exact-year, accrual, audited actual and related;

no 2024-25 fact appears;

ABS totals do not move;

every FBO leaf has citation/evidence;

unmapped functions are explicit report exceptions, not silent omissions.

Expected product result: broader second-ring coverage. Do not claim a third semantic ring from FBO Appendix A alone.

4.4 Improve ring-depth and branch UX

Replace “Depth 2 / 4” with semantic controls:

2 of 4 safe levels;

Show maximum action;

branch selector/chips when multiple related alternatives exist: Canonical actual, Audited FBO, Budget Statement 6, Contracts, Grants, etc.;

badges on hover/click: Additive, Related, Navigation;

source year, selected year, basis and estimate status visible without opening the citation panel.

Do not automatically prefer Statement 6 and hide FBO/additive alternatives. The user should choose a related branch explicitly, while the canonical branch remains the default.

Rename maxAdditiveDepth to maxVisibleDepth; compute additive depth separately from relationship metadata.

Exit gate

Federal actuals 2022-23 and 2023-24 gain audited historical branch coverage without total changes or future-year fallbacks; Federal 2024-25 clearly exposes its existing maximum and identifies related rings.

5. Wave 3 — acquire and build a genuine historical third ring

This is a distinct acquisition/adapter program, not an extension of the FBO bridge.

5.1 Edition manifest and acquisition

Register and acquire official sources for:

2023-24 Statement 6 and portfolio PBS documents;

2022-23 March Statement 6/PBS;

2022-23 October Statement 6/PBS;

corresponding FBO materials where not already represented.

Every source identity must include publication edition/vintage. Checksums and original URLs are mandatory.

5.2 Statement 6 adapters

Build bounded, edition-specific adapters for:

function;

subfunction;

component tables where published;

financial-year columns and estimate statuses.

Do not reuse current-edition page assumptions without layout tests.

5.3 Historical PBS adapter family

Reuse the generalized PBS classifier only after adding edition fixtures. Preserve:

portfolio/entity/outcome/program/component path;

publication edition;

fact year and estimate status;

page/table locator;

quarantine reason.

Treat March and October 2022-23 as separate vintages even where financial-year labels overlap.

5.4 Crosswalk and graph

Expose parallel, clearly labeled related branches:

audited FBO detail;

budget Statement 6 detail;

PBS program detail beneath matched Statement 6 nodes.

Do not chain one alternative classification into another merely to manufacture depth. same_group applies only inside a source family; crossings remain related_breakdown.

5.5 Repair current PBS gaps in the same framework

Repair federal_pbs_2026_27_ndia with a source-specific fixture.

Produce current unmapped-node coverage by source origin and portfolio.

Improve classifier precision on known malformed published labels.

Reconsider quarantined rows only with page/table evidence; never bulk promote.

Exit gate

At least one 2022-23 and one 2023-24 representative function has a verified function -> subfunction/component -> PBS-program route, with exact edition metadata, no future fallback and complete citations.

6. Wave 4 — reusable specialist explorer platform

Do not build six unrelated list pages. Build one reusable explorer framework and migrate families onto it.

6.1 Backend explorer API

Add a family registry and endpoints such as:

GET /v2/explorers
GET /v2/explorers/{family}/availability
GET /v2/explorers/{family}/tree?year=&path=&cursor=&limit=
GET /v2/explorers/{family}/facets
GET /v2/explorers/{family}/item/{fact_id}

Capabilities:

cursor pagination;

hierarchical path browsing;

full-result totals separate from page totals;

search;

facets for year, jurisdiction, source edition, measure, basis and status;

citations/evidence;

unit-safe values;

source-native hierarchy only.

Suggested files:

src/backend/routers/v2/explorers.py

src/backend/explorer_registry.py

config/explorers/*.yaml

6.2 Frontend explorer shell

Add a generic explorer page/component with:

breadcrumbs/tree navigation;

facet panel;

search and pagination;

source/semantic banner;

citation panel;

optional chart/table views;

explicit unit and period labels.

Suggested files:

src/frontend/app/explorers/[family]/page.tsx

src/frontend/components/ExplorerShell.tsx

src/frontend/lib/explorerApi.ts

6.3 Migrate families in this order

Contracts — remove the 200-row truncation; agency/category/supplier/notice depth only where present in source.

PBS — edition -> portfolio/entity -> outcome/program/component, with quarantine-safe search.

Grants — portfolio/program -> award/recipient, never additive to expenditure.

VIC output performance — immediate surfacing of the seven already-loaded output nodes.

ACT invoices — agency -> supplier/invoice cash-outflow product.

QLD QGIP — only after Wave 5 data repair.

Keep MFS, QLD RSF/MYFER, TAS GGS and VIC AFS/BPO dedicated product pages where their semantics are richer than the generic shell, but reuse common availability/citation components.

Exit gate

Contracts, PBS, grants and VIC output performance are reachable without forcing them into the annual additive tree; pagination and totals are truthful.

7. Wave 5 — repair and expand structured families

7.1 MFS sibling workbooks

Implement one workbook at a time, each with its own measure semantics and fixtures:

Note 3 function statement;

operating statement;

balance sheet;

tax Notes 1/2;

monthly profiles.

Expose them as tabs/dimensions in the MFS product, not annual-ring children.

7.2 QLD QGIP

Before UI work:

identify and correct the amount-column defect;

recover/validate missing subprogram structure;

investigate the 2099-00 observation;

publish a before/after reconciliation report;

rerun citations and idempotency tests.

Then expose a dedicated program/project explorer. Do not replace ABS GFS in state actuals.

7.3 State borrowing

Repair or add adapters for acquired missing/broken sources using a common borrowing adapter contract. Preserve:

observation date;

valuation basis;

instrument type;

issuer;

maturity;

stock versus flow status.

No mixed-valuation total without an explicit filter.

7.4 QLD Consolidated Fund

Create a new product model for gross cash/Public Account data with:

annual versus quarterly period;

publication vintage;

opening/closing balances and flows;

cash basis;

no merge into accrual/GFS expense.

Only then build adapters and a dedicated explorer.

7.5 QLD on-time payment

Create typed measures for counts, percentages, days and payment values. Keep compliance metrics separate from expenditure and procurement commitments.

7.6 VIC AFS and non-dollar output KPIs

Treat each deferred sheet family separately. Add typed units and dedicated views for equity, appropriations, administered statements and non-dollar KPIs; do not broaden the current AFS compatibility groups casually.

Exit gate

Each new product has an explicit compatibility/view family, source-native hierarchy, availability metadata, citation completeness and a dedicated surface.

8. Wave 6 — long historical coverage and external acquisition

8.1 Pre-2019 FBO generation parsers

The documents are acquired and text-extractable. Build generation-bounded parsers in this order:

2010-11–2018-19;

2003-04–2009-10;

1998-99–2002-03.

Each generation needs:

page/table-title manifest;

header and outcome-column resolution;

end-of-table detection;

allowed row vocabulary;

classification-version bridge;

negative fixtures proving revenue tables are rejected.

Never restore the current broad Table A.1 latch for these documents.

8.2 1985-86 and 1986-87

Keep this as a separate external acquisition issue. Require a verified Budget Paper No. 1/Statement source and checksum before adapter work begins.

9. PR and issue decomposition

Use small PRs with one behavioral concern each. Recommended sequence:

Order

PR / issue

Main result

Depends on

1

Projection signatures and depth audit

Stable baseline, no behavior change

none

2

Relationship/projection API contract

Explicit semantics, backward-compatible fields

1

3

Truthful sunburst values and unit formatting

No scaled or wrong-unit tooltip amounts

2

4

Per-year availability/basis fix

Early federal actual years become selectable

1

5

Edge-set registry and cascade merge safety

No path-child suppression; declarative policies

1–2

6

Generic flat-query pagination/total fix

No partial total presented as full

1

7

Lineage/registry and fiscal-year validation

Correct source identities and outlier handling

1

8

Historical FBO preflight report

Proves mapping before writes

2, 5

9

Historical FBO edge pack

2019-20–2023-24 audited related depth

8

10

Depth/branch UX

Safe-depth and branch semantics visible

2–3, 9

11

Explorer API and shell

Reusable specialist platform

2, 6

12

Contracts migration

Hierarchical, paginated contract browsing

11

13

PBS/grants/VIC output explorers

Surfacing of loaded hidden families

11

14

Historical edition acquisition manifests

Reproducible 2022-23/2023-24 source set

parallel after 1

15

Historical Statement 6 adapters

Function/subfunction/component facts

14

16

Historical PBS adapters + NDIA repair

Genuine program depth

14–15

17

MFS sibling adapters

Dedicated MFS depth

11

18

QGIP repair and explorer

Large project corpus safely surfaced

7, 11

19

State borrowing repairs

Broader debt coverage

7

20

QLD new products

Consolidated Fund and payment compliance

11

21

Pre-2019 FBO generations

Long historical audited depth

7–9

22

External 1985-87 acquisition

Verified source material

external

Do not combine PRs 2, 3, 5 and 9. The semantic contract, rendering correction, graph policy and FBO data change must be independently reviewable.

10. Test and release strategy

Required test layers

Unit

relationship propagation;

edge-set policy;

exact-only versus nearest-earlier fallback;

path/edge merge;

semantic folding;

reported versus layout values;

unit formatting.

In-memory database integration

edge idempotency;

exact-year fact selection;

no cross-group same-group edge;

canonical dataset assignment;

outlier quarantine.

Real facts.db API tests

named federal paths and totals;

historical FBO reachability;

availability/basis behavior;

pagination/full totals;

citations.

Audit scripts

zero scope, edge-kind, reconciliation, cross-year, label-quality and citation failures;

zero unexplained root-total delta;

depth signature updates reviewed.

Browser tests

2024-25 reports 2 of 4 safe levels and can show maximum;

tooltip amount equals cited fact despite layout scaling;

related badges and source year visible;

2022-23/2023-24 audited FBO branch reachable;

2005-06 accrual year selectable;

contracts pagination and hierarchy;

VIC output explorer visible.

Feature flags and rollout

Use two temporary flags:

backend DASHBOARD_PROJECTION_V2;

frontend NEXT_PUBLIC_DASHBOARD_PROJECTION_V2.

Run old and new projections in shadow comparison before cutover. Deploy backend schema/API compatibility first, then frontend. Add edge packs only after the new backend is live. Every edge pack must be deletable by edge-set ID.

Rollback

Disable projection flag to restore current API behavior.

Delete new edges by edge-set/crosswalk ID; no fact deletion needed for the FBO bridge.

Keep database backup before migrations and graph writes.

Frontend remains compatible with absent optional relationship/projection fields during rollback.

11. Program metrics

Track these per release:

Correctness

hard semantic audit failures: 0;

displayed amount versus fact mismatch: 0;

future-year fallback: 0;

cross-group additive edge: 0;

citation-missing published leaf: 0;

unexplained root-total delta: 0.

Coverage

maximum additive depth and visible depth by mode/level/year;

number of canonical leaves with valid related branches;

mapped versus exception FBO functions;

Statement 6/PBS crosswalk coverage by edition and portfolio;

loaded facts reachable from at least one appropriate surface;

quarantined rows by reason and source, with precision review for any promotions.

UX

available depth shown versus selected depth;

related branch selection rate;

explorer queries with truncation: 0;

hard-coded availability ranges remaining: 0.

12. Issue disposition matrix

Observed issue

Fix

Work class

Wave

Federal 2022-23/2023-24 function-only leaves

Historical FBO edge pack

repo graph

2

No true third historical ring

Acquire/adapt edition-specific Statement 6/PBS

acquisition + adapter

3

2024-25 starts below available depth

Safe-depth control and branch UX

frontend

2

Related versus additive rings unclear

Explicit relationship metadata and badges

backend + frontend

0–2

Ring tooltip can show scaled values

Separate reported value from layout weight

frontend correctness

1

Ring charts hard-code AUD formatting

Unit-safe formatter everywhere

frontend correctness

1

Statement 6 preference hides alternate branches

Explicit branch selector; remove name-based priority

frontend/backend

2

Other can lose/mix semantics

Semantics-aware folding

frontend correctness

1

Early federal accrual years hidden

Per-year basis availability

backend route

1

Budget edge cascade may suppress path children

Augment/authoritative edge policy

backend graph

1

FBO archive source prefix not recognized as FBO

Edge-set family metadata

backend graph

0–2

Related fallback policy too global

Per-edge-set fallback policy

backend graph

0–1

Flat /v2/tree capped/partial total

truthful totals + pagination; new explorer API

backend

1, 4

Historical FBO loaded but unwired

New archive pack

graph

2

PBS partial/broken/quarantined

NDIA repair, mapping report, evidence-led classifier work

adapter

3

No PBS/grants explorer

Reusable explorer platform

product/UI

4

Current contract branch uses 2019-20

Acquire current official source; retain visible vintage

acquisition

3/5

Contracts explorer is flat and capped

Explorer migration

backend/UI

4

Five MFS sibling workbooks lack adapters

Workbook-specific adapters and tabs

adapter/UI

5

VIC output performance API-only

Explorer registration/UI

UI

4

QGIP loaded but defective/hidden

Correct data contract, then explorer

data repair/UI

5

ACT invoices lack a product

Dedicated cash-outflow explorer

UI/product

4–5

QLD Consolidated Fund absent

New cash/vintage product model

semantic redesign

5

QLD on-time payment absent

Typed compliance product

adapter/product

5

State borrowing sources missing/broken

Shared adapter repair program

adapter

5

Pre-2019 FBO parser unsafe

Generation-specific parsers

adapter

6

1985-87 material absent

Verified external acquisition

acquisition

6

Canonical revenue source mismatch

Correct lineage config and invariants

config/data

1

canonical_dataset_id unused

Populate configured memberships

ingestion/data

1

Duplicate registry identities

Normalize aliases/status generation

config/data

1

Hard-coded explorer date ranges stale

Generate from availability API

frontend/API

1/4

2099-00 outlier

Source-aware year validation and investigation

data quality

1/5

Sparse graph visibility not measured

Depth coverage audit in CI

tooling

0

13. Smallest high-impact release

The first user-visible release should contain only:

projection baseline/audit;

truthful ring values and unit formatting;

per-year availability fix;

edge-set policy and cascade safety;

historical FBO preflight and graph pack;

safe-depth/branch UX.

That release fixes correctness first, exposes existing 2024-25 depth honestly, and uses the 415 already-loaded historical FBO facts to remove many 2022-23/2023-24 function dead ends. It does not pretend that FBO alone creates a third semantic ring.

14. Definition of done for the complete program

The program is complete when:

annual dashboard nodes are explicitly additive, related or navigation;

all displayed amounts and units match their facts;

every availability entry is queryable and basis-labeled;

no edge set can silently drop path data;

historical FBO is available for every supported same-year federal actual tree;

2022-23 and 2023-24 have at least one fully verified Statement 6/PBS program route where source documents support it;

contracts, PBS, grants, VIC output, ACT invoices and repaired QGIP have appropriate specialist surfaces;

MFS siblings and selected missing borrowing sources have explicit adapters/products;

QLD cash/compliance families have independent semantic models;

pre-2019 FBO adapters are generation-bounded and contamination-tested;

coverage, depth, source year, quarantine and citation metrics are generated in CI and release reports;

deliberate limitations remain visible rather than being presented as missing implementation.