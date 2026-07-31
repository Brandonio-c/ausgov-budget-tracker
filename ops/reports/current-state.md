# Current state — AusGov Budget Tracker

**Generated:** 2026-07-24T22:05:33Z  
**Commit (at generation):** see `git rev-parse HEAD`  
**Canonical facts (local):** ~331k rows in `data/facts.db` (not committed)

## Modes and semantics

- Compatibility specs: `config/compatibility/view_families.yaml`
- Migration `006_semantic_hardening`: `amount_value`, `view_family`, `price_basis`, PBS inference columns, ratio rows as `unit=percent`
- Dashboard modes include economy splits; legacy `gdp` → `gdp_current`
- Combined root chart: non-consolidated comparison (default bars; no misleading `$` total)

## Ingestion coverage (lineage)

See `ops/reports/ingestion-coverage-lineage.md` (from `make audit`).

## Revenue reconciliation

See `ops/reports/revenue-reconciliation-202425.json`.

## Tests

- `tests/unit` — no DB
- `tests/integration` — builds `data/test/facts_fixture.db`
- `tests/api` / `tests/ingest` — may use local production DB (`full_data` migration ongoing)
- CI: `.github/workflows/ci.yml`

## Known limitations

- Full PBS reprocess across all PDFs still required for production year-correction counts
- Some revenue jurisdiction pairs warn on detail vs GFS control gap
- Frontend lint has pre-existing React Compiler / a11y findings
- Debt instrument depth (AOFM under Debt securities) still thin

## Superseded docs

Phase 1 README archived at `docs/history/phase-1-readme.md`. Prefer this file + hardening-final reports over older `ops/reports/m*.md` milestones for architecture.
