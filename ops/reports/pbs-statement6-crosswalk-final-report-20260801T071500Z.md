# PBS -> Statement 6 crosswalk milestone — final report

Repository: `ausgov-budget-tracker`. Branch: `main` (worked directly on
`main` per instructions; no feature branch created). Starting commit:
`c971abe`. All work backed up before any `data/facts.db` write via
`scripts/ops/backup_facts_db.py` (`/home/vibe-server/backups/ausgov-budget-tracker/facts-20260801T064150Z.db`
is the pre-write baseline this milestone built on).

## Objective (recap)

Link the corrected `federal_pbs_programs_all` dataset (53,083 facts across
63 federal PBS documents) into the existing Statement 6 / portfolio
dashboard hierarchy as **related, non-additive** navigation - without
touching any authoritative Statement 6 total.

## Mappings added

`config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml`: a
declarative, evidence-tiered crosswalk (portfolio-ownership defaults +
exact-substring program-label overrides, evidence types recorded per
entry, ambiguous portfolios explicitly excluded rather than defaulted).
16 portfolio-level entries (14 mapped, 2 deliberately ambiguous), 12
program-label overrides (NDIA/NDIS split out of Health and Social
Services' defaults; DVA health/pharmaceutical programs split out of DVA's
welfare default; DSS aged/disability/carer/family/unemployment
subfunction routing).

## Facts made navigable

- **7,746 of 9,779 live PBS program nodes (79%)** are now reachable as
  `related_breakdown` children of a real Statement 6 node - 42,489 of the
  53,083 PBS facts (the remainder belong to nodes whose portfolio has no
  crosswalk entry, or is deliberately marked ambiguous - see below).
- 16,365 `related_breakdown` edges created (one per distinct
  PBS-node × Statement-6-edition pair, since three Statement 6 editions -
  `_2026_27`, `_a61`, `_components` - can each independently be the one a
  given dashboard render resolves to).
- 9,791 `same_group` edges created under `federal_pbs_programs_all` itself
  (portfolio-folder internal browsing, e.g. all of "Health Disability and
  Ageing"'s ~800 programs under one folder) - unrelated to the Statement 6
  boundary, purely PBS-internal convenience navigation.

## Portfolios covered

Mapped (portfolio-level default, further refined by label overrides where
applicable): Social Services, Health Disability and Ageing (incl. NDIA
carve-out), Defence, Education, Veterans' Affairs (incl. health/welfare
split), Agriculture Fisheries and Forestry, Employment and Workplace
Relations, Finance, Foreign Affairs and Trade, Home Affairs, Industry
Science and Resources, Climate Change Energy the Environment and Water,
Prime Minister and Cabinet, Treasury.

Deliberately **ambiguous, unmapped**: Attorney-General's (spans courts/
legal services, emergency management, human rights, integrity/security
with no single dominant Statement 6 function) and Infrastructure Transport
Regional Development Communications Sport and the Arts (spans Transport
and communication, Recreation and culture, and Housing and community
amenities by its own portfolio name). 1,376 PBS nodes fall here - none
were given a guessed function.

**Unmapped, no crosswalk entry**: the smaller Parliamentary bodies
(Parliamentary Departments, Senate, House of Representatives, Parliamentary
Budget Office) - 657 PBS nodes. Not addressed in this pass; genuinely
uncertain whether/how these map onto Statement 6's executive-government
function classification.

## Hierarchy depth: before and after

- **Before**: `federal_pbs_programs_all` had zero linkage into the
  Statement 6 hierarchy. Drilling into any Statement 6 function/
  subfunction in the dashboard showed only Statement 6's own structure.
- **After**: drilling into a mapped Statement 6 node now surfaces a
  clearly labelled "Related PBS program detail" (or, for true Statement 6
  leaves, a direct `related_breakdown` response) containing the relevant
  PBS programs, each with its own citation. Verified end-to-end (real
  backend + real static-export frontend, not just direct SQL) for all 7
  representative cases the milestone named: Social Services, Health, NDIA,
  Defence, Education, DVA (health-labelled programs), DVA
  (welfare-labelled programs). Full detail:
  `ops/reports/pbs-statement6-dashboard-depth-20260801T070500Z.md`.
