# Research Agent Handoff — Ingestion Architecture Redesign

**Date:** 2026-07-22
**Project:** AusGov Budget Tracker
**Repo:** `/home/vibe-server/vibe-factory/ausgov-budget-tracker`
**Audience:** Research AI agent — design a plan to ingest acquired data into a queryable, website-usable model **without** silently mixing incompatible measures.

**Companion coverage audit:** `ops/data-coverage-audit-20260722.md`
**Prior acquisition docs:** `ops/procurement-acquisition-report-20260722.md`, `ops/data-inventory-20260722.md`, `ops/research-findings-20260722.md`
**Draft schema (unused):** `data/ausgov_budget_hierarchical_schema.sql`
**Live site:** https://vibefactory.app/ausgov-budget-tracker/

---

## Your mission

Produce a **research + architecture plan** (not code) for a next-generation ingestion pipeline that can:

1. Take the **~8.1 GB / ~76 sources** already on disk under `data/raw/<level>/<source_id>/`
2. Normalize them into a **measure-aware, provenance-preserving** store
3. Feed the **existing or evolved** website (hierarchical drill-down + click-through to source files)
4. Scale to new sources without one-off parsers for every PDF

Deliverable: a structured plan with recommended architecture options, phased roadmap, risks, and open research questions — suitable for a coding agent to implement afterward.

---

## 1. Current state (two disconnected pipelines)

```
PIPELINE A — Website (Phase 1)          PIPELINE B — Procurement (acquisition)
scripts/sources.yaml  (3 sources)       config/procurement_sources.yaml (~82)
      │                                       │
fetch_sources.py (CKAN)                 procure_sources.py + adapters
      │                                       │
data/raw/<level>/<id>/*.xlsx            data/raw/<level>/<id>/snapshots/<run>/
      │                                       │ + latest.json
parsers/* → SpendingRow                 ✗ NO parsers
      │
build_processed_db.py
      │
data/processed/spending.db  ← ONLY THIS FEEDS THE WEBSITE
      │
FastAPI → Next.js dashboard
```

| | Pipeline A (website) | Pipeline B (procurement) |
|---|---|---|
| Registry | `scripts/sources.yaml` | `config/procurement_sources.yaml` |
| Sources on disk used | 3 | ~73 acquired |
| Bytes | ~1 MB xlsx | ~8.1 GB |
| Layout | flat file + `.meta.json` | versioned snapshots + `latest.json` |
| Normalize | 3 hand parsers | none |
| DB | SQLite `spending` table | none |
| Website | yes | no |

Explicit comment in `scripts/procure_sources.py`: procurement is **entirely independent** and never reads/writes the legacy DB build.

---

## 2. What the website can represent today

### Data model (`SpendingRow` / `spending` table)

Fixed columns:

- `financial_year` (AU FY string e.g. `2024-25`)
- `level_of_government` (`federal`\|`state`\|`local`) — **no territory**
- `jurisdiction` (free text)
- `category` / `subcategory` / `department` — **max depth 3**
- `amount_aud` (float) — **single undifferentiated money field**
- provenance: `source_document_name`, `source_url`, `retrieved_at`
- `source_context_json` — sheet/range/cells/highlight for spreadsheet tracing

### Coverage on site (definitive)

| Level | Jurisdiction | Years | Rows |
|---|---|---|---:|
| Federal | Commonwealth | 2005-06 … 2025-26 | 381 |
| State | SA only | 2012-13 … 2015-16 | 1,893 |
| Local | VIC councils | 2014-15 … 2018-19 | 1,700 |
| Territory | — | — | 0 |

### Product behaviors that must be preserved or evolved

- Level tabs + FY selector + pie/bar chart
- Drill-down through hierarchy
- Hover/click leaf → source evidence viewer (SheetJS over cached spreadsheet)
- Traceability to original government file

---

## 3. What we have acquired (input inventory for your plan)

- **8.1 GB** across **76** source trees
- **8.099 GB / 73 sources** not wired to website
- See full per-source tables in `ops/data-coverage-audit-20260722.md`

### Dominant format mix (latest assets)

| Format | Role | Ingestion implication |
|---|---|---|
| PDF (~1.4k assets) | Budget papers, annual reports, PBS | Need layout-aware extraction or accept as document-only with curated tables |
| CSV (~490) | Contracts, grants, disclosures, some GFS | Highest automation potential |
| XLSX/XLS (~445) | GFS, local returns, GrantConnect | Similar to Phase 1 parsers; table discovery needed |
| DOCX (~175) | Narrative reports | Low priority for amounts |
| JSONL.GZ (22) | NSW OCDS | Event/release model → contract facts |
| ZIP (22) | Bundles (ABS, TAS CDC) | Unpack then recurse |

### Dominant families by bytes (approx)

- `procurement_contracts`: 2.075 GB across 6 sources
- `program_forecast`: 1.478 GB across 1 sources
- `program_actuals`: 1.471 GB across 1 sources
- `participant_statistics`: 0.675 GB across 1 sources
- `payment_aggregates`: 0.675 GB across 1 sources
- `state_actuals`: 0.547 GB across 6 sources
- `state_budget`: 0.348 GB across 6 sources
- `grant_and_service_payments`: 0.21 GB across 1 sources
- `territory_actuals`: 0.169 GB across 2 sources
- `entity_annual_reports`: 0.089 GB across 2 sources
- `local_financial_returns`: 0.075 GB across 3 sources
- `whole_of_government_actuals`: 0.062 GB across 1 sources

### Measure-separation rule (non-negotiable)

