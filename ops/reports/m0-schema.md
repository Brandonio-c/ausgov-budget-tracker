# M0 — Schema foundation

## DoD (from engineering plan)

- Apply `data/ausgov_budget_hierarchical_schema.sql` idempotently via `schema_migrate.py` + `schema_migrations` log
- Additive deltas: `payment_timing_disclosure` (+ related measures), `native_unit` on `source_documents`, `facts_pending_attribution`
- Confirm `government_level` allows `territory`
- Idempotent migrate twice (second = no-op)
- Constraint / migration tests green

## Verification

| Check | Result |
|---|---|
| First migrate | `000_hierarchical_schema_draft=applied`, `001_m0_deltas=applied` |
| Second migrate | both `noop` |
| `facts_pending_attribution` | present |
| `payment_timing_disclosure` / `monthly_actuals` / `gfs_expense` | present in `measure_definitions` |
| `source_documents.native_unit` | present |
| `tests/ingest/test_schema_migrate.py` | 4 passed |
| Touched `spending.db` | **no** |

## Artefacts

- `scripts/ingest/schema_migrate.py`
- `data/facts.db`
- `ops/research-ingestion-plan-20260722.md`
- `ops/engineering-plan-20260722.md`
- `tests/ingest/test_schema_migrate.py`

## Notes

`native_unit` is applied via a conditional `ALTER TABLE` after the checksum-stable migration body so re-runs remain idempotent without checksum drift.
