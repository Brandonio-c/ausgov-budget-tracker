# NOW — AusGov Budget Tracker

> One-stop operational state for agents and engineers picking up this project.  
> **Last verified:** 2026-09-15T02:30Z — commit `3a2d6a9` — clean tree.

---

## MISSION

Build the authoritative Australian Government public-finance dashboard at  
`vibefactory.app/ausgov-budget-tracker`.  
Cover federal, state, territory, and local governments with traceable, semantically  
coherent spending/budget/debt facts down to program and contract level.

---

## DESIRED END STATE

- All tiers of Australian government represented with additive, citation-bearing fact trees.
- Federal: full historical depth from 1970-71, function → agency → program → contract/grant.
- States/territories: GFS actuals + borrowing; QLD extended to Consolidated Fund detail.
- Local: VAGO VIC aggregate + ACT invoice-level sample.
- Every fact in the published dashboard links to a retrievable, cached primary source document.
- Automated daily ingestion (fetch → parse → integrity-gate → deploy) with zero-downtime rolling updates.
- Production deployed at vibefactory.app with backend (FastAPI/Docker) + frontend (Next.js/Cloudflare Workers).

---

## CURRENT STATE ⚠️ NOT DEPLOYED

> **Loop 3–14 changes are NOT live in production.**  
> vibefactory.app still runs the pre-Loop 3 state (budget mode was inflated 6–7×).  
> A P0 integrity blocker (see below) must be resolved before deploying.

### Database (data/facts.db — 884 MB, gitignored)

| Metric | Value |
|--------|-------|
| Facts | 333,660 |
| Nodes | 241,742 |
| Breakdown edges | 18,170 |
| Source documents | 150 |
| Measure types | 219 |
| Financial years | 66 (FY1970-71 to FY2029-30) |
| Active source keys | 147 |

### Dashboard health (last audit 2026-08-26 / re-verified 2026-09-14)

- 12 canonical projections — **0 hard failures**, **fixture matches: true**
- Edge integrity: 0 duplicate semantic edges, 0 cycles
- task9 integrity gate: **1,640 hard failures** (all `pbs_crosswalk_children_with_rejected_labels`) — **P0 BLOCKER**
- All other checks: 0 orphan facts, 0 orphan nodes, 0 orphan edges, 172 reviewed false-positive duplicates

### Test suite

| Suite | Count | Status |
|-------|-------|--------|
| Backend unit + integration | 335 | PASS (Loop 14) |
| E2E (Playwright) | 25 | PASS (Loop 14) |
| Frontend lint:ci | baseline | at baseline |
| Frontend tsc | — | clean |
| Frontend build | 23 routes | static export clean |
| Local `make test` | — | FAIL — env missing pypdf/duckdb/openpyxl |

---

## DATA COVERAGE

### Federal (WORKING — not deployed)

- Actuals: GFS function series FY2022-23..FY2025-26 (GGS Monthly Financial Statements)
- Actuals depth: FBO historical FY2019-20..FY2023-24 (agency to program)
- Budget: Statement 6 FY2022-23..FY2029-30 (PBS programs; Loop 3 fixed 6-7x inflation)
- PBS label classifier: 332/472 `pbs_programs_s6_bridge` quarantined as navigation labels (Loop 5)
- NDIS participants (267 facts, depth 9), NDIS payments (20 facts), Health/Aged Care reachable
- AusTender contracts: 4-level UNSPSC hierarchy (Loop 12)
- COFOG crosswalk: all 17 federal functions non-zero (Loop 14)
- Education subfunctions: 17 crosswalk overrides, 23 schools / 9 higher-ed children (Loop 13)

### State (WORKING)

- VIC, NSW, QLD, SA, WA, TAS, NT, ACT — GFS actuals by function (state_actuals)
- Borrowing: all 7 named authorities covered via `state_debt_instruments` adapter
- QLD Consolidated Fund: 17-year annual series, 9 measures (FY2006-07..FY2022-23); quarterly/detail deferred

### Local (PARTIAL)

- VIC local governments: VAGO aggregate series
- ACT invoice-level sample (GrantConnect)
- No other jurisdictions at local tier

### Revenue / GDP (PARTIAL)

- GFS revenue: federal + some states; reconciliation surface working
- GDP deflators: current-price and chain-volume variants
- Revenue jurisdiction/detail gap warns remain (informational)

---

## WHAT WORKS

1. **Dashboard tree API** (`/v2/dashboard/tree`) — actuals and budget modes, all levels
2. **Semantic hardening** — view families enforced; no cross-group aggregation
3. **Citation chain** — every fact links to retrievable cached source document
4. **Explorer APIs** — flat-tree, per-family, ring depth, branch coverage
5. **Frontend** — pie/bar/rings charts; drill-down; citation viewer; combined view; MFS explorer
6. **Golden fixture gate** — 12 projections verified on every CI push
7. **task9 integrity gate** — blocks bad loads before they reach production (currently 1640 failures)
8. **Procurement source registry** — 376 sources catalogued across all tiers