From registry header: **Never sum** budget estimates, appropriations, accrual expenses, cash payments, contract values, grant awards, counts, or forecasts unless an explicit reconciliation defines the bridge.

Phase 1 violates the *spirit* of multi-measure analytics by stuffing everything into `amount_aud` — acceptable only because each Phase 1 source is a single measure family. A broader ingest **must** tag measure type / accounting basis.

---

## 4. Draft future schema (already in repo, unused)

`data/ausgov_budget_hierarchical_schema.sql` proposes:

- `source_documents` / `source_retrievals` (hash, path, HTTP meta)
- `entities` (agencies, councils)
- `nodes` + edges (arbitrary-depth hierarchies: functional, organisational, geographic, supplier)
- measure-typed facts (not a single `amount_aud`)
- provenance lineage to document/sheet/cell

Evaluate whether to adopt, simplify, or replace this draft. Compare to keeping SQLite vs DuckDB/Parquet lake + serving layer.

---

## 5. Pain points in the current ingestion method

1. **Dual registries / dual layouts** — Phase 1 flat vs procurement snapshots; builders don't share codepaths.
2. **Parser-per-source ceiling** — adding NSW/QLD/WA budgets as PDFs would require dozens of bespoke parsers.
3. **Depth-3 hierarchy** — insufficient for PBS outcomes/programs, OCDS contracts, council line items.
4. **No territory level** in website enum.
5. **No measure typing** — cannot safely show GFS expenses beside AusTender contract values.
6. **PDF-heavy corpus** — largest byte share is the hardest to automate.
7. **Acquisition ≠ readiness** — `latest.json` proves files exist; says nothing about parseability or grain.
8. **Quarantine / duplicates** — `data/quarantine/` (~0.5 GB) and staging `_downloads/` hold superseded copies; ingestion must prefer `latest.json` SHA paths.
9. **Unit ambiguity** — Phase 1 amounts are raw workbook numbers (often $'000 or $m); website displays as dollars. Research must specify unit normalization.

---

## 6. Research questions to answer

### Architecture

1. What is the best **serving model** for vibefactory: evolve SQLite `spending.db`, migrate to the hierarchical schema, or introduce a lakehouse (Parquet/DuckDB) with a thin API?
2. Should the website become **multi-mode** (GFS explorer vs contracts explorer vs budget papers) rather than one pie chart?
3. How should **measure catalogs** and **reconciliations** be declared in YAML so the UI can refuse illegal sums?

### Parsing strategy by format

4. For **CSV/XLSX** families (QLD disclosures, GrantConnect, QGIP, ABS GFS tables, NSW notices): propose a **schema-on-read + mapping YAML** approach vs hand parsers.
5. For **OCDS JSONL**: propose fact extraction grain (award, contract, planning) and hierarchy mapping.
6. For **budget PDFs**: survey approaches (manual curated tables, camelot/tabula, LLM-assisted with human verify, publisher open-data sidecars). Recommend a policy.
7. For **NDIS / DSS** statistical releases: are they in-scope for "spending tracker" or a separate demographics module?

### Prioritization

8. Rank the top **10 acquired sources** that unlock the most website value per engineering hour (prefer structured files, high traceability tier, fills jurisdiction gaps).
9. Which sources should remain **document library only** (download + search) without numeric ingest?

### Operations

10. How to unify registries (`sources.yaml` vs `procurement_sources.yaml`) without losing Phase 1 simplicity.
11. Incremental ingest: how to avoid full `DROP TABLE` rebuilds when one source updates.
12. Validation gates: checksum match, row-count sanity, unit checks, FY coverage tests before promoting to production DB.

---

## 7. Suggested plan outline (you may revise)

Propose phases such as:

1. **Inventory & classify** each on-disk source: parseable / document-only / blocked / duplicate
2. **Measure & node ontology** — finalize types, hierarchies, jurisdiction codes
3. **MVP structured ingest** — CSV/XLSX/OCDS only into new store; keep Phase 1 charts working
4. **API + UI modes** — GFS view, contracts view, grants view with measure guards
5. **PDF strategy** — pilot 1–2 budget paper tables with quality bar
6. **Unify acquisition → ingest** — single registry, snapshot → validated facts pipeline
7. **Production cutover** — dual-run, reconcile totals, deprecate flat `amount_aud`-only where unsafe

---

## 8. Key file paths

| Path | Role |
|---|---|
| `config/procurement_sources.yaml` | Acquisition registry (families, measures, tiers) |
| `scripts/sources.yaml` | Phase 1 website registry |
| `scripts/fetch_sources.py` | Phase 1 fetch |
| `scripts/build_processed_db.py` | Phase 1 ingest → SQLite |
| `scripts/parsers/` | Phase 1 parsers |
| `scripts/procure_sources.py` | Acquisition orchestrator |
| `scripts/procure/` | Adapters, storage, validation |
| `data/raw/**` | All acquired + Phase 1 raw |
| `data/processed/spending.db` | Live website DB |
| `data/ausgov_budget_hierarchical_schema.sql` | Proposed future schema |
| `src/backend/` | FastAPI |
| `src/frontend/` | Next.js dashboard |
| `ops/data-coverage-audit-20260722.md` | Per-level/source holdings |

---

## 9. Success criteria for your report

- Clear recommendation: **target architecture** (with alternatives considered)
- Phased roadmap with dependencies
- Prioritized source ingest list (top 10) with rationale
- Explicit handling of measure separation and unit normalization
- PDF policy (what to parse vs shelve)
- Migration path that does not break the live Phase 1 site
- Open questions / experiments still needed

Do **not** implement code in this research pass.

