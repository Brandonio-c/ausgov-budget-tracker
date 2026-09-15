# PROJECT STATUS — AusGov Budget Tracker

> Authoritative subsystem classification baseline.  
> **Generated:** 2026-09-15T02:30Z — commit `3a2d6a9` — clean tree.  
> Key: **COMPLETE** | **WORKING** | **PARTIAL** | **BROKEN** | **BLOCKED** | **PLANNED** | **UNKNOWN**

---

## MISSION

Build the authoritative Australian Government public-finance dashboard at vibefactory.app/ausgov-budget-tracker. All tiers of government. Traceable, semantically coherent fact trees. Citation-bearing. Automated ingestion pipeline. Production deployed.

---

## SUBSYSTEM STATUS

### 1. Data Pipeline — PARTIAL

| Stage | Status | Notes |
|-------|--------|-------|
| Source registry | WORKING | 376 sources in `config/procurement_sources.yaml` |
| Raw fetch (`scripts/fetch_orchestrator.py`) | WORKING | CKAN, web, scraping; 90 registry sources, 88 on disk |
| Ingest parsers (federal) | WORKING | GFS actuals, Statement 6, FBO historical (2019-20..2023-24), PBS, NDIS, AusTender, COFOG crosswalk |
| Ingest parsers (state) | PARTIAL | All states/territories covered for GFS actuals + debt; QLD CFFR annual only |
| Ingest parsers (local) | PARTIAL | VIC VAGO + ACT sample only; no NSW/QLD/SA/WA/TAS local |
| Ingest parsers (pre-2019 FBO) | PLANNED | Item 8.1: FY2010-11..FY2013-14 tractable, not yet built |
| Integrity gate (task9) | BROKEN | 1,640 PBS crosswalk label rejections — hard failures block deployment |
| CI ingestion tests | WORKING | `tests/ingest`, `tests/ops` wired to CI (fixture DB, not full corpus) |

### 2. Data Model / Database — WORKING

| Component | Status | Notes |
|-----------|--------|-------|
| Core schema (facts, nodes, fact_nodes, breakdown_edges, source_documents) | COMPLETE | Migration 006 (semantic hardening) applied |
| View families / compatibility groups | COMPLETE | `config/compatibility/view_families.yaml`; enforced in backend |
| Semantic columns (amount_value, view_family, price_basis, PBS inference) | COMPLETE | Migration 006 |
| Edge kinds (same_group vs related_breakdown) | COMPLETE | Additive vs non-additive traversal |
| preserve_amount flag | COMPLETE | Statement 6 A61 nodes; fixed in Loop 7 |
| Quality status (quarantined/rejected/ok) | COMPLETE | 332/472 PBS bridge facts quarantined (Loop 5) |
| Reviewed duplicates registry | COMPLETE | 172 confirmed false-positive duplicate groups |
| Database size | WORKING | 884 MB; 333,660 facts, 241,742 nodes, 18,170 edges |

### 3. Backend API — WORKING

| Endpoint family | Status | Notes |
|----------------|--------|-------|
| `/api/health` | COMPLETE | Liveness probe |
| `/v2/dashboard/levels` | COMPLETE | Lists available government levels per mode |
| `/v2/dashboard/availability` | COMPLETE | Years + basis + source families per level |
| `/v2/dashboard/tree` | COMPLETE | Full tree with additive/related nodes; mode-aware |
| `/v2/dashboard/item/{id}/children` | COMPLETE | Lazy budget-mode child expansion (not wired in frontend) |
| `/v2/dashboard/item/{id}/source-file` | COMPLETE | Cached source file streaming |
| `/v2/facts/{id}/citation` | COMPLETE | Citation chain with PDF locator, URL, SHA256 |
| `/v2/tree` / `/v2/explorers/{family}/tree` | COMPLETE | Cursor-paginated flat-tree explorer |
| `/v2/search` | COMPLETE | Hybrid FTS5 + FastEmbed semantic search (RRF merge) |
| `/v2/aggregate` | COMPLETE | Compatibility-group-guarded aggregate query |
| CORS | COMPLETE | `vibefactory.app` only; `CORS_EXTRA_ORIGINS` for dev |
| FastAPI version | WORKING | v2 routers at `src/backend/routers/v2/`; port 8010 via Docker |

### 4. Application State / Frontend — WORKING (not deployed)

