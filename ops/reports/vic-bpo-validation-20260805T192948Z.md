# Full validation (Task 7)

Generated: 2026-08-05T19:29:48Z. Every command Task 7 requires, run
against the real, now-VIC-BPO-loaded `data/facts.db`.

## Python

| command | result |
|---|---|
| `python -m pytest tests -q` | **365 passed** |
| `python scripts/ops/task9_sql_integrity_checks.py` | `hard_failures: 0` |
| `python scripts/ingest/ingestion_coverage_audit.py` | `fully_ingested: 49`, `adapter_missing: 167` - unchanged from Task 4's post-load state |
| `python scripts/ingest/ingestion_coverage_lineage.py` | 7 datasets, unchanged |
| `python scripts/ingest/quarantine_report.py` | `quarantined=36417` - unchanged |
| `python scripts/ingest/revenue_reconciliation.py` | 9 rows, 8 warnings - unchanged |
| `python scripts/ingest/debt_reconciliation.py` | 7/7 `status: pass` |

## Ruff

`ruff check scripts src/backend tests/unit tests/ops tests/ingest` (CI's
actual checked scope): clean.

## Frontend

| command | result |
|---|---|
| `npm run lint` | 38 problems (25 errors, 13 warnings) - identical to the committed baseline; zero new issues |
| `npm run build` | succeeds |
| `npm run test:e2e` (full local suite, real backend + real `data/facts.db`, all 4 spec files) | **20/20 passed** |

## Semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against a fresh backend on the real
database: **`total_hard_failures: 0`, `total_accepted_source_rounding_warnings: 0`**
across all 6 required paths and all 7 PBS crosswalk cases - identical to
the prior milestone's final clean state. Every existing dashboard path
remains unchanged; the VIC BPO family is reachable only through the GFS/
jurisdiction explorer's own `vic_bpo_*`-scoped API calls and cannot reach
any additive dashboard tree.

## Conclusion

Every command in Task 7's required list has been run against the real,
post-VIC-BPO-load database and passes. No existing behavior changed as a
result of this milestone's work.

## Next

Task 8: production verification - rebuild/restart the backend, deploy
the frontend (which now includes the VIC BPO UI), verify the public API
and UI for the new family, rerun the production dashboard audit, confirm
existing dashboard paths unchanged, and record the Cloudflare issue's
status (deferred - not touched this milestone, per Task 2's decision).
