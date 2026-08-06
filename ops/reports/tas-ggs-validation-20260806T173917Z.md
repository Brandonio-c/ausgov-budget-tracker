# Full validation (Task 9)

Generated: 2026-08-06T17:39:17Z. Every command Task 9 requires, run
against the real, now-TAS-GGS-loaded `data/facts.db`.

## Python

| command | result |
|---|---|
| `python -m pytest tests -q` | **444 passed** |
| `python scripts/ops/task9_sql_integrity_checks.py` | `hard_failures: 0` |
| `python scripts/ingest/ingestion_coverage_audit.py` | `fully_ingested: 50` - unchanged from Task 6's post-load state |
| `python scripts/ingest/ingestion_coverage_lineage.py` | 7 datasets, `facts_source_keys_observed: 127` - unchanged from Task 7's committed state |
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
| `npm run test:e2e` (full local suite, real backend against real `data/facts.db`, all 4 spec files) | **20/20 passed** |

## Semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against a fresh backend on the real
database: **`total_hard_failures: 0`, `total_accepted_source_rounding_warnings: 0`**
across all 6 required paths and all 7 PBS crosswalk cases.

## Existing dashboard views confirmed unchanged

| view | result |
|---|---|
| Federal actuals FY2024-25 | 745,030,000,000 |
| VIC state actuals FY2024-25 | 553,464,488,764.25 |
| VIC AFS measures | 11 (unaffected) |
| VIC BPO measures | 11 (unaffected) |
| VIC BPO SOCE/Admin measures | 9 (unaffected) |
| MFS measures | 15 (unaffected) |

The TAS GGS family is reachable only through its own dedicated
`/v2/tas-ggs/*` API (surfaced in the GFS explorer's own "TAS GGS"
toggle) and cannot reach any additive dashboard tree - confirmed by the
audit's own traversal, not just by inspection.

## Conclusion

Every command in Task 9's required list has been run against the real,
post-TAS-GGS-load database and passes. No existing behavior changed as
a result of this milestone's work.

## Next

Task 10: production verification - rebuild/restart the backend (new
router), deploy the frontend (now includes the TAS GGS toggle), verify
the public API and UI for the new family, rerun the production
dashboard audit, confirm existing dashboard paths unchanged, and record
the Cloudflare issue's status (unchanged, deferred - not touched this
milestone, per Task 2's decision).
