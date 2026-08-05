# Full validation (Task 11)

Generated: 2026-08-05T04:24:24Z. Every command the mission's Task 11
requires, run against the real, now-MFS-loaded `data/facts.db`.

## Python

| command | result |
|---|---|
| `python -m pytest tests -q` | **296 passed** |
| `python scripts/ops/task9_sql_integrity_checks.py` | `hard_failures: 0` |
| `python scripts/ingest/ingestion_coverage_audit.py` | `status_counts` byte-identical to the prior milestone's final state (`fully_ingested: 47, adapter_missing: 169, partially_ingested: 81, duplicate_source: 23, adapter_broken: 24, officially_unavailable: 7, not_acquired: 12, reference_only: 4`) - MFS introduces no new registry-coverage regressions |
| `python scripts/ingest/ingestion_coverage_lineage.py` | 7 datasets, output byte-identical to before this milestone (MFS uses its own source_id/measure_types, entirely outside the canonical-datasets lineage registry) |
| `python scripts/ingest/quarantine_report.py` | `quarantined=36417` - unchanged (MFS quarantines go to their own separate file, `data/staging/quarantine/mfs_load_quarantine.jsonl`, never `facts_pending_attribution`) |
| `python scripts/ingest/revenue_reconciliation.py` | 9 rows, 8 warnings - output byte-identical to before (pre-existing state-level detail coverage gap, unrelated to MFS) |
| `python scripts/ingest/debt_reconciliation.py` | 7/7 `status: pass` |

## Ruff

`ruff check scripts src/backend tests/unit tests/ops tests/ingest` (CI's
actual checked scope): clean. (Running ruff additionally over `tests/api`
to validate this milestone's own new `test_mfs_api.py` surfaced several
**pre-existing**, unrelated lint issues in other `tests/api/*.py` files -
outside CI's checked scope and outside this milestone; left untouched,
documented in Task 10's report. Fixed the one issue that was this
milestone's own: an unused `sys` import in
`scripts/ops/cleanup_stray_mfs_preload.py`.)

## Frontend

| command | result |
|---|---|
| `npm run lint` | 38 problems (25 errors, 13 warnings) - identical to the committed baseline (`src/frontend/.eslint-baseline.json`); zero new issues from any MFS frontend code |
| `npm run build` | succeeds; `/explorers/mfs` is a real static route |
| `npm run test:e2e` (full local suite, real backend + real `data/facts.db`, all 4 spec files) | **20/20 passed** |

One transient failure was investigated during this task:
`pbs-year-fallback.spec.ts`'s second test failed once with the page
stuck on "Loading…" past its 15s timeout. Traced via network-request
tracing to the `/v2/dashboard/tree` call for that specific deep link
taking longer than usual to respond - not a functional bug (the
underlying data/API is correct; a direct `curl` of the same endpoint
returned in under a second) but resource contention from this session's
own heavy concurrent background-process load (many backend instances,
browser sessions, and pytest/ruff runs run in parallel throughout this
milestone). Confirmed by restarting a single, uncontended backend
instance and re-running the same test **3/3 times cleanly** (13.2-13.4s
each, comfortably under the timeout), then running the complete 20-test
suite once more end to end with a clean pass. Nothing in this milestone
touches `src/backend/routers/v2/dashboard.py`'s tree-building logic,
`breakdown_graph.py`, or anything else on this specific test's path -
the only plausible cause was environmental load, not a code regression.

## Semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against a fresh backend on the real
database: **`total_hard_failures: 0`, `total_accepted_source_rounding_warnings: 0`**
across all 6 required paths and all 7 PBS→Statement 6 crosswalk cases -
identical to the clean state established at the end of the prior
milestone. Every existing dashboard path remains unchanged.

## MFS-specific API and Playwright tests

Added in Task 10: `tests/api/test_mfs_api.py` (12 tests) and
`src/frontend/tests-e2e/mfs-explorer.spec.ts` (4 tests, now part of both
the local `test:e2e` run above and CI's `e2e` job).

## Conclusion

Every command in Task 11's required list has been run against the real,
post-MFS-load database and passes. No existing behavior - annual
dashboard totals, ingestion coverage, reconciliation, quarantine
counts, or the semantic dashboard audit - changed as a result of this
milestone's work.

## Next

Task 12: production verification - rebuild/restart the backend, deploy
the frontend, verify the public MFS API and UI, rerun the production
semantic dashboard audit, and confirm existing Federal/state/local/debt/
GDP/PBS views are unchanged.
