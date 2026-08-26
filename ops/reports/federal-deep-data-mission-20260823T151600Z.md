# Federal Deep-Data Mission — Execution Report

Started: 2026-08-23T15:15Z
Mission: maximize genuine, useful Federal expenditure drill-down (target 10+ meaningful
semantic levels on high-value branches where official source data genuinely supports it),
per the master autonomous federal data-depth mission directive.

Standing constraints reaffirmed from the prior visualization-remediation phase: all work on
`main` only; production deployment (Docker image rebuild for the backend, static-export
redeploy for the frontend) remains a human decision this loop does not trigger itself.

Prior phase (P0/P1 visualization remediation, commits `36744f4`..`5a8ad76`) is documented in
`ops/reports/federal-depth-visualization-remediation-20260820T151500Z.md` and is **not**
reopened here except where this phase's own investigation surfaced a regression (none did).

## Loop 1 — Closing the inherited Loop-11 verification gap (explicitly requested, done first)

Commit: `f2e003d` (carried out at the start of this session before the depth-matrix work
below; documented in full in the prior phase's report, Loop 12). Summary: replaced blind
canvas pixel/angle guessing with a deterministic test hook (`__echartsInstance` exposed on
the chart container) so `tests-e2e/second-level-legend.spec.ts` can read a named data item's
real rendered layout and drive a genuine mouse hover. Confirmed working, permanent E2E test
now in the suite. This item is fully closed; not revisited further in this report.

## Loop 2 — Building the Federal depth opportunity matrix

### Observe

Before writing any new ingestion code, per the mission's own required first step, built
`scripts/ops/federal_depth_opportunity_matrix.mjs` (committed `509d509`) to regenerate the
Federal depth picture from the live database. Deliberately reuses the *shipped* frontend
depth logic (`lib/sunburstTree.ts`'s `perFunctionDepth`/`nestableChildren`/
`additiveChildren`) via a live local backend, rather than a separate Python
re-implementation — the same discipline the prior phase established, so the matrix reflects
exactly what the production UI would compute, not a parallel approximation that could
silently drift from it.

Ran against `federal_actuals_2024_25`, `federal_actuals_2025_26`, `federal_budget_2025_26`.

### First finding: Federal Actuals mode has zero native additive sub-function depth

For FY2025-26 Federal Actuals, every one of the 17 top-level functions showed
`canonical_additive_depth: 1` — genuinely, uniformly flat at the canonical level (already
known from the prior phase's Loop 3/4 work, now confirmed as a structural property of the
*currently loaded* actuals data, not a rendering artifact). The only depth available for
Actuals mode today is through related branches (Statement 6, Contracts, Grants, PBS,
Recipients) — consistent with the prior phase's findings and not a new discovery.

### Second finding: a severe, live, pre-existing correctness defect in Budget mode (see Loop 3)

`federal_budget_2025_26`'s matrix row initially showed `canonical_additive_depth: 4`, 39
terminal leaves, and a `Social security and welfare` value of $324.9B — an unexpectedly deep
result compared to Actuals mode, and a specific dollar figure that didn't match any other
verified source. This became the input to Loop 3's investigation, below.

## Loop 3 — Federal Budget mode's total was inflated by roughly 6-7x (P0 correctness defect, fixed)

Commit: `8ee0d36`

### Observe

Live browser check, production-style static export, Federal Budget FY2029-30 (the default
"latest" year): reported **"Total: $5,282,190,045,000"** — a $5.28 trillion figure against a
real Australian federal budget of roughly $780-950B for that era. Screenshot evidence
captured. This is completely independent of anything touched by the prior visualization
phase (which worked exclusively in Actuals mode); it was a live, shipped, user-facing defect
this phase's own audit tooling surfaced.

### Diagnose

Traced through `dashboard_tree()` → `_fact_rows()` → `_build_tree_dict()` →
`apply_edge_cascade_to_budget_tree()` → `_to_tree_node()` in
`src/backend/routers/v2/dashboard.py` / `src/backend/breakdown_graph.py`. Found **three
independently compounding bugs** in the same code path, each verified in isolation via direct
SQL against `data/facts.db` before any code change:

1. **Query-level axis conflation.** At least four source families share
   `compatibility_group = 'budget_expense'` for federal FY2025-26, representing genuinely
   different, overlapping classification axes of the *same* underlying spending:
   - `federal_budget_statement_6_a61` (COFOG-style function classification — "Social
     security and welfare", "Health", ...) — 72 rows/year, levels 1+2, FY2024-25..FY2029-30.
   - `federal_budget_statement_6_components` — 45 rows/year, level-3 program detail, same
     years.
   - `federal_pbs_programs_all` — PBS *portfolio/agency* rollups ("Finance" $1.0-2.1T,
     "Treasury" $1.7-2.1T, "Social Services" $500-850B, "Health Disability and Ageing"
     $500-950B, ...) — 3214 facts for FY2025-26 alone, raw sum $7.23T. A genuinely
     different axis (who spends it) from Statement 6 (what it's classified as), not a
     further breakdown of it.
   - `federal_pbs_programs_s6_bridge` — PBS programs remapped onto Statement 6 paths, with
     observed extraction-quality problems: operating-statement/balance-sheet rows ("Interest
     – – – – – Dividends – – – – – Taxes", "Surplus/(deficit) after income tax") and
     duplicate mis-parsed "Total for Program" rows (the identical program appearing twice at
     different dollar amounts) mixed into what should be pure program-expense rows.
   - `federal_budget_statement_6_2026_27` — a smaller (15 rows/year), newer vintage of the
     *same* level-1 totals for FY2025-26/FY2026-27, fully redundant with `_a61`'s broader
     coverage of those same years.

   `dashboard_tree()` queried all of these together with no source distinction, and
   `_build_tree_dict()` flattened them as additive siblings under one "Commonwealth" node
   purely by matching fact `node_name` strings — exactly the "false partition of
   incompatible amounts" pattern the mission directive explicitly forbids, just manifesting
   in Budget mode rather than the Actuals mode the prior phase had already hardened against.

2. **Graph-edge cascade reintroducing the same pollution via a second pathway.**
   `apply_edge_cascade_to_budget_tree()` (called only for `mode == "budget" and level ==
   "federal"`) separately queries `breakdown_edges` for `same_group` edges and sums their
   targets into the parent's reported amount. One such edge, `crosswalk_id: a61_to_components`,
   connects each `_a61` function node to the *corresponding* `_components` node — a
   reconciliation cross-reference between two representations of the same total, not a
   further partition of it — but the cascade treated it as an ordinary additive child and
   summed it in, inflating "Social security and welfare" from $297.805B to $324.855B on its
   own (confirmed via direct SQL query of `breakdown_edges` before touching any code).

3. **Children-rollup amplifying `_components`' own internal duplicate rows.**
   `_to_tree_node()` sums a node's children into its reported value unless
   `preserve_amount` is set. `federal_budget_statement_6_components` lists some level-3
   amounts under *two different* level-2 parent paths for the identical dollar figure — e.g.
   `"Health / Medical services and benefits / Medical benefits"` and `"Health /
   Pharmaceutical benefits and services / Medical benefits"` both $35.144B — so summing that
   duplicated detail back up inflated "Health" past its own published total. Separately,
   `_components` also contains bare (no `"/"`) level-1 rows redundant with `_a61`'s own
   figure for the same function (e.g. a bare `"Defence"` row at $52.854B identical to
   `_a61`'s), which the plain row-accumulation step summed onto the same path before
   `preserve_amount` even had a chance to apply.

### Implementation

`src/backend/routers/v2/dashboard.py`:
- New `_BUDGET_FEDERAL_CANONICAL_SOURCE_KEYS = ("federal_budget_statement_6_a61",
  "federal_budget_statement_6_components")` and `_statement_6_covers_year()` helper.
- `_fact_rows()`: for `mode == "budget" and level == "federal"`, restrict to the two
  canonical source keys **only for years those sources actually cover** (FY2024-25 onward).
  FY2022-23/FY2023-24 — which have no Statement 6 data at all, only
  `federal_pbs_programs_all` — deliberately keep their prior, already-reviewed behavior
  unchanged (this per-year gate was added after a first, unconditional version of the fix
  caused those two years to 404 — caught immediately by the full regression suite, fixed
  before commit, not shipped broken).
- `dashboard_tree()`: removed the `apply_edge_cascade_to_budget_tree()` call for the federal
  budget tree (import removed as it becomes otherwise-unused in this file). The path-based
  Statement 6 hierarchy from `_a61`/`_components` already nests correctly via their own
  `" / "`-delimited node names; the cascade added no depth these two sources don't already
  provide, only the harmful reconciliation-edge double-count.
- `_build_tree_dict()`: rows from `federal_budget_statement_6_a61` get
  `preserve_amount = True` (trust the authoritative Statement 6 figure directly rather than
  recomputing it from children that may double-count); bare (no `"/"`) rows from
  `federal_budget_statement_6_components` are skipped during accumulation (they duplicate
  `_a61`'s own level-1 figure for the same function; genuine nested detail —
  `len(nested) > 1` — is unaffected).

### Tests

Full backend suite: **325 passed, 0 failed** (`pytest tests/ --ignore=tests/ingest
--ignore=tests/api/test_citation.py` — those two ignores are pre-existing, unrelated
`duckdb`/`pandas` import environment gaps, confirmed present before this session started).
A first-pass version of fix #1 (unconditional source restriction, no per-year gate) broke 5
tests (`federal_budget_2022_23`/`federal_budget_2023_24` 404ing) — caught by this same suite
run, root-caused, and fixed via the per-year `_statement_6_covers_year()` gate before
committing; the failing version was never committed to `main`.

`scripts/ops/dashboard_depth_audit.py --check-fixture`: confirmed the diff was scoped
exactly as expected — only the 5 `federal_budget_*` projections changed (all in the
corrected direction: `federal_budget_2022_23`/`_2023_24` byte-identical, unaffected;
`federal_budget_2024_25` $770,071,000,000; `federal_budget_2025_26` $812,063,000,000, depth
3; `federal_budget_latest` (FY2029-30) $933,729,000,000, depth 3) — every other projection
(`state_debt_latest`, `local_actuals_latest`, `federal_ratios_latest`, all `federal_actuals_*`)
byte-identical, confirming zero blast radius outside federal budget mode. Golden fixture
regenerated (`--write-fixture`) and reconfirmed idempotent across 2 consecutive
`--check-fixture` runs.

### Browser verification

Fresh local backend (port 8099, never the production container) + production-style static
export (`next build` + `serve`), FY2025-26: the "Budget" mode top-level legend and the
chart's own "Total:" line both read exactly **$812,063,000,000**, matching Statement 6's own
published "Total expenses" row. Verified across all queried years (FY2022-23 through
FY2029-30) via direct API calls showing plausible, correctly-ordered totals
($1.63B → $1.79T[footnote: FY2023-24's federal_pbs_programs_all-only figure was already
reviewed/expected before this session and is unchanged] → $770B → $812B → $833B → $934B).
Actuals mode confirmed completely unaffected (unchanged code path; root total exactly
$724,901,922,000 as in every prior-phase verification). 0 console errors.

### Data/graph impact

None — pure backend query-logic fix. No migration, no `facts.db` row mutation, no new or
deleted facts/nodes/edges. The `breakdown_edges` table's `a61_to_components` crosswalk edges
still exist (untouched) — they are simply no longer traversed for the federal budget tree.

### Depth impact — this fix *increased* usable depth, not just corrected the total

Verified via the regenerated matrix (`ops/reports/federal-depth-opportunity-matrix-
20260823T151533Z.json`), FY2025-26 Budget mode, post-fix:

| Function | Value | Canonical depth | Terminal leaves | Largest leaf | Leaves >$1B |
|---|---:|---:|---:|---:|---:|
| Social security and welfare | $297.81B | 3 | 25 | $65.31B | 16 |
| Health | $127.02B | 3 | 21 | $35.14B | 11 |
| Education | $64.97B | 2 | 8 | $66.02B* | 7 |
| Other purposes | $149.21B | 2 | 4 | $107.89B | 4 |
| Transport and communication | $16.93B | 2 | 6 | $9.14B | 3 |
| Other economic affairs | $14.67B | 2 | 6 | $4.54B | 5 |
| Public order and safety | $9.60B | 2 | 2 | $7.44B | 2 |
| Housing and community amenities | $8.83B | 2 | 3 | $4.37B | 3 |
| Recreation and culture | $5.98B | 2 | 4 | $2.33B | 2 |
| Agriculture, forestry and fishing | $4.71B | 2 | 9 | $1.55B | 2 |
| Defence, General public services, Fuel and energy, Mining/manufacturing/construction | — | 1 | 1 each | own value | 1 each |

\* a leaf's reported value can slightly exceed its immediate parent's reported value where
the source table's own component/parent figures don't reconcile to the cent; this is
disclosed as-is, not silently rounded.

Concretely, before this fix "Social security and welfare" reported an inflated $324.9B with
39 leaves at depth 4 — numbers that *looked* deeper but were wrong. After the fix it reports
the correct $297.81B with 25 genuine leaves at depth 3, including exactly the kind of
detail the mission's Priority 1/2 want directly reachable without further ingestion work:

```
Social security and welfare ($297.81B)
  → Assistance to the aged ($109.975B)
      → Aged care services ($41.4B)
      → Support for seniors ($65.315B)
  → Assistance to people with disabilities ($93.358B)
      → National Disability Insurance Scheme ($53.778B)
      → Financial support for people with disability ($26.209B)
      → Financial support for carers ($13.18B)
```

This is real, correctly-reconciling, depth-3, source-backed hierarchy already loaded in the
database and now correctly exposed via Budget mode's own canonical additive tree — no new
ingestion required to reach this depth for Social Security and NDIS specifically.

### Deployment status

**Not yet deployed.** Same standing constraint as the prior phase: this backend fix requires
a Docker image rebuild of the production container, which remains a human-authorized action.
Exact command recorded here for when authorized:
`docker compose -f docker-compose.vibefactory.yml up --build -d` (rebuilds `src/backend`;
`data/`/`config/` are already bind-mounted so this fix's frontend-visible effect requires
only the backend rebuild, not a frontend redeploy).

## Loop 4 — Priority 1 audit: how deep is Social Security *already*, live, right now?

Before writing any new extractor, checked what the existing graph already exposes via the
live API (Federal Actuals FY2025-26), per the mission's own "re-audit existing data before
acquiring more" instruction.

### Finding: Job Seeker Income Support already reaches genuine 5-level depth, live

```
Federal
  → Social security and welfare                          (additive, canonical)
    → Assistance to the unemployed and the sick           (related, branch_family=statement_6)
      → Job Seeker Income Support                          (related, branch_family=pbs)
        → Recipients by state                               (related, branch_family=recipients)
          → New South Wales: 280,995 · Victoria: 236,045 · Queensland: 218,530 · ...
        → Recipients by age                                 (related, branch_family=recipients)
```

Confirmed live via direct API query (not just graph inspection): every hop correctly labeled
`branch_kind: "related"` with the correct `branch_family` at each transition
(statement_6 → pbs → recipients), never presented as a false additive partition — exactly
the "explicit sub-branch selectors, not falsely nested" pattern the mission directive
requires. Traced the underlying graph edges: this reachability runs through
`federal_dss_payment_demographics` (source_family `recipient_statistics`, 52 already-loaded
facts, source: DSS JobSeeker monthly recipient profile) connected via a `dss_demo_under_pbs`
crosswalk, itself dependent on the `cofog_to_budget_function` crosswalk fixed in the prior
visualization-remediation phase's Loop 1 (`36744f4`). No new code or data was needed for
this specific path — it was already fully wired and already correct, simply not previously
confirmed end-to-end.

### Finding: NDIS currently stops at depth 3 — a genuine, concrete opportunity (category D)

`Assistance to people with disabilities → National Disability Insurance Scheme` reaches only
one further "related/pbs" hop reporting a near-duplicate of the Statement 6 figure itself
($53,777,000,000 vs the parent's $53,778,000,000) — not genuinely deeper detail, consistent
with the earlier finding that `federal_dss_pbs_programs`/`federal_health_pbs_programs`
largely duplicate `federal_budget_statement_6_components`'s level-3 figures rather than
adding a level 4. `dss_payment_demographics_2024_25.csv` (the source of the Job Seeker
recipients-by-state/age depth above) covers *only* JobSeeker payments — no equivalent
NDIS participant/geography dataset is currently staged or loaded. This is a genuine,
well-scoped **category D** opportunity (official source likely exists — NDIS Quarterly
Reports publish participant counts by state/age/disability type/support category — but must
be acquired and extracted) for a future ingestion loop, not a wiring or graph gap.

### Disposition

Social Security's Priority 1 status: **substantially deeper than the pre-fix baseline
suggested**, once the Budget-mode correctness fix (Loop 3) and existing-data audit are both
accounted for. Statement 6 alone provides depth 3 for every major sub-function; the
JobSeeker-specific recipient demographic branch already reaches depth 5. NDIS, Aged Care
(beyond "Aged care services"/"Support for seniors"), and the other Social Security
sub-programs remain at depth 3 pending genuinely new ingestion (participant/recipient
demographic data equivalent to what JobSeeker already has) — tracked as the concrete next
target, not a vague "go deeper" instruction.

## Loop 5 — Phase 1: repair federal_pbs_programs_s6_bridge label quality

Commit: `2a0847e`

### Observe

Per the master directive's explicit ordering ("repair the hierarchy spine... before adding
more depth"), audited the bridge dataset directly against live, currently-published facts
rather than trusting the prior milestone's test suite alone. A prior milestone (Task 5/8)
had already built `scripts/ingest/pbs_label_classifier.py` and run
`scripts/ops/cleanup_pbs_s6_bridge_labels.py` once against this exact dataset (37,084 facts
already quarantined via this mechanism, confirmed via `facts_pending_attribution`), but
direct inspection of the still-published facts found real defects still present:
`"Interest – – – – – Dividends – – – – – Taxes"` (three financial-statement line items
concatenated) and `"Aged Care (Accommodation Payment Security) Act 2006 - - - - - Total for
Program"` (a malformed concatenated row) were both being served live as if they were program
names, one of them appearing twice under the same portfolio at different dollar amounts.

### Diagnose

Root-caused two independent classifier gaps: (1) `BARE_DASH_RUN`'s character class covered
only ASCII `-` and U+00AD soft hyphen, not the broader Unicode dash-glyph set `YEAR_TOKEN`
already handles elsewhere in the same file — the malformed row used EN DASH (U+2013)
specifically; (2) no vocabulary coverage at all for several defect classes: "Surplus/
(deficit) ..." operating-statement lines, ~40 balance-sheet/income-statement terms
(Buildings, Trade and other receivables, Depreciation and amortisation, ...), Statement-of-
Cash-Flows/appropriation-funding-source line prefixes ("Cash used X", "Funded by/internally
from X", "Payments to corporate entities X"), a shorter 2-dash placeholder pair combined
with an embedded value token, a standalone "nfp" (not-for-publication) placeholder run, bare
"Operating"/"Operations"/"Workforce" with no supporting numbering, and PBS footnote markers
like "(a)"/"(b)" defeating the curated-vocabulary exact match.

Broadened the audit to the *entire* currently-published bridge dataset (not just the two
examples that prompted the investigation): of 459 fact-bearing nodes, 301 were still
classified as "publishable" before any fix — many genuinely fine, but manual review found
well over 100 more real defects across the classes above.

### Implementation

`scripts/ingest/pbs_label_classifier.py`: fixed `BARE_DASH_RUN`'s dash-glyph set; added
`SURPLUS_DEFICIT_LINE`, `CASH_FLOW_FUNDING_LINE`, `WEAK_DASH_PAIR`, `NFP_RUN` patterns and
~40 new `FINANCIAL_STATEMENT_LINE_ITEMS` vocabulary entries; extended `NARRATIVE_LEAD` to
recognize "Add" continuations; extended the bare-generic-term check to "operating"/
"operations"/"workforce"; added footnote-marker stripping (`lowered_no_footnote`) before the
curated-vocabulary lookup so "(a)"/"(b)"-suffixed variants of a known term are recognized.

### Tests

12 new tests (40 total, up from 29) in `tests/ingest/test_pbs_label_classifier.py`, each
using a real, verbatim string found live in `data/facts.db`, each paired with a positive
check proving a genuine program name is not false-positived by the same rule (e.g. "Add
Provision for Impairment" rejected as a narrative lead, but "Additional Support Payments"
still accepted). All 40 pass; `ruff check` clean.

### Reload (disposable copy first, then live, with idempotency proven at both stages)

Backed up `data/facts.db` (`scripts/ops/backup_facts_db.py`), copied to a disposable path,
ran `cleanup_pbs_s6_bridge_labels.py` there first: 332 of 472 facts newly quarantined (up
from the original run's 164), 325 now-orphaned nodes and 639 stale edges removed, 140
genuine program/entity rows remain published. Re-ran on the same disposable copy: 0
additional quarantined, 0 nodes/edges removed — idempotent. Applied to the live
`data/facts.db` (git-ignored — the mutation is durably applied to disk, no DB commit
needed): identical counts. Re-ran on the live DB: idempotent there too. Before/after counts
reconcile exactly: `facts` 331611→331279 (−332), `nodes` 241019→240694 (−325),
`breakdown_edges` 13923→13284 (−639), `source_documents` unchanged (147), `facts_pending_
attribution` 37099→37431 (+332). `PRAGMA integrity_check`: ok.

### Tests (full suite, against the modified live DB)

325/325 backend tests passed. `dashboard_depth_audit` golden fixture regenerated and
reconfirmed idempotent across 2 consecutive `--check-fixture` runs — **root totals for every
projection unchanged** (Federal Actuals FY2025-26 $724,901,922,000; Federal Budget FY2025-26
$812,063,000,000; all others byte-identical), confirming this cleanup only removed
non-canonical related-branch noise and never touched anything contributing to a canonical
total, exactly as required by the mission's "canonical total safety" gate.

### Browser verification

Fresh local backend + production-style static export: both Actuals and Budget mode totals
render correctly for FY2025-26 ($724,901,922,000 / default-year $933,729,000,000 for
FY2029-30), 0 console errors.

### Remaining, disclosed (not fixed in this pass)

- **~5 residual malformed rows** with harder-to-generalize embedded-number shapes (e.g.
  `"Borrowing costs 63 110 - - 689 Net GST paid"`, where the embedded numbers have no
  thousands separator and are separated from a 2-dash run by intervening text) — a small,
  disclosed tail after removing 332 of 472 facts; not pursued further given the accuracy-vs-
  effort tradeoff of hand-tuning for single-occurrence shapes.
- **A separate, different-class defect**: `pbs_programs_s6_bridge.py`'s `PORTFOLIO_TO_S6`
  mapping table crudely maps the entire "infrastructure" portfolio (real name:
  "Infrastructure, Transport, Regional Development, Communications, Sport and the Arts") to
  a single COFOG function, "Transport and communication" — so arts/culture institutions
  genuinely funded through that portfolio (National Gallery of Australia, National Library
  of Australia, National Museum of Australia, National Portrait Gallery of Australia, Screen
  Australia, Creative Australia, National Film and Sound Archive) are attributed to the
  wrong function; they should be "Recreation and culture". This is a **parent-attribution**
  defect (correct row content, wrong parent), not the label-quality defect this loop
  targeted — fixing it means adding `SUBFUNCTION_HINTS`-style keyword detection to
  `pbs_programs_s6_bridge.py`'s function-mapping step (not the label classifier), and would
  require regenerating `pbs_programs_s6_bridge.csv` from the raw PDFs via the extractor, not
  a DB-level cleanup. Tracked as separate follow-up work, not fixed here to avoid conflating
  two independent defect classes in one change.

## Loop 6 — Arts/culture parent-attribution fix, and a canonical-total-safety regression it surfaced

### Part A: fixing the `PORTFOLIO_TO_S6` arts/culture misattribution (disclosed at the end of Loop 5)

Root cause (already identified in Loop 5): `pbs_programs_s6_bridge.py`'s portfolio→COFOG-
function mapping crudely sends the entire "Infrastructure, Transport, Regional Development,
Communications, Sport and the Arts" portfolio to a single function, "Transport and
communication" — so genuinely arts/culture-funded entities (National Gallery of Australia,
National Library of Australia, National Museum of Australia, National Portrait Gallery,
Screen Australia, Creative Australia, National Film and Sound Archive, the Australian
National Maritime Museum, SBS, and others) were attributed to the wrong COFOG function
entirely. This is a parent-attribution defect (correct row content, wrong parent), distinct
from Loop 5's label-quality defect.

Fix: added `ARTS_CULTURE_SPORT_PROGRAM_OVERRIDE` (a curated regex over program/entity names)
and `_function_override_from_program()`, checked *before* the existing portfolio-substring
lookup in `_s6_function()`. Extended `_subfunction()` with a `"Recreation and culture"`
branch that further splits into `"Sport and recreation"` / `"Broadcasting"` / `"Arts and
cultural heritage"` by keyword. Fixed an argument-ordering bug caught while wiring this in:
`remap_rows()` was computing `program_label` *after* calling `_s6_function(portfolio,
program_label)`, which would have passed an undefined value — reordered so the label is
computed first.

Applying this required the full reload pipeline, not just a code change, and each step
surfaced its own defect:

1. Regenerated `pbs_programs_s6_bridge.csv` via the extractor (2,287 rows, now including 61
   `Recreation and culture` rows).
2. First reload attempt (`scripts/ingest/run.py`) revealed `federal_pbs_programs_s6_bridge
   .yaml` lacked `replace_on_reload: true` (unlike its sibling `federal_pbs_programs_all
   .yaml`) — reloading was purely additive, leaving the *old*, wrongly-attributed facts
   (e.g. National Gallery of Australia under "Transport and communication", $81.789M) living
   alongside the *new*, correctly-attributed ones as duplicates. Fixed by adding
   `replace_on_reload: true` to the mapping; re-tested: `replaced_existing: 140` confirmed
   the old facts were cleared before the fresh load.
3. Re-ran `cleanup_pbs_s6_bridge_labels.py` (Loop 5's classifier-driven cleanup) against the
   freshly-loaded rows, which also caught one more classifier precision gap: labels like
   `"Adjusted opening balance (1,431)"` and `"Investments (91,081) (1,944)"` — trailing
   numeric parenthetical value groups — were still passing as `program: True` because
   `lowered_no_footnote` only stripped *alphabetic* 1–2 char footnote markers (`(a)`/`(b)`),
   not numeric value groups. Added a second normalization, `lowered_no_trailing_values`
   (strips one or more trailing `(-?numeric[,numeric])`-style groups), checked alongside the
   existing normalizations before the vocabulary lookup. One new positive test added
   (`test_trailing_parenthesized_numeric_values_stripped_before_vocabulary_lookup`),
   `tests/ingest/test_pbs_label_classifier.py` now at 41 tests, all passing.
4. Even after the corrected facts existed in `data/facts.db`, "Arts and cultural heritage"
   had no children reachable via the live API's related-branch resolution
   (`attach_related_to_tree`). Root cause: the `pbs_dss_bridge` edge set
   (`scripts/ingest/breakdown_pack.py`'s `link_pbs_to_components`) is a *separate* build step
   from fact-loading, not rebuilt automatically by `run.py`. The old edges (pointing at the
   now-deleted "Transport and communication" nodes) had already been orphan-cleaned by step
   3; new edges to the correct nodes were simply never created. Fixed by explicitly running
   `scripts/ingest/edge_pack.py --rebuild --crosswalk-id pbs_dss_bridge --apply`.

Disposable-copy-first discipline followed throughout (each step tested against a scratch
copy of `data/facts.db` via `FACTS_DB_PATH` before being applied to the live file); idempotency
confirmed at each step (second run of reload/cleanup/edge-rebuild produced 0 further change).
Backed up live DB immediately before applying the full pipeline to it
(`/home/vibe-server/backups/ausgov-budget-tracker/facts-20260823T192212Z.db`). Before→after on
the live DB: `facts` 331279→331583 (+304), `nodes` 240694→240754 (+60), `breakdown_edges`
13284→13332 (+48), `facts_pending_attribution` 37431→38141 (+710 — the stricter
trailing-value classifier fix quarantines more junk even as it also newly publishes 37
genuine arts/culture and other program rows), `source_documents` unchanged (147).
`PRAGMA integrity_check`: ok.

### Part B: a canonical-total-safety regression this surfaced, and its fix

While the live DB mutation above only touches related-branch (PBS bridge) data, a routine
`dashboard_depth_audit.py --check-fixture` re-verification (run proactively, not because
anything was expected to fail) caught that `federal_budget_2023_24`'s canonical **additive**
root total had silently shifted from $1,787,437,333,000 to $1,819,600,186,000 (+$32.16B) —
a figure Loop 3's fix had explicitly, deliberately left untouched (Statement 6 doesn't cover
FY2023-24, so that year was never brought under the canonical-source restriction).

Root cause: the classifier-precision improvement in Part A (and Loop 5) newly *published* 37
previously-quarantined `federal_pbs_programs_s6_bridge` facts for FY2023-24, totaling
$32,162,853,000. These are genuinely well-formed program facts (real Defence programs, Other
economic affairs programs, NDIS-related items — verified individually, not junk) — but for
years without Statement 6 coverage, `_fact_rows()` had no restriction excluding the bridge
source from the canonical budget-mode query, so these newly-legitimate facts flowed straight
into the additive total *alongside* `federal_pbs_programs_all`, which already covers the same
spending at portfolio level. This is the same double-counting class Loop 3 fixed for
FY2024-25+; FY2023-24 just had no clean Statement-6-based alternative source to switch to, so
Loop 3 deliberately preserved its pre-existing (imperfect but already-reviewed) baseline
un touched. Letting the bridge's newly-published facts add on top of that baseline would have
made an already-known-imperfect figure worse — a straightforward canonical-total-safety
violation, not a legitimate correction (no source error is being fixed; the *old* figure was
never wrong for what it represented, it was just already excluding this source deliberately).

Fix, in `src/backend/routers/v2/dashboard.py`'s `_fact_rows()`: restructured the budget-mode
federal source-filtering into an explicit if/else on `_statement_6_covers_year()`. Years
Statement 6 covers keep the existing canonical-pair restriction
(`_BUDGET_FEDERAL_CANONICAL_SOURCE_KEYS`). Years without Statement 6 coverage now explicitly
exclude `federal_pbs_programs_s6_bridge`, `federal_dss_pbs_programs`, and
`federal_health_pbs_programs` from the canonical query, restoring `federal_pbs_programs_all`
as the sole contributor — exactly the pre-session baseline for those years.

Verified via a disposable local backend restart against the live DB, across all five
previously-established reference years:

| Year | Root total |
|---|---|
| FY2022-23 | $1,629,222,000 |
| FY2023-24 | $1,787,437,333,000 (restored) |
| FY2024-25 | $770,071,000,000 |
| FY2025-26 | $812,063,000,000 |
| FY2029-30 | $933,729,000,000 |

All five match their established, previously-reviewed baselines exactly.

### Tests

Full backend suite (`pytest tests/ --ignore=tests/ingest --ignore=tests/api/test_citation.py`,
325 tests): confirmed the two tests that had caught the Part B regression
(`test_root_total_still_unaffected_after_edge_deployment[2023-24-...]` in
`test_historical_pbs_s6_crosswalk.py`, `test_federal_budget_root_total_unaffected_by_
historical_evidence[2023-24-...]` in `test_historical_related_evidence_isolation.py`) pass
again with the Part B fix applied. `tests/ingest/test_pbs_label_classifier.py`: 41/41 passing
after the Part A trailing-value fix.

`dashboard_depth_audit` golden fixture regenerated to reflect Part A's related-branch changes
(canonical/additive branch counts unchanged in every projection — proving Part A never
touched a canonical total; only `related` branch counts, `edge_count` (13284→13332), and
per-projection `source_families.budget` / citation leaf counts grew, reflecting the newly-
reachable arts/culture and other previously-misattributed/quarantined facts). Reconfirmed
idempotent across 2 consecutive `--check-fixture` runs. Full suite re-run with the fixture
change included: 325/325 passing.

### Remaining, disclosed

- A small number of single-occurrence malformed label shapes remain unclassified per Loop 5's
  original disclosure (unchanged by this loop, not pursued further — same accuracy-vs-effort
  tradeoff already documented there).

### Matrix regeneration and a disclosed measurement limitation (not a regression)

Regenerated `ops/reports/federal-depth-opportunity-matrix-20260823T194438Z.{csv,json}` per
the mission's requirement that the matrix become the authoritative engineering queue after
the bridge repair. While reviewing it, every `federal_budget_2025_26` row showed
`max_related_depth: 0`, despite this loop having just live-verified that "Recreation and
culture" genuinely has reachable related PBS-bridge children (National Gallery, Creative
Australia, etc., confirmed via `/v2/dashboard/item/257942/children`).

Root cause, confirmed via `git blame`: `dashboard_tree()` only calls `attach_related_to_tree()`
- which inlines the related overlay directly into the initial full-tree response - when
`mode == "actuals"` (`src/backend/routers/v2/dashboard.py:889`, dating to commit `64c0f6d8`,
2026-07-24 - **pre-dating this entire session**, not something Loop 3 or Loop 6 introduced).
Budget mode's related children are real and reachable, but only via a separate, per-node
`/item/{id}/children` call (the same lazy mechanism the frontend uses on click/hover to
progressively disclose deeper rings) - never inlined into the single-call tree payload the
matrix script reads. So the matrix's `max_related_depth` column is a genuine **measurement
blind spot for budget-mode projections specifically**, not evidence those functions lack
related depth. `canonical_additive_depth` (which the matrix computes correctly for both
modes, from the same inline payload) remains a trustworthy signal either way.

Not fixed here: extending the matrix to recursively probe `/item/{id}/children` for every
budget-mode leaf is a materially larger change (many additional HTTP calls per run, needs its
own care around request volume and caching) than "regenerate the matrix," and is better done
as its own scoped, tested unit of work. Flagging this explicitly so a future loop doesn't
read a `0` in this column for a budget-mode function and wrongly conclude no related depth
exists there — check via the live API (`/item/{fact_id}/children`) before treating a
budget-mode function as a dead end on this basis alone.

## Loop 7 — investigating the budget-mode related-depth blind spot: one real fix landed, one attempted fix reverted

A follow-up mission prompt asked to fix the matrix's `max_related_depth=0`-for-budget-mode
blind spot (disclosed at the end of Loop 6) before relying on budget metrics for
prioritization, explicitly framing it as reachable "only through the lazy per-node
related-detail endpoint" (`/v2/dashboard/item/{id}/children`). Investigating that endpoint
directly surfaced three separable findings.

### Finding 1 (real, fixed): a second, independent "sum children instead of trusting the
published fact" bug

Calling `/item/{id}/children` on `"Recreation and culture"` (budget mode, FY2025-26) returned
its child `"Arts and cultural heritage"` at **$1,199,606,000** — not its real
`federal_budget_statement_6_a61` figure of **$2,329,000,000**. Root cause: `dashboard_tree()`'s
own tree builder (`_build_tree_dict()`) marks `_a61`-sourced nodes `preserve_amount=True`
since Loop 3, so a parent's published amount is never silently overridden by summing its
children — but `build_same_group_subtree()` (`breakdown_graph.py`), the *separate* tree
builder that powers `/item/{id}/children`, never got this same marking. Any node reached
through it that also has its own nested `same_group` children (here: 13 `pbs_dss_bridge`
program facts, which sum to only $1.1996B — 48% short, a known-partial, non-exhaustive
subset, not a genuine partition) silently reported the wrong, recomputed total instead of its
real fact.

**Fixed**: `build_same_group_subtree()` now sets `preserve_amount=True` on every node it
constructs, mirroring `_build_tree_dict()`'s Loop 3 fix exactly (`src/backend/breakdown_graph.py`).
New regression test `tests/api/test_item_children_preserve_amount.py` proves the bug on revert
(`1199606000.0` obtained vs `2329000000.0` expected) and passes with the fix. Full backend
suite: 861/861 passing. Canonical `/tree` totals for all 5 reference years confirmed
unchanged (this code path is never read by `dashboard_tree()`). Committed `52ea833`.

### Finding 2 (real, disclosed, not fixed): `build_related_subtree()` can silently drop a
related family when two crossings share a child name

While tracing why `/item/{id}/children` on the canonical GFS "Defence" node returned only one
related child (via `fbo_2024_25_under_abs`) while the live `/tree` response for the same node
exposes a much richer one (via `statement_6_under_abs`, prioritized by `attach_related_to_tree`'s
own explicit per-policy grouping), found that `dashboard_item_children()` calls
`build_related_subtree()` **without** an `edge_set_ids` filter — so if two different
related_breakdown crossings from the same node happen to produce a child with the same name,
`build_related_subtree`'s internal `children: dict[str, Any] = {}` (keyed by name) lets
whichever edge is processed last silently overwrite the other's data. `attach_related_to_tree()`
avoids this by calling `build_related_subtree()` once *per policy*, explicitly. Not fixed
here — confined to the still-unused `/item/{id}/children` endpoint; disclosed for whoever
next builds a real consumer on top of it.

### Finding 3 (attempted fix, reverted): reclassifying cross-source crosswalks broke actuals
mode's own, already-working depth cascade

Deeper investigation of `/item/{id}/children`'s `same_group` vs `related_breakdown`
classification found that `link_pbs_to_components()`, `link_a61_to_components()`, and
`link_path_children_under_cascade()` (`breakdown_pack.py`) all hardcode `edge_kind='same_group'`
for crosswalks that connect genuinely *different* measurement axes (PBS/DSS/Health-PBS
programs, GrantConnect awards, AusTender contracts, DSS recipient-demographic **counts** —
the last confirmed via direct query to carry `measure_type='recipient_count'` while its `unit`
column is separately, wrongly labeled `'AUD'`, a distinct disclosed data-quality defect) under
Statement 6 nodes. `edge_sets.yaml`'s declared `edge_kind` field for these crosswalks turned
out to be purely descriptive — `_insert_same_group()` writes the literal DB value regardless
of what the YAML says, so the config had silently drifted from reality.

Attempted fix: added `_insert_related_breakdown()` and switched all six affected call sites to
it, updated `edge_sets.yaml` to match, rebuilt the edge sets on a disposable copy first
(idempotent, verified via live API — the exact bug from Finding 1 was fixed *and* correctly
relabeled `branch_kind: related`). **But** the full backend suite then failed three tests, all
in `mode=="actuals"`: `Defence`'s related cascade lost its AusTender contract-level detail
entirely, and `max_visible_depth` dropped from 4 to 2. Root cause: `attach_related_to_tree()`
(the mechanism actuals mode already successfully uses) deliberately keeps this *entire* chain
(a61 → components → PBS → contracts/grants) as one continuous `same_group` traversal for
`build_same_group_subtree()`'s own internal recursion to walk in a single pass — applying
non-additive labeling correctly via a **separate, dedicated function**, `_mark_related_descendants()`
("Force every descendant beneath a related_breakdown attach point to carry its own explicit
non-additive tag... regardless of depth"), rather than by making every individual crossing its
own `related_breakdown` edge. Reclassifying the edges at the source fragmented that chain into
disconnected islands `build_same_group_subtree`'s single call could no longer bridge, since
`walk()`'s own recursion never re-visits past the *first* `related_breakdown` crossing.

**Reverted in full**: `scripts/ingest/breakdown_pack.py` and `config/breakdowns/edge_sets.yaml`
restored via `git checkout`; the six edge sets rebuilt back to `same_group` on both the
disposable copy and the live DB (`edge_pack.py --delete`/`--rebuild`, matched before/after
counts exactly: 53/187/7/3/478/15, `PRAGMA integrity_check: ok`). Full suite reconfirmed
861/861 passing with the revert applied. The `preserve_amount` fix from Finding 1 (which does
*not* depend on edge_kind and doesn't affect traversal) was kept.

**Why not pursued further this loop**: safely enabling budget-mode related overlays for real
(the underlying, genuine gap) means either (a) extending `attach_related_to_tree()`/`dashboard_tree()`
to call the same mechanism for `mode == "budget"` too — architecturally different from actuals
mode since budget mode's canonical structure is *already* deep (Statement 6 A61/components),
unlike actuals mode's shallow GFS purposes, so the interaction needs its own careful,
dedicated verification, not a same-day change — or (b) hardening `/item/{id}/children` itself
(fixing Finding 2, adding its own non-additive marking) before trusting it as a real API
surface. Both are real, valuable, correctly-scoped follow-on work, not done here.

### Matrix outcome

Rather than build the matrix's "fix" on the now-proven-fragile `/item/{id}/children` endpoint,
`federal_depth_opportunity_matrix.mjs` now explicitly reports `related_depth_measurable: false`
and `max_related_depth: null` (CSV: `not_measurable_budget_mode`) for every budget-mode row,
replacing the previous misleading `0`. `canonical_additive_depth` is untouched and remains
trustworthy for both modes. Regenerated matrix:
`federal-depth-opportunity-matrix-20260824T033607Z.{csv,json}`. Committed and pushed `2e0a0b1`
(`HEAD == origin/main` confirmed).

## Loop 8 — NDIS participant/plan-budget depth (Priority 2), and a systemic unit-mislabeling fix found along the way

### Part A: a genuinely systemic bug found preparing the NDIS work

Reviewing `federal_dss_payment_demographics.yaml` (the closest existing template - recipient
counts attached as related evidence) as a model for the new NDIS mapping found it already
correctly declares `native_unit: recipients` - but the live database showed `unit: 'AUD'`
for every one of its 52 facts anyway. Root cause: `load_facts.py`'s `upsert_fact()` and
`quarantine_fact()` hardcoded the literal `'AUD'` in their `INSERT` statements, completely
ignoring `mapping.get("native_unit")` - a field only `source_documents` actually stored,
never `facts` itself. Every count-based source in the whole pipeline has silently had its
`unit` column mislabeled since inception; only 1 of 133 existing mappings happens to declare
`native_unit` at all (dss_payment_demographics), so the practical blast radius was exactly
that one source - every other mapping's correct default ('AUD' for genuinely dollar
figures) was unaffected.

**Fixed** (`scripts/ingest/load_facts.py`): both INSERTs now bind `mapping.get("native_unit")
or "AUD"` instead of the hardcoded literal, and both `ON CONFLICT` clauses now also update
`unit`, so a plain reload (no `replace_on_reload` needed) fixes existing rows in place.
Verified via disposable-copy-first reload of `federal_dss_payment_demographics` (52/52
facts, `unit` AUD → recipients, idempotent), then applied identically to the live DB. Golden
fixture regenerated with a precisely-explained diff (43 recipient-count facts moved from the
`AUD` unit bucket to a new `recipients` bucket, matching the source's exact fact count).
Full backend suite: 861/861 passing. Committed `fadb801`.

### Part B: NDIS "Participant Numbers and Plan Budgets" - full ingestion

**Source forensics** (official NDIA data dictionary, read in full - `data/raw/federal/
ndis_participant_numbers_and_plan_budgets/snapshots/20260824T035116Z/files/
participant-plan-budgets-data-rules.docx`): a confidentialized statistical cube,
`RprtDt`/`StateCd`/`SrvcDstrctNm`/`DsbltyGrpNm`/`AgeBnd`/`SuppClass` × `ActvPrtcpnt`
(participant count) × `AvgAnlsdCmtdSuppBdgt` (average annualised committed support budget
per participant - Total Annualised Budget / Participant Count, NOT an aggregate). 100,395
rows, single edition (30 June 2026 = end of FY2025-26; each quarter is a separate
downloadable file, no time series loaded here).

Empirically confirmed (not assumed) beyond what the data dictionary states:
- Counts <11 are suppressed to `"<11"` with budget withheld (36,167 rows) - matches the
  documented rule exactly (`< 11`, not `<= 11`, confirmed via 1,038 rows with exactly 11
  participants that correctly retain both fields).
- A **separate, undocumented** `"<N"` pattern also occurs for N far above 11 (up to 49,918)
  - these retain their budget figure, unlike the true suppression case. Represented
  faithfully as an upper bound either way, via a `count_is_upper_bound` flag - never treated
  as an exact count, and never assumed to mean the same thing as the documented threshold.
- Every service district maps to exactly one state except the shared "Other" catch-all
  bucket (scoped per-state in node names to avoid conflation) - geography genuinely
  supports a two-level State → District nesting.
- Disability group, age band, and state each sum to exactly the grand total (782,013,
  cross-checked against a live NDIA web search finding 774,456 participants as at 31 March
  2026 - a plausible growth trend) - genuinely mutually-exclusive, exhaustive
  classifications. **Support class does not** (sums to 1,611,496 - participants hold
  multiple support classes simultaneously) and **district does not either** (sums to only
  762,917 - suppression drops some districts' exact contribution). This directly shaped the
  extractor design (see below).

**Design decision, per the mission's explicit "do not fabricate a cross-product hierarchy"
rule**: only marginal single-dimension slices are emitted (all other dimensions held at
`"ALL"`), never joint cross-tabulation cells, even though the source does publish full
5-way joint data (28,130 of 100,395 rows have all five dimensions specific) - exposing that
would mean imposing an arbitrary nesting order (state → district → disability → age →
support) the source itself does not structurally support, since disability/age/support are
orthogonal classifications, not children of geography. Structure: `NDIA Participant
Statistics` (root) → `Participants by geography` (State → District, genuine 2-level
nesting) / `Participants by disability group` / `Participants by age band` / `Participants
by support class` (each flat, one level).

Given the empirical non-reconciliation found above, **intermediate folder nodes never carry
a recomputed sum of their children** (would silently double the true total for "by support
class", or understate it for "by geography" districts) - every folder instead carries the
same grand-total value the root already reports, since it is purely a navigation label, not
an independent figure.

**Semantic model** (`scripts/ingest/migrations/028_ndis_participant_plan_budgets_measures.sql`):
two new, deliberately separate measures, both `additive_across_nodes=0`,
`root_total_allowed=0` (matching the established defensive pattern from migration 019's
NDIA PBS-overlap measure): `ndis_participant_count` (unit `participants`) and
`ndis_average_committed_plan_budget` (unit `AUD_per_participant`) - never merged, never
multiplied together to reconstruct a total the source does not itself publish.

**Extractor** (`scripts/ingest/extractors/ndis_participant_plan_budgets.py`, 15 tests in
`tests/ingest/test_ndis_participant_plan_budgets.py`, all passing): writes two staging CSVs
(`ndis_participant_count.csv`, 135 rows; `ndis_average_committed_plan_budget.csv`, 132 rows
- 3 fewer, the true-suppression rows with no budget) loaded by two mapping YAMLs
(`config/mappings/federal_ndis_participant_count.yaml`,
`federal_ndis_average_committed_plan_budget.yaml`).

**Source registration**: added `ndis_participant_numbers_and_plan_budgets` to
`config/procurement_sources.yaml` (validated against the full JSON schema, `direct_file`
access method matching the exact download URL used), with full disclosed caveats
(single-quarter snapshot, suppression, the December 2024 age-band redefinition). Raw files
placed at `data/raw/federal/ndis_participant_numbers_and_plan_budgets/snapshots/
20260824T035116Z/` with `hashes.json` (SHA256) and a `discovery.json` honestly documenting
manual `curl` retrieval (not the automated crawler) against the exact URL found on the NDIA
Data Research portal.

**Graph attachment** (`scripts/ingest/breakdown_pack.py`'s `link_ndis_participant_statistics()`,
registered in `edge_pack.py` and `config/breakdowns/edge_sets.yaml`): one `related_breakdown`
edge per measure from the canonical node (`"Social security and welfare / Assistance to
people with disabilities / National Disability Insurance Scheme"`, `federal_budget_
statement_6_components`, node 214873, $53.778B for FY2025-26 - located via explicit program
identity, not label matching) to each measure's own source-native root. Uses
`related_breakdown`, not `same_group`, for this cross-source boundary - unlike the
`pbs_dss_bridge`/`a61_to_components` case Loop 7 found and reverted, there is no existing
consumer relying on `same_group` chain continuity through this brand-new attach point, so
the safer classification carries no traversal risk here.

**A second same-name collision bug found and worked around**: the first attempt gave both
measures' root nodes the identical name `"NDIA Participant Statistics"` - live verification
showed only the budget edge's data survived in `/item/{id}/children`'s combined view (the
count edge's $782,013 was silently overwritten), exactly the `build_related_subtree()`
same-name-collision defect Loop 7 disclosed but did not fix. Rather than touch that fragile
shared function again, worked around it: the two roots now have deliberately distinct names
(`"NDIA Participant Statistics"` / `"NDIA Average Committed Plan Budget"`), verified live to
coexist correctly.

**Disposable-copy-first verification** (both before AND after the collision fix): before/after
on the live DB: `facts` 331583→331850 (+267 = 135+132), `nodes` 240754→241021 (+267),
`breakdown_edges` 13323→13590 (+267 = 134+131+2), `source_documents` 147→149,
`facts_pending_attribution` unchanged (0 quarantined). `PRAGMA integrity_check`: ok.
Idempotent on all four edge-set rebuilds (source-native ×2, crosswalk ×2) and both mapping
reloads.

**Live API verification**, full drill-down confirmed working end to end: Federal → Commonwealth
→ Social security and welfare → Assistance to people with disabilities → National Disability
Insurance Scheme ($53.778B, unchanged) → *related crossing* → NDIA Participant Statistics
(782,013) → Participants by geography (782,013, navigation) → New South Wales (230,427) →
Central Coast (13,272) - **genuine depth 9 from the Federal root**, matching real,
source-native structure at every level (no fabricated hierarchy). The average-budget branch
verified in parallel (root $85,000 → by geography → ACT $76,000). Every leaf's
`relationship.unit` correctly reads `"participants"` or `"AUD_per_participant"` (never bare
`"AUD"`), confirming Part A's fix is working as intended for genuinely new data too.

**Canonical total safety**: all 5 reference-year Budget-mode root totals confirmed
byte-identical before and after (`dashboard_tree()` never reads `breakdown_edges` for its
canonical query). Golden fixture diff after this loop's changes: exactly one line
(`edge_count` 13323→13590, +267, matching precisely) - no canonical or additive branch count
moved at all, confirming this data is invisible to (does not corrupt) the canonical
projection, exactly as the semantic model requires.

**Full backend suite**: 875 passed, 0 unexpected failures (only the expected, since-fixed
fixture staleness). **Frontend**: production-style build + `next build` clean, TypeScript
clean; live browser check (real backend, CORS-configured) confirmed 0 console errors in both
Actuals and Budget mode, and confirmed the NDIS `item/children` endpoint is reachable from
the browser's own fetch context with the new data correctly nested. **Honest limitation
disclosed, not hidden**: as established in Loop 7, no frontend UI component currently calls
`/item/{id}/children` interactively (`apiDashboard.itemChildren` has zero component
callers) - so while this data is now genuinely loaded, correctly modeled, non-double-
counting, and API-reachable exactly like the rest of the graph, a user cannot yet click
through to see it in the live sunburst chart. This is a pre-existing platform limitation
(not created by NDIS), already disclosed as follow-on work.

Committed `52ea833` (Part A unit fix, already covered above), plus this loop's NDIS commits
(migration, extractor, mappings, source registration, graph attachment, tests, fixture,
matrix regen) - see commit log for exact hashes. Pushed; `HEAD == origin/main` confirmed.

### Depth/success metrics for this loop

- NDIS max total semantic depth (Federal root to deepest genuine leaf): **9** (previously 3
  - Loop 4's audit found NDIS "stops at depth 3, no equivalent participant dataset exists").
- New branch families: 2 (`ndis_participants`, `ndis_average_budget`), each with genuine
  multi-dimension structure (geography 2-level, disability/age/support 1-level) - multiple
  legitimate shallow-to-medium branches, not one fabricated deep chain, per the mission's
  explicit "multi-dimension depth is better than fake linear depth" principle.
- New facts: 267. New nodes: 267. New edges: 267. Zero change to any canonical/additive
  total anywhere in the system.
- Disclosed, not silently worked around: the frontend-reachability gap (pre-existing,
  documented in Loop 7) means this depth is proven correct and complete in the data/graph
  layer, but not yet visible to a real user without a future, separate UI feature.

### Loop 9 (forensics only, not yet built) - NDIS payments data: a genuinely richer, verified-additive opportunity, deliberately not rushed

Searched for and found NDIA's official "Payments data" (`dataresearch.ndis.gov.au/datasets/
payments-datasets`, June 2026 edition, `payments_june_2026.csv`, 120,774 rows). Unlike the
Part B participant dataset (counts/averages, never additive), this one reports **actual
aggregate dollars paid** (`PmtAmt`, "Total amount paid to participants in the preceding 12
months") by `SuppClass` (support class) → `SuppCatNm` (support category) → `SuppItemNmbr`
(individual support item), each also cross-tabulated with geography/disability/age in
various combinations.

**Verified, not assumed**:
- The implied grand total (summing the 4 non-`ALL` `SuppClass`-level rows: Core $40.53B +
  Capacity Building $9.40B + Capital $1.52B + Missing -$3,000) = **$51.45B**, close to but
  **not exactly** the canonical NDIS $53.778B (Statement 6 components, FY2025-26) - a ~4.3%
  gap plausibly explained by different accounting basis/period ("preceding 12 months" ending
  30 June 2026 is a rolling actual-payments window, not the same construct as a Statement 6
  estimate) or scope differences. **This must attach as `related`, never replace or
  additively merge with the canonical total** - the same discipline applied to the
  participant dataset.
- `SuppClass → SuppCatNm` **is** a genuine, verified, near-exact additive partition *within*
  this source: the 9 categories under "Capacity Building" sum to $9,400,383,000 against the
  class total of $9,400,381,000 (a $2,000 rounding difference on $9.4B) - unlike the
  participant dataset's support-class dimension (where multiple classes per participant
  made summing invalid), a single *payment* transaction belongs to exactly one class and
  category, so summing dollars is safe here.
- `SuppCatNm → SuppItemNmbr` also exists (70,616 item-level rows across 16 categories,
  individual items like "Early Childhood Intervention Professional - Psychologist") but is
  **only published jointly with geography** (state specific, never `ALL`) for the categories
  checked - reconstructing a national item total requires summing across all 9
  state/territory values first, not a simple marginal read.
- The dataset's dimension-availability pattern is **not uniform** like the participant
  dataset's clean single-dimension marginals: 12 distinct "which dimensions are `ALL` vs
  specific" combinations appear across the 120,774 rows (e.g. item-level rows pair with
  geography but never disability/age; class-level rows pair with disability×age jointly but
  never geography). A correct, faithful extractor needs dataset-specific handling per
  pattern, not the participant extractor's uniform "one dimension free, rest `ALL`" logic.

**Deliberately not built this loop**: the participant-dataset build (Loop 8) hit three
distinct, real bugs before landing correctly (a same-name collision, a folder-sum
non-reconciliation trap on two of five dimensions, a root-name mismatch) - each caught only
through careful, repeated empirical verification. This payments dataset's more complex,
non-uniform structure raises the same risk class further, and rushing it within this loop's
remaining budget would trade away exactly the rigor that caught those three bugs. Recording
the verified forensics above (grand total non-reconciliation, confirmed-safe
`SuppClass→SuppCatNm` additive nesting, the state-joint item-level caveat, the 12-pattern
non-uniformity) so a dedicated follow-up loop can build this efficiently and correctly
without repeating the discovery work. Raw file cached locally (not yet formally registered
in `procurement_sources.yaml` or moved into `data/raw/` - a deliberate half-step, since
formal registration is normally done alongside, not ahead of, the ingestion it supports).

## Loop 10 — NDIS payments depth built (Loop 9's forensics executed)

Built the extractor Loop 9 deliberately deferred, using the verified forensics already
banked: `scripts/ingest/extractors/ndis_payments.py` extracts only the verified-safe
`SuppClass → SuppCatNm` slice (20 rows: 4 support-class totals + 16 categories), 7 tests in
`tests/ingest/test_ndis_payments.py` (all passing, including one that pins the exact
$2,000-on-$9.4B reconciliation tolerance and one that asserts the implied grand total does
*not* exactly match the canonical $53.778B figure - guarding the reason this attaches as
`related_breakdown`, not `same_group`, at the canonical boundary).

New measure `ndis_payment_amount` (`scripts/ingest/migrations/029_ndis_payment_amount_
measure.sql`, `additive_across_nodes=0`, `root_total_allowed=0` - same defensive pattern as
migrations 019/028), source registered in `procurement_sources.yaml`
(`ndis_payments_data`), raw file cached at `data/raw/federal/ndis_payments/snapshots/
20260824T044821Z/` with `hashes.json`/`discovery.json`. Graph: extended the existing
`link_ndis_participant_statistics()` crosswalk (now covering three NDIS statistics families)
with a third `related_breakdown` edge from the canonical NDIS node to a new `"NDIA Payments"`
root; internal `SuppClass → SuppCatNm` nesting is `same_group` (verified genuine partition,
single source) via a new `ndis_payments_source_native` edge set.

**A genuine difference from Loop 8, verified live and worth noting**: the `"NDIA Payments"`
root node has no fact of its own (no grand-total row was extracted, since none exists
natively in the source), so `_to_tree_node()`'s default "sum children" behavior applies -
and *unlike* the participant dataset's folder-aggregate trap, this is exactly correct here:
the 4 support classes are genuinely mutually exclusive and exhaustive of the whole dataset,
so their sum ($51,451,547,000) is the same real figure already independently verified during
Loop 9's forensics, not a fabricated recomputation.

**Disposable-copy-first verified** (facts/nodes/edges each +20/+21/+21, 0 quarantined,
idempotent on both edge-set rebuilds and the mapping reload, integrity ok), applied
identically to the live DB. **Live drill-down confirmed**: canonical NDIS ($53.778B,
unchanged) → related crossing → NDIA Payments ($51.45B) → Capacity Building ($9.4B) →
CB Daily Activity ($5.96B) - depth 9 from the Federal root, a second, independent genuine
deep branch alongside Loop 8's participant/geography chain. Every leaf's `relationship.unit`
correctly reads `"AUD"` (a genuine dollar figure this time, unlike Loop 8's `participants`/
`AUD_per_participant`) and `compatibility_group` reads `"ndis_payment_statistics"` (never
`budget_expense`/`actual_expense`, so it can never be swept into a canonical total by a
future query that filters on compatibility_group).

**Canonical total safety**: all 5 reference-year Budget-mode totals confirmed byte-identical
before and after. Golden fixture diff: exactly one line (`edge_count` 13590→13611, +21,
matching precisely). **Full backend suite**: 882 passing (0 unexpected failures). **Frontend**:
clean build, 0 console errors, live browser check (real backend, CORS-configured) confirmed
the payments branch is reachable from the browser's own fetch context with the correct
value. Same disclosed, pre-existing limitation as Loop 8: no frontend UI component yet calls
`/item/{id}/children` interactively, so this data is proven correct and complete but not yet
clickable in the live chart.

### Depth/success metrics after Loops 8–10 combined (NDIS)

- NDIS now has **two independent, genuine deep branches** (participant/geography chain,
  depth 9; payments/support-category chain, depth 9) plus the average-budget branch -
  multiple legitimate dimensions, not one fabricated linear chain, per the mission's
  explicit "multi-dimension depth is better than fake linear depth" principle.
- Three new, deliberately separate non-additive measures total; zero change to any
  canonical/additive total anywhere in the system across all three.
- Explicitly disclosed remaining NDIS opportunity (not pursued, correctly scoped out):
  support-item-level payment detail (only published jointly with geography) and
  disability/age cross-tabulated payment views (non-uniform dimension availability) - both
  real, bounded, well-understood follow-on work, not silently abandoned.

## Loop 11 — Aged Care / Health survey: one real bug fixed, existing depth confirmed reachable, external MBS/PBS depth disclosed

Health is one of the largest Federal functions (~16% of Federal share, $118-127B across
projections) - the mission's next priority after NDIS. Began with a full inventory of
already-loaded data (per the mission's own "resolve A/B/C/E/F before new acquisition D"
ordering) rather than assuming a source needed acquiring.

### A real bug found and fixed immediately

Drilling into Health's structure surfaced "Medical services and benefits" ($44.768B) and
"Pharmaceutical benefits and services" ($23.318B) both displaying the **identical** 8-item,
$68.086B child set - neither parent's own total. Traced to a `federal_budget_statement_6_
components` mapping missing `replace_on_reload` (the same bug class found and fixed for
Health's own PBS bridge in an earlier session, and for NDIS's DSS demographics unit
labeling this session) - the staging CSV confirmed the 8 cross-contaminated paths don't
exist in the current extraction at all; a prior extractor version's Table 6.8.1/6.8.2
scoping bug left them as stale orphans that a plain reload never purged. Fixed, disposable-
copy-first verified (facts -40, nodes -8, edges -21, idempotent, integrity ok), applied
live. Both parents now reconcile **exactly** with their own (corrected) children. Canonical
totals unaffected (protected by `preserve_amount` throughout - the bug was real but never
inflated a displayed total). Golden fixture's additive leaf count for the affected
projection dropped by exactly 8 (108→100). Full suite: 882 passing. Committed `3d2341d`.

### Existing depth confirmed reachable (Class B, no acquisition needed)

- **Aged Care under "Health / Health services"** ($16.796B canonical parent): `federal_pbs_
  programs_s6_bridge` already provides "Aged Care Act 2024 - Residential Care Subsidies"
  ($26.02B), "- Specialist Aged Care Programs" ($737M), "- Support at Home" ($8.96B), and
  "Related receipts Department of Health and Aged Care" ($2.8M) - combined $35.7B, larger
  than the GFS parent itself (confirming, as expected from prior loops, this is a genuinely
  different classification axis - portfolio/program view vs COFOG subfunction - not an
  exhaustive partition; correctly non-additive by the same reasoning established for every
  other PBS-bridge crossing this mission has built). **Verified live via `/item/{id}
  /children`: already reachable** (`kind: same_group`, `edge_set_id: pbs_dss_bridge`).
- **"Assistance to the states for public hospitals"** ($33.925B, the second-largest single
  Health line): `federal_health_pbs_programs` provides an exact 1:1 re-statement
  ("Assistance to the States for Healthcare Services", $33,925,000,000 - an exact match, not
  a partition) with no further children of its own in any currently-loaded source. This
  reads as a genuine **G-class terminal** at the Federal level: the National Health Reform
  Agreement is a single COAG-negotiated hospital funding pool; more granular by-hospital
  detail is a state-government reporting matter, out of this tracker's Federal scope.
- **"Medical benefits"/Medicare** ($35.144B, the single largest Health component):
  `federal_health_pbs_programs` similarly provides an exact 1:1 re-statement with no further
  children currently loaded.

### Disclosed, not acquired this loop (Class D/E)

- **Medicare Benefits Schedule (MBS) statistics** and **Pharmaceutical Benefits Scheme (PBS)
  dispensing statistics** - both official, AIHW/Services Australia/health.gov.au-published
  datasets with genuine service-category and, in some views, individual-item-level detail -
  are the clearest remaining high-value depth opportunity for Health's two largest
  components ($35.1B Medicare, $22.1B PBS). The specific data.gov.au "MBS Group Statistics"
  listing found is stale (last resource dated July 2016, likely superseded); health.gov.au's
  current "Medicare statistics collection" page did not respond during this loop's access
  attempt. Not pursued further this loop given the friction and the mission's broader scope
  - recorded here as a concrete, well-justified next acquisition target rather than silently
  dropped.
- **"General administration"** ($5.691B), **"Aboriginal and Torres Strait Islander health"**
  ($1.297B), **"Hospital services(a)"** ($1.220B): no PBS/program-level data currently loaded
  or found via keyword search of the existing PBS bridge corpus. "General administration" is
  plausibly a genuine terminal (departmental running costs, not typically further
  decomposed); the other two are smaller, disclosed, lower-priority Class D/E opportunities
  given their size relative to the leaves above.
- **Frontend reachability** (Class F, disclosed repeatedly since Loop 7): Aged Care data
  above joins NDIS's three branches as genuinely-loaded, non-double-counting, API-verified
  related data with no live UI path to click through to it yet. Given this gap now affects
  four+ independent data families, consolidating a fix (a real frontend UI component wired
  to `/item/{id}/children`, per this mission's own explicit "use an explicit hierarchical
  explorer/side panel" guidance) is increasingly the single highest-leverage remaining
  action - tracked as a dedicated follow-on rather than repeated piecemeal per data family.

Regenerated the Federal depth opportunity matrix reflecting the Health stale-fact cleanup:
`federal-depth-opportunity-matrix-20260824T151356Z.{csv,json}`.

## Loop 12 — Defence: AusTender contract refresh with genuine 4-level UNSPSC hierarchy

Defence expenditure is the third largest Federal function (~$53B+). Prior loops had identified that AusTender procurement contracts attached under Defence were from a stale FY2019-20 sample and used flat, non-standard text categories.

### Observe & Diagnose

1. **Stale vintage and flat hierarchy**: Old AusTender procurement data was frozen in FY2019-20, while the rest of actuals/budget data is in FY2024-25/2025-26+. The category structure was opaque text rather than structured commodity classification.
2. **OCDS data availability**: AusTender publishes standard Open Contracting Data Standard (OCDS) releases with 8-digit UNSPSC codes that cleanly decompose into Segment (2 digits) → Family (4 digits) → Class (6 digits) → Commodity/Supplier (8 digits).

### Implementation

1. **Extractor (`scripts/ingest/extractors/austender_ocds_contracts.py`)**: Built a structured OCDS extractor that parses release packages, resolves UNSPSC codes against official UNSPSC hierarchy titles, and extracts contracts with genuine 4-level depth (Segment → Family → Class → Supplier).
2. **Config & Source registration**: Registered `austender_ocds_contract_notices_current` in `config/procurement_sources.yaml` and updated `config/mappings/federal_austender_contracts.yaml` with `replace_on_reload: true` to purge old FY2019-20 facts upon reload.
3. **Crosswalk refinement**: Corrected `pbs_programs_all_under_s6.yaml` for Veterans' pharmaceutical benefits (`Health / Pharmaceutical benefits and services`), scoped `resolve_s6_node_ids` in `scripts/ingest/pbs_s6_crosswalk.py` to current Statement 6 documents, and verified reachability across all test targets.

### Verification & Test Suite Hardening

- **Backend tests**: Added 11 new tests in `tests/ingest/test_austender_ocds_contracts.py`.
- **Year fallback adjustments**: Because contract data is now current (FY2025-26), FY2024-25 requests correctly do not fall forward into 2025-26 data (respecting the non-negotiable no-future-fallback invariant). Adjusted `tests/api/test_breakdown_related.py`, `tests/api/test_dashboard_projection_contract.py`, and re-scoped `src/frontend/tests-e2e/pbs-year-fallback.spec.ts` to test Economic Affairs / PBS fallback.
- **Fixture verification**: Golden fixture regenerated (`dashboard-depth-audit-20260826T061354Z.{json,md}`). Reconfirmed idempotent across multiple runs.
- **Full test gates**: Backend suite 326/326 passed (`pytest`). Frontend `npm run test:unit`, `npx tsc --noEmit`, `npm run lint:ci` (23 errors, 13 warnings matching baseline), `npm run build`, and all 25 Playwright E2E tests in `run_e2e.py` passed with 0 errors.

## Loop 13 — Education (Phase 3): Statement 6 Subfunction Routing and Bridge Classification Precision

Education is the fourth largest Federal function (~$65B in FY2025-26 Budget, ~8% of total Commonwealth spending).

### Observe & Diagnose

1. **Subfunction mismatch in legacy bridge**: `scripts/ingest/extractors/pbs_programs_s6_bridge.py` originally emitted subfunction paths `Education / School education` (which did not match the official Statement 6 node name `Education / Schools`) and `Education / Vocational and industry training` (which did not match `Education / Vocational and other education`). Consequently, `Education / Schools` had 0 children attached in the bridge.
2. **Artificial dumping into General administration**: Because unmatched Education programs defaulted to `General administration`, 27 major policy programs (including Needs-based school funding, NCRIS research infrastructure, Research Training Program, Launch Australia's Economic Accelerator, Quality Outcomes, Teacher Workforce) were dumped under `Education / General administration` instead of their authentic subfunctions.
3. **Missing crosswalk overrides**: `config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml` lacked `program_label_overrides` for Education, attaching all Education PBS programs only to the root `Education` function node.

### Implementation

1. **Bridge Extractor Refinement (`scripts/ingest/extractors/pbs_programs_s6_bridge.py`)**:
   - Corrected Education subfunction names to match Statement 6 exactly: `Higher education`, `Schools`, `Vocational and other education`, `Student assistance`.
   - Integrated `pbs_label_classifier.py` (`classify_label`) to filter out raw table ledger noise and financial statement lines (`financial_statement_line`, `table_header`, `subtotal`, `total`).
   - Mapped programs precisely by statutory program keywords (e.g. Higher Education Support Act, Australian Education Act, NCRIS, Research Support Program, Choice and Affordability Fund, Teacher Workforce, Quality Outcomes, Tertiary Access Payment).
2. **Crosswalk Overrides (`config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml`)**:
   - Added 17 high-confidence `exact_label_with_portfolio_context` overrides routing specific PBS programs to `Higher education`, `Schools`, `Government schools`, `Non-government schools`, `Student assistance`, and `Vocational and other education`.
3. **Database Reload & Verification**:
   - Ingested `federal_pbs_programs_s6_bridge` and rebuilt crosswalk `pbs_programs_all_under_s6` on disposable copy first, then applied live.
   - Verified live reachability:
     - `Education / Higher education`: 9 authentic children (Research Training Program, NCRIS, Study Hubs, etc.)
     - `Education / Schools`: 23 authentic children (Choice and Affordability Fund, Quality Outcomes, Teacher Workforce, Disability Support, etc.)
     - `Education / Student assistance`: 3 children (Tertiary Access Payment, Youth Support, Related PBS)
     - `Education / Vocational and other education`: 2 children (Increase Workforce Mobility, Related PBS)
     - `Education / General administration`: 0 dumped children (clean terminal leaf).

### Verification & Test Suite Hardening

- **New tests**: Added `tests/api/test_education_depth.py` (5/5 passing).
- **Backend test suite**: 331/331 passing (`pytest`).
- **Fixture verification**: Golden fixture updated (`dashboard-depth-audit-20260826T065813Z.{json,md}`) with 0 hard failures, 0 duplicate semantic edges, 0 cycles.
- **Frontend test suite**: Unit tests passing, `npx tsc --noEmit` 0 errors, `npm run lint:ci` 23 errors / 13 warnings (exact baseline match), `npm run build` static export clean.
- **Playwright E2E**: 25/25 passing in real browser against local backend.
- **Opportunity Matrix**: Regenerated at `ops/reports/federal-depth-opportunity-matrix-20260826T070800Z.{csv,json}`.

## Next

1. Proceed to **Phase 4: Federal Dead-End Sweep** across all remaining Federal functions (Transport and Communication, Housing and Community Amenities, Public Order and Safety, Agriculture/Fuel/Energy, Mining/Manufacturing/Construction, General Public Services).
2. For each remaining function: run audit-before-acquisition, attach available PBS/grants/procurement depth where high-confidence evidence exists, or document as genuine terminal leaf.
3. Perform final Exhaustion Gate audit and summary report.
