# Full validation (Task 7)

Generated: 2026-08-06T17:00:24Z. Every command Task 7 requires, run
against the real, now-VIC-SOCE-Admin-loaded `data/facts.db`.

## Python

| command | result |
|---|---|
| `python -m pytest tests -q` | **399 passed** |
| `python scripts/ops/task9_sql_integrity_checks.py` | `hard_failures: 0` |
| `python scripts/ingest/ingestion_coverage_audit.py` | `fully_ingested: 49` - unchanged (same already-fully-ingested `source_id`) |
| `python scripts/ingest/ingestion_coverage_lineage.py` | 7 datasets - byte-identical to pre-load |
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
across all 6 required paths and all 7 PBS crosswalk cases - identical to
the pre-load clean state. Every existing dashboard path (Federal,
state, local, debt, GDP ratios, PBS crosswalk) remains unchanged; the
VIC SOCE/Admin family is reachable only through its own dedicated
`/v2/vic-bpo-soce-admin/*` API (surfaced in the GFS explorer's existing
VIC BPO toggle) and cannot reach any additive dashboard tree.

## Test-file fix carried in this milestone

`tests/ingest/test_vic_bpo.py`'s `test_dedicated_compatibility_groups_
distinct_from_annual_and_vic_afs` used a `LIKE 'vic_bpo_%'` wildcard
that over-matched once the sibling `vic_bpo_soce_admin` family (which
deliberately shares the `vic_bpo_` prefix) was loaded into the same
database. Fixed to check the family's own known 11 measure_types
(sourced from `vic_bpo.yaml` itself) - a test-file correction, not a
change to `vic_bpo.py`/`reload_vic_bpo.py`/`vic_bpo.yaml`.

## Conclusion

Every command in Task 7's required list has been run against the real,
post-VIC-SOCE-Admin-load database and passes. No existing behavior
changed as a result of this milestone's work.

## Next

Task 8: production verification - rebuild/restart the backend (code
changed - new router), deploy the frontend (now includes the merged
VIC BPO dropdown), verify the public API and UI for the new family,
rerun the production dashboard audit, confirm existing dashboard paths
unchanged, and record the Cloudflare issue's status (deferred - not
touched this milestone, per Task 2's decision).
