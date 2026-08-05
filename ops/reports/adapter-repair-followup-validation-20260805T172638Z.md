# Full validation (Task 7)

Generated: 2026-08-05T17:26:38Z. Every command Task 7 requires, run
against the real, now-VIC-AFS-loaded `data/facts.db`.

## Python

| command | result |
|---|---|
| `python -m pytest tests -q` | **328 passed** |
| `python scripts/ops/task9_sql_integrity_checks.py` | `hard_failures: 0` |
| `python scripts/ingest/ingestion_coverage_audit.py` | `fully_ingested: 48`, `adapter_missing: 168` - unchanged from Task 4's post-load state |
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

One operational note: the first `test:e2e` attempt this task used a
mismatched port (static export served on 3319, backend CORS configured
for 3319, but the Playwright config's hardcoded `BASE_URL` is
`127.0.0.1:3313`) - all 20 tests failed with `ERR_CONNECTION_REFUSED`
against the wrong port, not a real regression. Restarted both the
static server and backend on the correct port 3313 with matching CORS;
re-ran cleanly: 20/20 passed, no other issues.

## Semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against a fresh backend on the real
database: **`total_hard_failures: 0`, `total_accepted_source_rounding_warnings: 0`**
across all 6 required paths and all 7 PBS crosswalk cases - identical to
the MFS-aggregates milestone's final clean state. Every existing
dashboard path remains unchanged; the VIC AFS family is reachable only
through the GFS/jurisdiction explorer's own `vic_afs_*`-scoped API calls
and cannot reach any additive dashboard tree.

## Conclusion

Every command in Task 7's required list has been run against the real,
post-VIC-AFS-load database and passes. No existing behavior changed as a
result of this milestone's work.

## Next

Task 8: production verification - rebuild/restart the backend, deploy
the frontend (which now includes both the Cloudflare route fix and the
VIC AFS UI), verify the public API and UI for the new family, rerun the
production dashboard audit, and document the Cloudflare fix's final
status.
