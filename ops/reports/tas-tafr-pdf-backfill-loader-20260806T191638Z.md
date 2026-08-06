# TAS TAFR PDF backfill: load and validate (Task 6)

Generated: 2026-08-06T19:16:38Z.

## Backup

`data/facts.db` backed up via `scripts/ops/backup_facts_db.py` to
`/home/vibe-server/backups/ausgov-budget-tracker/facts-20260806T191545Z.db`
before any write - counts recorded in the backup's own report
(288,835 facts, 222,549 nodes, 130 source_documents, 36,417
quarantined).

## First `--apply`

```
python3 scripts/ingest/reload_tas_tafr_pdf_backfill.py --apply
```

54 rows extracted (42 unique + 12 same-value cross-table duplicates), 5
quarantined by the extractor (2 excluded "Underlying Net Operating
Surplus/(Deficit)" rows, 3 narrative false-positive matches correctly
caught by the token-count check). 42 facts published (7 measures x 3
editions x 2 estimate_status), 0 nodes inserted (the `tas_ggs_*`
measure nodes already exist from the xlsx loader - correctly reused,
not duplicated), 12 in-run idempotent skips (the expected cross-table
duplication), 0 revision conflicts.

`facts`: 288,835 -> 288,877 (+42). `nodes`: unchanged at 222,549.
`fact_nodes`: 288,835 -> 288,877 (+42). `measure_definitions`:
unchanged at 81 (no new migration - this adapter reuses all 7
already-shipped `tas_ggs_*` measure_types).

Every new fact's `amount_aud` verified directly against Task 3's
manually-inspected source values, including the genuine sign
difference in 2012-13's `tas_ggs_net_debt` (budget = +134,000,000,
actual = -220,000,000).

## Second `--apply` (idempotency proof)

```
python3 scripts/ingest/reload_tas_tafr_pdf_backfill.py --apply
```

`facts_to_insert: 0`, `nodes_inserted: 0`,
`facts_already_present_idempotent_skip: 54` (42 against the DB + 12
in-run cross-table dupes), `revision_conflicts_quarantined: 0` -
byte-identical database state, zero duplicate fact_keys.

## Integrity / coverage / lineage / quarantine

| check | result |
|---|---|
| `scripts/ops/task9_sql_integrity_checks.py` | `hard_failures: 0`, `orphan_facts: 0`, `orphan_nodes: 0` |
| `scripts/ingest/ingestion_coverage_audit.py` | `fully_ingested: 50` - unchanged (same already-fully-ingested `source_id` as the xlsx loader; this backfill adds more measures/years to it, not a new dataset) |
| `scripts/ingest/ingestion_coverage_lineage.py` | 7 datasets - unchanged |
| `scripts/ingest/quarantine_report.py` | `quarantined=36417` - unchanged (this adapter's own quarantine file is separate, consistent with every other family's loader-specific quarantine file) |

## Dashboard contamination check

`scripts/ops/dashboard_api_audit.py` against the real, bind-mounted
production backend (`http://127.0.0.1:8010`) immediately after the
load: **`total_hard_failures: 0`, `total_accepted_source_rounding_
warnings: 0`** across all 6 required paths and 7 PBS crosswalk cases -
identical to the pre-load clean state. All 7 `tas_ggs_*`
compatibility_groups touched by this adapter were already isolated
from any dashboard mode_to_family mapping (confirmed unchanged from
the xlsx loader's own milestone).

## Next

Task 7: expose the extended years (2010-11 to 2012-13) - the existing
"TAS GGS" toggle on `/explorers/gfs` already reads from the same
`/v2/tas-ggs/series` endpoint by `measure_type`, which returns ALL
years for that measure ordered by `financial_year` - so no frontend
code change should be needed; verify this in a real browser and
document why.
