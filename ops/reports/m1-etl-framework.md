# M1 — ETL framework + Gates 1–6

## DoD

- Mapping YAML spec; `duckdb_etl` / `validate` / `load_facts` / `quarantine_report` / `run.py`
- Synthetic fixture: published facts + one Gate-6 quarantine (missing `landing_url`)
- Idempotent second run

## Verification

| Check | Result |
|---|---|
| Synthetic first run | published=2, quarantined=1, gate6=1 |
| Synthetic second run | same counts; facts table still 2 rows |
| Quarantine reason | `Gate 6 attribution: incomplete citation: ['landing_url']` |
| `tests/ingest/` | 5 passed |
| Touched `spending.db` | **no** |

## Artefacts

- `config/mappings/README.md`, `config/mappings/synthetic_demo.yaml`
- `tests/fixtures/ingest/synthetic_demo.csv`
- `scripts/ingest/{duckdb_etl,validate,load_facts,quarantine_report,reconcile,run}.py`
