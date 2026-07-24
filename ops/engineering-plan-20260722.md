# AusGov Budget Tracker — Engineering Plan (M0–M12)

**Date:** 2026-07-22  
**Status:** Execution plan (locked)  
**Architecture:** `ops/research-ingestion-plan-20260722.md`  
**Schema draft:** `data/ausgov_budget_hierarchical_schema.sql`

---

## Hard rules

1. Never write to `data/processed/spending.db` or modify Phase 1 scripts / default frontend route until M12 cutover criteria script passes.
2. Never publish a fact without complete Citation (`landing_url`, `original_resource_url`, cached copy URL, non-empty locator, retrieval sha256/`retrieved_at`).
3. Never sum across `compatibility_group` boundaries (API 400).
4. Per-source isolation; idempotent `fact_key` upserts.

---

## Repo layout (create as milestones progress)

```
config/mappings/                    # YAML mapping specs + README.md
scripts/ingest/
  schema_migrate.py
  duckdb_etl.py
  validate.py                       # Gates 1–6
  load_facts.py
  reconcile.py
  quarantine_report.py
  run.py
data/facts.db                       # never the live spending file
src/backend/routes/v2/              # citation-bearing read API
src/frontend/components/CitationPanel/
src/frontend/app/explorers/
tests/ingest/ | tests/api/ | tests/frontend/
ops/reports/m0-schema.md … m12-cutover.md
```

---

## Validation gates (Gates 1–6)

| Gate | Name | Fail behaviour |
|---|---|---|
| 1 | Schema / required columns present | Reject batch |
| 2 | Types & units coerce cleanly | Reject or quarantine row |
| 3 | Period / FY parse | Reject or quarantine row |
| 4 | Entity / node resolution | Quarantine if unmapped |
| 5 | Measure + compatibility declared | Reject batch |
| 6 | **Attribution completeness** | Always → `facts_pending_attribution` if incomplete; never publish |

Gate 6 fields: `landing_url`, `original_resource_url`, cached copy path/URL, non-empty locator JSON/text, retrieval `sha256`, `retrieved_at`.

---

## Working method (every milestone)

1. Branch `ingest/mN-<slug>` from main (or current integration branch)
2. Restate DoD from this plan in the report header
3. Implement + tests alongside
4. Run real verification (row counts, gate outcomes, attribution %)
5. Write `ops/reports/mN-*.md`
6. Merge + tag `ingest-mN`; continue immediately to next milestone

No mid-build check-ins. Only mark individual sources `blocked` if files are inaccessible/corrupt/self-contradictory; continue everything else.

---

## Milestone DoD

### M0 — Schema foundation

- Apply `data/ausgov_budget_hierarchical_schema.sql` idempotently via `schema_migrate.py` + `schema_migrations` log
- Additive deltas:
  1. `payment_timing_disclosure` (and related) in `measure_definitions`
  2. `native_unit` on `source_documents`
  3. `facts_pending_attribution` mirroring `facts` + `is_publishable`, `quarantine_reason`
  4. Confirm `government_level` allows `territory`
- Idempotent migrate twice (second = no-op)
- Constraint / migration tests green
- Report: `ops/reports/m0-schema.md`

### M1 — ETL framework + Gates 1–6

- Mapping YAML spec under `config/mappings/` + README
- `duckdb_etl` / `validate` / `load_facts` / `quarantine_report` / `run.py`
- Synthetic fixture: published facts + one Gate-6 quarantine (missing `landing_url`)
- Idempotent second run
- Report: `ops/reports/m1-etl-framework.md`

### M2 — Citation API + CitationPanel (before volume)

- `GET /v2/facts/{id}/citation` matching Citation contract
- CitationPanel tests: complete citation renders 3 links; quarantined facts never reachable via UI/API
- Report: `ops/reports/m2-citation-panel.md`

### M3 — Phase 1 backfill

- Mapping YAMLs from existing `source_context_json` locators
- Reconcile vs `spending.db` per FY; record `reconciliations` for gaps (never block)
- 100% attribution on published Phase 1 facts
- Report: `ops/reports/m3-phase1-backfill.md`

### M4 — ABS GFS ×13 + ACT + NT

- DuckDB-inspect ABS files; shared template or documented variants
- First `territory` facts; attribution completeness reported
- Report: `ops/reports/m4-gfs-act-nt.md`

### M5 — Local NSW / TAS / VIC

- ZIP unpack for TAS CDC; inspect year layout before mapping
- VIC 2014–19 still present vs M3 baseline
- Report: `ops/reports/m5-local-government.md`

### M6 — Federal monthly + NSW OCDS

- `monthly_actuals` measure; OCDS flatten to `contract_value` + supplier/contract nodes
- Spot-check 3–5 NSW contracts vs public eTendering
- Report: `ops/reports/m6-federal-monthly-nsw-ocds.md`

### M7 — QLD QGIP + Contract Disclosure

- Sample ≥15 disclosure CSVs; auto decision: ≥90% identical schema → one mapping; exceptions in `ops/reports/m7-schema-exceptions.md`
- Agency renames via `entities.valid_from/valid_to`
- Report: `ops/reports/m7-qld-procurement.md`

### M8 — API v2 + compatibility guard

- Routes require one `(compatibility_group, accounting_basis, estimate_status)` triple
- Illegal cross-group → 400; reconciliation view allowed; all responses citation-bearing
- Tests: `test_compatibility_guard.py`, `test_citation_completeness.py`
- Report: `ops/reports/m8-api-v2.md`

### M9 — Frontend explorers

- Contracts + GFS/jurisdiction explorers with CitationPanel
- Default-view DOM/screenshot regression green (legacy unchanged)
- Report: `ops/reports/m9-frontend-explorers.md`

### M10 — PDF Tier A pilot

- Hand CSV for BP1 Statement 6 + one state headline table; page/table locators satisfy Gate 6
- Reconcile vs GFS Table 130; go/no-go recommendation recorded; proceed either way
- Report: `ops/reports/m10-pdf-pilot.md`

### M11 — Registry unification

- Merge Phase 1 into `procurement_sources.yaml`; single orchestrator; retire `scripts/sources.yaml`
- Re-run M9 regression
- Report: `ops/reports/m11-registry-unification.md`

### M12 — Autonomous cutover

- Script checks: top-10 published; Gate 6 100% on exposed facts; M3 reconciliations balanced or explained; regression green
- Switch default route to new store; keep `/legacy`
- Checklist with measured values in `ops/reports/m12-cutover.md`

---

## Immediate start

1. Create branch `ingest/m0-schema`
2. Write missing `ops/research-ingestion-plan-20260722.md` + this file
3. Implement `schema_migrate.py`, apply schema + M0 deltas to `data/facts.db`, tests, `ops/reports/m0-schema.md`
4. Merge/tag and continue M1 without pausing