- **Root and subfunction totals: unchanged.** Budget mode, federal level,
  FY2026-27: root total $24,679,913,611,800 identical before and after
  (compared programmatically across every top-level sibling, not
  spot-checked). Confirmed both by direct API comparison and by
  construction: `related_breakdown` edges are only consulted by
  `/item/{fact_id}/children` on user-driven drill-down, never by the tree
  endpoint's own root-sum calculation.

## Real bugs found and fixed during this work

1. **SQLite NULL-uniqueness gap in `breakdown_edges`'s dedup.** SQL NULLs
   are never equal to each other, even inside a UNIQUE constraint -
   `INSERT OR IGNORE` therefore did not dedupe edges where the differing
   column was NULL (`financial_year` on every edge this crosswalk and
   several *pre-existing* crosswalks create). Fixed in three places in
   `scripts/ingest/breakdown_pack.py` (`link_same_group_from_paths`,
   `link_related_crosswalk`, `_insert_same_group` - the latter shared by 5
   call sites) with an explicit `IS`-based check-then-insert. This bug
   predated this milestone and had already produced **7,311 duplicate
   rows in production** (31% of `breakdown_edges`) from earlier,
   unrelated crosswalk runs - cleaned up as part of this work (kept the
   lowest `id` per duplicate group; every deleted row was byte-identical
   to the one kept in every non-`id` column, confirmed before deleting).
2. **`fact_for_node_year()` requires the `related_breakdown` child to
   carry a fact directly.** The first implementation attached edges to a
   shared "portfolio folder" node per portfolio to avoid thousands of
   direct children under one Statement 6 parent - a fact-less aggregation
   node, which this function silently drops. Found via the real dashboard
   API (not assumed), not a hypothetical. Fixed by attaching directly to
   each individual PBS program node instead, matching the existing
   precedent (`pbs_dss_bridge`, `grantconnect_under_pbs`).
3. **`/item/{fact_id}/children` treats `same_group` and
   `related_breakdown` as mutually exclusive** (`same_group` always wins
   when present). Since most Statement 6 function/subfunction nodes
   already have real internal `same_group` structure, this would have
   made every one of this crosswalk's edges on a non-leaf node permanently
   unreachable. Fixed with a minimal, additive change to
   `dashboard_item_children()` in `src/backend/routers/v2/dashboard.py`:
   when both exist, `same_group` children are returned as before, with an
   extra "Related PBS program detail" folder appended (clearly labelled
   non-additive, preserving the parent's own amount).
4. **4,257 pre-existing orphaned `federal_pbs_programs_all` nodes**
   (left behind by an earlier session's `replace_on_reload` fact-delete,
   which never cleaned up the `nodes` table itself) were about to
   accumulate *more* dead same_group edges once `link_same_group_from_paths`
   ran over them. Deleted (verified zero references first) before loading
   this crosswalk.

All four are documented with regression tests / verified before-and-after
evidence, not silently patched.

## Tests run

- `pytest tests` (backend + ingest): **112 passed**, 0 failed. Includes 24
  new tests in `tests/ingest/test_pbs_s6_crosswalk.py` covering: crosswalk
  schema validation, evidence-tier precedence (label override before
  portfolio default), all 6 named representative portfolios plus the
  ambiguous case, idempotent edge creation (including a specific
  regression test for the NULL-uniqueness bug and for a label containing a
  literal "/" as ordinary phrasing), no duplicate edges, no orphan
  endpoints, no 2-node cycles, no cross-year edge contamination
  (`financial_year IS NULL` universally), no additive PBS-into-S6 edge,
  ambiguous portfolios get zero edges, citation/root-total preservation
  after edge load, and orphan-node exclusion.
- `npm run build` (frontend): clean, all 9 routes statically generated.
- `npm run test:e2e` (Playwright, static export + real backend): **14
  passed** - the 7 pre-existing dashboard regression tests plus 7 new
  tests in `tests-e2e/pbs-s6-crosswalk.spec.ts` verifying, through the
  real browser's own CORS-enabled fetch (not a server-side curl), that
  each representative case's related PBS detail is reachable, labelled
  non-additive, and carries a complete citation.
- `ingestion_coverage_audit.py`: status counts unchanged from the prior
  milestone's final state (this work doesn't touch registry
  classification).