| Component | Status | Notes |
|-----------|--------|-------|
| Home dashboard (actuals + budget modes) | COMPLETE | `app/HomeClient.tsx`; pie/bar/rings; drill-down; branch selector |
| Combined national view | COMPLETE | `app/combined/page.tsx`; multi-level comparison, non-consolidated bars |
| MFS explorer | COMPLETE | Monthly Financial Statements explorer surface |
| Debt viewer | COMPLETE | `DebtViewer` component |
| Citation viewer | COMPLETE | `FactCitationViewer`; PDF locator + source document links |
| Ring depth control | COMPLETE | Branch coverage disclosed per branch before selection |
| Dark mode | COMPLETE | System-preference aware |
| Deep-link query params | COMPLETE | `?mode=&level=&year=&fact=&highlight=` |
| Static export | COMPLETE | 23 routes; Cloudflare Workers ready |
| Search page | COMPLETE | Hybrid search with scope filter |
| `/item/{id}/children` UI | PLANNED | API exists; no frontend component wired yet |
| Deploy to production | BROKEN | Loop 3-14 changes not deployed; prod runs pre-Loop 3 |

### 5. Analytics / Dashboard — WORKING

| Feature | Status | Notes |
|---------|--------|-------|
| Actuals mode (federal, state, local) | COMPLETE | GFS + FBO + accrual per level; year-aware basis selection |
| Budget mode (federal) | COMPLETE | Loop 3 fixed 6-7x inflation; `preserve_amount` on A61; PBS source-key restriction |
| Debt mode | PARTIAL | State borrowing authorities covered; instrument depth thin at AOFM |
| GDP / ratio mode | PARTIAL | Current-price and chain-volume variants; limited coverage |
| COFOG crosswalk (federal functions) | COMPLETE | All 17 functions non-zero (Loop 14) |
| Education subfunctions | COMPLETE | 17 overrides, 23 schools / 9 higher-ed children (Loop 13) |
| NDIS participants | COMPLETE | 267 facts, depth 9 |
| NDIS payments | COMPLETE | 20 facts |
| Health / Aged Care | PARTIAL | Reachable via `attach_related_to_tree()`; stale health facts cleaned (Loop 11) |
| AusTender contracts | COMPLETE | 4-level UNSPSC hierarchy (Loop 12) |
| GrantConnect grants | COMPLETE | Part of explorer API families |
| Revenue reconciliation | PARTIAL | Surface exists; some jurisdiction/detail pairs warn |

### 6. Operations — PARTIAL

| Component | Status | Notes |
|-----------|--------|-------|
| Docker deployment (`docker-compose.vibefactory.yml`) | PARTIAL | Config correct; image not rebuilt since Loop 3 |
| Backend bind mounts (facts.db, data/raw, config) | COMPLETE | Read-only; port 127.0.0.1:8010:8010 |
| Cloudflare Workers (frontend) | PARTIAL | Config exists; not re-deployed since Loop 3-14 changes |
| Golden fixture audit (`make audit`) | COMPLETE | `scripts/ops/dashboard_depth_audit.py`; 12 projections; CI-gated |
| Integrity gate (`task9`) | BROKEN | 1,640 hard failures (PBS labels) — must be 0 before deploy |
| CI pipeline (`.github/workflows/ci.yml`) | COMPLETE | python + frontend + e2e jobs; fixture DB, unit, integration, ops tests |
| Local test env | BROKEN | `make test` fails — missing `pypdf`, `duckdb`, `openpyxl` in conda env |
| Monitoring / alerting | UNKNOWN | No monitoring config found in repo |
| Automated daily ingestion | PLANNED | Not yet implemented |

### 7. Testing — WORKING

| Suite | Count | Status | Last Run |
|-------|-------|--------|----------|
| Backend unit + integration | 335 | PASS | Loop 14 (2026-08-26) |
| E2E (Playwright: dashboard + MFS explorer) | 25 | PASS | Loop 14 (2026-08-26) |
| Frontend lint:ci | baseline | PASS | Loop 14 (2026-08-26) |
| Frontend tsc | — | PASS | Loop 14 (2026-08-26) |
| Frontend build | 23 routes | PASS | Loop 14 (2026-08-26) |
| task9 integrity gate (full corpus) | — | FAIL | 2026-09-14: 1,640 PBS label failures |
| Golden fixture (12 projections) | 12 | PASS | 2026-09-14 |
| `make test` locally | — | FAIL | missing conda packages |

---

## DATA SOURCES INVENTORY

