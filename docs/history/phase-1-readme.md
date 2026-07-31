# AusGov Budget Tracker 🇦🇺📊

**Site (once deployed):** [https://vibefactory.app/ausgov-budget-tracker](https://vibefactory.app/ausgov-budget-tracker) — deployment artifacts are built and verified locally; see `ops/runbooks/project-rollout-order.md` (§D) for what's left to cut over.

A dashboard for visualizing Australian government spending across Federal,
State, and Local levels, with click-through source tracing back to the
original government dataset for every figure shown.

## Status: Phase 1

Australia's spending data is split across dozens of portals with wildly
different formats, and several of them actively block scripted downloads
(see [Known limitations](#known-limitations) below). Rather than fake broad
coverage, Phase 1 proves the full pipeline — fetch → parse → normalize →
serve → visualize → trace-to-source — end to end with **one real, verified,
live dataset per level of government**:

| Level | Source | Jurisdiction |
|---|---|---|
| Federal | Dept of Finance — General Government Sector Monthly Financial Statements, Note 3 (Expense by Function) | Commonwealth |
| State | SA Dept of Treasury and Finance — Government Finance Statistics, GPC by ETF | South Australia |
| Local | Victorian Auditor-General's Office — Results of Audits: Local Government financial data | 85 Victorian councils |

`scripts/sources.yaml` is a declarative registry — adding another
jurisdiction is: add an entry + a parser module, no changes to the API or
frontend.

## Project structure

```
data/raw/<level>/<source_id>/       # cached downloads + a .meta.json sidecar (source_url, retrieved_at, status)
data/processed/spending.db          # normalized SQLite table built from the raw sources
scripts/
  sources.yaml                      # declarative source registry
  fetch_sources.py                  # discovers + downloads current resource URLs via data.gov.au's CKAN API
  build_processed_db.py             # runs each source's parser, writes data/processed/spending.db
  parsers/                          # one module per source, each source's real workbook shape is different
src/backend/                        # FastAPI app serving the hierarchical spending tree + source-trace lookups
src/frontend/                       # Next.js + TypeScript + ECharts dashboard
```

## Running it

### 1. Data pipeline (conda env `ausgov-budget-tracker`, see `environment.yml`)

```bash
conda env create -f environment.yml   # first time only
conda activate ausgov-budget-tracker
python scripts/fetch_sources.py       # downloads the 3 sources into data/raw/
python scripts/build_processed_db.py  # writes data/processed/spending.db
```

`fetch_sources.py` resolves each resource's *current* URL live via CKAN
rather than hardcoding it (government portals re-upload resources under new
IDs periodically). If a source fails to fetch (dead link, bot-challenge WAF,
timeout) it's logged and skipped — the run doesn't fabricate data for it.

### 2. Backend API

```bash
cd src
uvicorn backend.main:app --reload --port 8000
```

Key endpoints: `GET /api/spending/levels`, `GET /api/spending/years?level=`,
`GET /api/spending/tree?level=&year=` (hierarchical rollup for the chart),
`GET /api/spending/item/{id}` (single row + source document/link) and
`GET /api/spending/item/{id}/context` (captured sheet/range, nearby source
cells, and the exact highlighted figure) and
`GET /api/spending/item/{id}/source-file` (the byte-for-byte cached public
government spreadsheet, streamed with its original spreadsheet media type).
The browser parses the source file with SheetJS, selects the relevant sheet,
and highlights the recorded cell; the reconstructed context remains visible
while loading and if the cached file is unavailable.

### 3. Frontend

```bash
cd src/frontend
npm install
npm run dev          # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE` if the backend isn't at `http://localhost:8000`.

> If `npm run dev` fails with a Turbopack "OS file watch limit reached"
> error (common in shared/containerized environments with a low
> `fs.inotify.max_user_instances`), use `npm run build && npm start`
> instead — no filesystem watcher required.

### Production (vibefactory.app)

Follows the same Cloudflare Worker + Tunnel pattern as `dance-machine` and
`karaoke-machine` — see `ops/runbooks/project-rollout-order.md` (§D) and
`ops/phase8-ausgov-budget-tracker-rollout-report.md` for the full writeup.
Short version:

```bash
# Self-hosted backend origin (Docker, behind the shared Cloudflare Tunnel)
docker compose -f docker-compose.vibefactory.yml up --build -d

# Backend Worker (proxies to the origin above)
cd src/backend-cloudflare && npm run deploy:vibefactory

# Frontend (static export, deployed as a Worker with an Assets binding —
# there is no running Node process in production, matching both siblings)
cd src/frontend && npm run deploy:vibefactory
```

The frontend is a static export (`next.config.ts` sets `output: 'export'`
and `basePath: '/ausgov-budget-tracker'`) — `NEXT_PUBLIC_API_BASE` is baked
in at build time by `npm run build:vibefactory`, not read at runtime.

## Data model

Every row in `spending.db` carries: `financial_year`, `level_of_government`,
`jurisdiction`, `category`, `subcategory`, `department`, `amount_aud`,
`source_document_name`, `source_url`, `retrieved_at`, plus parser-captured
source context stored as JSON (sheet, range, nearby raw cells, highlight,
and unit). Nulls render as "Uncategorized" rather than being dropped. The
Australian financial year (1 July – 30 June) is used throughout, not the
calendar year.

## Known limitations

- **ABS Government Finance Statistics has no working API.** The full ABS
  SDMX dataflow catalog (1200+ flows) has nothing GFS-related — it's a
  Data-Explorer manual-export-only dataset. This is the source the user
  brief pointed to for a unified, double-counting-free cross-level view; it
  isn't wired up here. To add it: export a CSV from the [ABS Data
  Explorer](https://www.abs.gov.au/about/data-services/data-explorer), drop
  it in `data/raw/`, and add a parser.
- **PBO's Historical Fiscal Data (pbo.gov.au) hangs on scripted requests**
  (Akamai bot protection — the TLS handshake completes but the server never
  responds). Not usable in an automated pipeline as-is.
- **Some state portals block scripted downloads outright.**
  `data.qld.gov.au`, for example, returns an AWS WAF bot challenge
  (`x-amzn-waf-action: challenge`, HTTP 202/empty body) on every resource
  URL tried. `fetch_sources.py` detects this and skips the source rather
  than failing the whole run — check a source's `.meta.json` for
  `"status": "fetch_failed"` and the `reason`.
- **Only 1 state (SA) and 1 territory's worth of local government (VIC) are
  wired up**, not all 8 states/territories or all ~500 councils. Extending
  coverage is mechanical (new `sources.yaml` entry + parser) but each
  portal's format and access quirks need handling one at a time.
- **Federal↔State double-counting (tied grants) isn't addressed** — since
  levels are shown as separate toggle-able views rather than summed
  together, it isn't currently triggered. Relevant if a combined
  cross-level total is ever added.

## Data Sources

* **Federal:** [data.gov.au](https://data.gov.au) (CKAN API), [budget.gov.au](https://budget.gov.au)
* **State:** State Treasury / open data portals (e.g. data.sa.gov.au, data.nsw.gov.au, data.vic.gov.au)
* **Local:** State auditors-general and Local Government Grants Commissions
* **Unified (not yet wired up):** [ABS Government Finance Statistics](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-australia/latest-release)
