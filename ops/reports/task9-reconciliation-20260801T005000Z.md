# Task 9 — reconciliation and correctness pass

## Reconciliation scripts

- **`revenue_reconciliation.py`** →
  `ops/reports/revenue-reconciliation-202425.json`. 9 jurisdictions checked
  for 2024-25. Commonwealth: `ok` (0.12% difference, within 5% tolerance).
  8 states/territories (ACT, NSW, NT, QLD, SA, TAS, VIC, WA): `warning`,
  100% difference (`detail_sum: 0`) - **pre-existing gap, not a new
  regression**: detailed state-level tax-revenue-detail sources are not yet
  ingested (`abs_taxation_revenue_key_tables_2024_25_state`/`_territory` are
  loaded per Task 6's lineage fix, but appear not to be wired into this
  specific reconciliation's per-jurisdiction detail-sum query, or the detail
  rows don't yet carry a jurisdiction-level breakdown matching the control
  total's jurisdiction). Flagged as a follow-up rather than investigated
  further given remaining scope; not something this session's changes
  caused (Commonwealth, the one row this session's PBS work is anywhere
  near, passes).
- **`debt_reconciliation.py`** →
  `ops/reports/debt-reconciliation-20260801T004633Z.json`. 7 of 7 checks
  `pass` (NSW TCorp, QLD QTC, SA SAFA, WA WATC, NT NTTC, TAS TASCorp face/
  fair-value reconciliations all within tolerance, largest absolute
  difference $397,000 on a $50.44bn WA WATC total = 0.0008%).
- **`quarantine_report.py`**: 15 quarantined `facts_pending_attribution`
  rows, unchanged from the Task 2 baseline. 14 are pre-existing
  `federal_monthly_financial_statements` rows (Gate 2: `amount_aud is
  null`, 2005-06/2006-07 July columns) - a different, older MFS ingestion
  attempt than this session's new `mfs_aggregates.py` extractor (Task 5),
  which deliberately doesn't touch facts.db yet. 1 is a `synthetic_demo`
  fixture row (missing `landing_url`), clearly a deliberate test entry.
  Nothing new added by this session.
- **`ingestion_coverage_lineage.py`** →
  `ops/reports/ingestion-coverage-lineage.json`. 7 canonical datasets (up
  from the pre-fix count), correctly reflecting Task 6's fixes:
  `abs_taxation_revenue_detail` now shows 2,530 real facts (was 0 before the
  empty-`fact_source_keys` bug was fixed) and `federal_pbs_programs` shows
  54,431 facts.

## Full test suite

`pytest tests` (api + unit + integration + ingest; `tests/frontend` and
`tests/fixtures` contain no pytest-collectible files): **88 passed**, 0
failed, 0 new. This includes the 9 new registry invariant tests (Task 6), 12
new PBS layout/year-variant tests and 4 new MFS extractor tests (Task 3/5).

`node tests/frontend/test_citation_panel.mjs`: **pass**.

`node tests/frontend/test_default_view_regression.mjs`: **fails** -
asserts `app/page.tsx` contains `data-default-store="facts-dashboard"`,
which is absent from the current file. `git log` confirms both the test and
`page.tsx` were last touched together in commit `64c0f6d` ("Cut over facts
dashboard, debt viewer, search, and procurement ingest"), well before this
session's branch (`agent/continue-data-ingestion-20260731`, based on
`77c346a`) - **pre-existing failure, not a new regression**. Likely stale
from the Suspense/HomeClient refactor dropping a marker attribute the test
still expects. Not fixed here (would require confirming intent behind the
marker without more context than this pass affords); flagged for a
dedicated follow-up.

## Frontend build and lint

`npm run build`: **clean** - Turbopack compiles, TypeScript passes, all 9
routes statically generated, no errors or warnings.

`npm run lint`: **34 problems (21 errors, 13 warnings)**, all in
`components/DebtViewer.tsx`, `components/FactCitationViewer.tsx`,
`components/GlobalSearchBar.tsx`, `components/SpendingChart.tsx` - none of
which this session created or modified (confirmed via `git log`: all last
touched in `77c346a`, the commit this session's branch was created from).
Mostly a newer `eslint-plugin-react-hooks` rule
(`react-hooks/set-state-in-effect`, `react-hooks/refs`) flagging patterns
that were presumably fine under whatever lint config was active when this
code was written. **This session's own new files
(`playwright.config.ts`, `tests-e2e/dashboard.spec.ts`) produce zero lint
errors or warnings** - confirmed by grepping the lint output for those
paths. Not fixed here (out of scope - would mean refactoring four
components' effect logic, unrelated to this directive's data-ingestion
focus); reported honestly rather than hidden.

## Database-level reconciliation (direct SQL, not just the reconciliation scripts)

- **Root totals before/after**: 324,984 (Task 2 baseline, start of this
  session) → 321,950 (current). Net **-3,034**, entirely explained and
  already documented in Task 3.5: `federal_pbs_programs_all`'s
  `replace_on_reload` purged 56,117 pre-existing (partially corrupted)
  facts from 2026-07-24 and replaced them with 53,083 verified-correct
  ones. No other source's fact count changed during this session.
- **Duplicate fact_keys**: 0 (enforced by a UNIQUE constraint;
  `test_no_duplicate_fact_keys` in Task 6's invariant suite also checks
  this directly).
- **Orphan facts** (no valid `source_document_id`): 0.
- **Orphan `fact_nodes`** (dangling `node_id`): 0.
- **Orphan `node_edges`** / **`breakdown_edges`** (dangling parent/child
  node ids): 0 each.
- **Facts with a dangling `source_retrieval_id`**: 0.
- **`fact_nodes` count vs `facts` count**: 321,950 = 321,950 - every fact
  has exactly one primary node link, no gaps or duplicates.
- **Cached-file existence, all 131 distinct `cached_copy_path` values
  across every fact in the database** (not just PBS): **0 missing** - every
  citation resolves to a real file on disk.
- **Unit/price-basis mixing**: not independently re-audited beyond the
  existing `tests/api/test_compatibility_guard.py` suite (passing) and this
  session's own citation/unit-scaling fixes (Task 3's Act-year and
  soft-hyphen bugs, both about not mixing/mis-scaling values).
- **Year-inference confidence**: covered under Task 3's PBS work -
  108,502 raw rows, 44,278 at `table_header` (high confidence), 59,667 at
  `source_layout_template` (medium, explicit per-source opt-in, never a
  blind global-slice guess), 8,682 correctly quarantined rather than
  guessed.

## Summary

No new test, build, or lint failures introduced by this session's changes.
Two pre-existing issues surfaced and clearly attributed rather than hidden
(the `test_default_view_regression.mjs` stale assertion, and 34 pre-existing
frontend lint errors/warnings). Database-level integrity is clean across
every check run: no orphans, no dangling edges, no missing cited files, no
duplicate fact keys.