| Source Category | Coverage | Status |
|----------------|----------|--------|
| Federal actuals (GFS/COFOG) | FY2022-23..FY2025-26 | COMPLETE |
| Federal budget (Statement 6 / PBS) | FY2022-23..FY2029-30 | COMPLETE |
| Federal historical FBO | FY2019-20..FY2023-24 | COMPLETE |
| Federal pre-2019 FBO | Not loaded | PLANNED (item 8.1) |
| Federal NDIS / health programs | Participants + plan budgets + payments | COMPLETE |
| Federal AusTender contracts | OCDS + 4-level UNSPSC | COMPLETE |
| Federal GrantConnect grants | Award-level | COMPLETE |
| State actuals | All states/territories | COMPLETE |
| State debt instruments | All 7 borrowing authorities | COMPLETE |
| QLD Consolidated Fund | 17-year annual series, 9 measures | PARTIAL |
| QLD on-time payment | Data + dedicated explorer | COMPLETE |
| Local — VIC VAGO | Aggregate series | COMPLETE |
| Local — ACT invoices | Invoice-level sample | COMPLETE |
| Local — other jurisdictions | No facts loaded | PLANNED |
| Revenue / GDP | Federal + selected states | PARTIAL |
| **Registry total** | **376 sources; 88 on disk; 29 primary families loaded** | PARTIAL |

---

## KEY SEMANTIC RULES (never violate)

1. Never mix `view_family` groups in one additive tree.
2. Never mix `percent` unit and `AUD` in the same fact set.
3. Never mix `current_price` and `chain_volume` without explicit deflator bridge.
4. No "Combined national total" without explicit reconciliation.
5. `same_group` edges only within one source hierarchy and one government level/jurisdiction.
6. `related_breakdown` edges cross-source navigational only — never additive.
7. `preserve_amount = True` on Statement 6 A61 nodes — children do not recompute the parent.

---

## KNOWN GAPS & DEFERRALS

| Item | Disposition | Evidence |
|------|-------------|---------|
| Pre-2019 FBO FY2010-11..FY2013-14 | Confirmed tractable, not yet built | `ops/reports/fbo-appendix-a-page-anchor-scoping-20260818T160000Z.md` |
| Pre-2019 FBO remaining sub-generations | Needs separate investigation per generation | Same report |
| FY1985-86 / FY1986-87 | BLOCKED EXTERNAL — no primary source exists | `ops/reports/fbo-historical-archive-triage-20260807T175900Z.md` |
| QLD Consolidated Fund quarterly/detail | Deferred by explicit plan decision | `ops/reports/data-remediation-progress.md` item 7.4 |
| VIC non-dollar output KPIs (~70 rows) | Deferred — single-year, no time series, poor value/effort | Same report item 7.6 |
| 2 of 5 MFS sibling workbooks | Deferred with evidence | `ops/reports/federal-deep-data-mission-20260823T151600Z.md` |
| `/item/{id}/children` frontend component | Not yet built | No tracking issue exists |

---

## DEFINITION OF DONE (11/12 CRITERIA MET)

| Criterion | Status |
|-----------|--------|
| Annual dashboard nodes explicitly additive/related/navigation | Met |
| Displayed amounts/units match their facts | Met |
| Every availability entry queryable and basis-labeled | Met |
| No edge set can silently drop path data | Met |
| Historical FBO available for 2019-20..2023-24 | Met |
| 2022-23/2023-24 have verified Statement 6/PBS program route | Met |
| Contracts/PBS/grants/VIC/ACT/QGIP have specialist surfaces | Met |
| MFS siblings and missing borrowing sources handled | Met (3/5 MFS + 2/5 deferred; all 7 borrowing authorities covered) |
| QLD cash/compliance families have independent semantic models | Met |
| **Pre-2019 FBO adapters generation-bounded and contamination-tested** | **Not met** — item 8.1 |
| Coverage/depth/source-year/quarantine/citation metrics in CI | Met |
| Deliberate limitations visible, not presented as missing | Met |

---

## HEALTH SUMMARY

| Subsystem | Health |
|-----------|--------|
| Data model | HEALTHY |
| Ingest pipeline | DEGRADED (PBS label gate failing) |
| Backend API | HEALTHY |
| Frontend | HEALTHY (not deployed) |
| CI | HEALTHY |
| Production deploy | STALE (pre-Loop 3) |
| Local dev env | BROKEN (missing packages) |

**Overall: NOT READY FOR PRODUCTION DEPLOY** — resolve PBS label gate (P0), then deploy.
