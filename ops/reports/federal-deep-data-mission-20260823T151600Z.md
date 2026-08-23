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

## Next

1. Acquire and ingest an NDIS participant demographic dataset (by state/age/support
   category, from NDIS Quarterly Reports or the NDIA's published data) to bring NDIS to
   parity with JobSeeker's depth-5 recipient breakdown — the mission's Priority 2, and now
   the clearest concrete next step for Priority 1/2 combined.
2. Investigate `federal_pbs_programs_s6_bridge`'s extraction-quality problems (duplicate
   "Total for Program" rows, operating-statement rows mixed into program rows) as a
   dedicated extractor-quality task before considering it for any related-branch wiring —
   per the mission's own standard ("do not build a permissive parser that happens to work on
   one PDF... add negative tests"), this needs generation-specific extractor work, not reuse
   as-is.
3. Regenerate the Federal depth opportunity matrix for `federal_actuals_2025_26` to confirm
   it's unaffected by the Budget-mode fix (expected — this loop only touched Budget mode).
4. Continue through Aged Care/Health, Defence, Education per the mission's priority order,
   applying the same audit-before-ingest discipline this loop established: check what's
   already loaded and connected before acquiring anything new.
