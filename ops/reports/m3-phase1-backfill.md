# M3 — Phase 1 backfill

## DoD

- Mapping YAMLs from existing `source_context_json` locators
- Reconcile vs `spending.db` per FY; record `reconciliations` for gaps (never block)
- 100% attribution on published Phase 1 facts

## Verification

| Check | Result |
|---|---|
| federal_expense_by_function | 381 published / 0 quarantine |
| sa_gfs_by_function | 1893 published / 0 quarantine |
| vic_local_govt_financial | 1700 published / 0 quarantine |
| Total Phase 1 facts | 3974 |
| Attribution (Gate 6) | **100%** on published |
| Reconciliations recorded | 30 (per FY × source) |
| Wrote to `spending.db` | **no** (read-only) |

## Artefacts

- `scripts/ingest/phase1_backfill.py`
- `config/mappings/{federal_expense_by_function,sa_gfs_by_function,vic_local_govt_financial}.yaml`
- `data/staging/phase1/*.csv`
