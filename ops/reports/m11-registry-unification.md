# M11 — Registry unification

## DoD

- Merge Phase 1 into `procurement_sources.yaml`; single orchestrator; retire `scripts/sources.yaml`
- Re-run M9 regression

## Verification

| Check | Result |
|---|---|
| Phase 1 ids in procurement registry | federal_expense_by_function, sa_gfs_by_function, vic_local_govt_financial |
| `scripts/sources.yaml` | retired → `sources.yaml.retired` |
| Orchestrator | `scripts/fetch_orchestrator.py` (`--mode phase1\|procure\|all`) |
| `fetch_sources` / `build_processed_db` | load via `unified_registry.phase1_sources()` |
| M9 default-view regression | ok |

## Artefacts

- `scripts/unified_registry.py`
- `scripts/fetch_orchestrator.py`
- `scripts/SOURCES_YAML_RETIRED.md`
