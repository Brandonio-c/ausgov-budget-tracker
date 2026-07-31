# AusGov Budget Tracker

Dashboard for Australian government finances — Actuals, Budget, Debt, Revenue, and Economy views — with citation back to source documents for every publishable leaf.

**Live:** [https://vibefactory.app/ausgov-budget-tracker](https://vibefactory.app/ausgov-budget-tracker)

## Architecture (current)

```text
config/procurement_sources.yaml + acquisition scripts
        ↓
data/raw/** snapshots (gitignored)
        ↓
mappings + extractors (scripts/ingest/)
        ↓
data/facts.db  (canonical facts; gitignored)
        ↓
FastAPI v2  (src/backend)  ← compatibility / view_family guards
        ↓
Next.js frontend (src/frontend)  ← Actuals | Budget | Debt | Revenue | Economy
```

| Layer | Role |
|-------|------|
| Procurement registry | Declares sources, URLs, acquisition strategy |
| Raw snapshots | Content-addressed downloads under `data/raw/` |
| Mappings / extractors | Stage CSVs → `load_facts` → SQLite |
| `facts.db` | Typed measures, provenance, breakdown edges |
| Semantic compatibility | [`config/compatibility/view_families.yaml`](config/compatibility/view_families.yaml) — incompatible families never share one additive tree |
| Lineage | [`config/lineage/canonical_datasets.yaml`](config/lineage/canonical_datasets.yaml) — coverage without source-name heuristics |
| API | `/v2/dashboard/*`, citations, search |
| Frontend | Rings / bars / pie; Combined is **non-consolidated comparison** |

Historical Phase 1 README: [`docs/history/phase-1-readme.md`](docs/history/phase-1-readme.md).

## Dashboard modes

| Mode | View family | Notes |
|------|-------------|-------|
| `actuals` | actual_expense | ABS GFS preferred |
| `budget` | budget_expense | Estimates / forward estimates |
| `debt` | debt_stock | Mixed valuation bases disable unqualified totals |
| `revenue` | gfs_revenue | Table 1 control; detailed tax is reconciled detail |
| `gdp_current` / `gdp_chain_volume` / `gdp_expenditure` / `gva_*` / `gsp_*` / `ratios` | separate families | Never mixed in one pie; ratios use `unit=percent` (no `$`) |
| `gdp` | alias → `gdp_current` | Legacy |

## Developer commands

```bash
make setup
make migrate
make build-fixture-db
make test          # unit + integration (fixture DB; no production raw)
make test-full     # @pytest.mark.full_data only
make audit         # lineage coverage + revenue reconciliation
make frontend-build
```

Ordinary CI does **not** require `data/facts.db` or `data/raw/`.

## Semantic rules (non-negotiable)

- Do not sum percent with AUD.
- Do not mix current-price and chain-volume GDP.
- Do not invent PBS financial years — headers, templates, or quarantine.
- Do not co-add GFS taxation controls with detailed ABS tax replacements.
- Do not show an unqualified Combined national total.
- Do not commit production `facts.db` or raw downloads.

## Reports

- [`ops/reports/current-state.md`](ops/reports/current-state.md) — canonical snapshot
- [`ops/reports/hardening-baseline-*.md`](ops/reports/) / `hardening-final-*.md` — hardening program

## Deployment (vibefactory)

```bash
docker compose -f docker-compose.vibefactory.yml up --build -d
cd src/backend-cloudflare && npm run deploy:vibefactory
cd ../frontend && npm run deploy:vibefactory
```

`facts.db` is bind-mounted read-only into the API container.
