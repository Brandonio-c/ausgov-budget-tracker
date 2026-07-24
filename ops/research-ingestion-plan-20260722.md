# AusGov Budget Tracker — Research Ingestion Plan

**Date:** 2026-07-22  
**Status:** Architecture decision (locked for M0–M12)  
**Companions:** `ops/research-ingestion-handoff-20260722.md`, `ops/engineering-plan-20260722.md`, `ops/data-coverage-audit-20260722.md`  
**Draft schema:** `data/ausgov_budget_hierarchical_schema.sql`

---

## 1. Decision summary

Rebuild ingestion as an **additive** path alongside the live Phase 1 site:

| Concern | Decision |
|---|---|
| Store | New `data/facts.db` only until M12; never write live `data/processed/spending.db` |
| ETL | DuckDB + per-source (or shared-template) YAML under `config/mappings/` |
| Validation | Six automated gates; Gate 6 attribution is mandatory for publish |
| Incomplete citation | Quarantine in `facts_pending_attribution`, never public `facts` / UI |
| Aggregation | Never sum across `compatibility_group` boundaries (API 400) |
| Product | Citation API + CitationPanel before volume; Contracts + GFS explorers |
| Cutover | Autonomous when M12 criteria script passes; keep `/legacy` |

---

## 2. Current dual-pipeline problem

```
Pipeline A (website)                    Pipeline B (procurement)
scripts/sources.yaml (3)                config/procurement_sources.yaml (~82)
→ parsers → spending.db → site          → snapshots + latest.json → ✗ no ingest
```

~8.1 GB / ~73 acquired sources are unused by the website. Phase 1 has no `territory` level and a single undifferentiated `amount_aud` with no measure typing.

---

## 3. Target architecture

```
Acquisition (untouched until M11)
  procurement_sources.yaml → data/raw/.../snapshots + latest.json

New path (M0–M11)
  config/mappings/*.yaml
       ↓
  scripts/ingest/run.py
       → duckdb_etl → validate (Gates 1–6) → load_facts | quarantine
       ↓
  data/facts.db
       ↓
  API /v2 (citation-bearing) → CitationPanel + explorers

Phase 1 live path (untouched until M12)
  spending.db → /api/spending → default pie / drill-down
```

**Hard rules while building:**

1. Never write `data/processed/spending.db` or modify Phase 1 scripts / default frontend route until M12.
2. Never publish a fact without complete Citation (`landing_url`, `original_resource_url`, cached copy URL, non-empty locator, retrieval sha256 / `retrieved_at`).
3. Never sum across `compatibility_group` boundaries (API 400).
4. Per-source isolation; idempotent `fact_key` upserts.

---

## 4. Measure separation

Every fact declares `measure_type` → `measure_definitions`, plus `accounting_basis` and `estimate_status`.

`compatibility_group` is the aggregation key. Legal tree/aggregate queries require exactly one `(compatibility_group, accounting_basis, estimate_status)` triple. Cross-group sums are rejected unless the request is an explicit reconciliations view.

Seeded groups: `budget_expense`, `actual_expense`, `cash_outflow`, `authority`, `commitment`, `count`.

New measures added as milestones need them (e.g. `monthly_actuals`, `contract_value`, `payment_timing_disclosure`).

---

## 5. Citation contract

Every publicly exposed number resolves to a Citation with three links:

1. `landing_url` — publisher landing page  
2. `original_resource_url` — exact file URL  
3. `cached_copy_url` — our held copy  

Plus: non-empty human-readable `locator` (sheet/cell, page/table, or row key), `retrieved_at`, and `sha256`.

Incomplete attribution → `facts_pending_attribution` with `quarantine_reason`; never UI/API publish paths.

---

## 6. PDF policy

| Tier | Policy |
|---|---|
| **A (M10 pilot)** | Hand-curate BP1 Statement 6 expense-by-function + one state budget headline table as CSV transcriptions with page/table locators. Reconcile vs ABS GFS Table 130; record go/no-go. |
| **B** | Expand Tier A only if M10 recommends go; otherwise leave PDFs as document library. |
| **C** | Narrative DOCX/PDF — metadata + download links only; no numeric extract. |

---

## 7. Top-10 / milestone source map

| Milestone | Sources |
|---|---|
| M3 | `federal_expense_by_function`, `sa_gfs_by_function`, `vic_local_govt_financial` |
| M4 | ABS GFS ×13 (`abs_gfs_*`), `act_notifiable_invoices`, `nt_awarded_government_contracts` |
| M5 | `nsw_local_olg_time_series`, `tas_local_cdc`, `vic_local_vgc_abs_returns` |
| M6 | `federal_monthly_financial_statements`, `nsw_procurement_ocds_registry` |
| M7 | `qld_qgip_expenditure`, `qld_contract_disclosure_agency_datasets` (schema-variance rule) |
| M10 | Tier A: `federal_budget_statement_6_2026_27` + one state budget headline table |

---

## 8. Schema deltas beyond draft SQL

1. Seed `payment_timing_disclosure` (and related) in `measure_definitions`
2. Add `native_unit` on `source_documents`
3. Create `facts_pending_attribution` mirroring `facts` + `is_publishable`, `quarantine_reason`
4. Confirm `government_level` allows `territory` (draft already does)
5. `schema_migrations` log table for idempotent apply

---

## 9. Non-goals (M0–M12)

- Rewriting acquisition adapters except registry unification (M11)
- Unblocking Cloudflare for SA LGGC / NT grants (mark `blocked` if inaccessible)
- Force-fitting inconsistent QLD disclosure schemas (exceptions doc instead)
- Modifying live default route until cutover criteria pass

---

## 10. Success criteria (cutover)

See `ops/engineering-plan-20260722.md` M12. In short: top-10 published, Gate 6 at 100% on exposed facts, M3 reconciliations balanced or explained, default-view regression green, criteria script exits 0.
