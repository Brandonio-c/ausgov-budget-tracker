# VIC SOCE/Admin: load and validate (Task 4)

Generated: 2026-08-05T21:41:41Z.

## Backup

`data/facts.db` backed up to
`data/backups/facts.db.pre-vic-soce-admin-20260805T213232Z` before any
write (this directory is gitignored - never committed, per the ground
rules).

## First `--apply`

```
python3 scripts/ingest/reload_vic_bpo_soce_admin.py --apply
```

18/18 facts published (9 measures x 2 estimate_status - actual/budget),
9 nodes inserted, 52 rows quarantined by the loader (Admin's own
sub-component breakdown rows, out of scope by design; SOCE's duplicate-
by-design "Balance at 30 June 2025"/"Comprehensive result" rows, already
captured by the existing `vic_bpo_net_assets`/`vic_bpo_net_result`
facts).

`facts`: 288657 -> 288675 (+18). `nodes`: 222530 -> 222539 (+9).
`fact_nodes`: 288657 -> 288675 (+18). `measure_definitions`: 62 -> 71
(+9, migration 010 applied automatically by `reload_vic_bpo_soce_admin.
py`'s own `migrate()` call).

Every new fact's `amount_aud` verified directly against the manually-
inspected source values from Task 1/3 (e.g. `vic_bpo_admin_income`
actual = 82,428,000,000 = $82,428m x 1,000,000; `vic_bpo_net_assets_
opening` actual/budget = 76,000,000 = $76m x 1,000,000).

## Second `--apply` (idempotency proof)

```
python3 scripts/ingest/reload_vic_bpo_soce_admin.py --apply
```

`facts_to_insert: 0`, `nodes_inserted: 0`,
`facts_already_present_idempotent_skip: 18`,
`revision_conflicts_quarantined: 0` - byte-identical database state,
zero duplicate fact_keys.

## Integrity / coverage / lineage / quarantine

| check | result |
|---|---|
| `scripts/ops/task9_sql_integrity_checks.py` | `hard_failures: 0`, `orphan_facts: 0`, `orphan_nodes: 0`, `orphan_edges: 0` |
| `scripts/ingest/ingestion_coverage_audit.py` | `fully_ingested: 49` - unchanged (same `source_id` as the already-fully-ingested VIC BPO family; this is additional coverage of an already-fully-ingested source, not a new dataset) |
| `scripts/ingest/ingestion_coverage_lineage.py` | 7 datasets - byte-identical output to the pre-load report |
| `scripts/ingest/quarantine_report.py` | `quarantined=36417` - unchanged (this report scans a different, pre-existing set of quarantine sources; the new adapter's own quarantine file - `data/staging/quarantine/vic_bpo_soce_admin_load_quarantine.jsonl` - is a separate file not included in that report's scan list, consistent with how the sibling `vic_bpo_load_quarantine.jsonl` file is also not included there) |

## Dashboard contamination check

`scripts/ops/dashboard_api_audit.py` against the real, bind-mounted
production backend (`http://127.0.0.1:8010`) immediately after the
load: **`total_hard_failures: 0`, `total_accepted_source_rounding_
warnings: 0`** across all 6 required paths and 7 PBS crosswalk cases -
identical to the pre-load clean state. None of the 9 new measure_types
is registered under any `mode_to_family` mapping
(`config/compatibility/view_families.yaml`), so this family cannot
reach any existing dashboard tree even in principle - confirmed by the
audit's own traversal, not just by inspection.

## Next

Task 5: expose the new measures (see the same-commit backend router
and frontend changes) - wiring into the existing GFS explorer's VIC BPO
toggle rather than a new page, since these are simply more measures of
the same overall family from the user's point of view.
