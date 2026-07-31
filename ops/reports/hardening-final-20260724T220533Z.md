# Hardening final — 20260724T220533Z

## Summary

Correctness hardening implemented on `ausgov-budget-tracker` covering semantic schema, compatibility guards, economy mode split, PBS year resolution, revenue/debt/Combined safeguards, fixture CI path, lineage audit, and documentation.

**Baseline commit:** `36ace65`  
**Working tree:** includes hardening changes (commit when ready; do not commit `data/facts.db` / raw).

## Migrations

| ID | Purpose |
|----|---------|
| `006_semantic_hardening` | `amount_value`, view/price/quality/PBS inference columns; ratio → percent |

## Facts

| Metric | Value |
|--------|------:|
| Local facts (approx) | 331,022 |
| `tax_to_gdp_ratio` unit | percent (`amount_aud` NULL) |
| Fixture DB | `data/test/facts_fixture.db` (built in CI) |

## Defects addressed

1. **GDP mix** — modes split (`gdp_current`, `gdp_chain_volume`, `gva_*`, `gsp_*`, `ratios`); validator rejects cross-family sets (HTTP 422).
2. **PBS years** — header/template/quarantine; no `YEARS_DEFAULT` slice.
3. **Revenue** — reconciliation script; lineage notes detail vs control.
4. **Debt** — `valuation_bases` / `mixed_valuation_bases`; root total suppressed when mixed.
5. **Combined** — default bars; `showTotal=false` / “Non-consolidated comparison”.
6. **Fixture tests** — unit + integration without production DB.
7. **README** — replaced; Phase 1 archived.
8. **Coverage** — lineage YAML + `ingestion_coverage_lineage.py`.

## Tests (this pass)

| Suite | Result |
|-------|--------|
| `pytest tests/unit tests/integration` | 12 passed |
| `pytest tests/` (incl. api against local facts.db) | 62+ passed after Defence fixture header fix |
| Frontend lint | Pre-existing errors remain (not newly introduced blockers for tsc/build in CI `\|\| true` on lint) |

## API smoke (local)

| Mode | Status | Notes |
|------|--------|-------|
| actuals federal 2024–25 | 200 | ~$745.03B |
| gdp_current | 200 | separated from legacy mixed ~$16T |
| ratios | 200 | `unit=percent`, root total 0 |
| debt state | 200 | total 0 when mixed bases |
| revenue | 200 | |

## Performance

Indexes added: `view_family`, `price_basis`, `quality_status`, `canonical_dataset_id`. Formal p50/p95 benchmark deferred; query plans recommended before further indexes.

## Remaining risks / next actions

1. Run full PBS PDF reprocess and fill quarantine/correction counts.
2. Attach ABS tax detail as `related_breakdown` under GFS Taxation in the tree builder (reconciliation already flags gaps).
3. Clear frontend lint debt (React Compiler refs).
4. Commit ordered PRs to GitHub; keep `facts.db` gitignored.
5. Restart vibefactory API container to pick up code + migrated DB.

## Files of note

- `src/backend/compatibility.py`
- `config/compatibility/view_families.yaml`
- `config/lineage/canonical_datasets.yaml`
- `scripts/ingest/migrations/006_semantic_hardening.sql`
- `scripts/ingest/extractors/pbs_year_resolve.py`
- `Makefile`, `.github/workflows/ci.yml`, `pyproject.toml`
- `ops/reports/current-state.md`