- `ingestion_coverage_lineage.py`: 7 canonical datasets, unchanged.
- `quarantine_report.py`: 15 quarantined rows, unchanged (no new
  quarantine from this work).
- `revenue_reconciliation.py` / `debt_reconciliation.py`: unchanged from
  the prior milestone's results (Commonwealth revenue reconciles at
  0.12%; 7/7 debt-authority reconciliations pass).

## Exact database changes

Starting state: 321,950 facts, 234,610 nodes, 14,911 `breakdown_edges`
(0 idempotency-safe - 7,311 were duplicates from a pre-existing bug).

- **Facts: unchanged at 321,950.** This milestone never inserts, updates,
  or deletes a single row in `facts`.
- **Nodes: 234,610 → 230,391** (net -4,219): -4,257 genuinely orphaned
  `federal_pbs_programs_all` nodes deleted (zero facts, zero edges,
  verified safe before deleting), +38 new legitimate portfolio-folder
  nodes created for PBS-internal same_group browsing.
- **`breakdown_edges`: 14,911 → 33,756**: -7,311 pre-existing duplicate
  rows removed (bug #1 above, cleanup), +9,791 new `same_group` edges
  (PBS-internal portfolio folders), +16,365 new `related_breakdown` edges
  (this crosswalk, `crosswalk_id = 'pbs_programs_all_under_s6'`).
- Idempotency proven directly: running the load a second (and third) time
  after the fix inserts exactly 0 new rows of either kind.
- All operations backed up beforehand
  (`facts-20260801T061340Z.db`, `facts-20260801T064150Z.db` under
  `/home/vibe-server/backups/ausgov-budget-tracker/`, outside the repo).
  `data/facts.db` itself, raw data, and backups are not committed to git.

## Acceptance criteria checklist

1. PBS program facts reachable from appropriate Federal dashboard
   branches - **yes**, verified for all 7 named representative cases via
   real backend + real frontend.
2. Related PBS details not summed into authoritative Statement 6 totals -
   **yes**, structurally guaranteed (`related_breakdown` only,
   `preserve_amount` semantics) and verified directly.
3. Root and subfunction totals unchanged - **yes**, verified
   programmatically before/after.
4. Crosswalk coverage and unresolved mappings quantified - **yes**,
   `ops/reports/pbs-statement6-crosswalk-coverage-20260801T065957Z.{csv,md}`.
5. All new edges idempotent and citation-preserving - **yes**, verified
   by running the load twice and by direct citation-preservation tests.
6. No orphan, duplicate, cyclic, or incompatible edges - **yes**, verified
   directly against the full `breakdown_edges` table (not just this
   crosswalk's own rows).
7. Unit, basis, year, and estimate-status safeguards pass - **yes**
   (edges are year-agnostic by construction; amount/unit/basis are never
   touched, only graph edges between existing facts).
8. Full backend tests pass - **yes**, 112/112.
9. Frontend build and Playwright tests pass - **yes**, build clean,
   14/14 Playwright tests pass.
10. This report.

## Known, documented limitations (not fixed in this pass)

- One specific Statement 6 leaf (`federal_budget_statement_6_components`'s
  "...National Disability Insurance Scheme" node) has a pre-existing
  `same_group` edge (unrelated cascade, predates this work) pointing at a
  same-named node from a *different* dataset
  (`federal_dss_pbs_programs`), which shadows this crosswalk's own edge at
  that one specific node. Does not affect the other 32 attach points or
  NDIA's overall reachability (confirmed reachable via a different, real
  leaf). See the dashboard-depth report for detail.
- 657 PBS facts (smaller Parliamentary bodies) and 1,376 PBS facts
  (Attorney-General's, Infrastructure/Transport/Regional Development/
  Communications/Sport/Arts) remain unmapped/ambiguous by design -
  resolving them would require either a policy decision (do Parliamentary
  bodies belong in Statement 6's executive-function classification at
  all?) or program-level evidence this pass didn't establish with
  confidence.
- `revenue_reconciliation.py`'s pre-existing 8-jurisdiction warning (state
  detail sums showing $0) predates and is unrelated to this work; not
  investigated further here.