---

## KNOWN PROBLEMS

| ID | Severity | Description |
|----|----------|-------------|
| PBS-LABELS | P0 | 1,640 `pbs_crosswalk_children_with_rejected_labels` hard failures (Loop 13 crosswalk additions brought in nodes with labels the classifier rejects) |
| DEPLOY-GAP | P1 | Loop 3-14 changes not deployed; production runs pre-Loop 3 (inflated budget mode) |
| LOCAL-ENV | P1 | `make test` fails locally (missing `pypdf`, `duckdb`, `openpyxl` in conda `vibe-factory` env) |
| PRE-2019-FBO | P2 | FY2010-11..FY2013-14 FBO slice not built (confirmed-tractable, item 8.1) |
| QLD-CFFR | P2 | QLD Consolidated Fund quarterly editions and Note 1/2 detail deferred |
| CHILDREN-UI | P2 | `/item/{id}/children` API exists but not wired to any frontend component (NDIS/Health depth inaccessible to users) |
| MFS-SIBLINGS | P3 | 2 of 5 MFS sibling workbooks deferred with evidence |
| DEBT-THIN | P3 | AOFM debt instrument depth thin (Debt securities to instruments) |
| FBO-1985 | BLOCKED | FY1985-86 / FY1986-87 — no machine-accessible primary source exists |

---

## P0 — MUST FIX BEFORE PRODUCTION DEPLOY

**PBS crosswalk label rejections (1,640 hard failures)**

- Cause: Loop 13 (Education routing, commit `3529114`) added 17 crosswalk overrides to `pbs_programs_all_under_s6`; some child nodes' labels are classified `rejected` by `pbs_label_classifier.py`
- Impact: `task9_sql_integrity_checks.py` exits non-zero; the integrity gate is failing
- Required fix: investigate whether labels are genuinely unpublishable (quarantine nodes or remove overrides) or whether the classifier needs calibration for these Education subtree labels
- Key files: `scripts/ops/pbs_label_classifier.py`, `scripts/ops/task9_sql_integrity_checks.py` (lines 213-228), `src/backend/routers/v2/dashboard.py` (crosswalk override list)

---

## P1 — HIGH PRIORITY

1. **Deploy Loop 3-14** — Docker rebuild (backend) + Cloudflare Workers deploy (frontend)
   - Prerequisite: PBS label rejections resolved (P0 above)
   - Prerequisite: production env vars confirmed (`DB_PATH`, `CORS_EXTRA_ORIGINS`)
2. **Fix local test environment** — install `pypdf duckdb openpyxl` in conda `vibe-factory` env

---

## P2 — NEXT INGESTION WORK

1. **FBO pre-2019 slice** — FY2010-11..FY2013-14 (4-year cluster, confirmed stable page anchor)
   - Reference: `ops/reports/fbo-appendix-a-page-anchor-scoping-20260818T160000Z.md`
2. **QLD Consolidated Fund** — quarterly editions, Operating/Investment split, 3 ambiguous receipt lines, Note 1/2 department-level detail
3. **Wire `/item/{id}/children`** — expose lazy budget-mode child expansion in frontend so NDIS/Health/Aged Care related depth becomes user-accessible

---

## BLOCKERS

- Nothing externally blocked except FY1985-86/1986-87 (no primary source exists)
- P0 PBS label rejections are self-resoluble within the repo — no external dependency

---

## NEXT 3 ACTIONS

1. **Investigate PBS label rejections** — run `scripts/ops/task9_sql_integrity_checks.py --db data/facts.db`, sample the 1,640 rejected-label node names, determine if classifier calibration or node quarantine is needed.
2. **Resolve and verify** — once PBS gate passes (0 hard failures), run full golden fixture audit (`make audit`), confirm 12 projections still match, then proceed to deploy.
3. **Deploy Loop 3-14** — `docker-compose -f docker-compose.vibefactory.yml up --build -d` (backend) + Cloudflare Workers publish (frontend).

---

## LAST VERIFIED

| Check | Result | When |
|-------|--------|------|
| Git tree | clean (3a2d6a9) | 2026-09-15 |
| DB row counts | 333,660 facts / 18,170 edges | 2026-09-15 |
| Golden fixture (12 projections) | fixture_matches=true, 0 hard failures | 2026-09-14 |
| Backend tests | 335/335 | Loop 14 (2026-08-26) |
| E2E tests | 25/25 | Loop 14 (2026-08-26) |
| Frontend build | clean (23 routes) | Loop 14 (2026-08-26) |
| task9 integrity gate | 1,640 hard failures (PBS labels) | 2026-09-14 |
| Final DoD audit | 11/12 criteria met | 2026-08-18 |
