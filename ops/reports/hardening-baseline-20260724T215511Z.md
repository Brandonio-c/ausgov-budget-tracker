# Hardening baseline — 20260724T215511Z

**Commit SHA:** `36ace65ffa7ec2f0064baa5a7a7f1f26d7085fb7` (`main`)  
**Repo:** `ausgov-budget-tracker`  
**Facts DB (local, not committed):** 331,022 facts

## Tests run

| Command | Result |
|---------|--------|
| `python -m pytest tests/ -q` | **51 passed**, 0 failed, 0 skipped (1 Starlette warning) |
| `cd src/frontend && npm run lint` | **21 errors, 13 warnings** (pre-existing; SpendingChart ref-during-render, a11y) |
| `npx tsc --noEmit` | (ran after lint; lint failed first — tsc not separately gated in this pass) |

No GitHub Actions, Makefile, ruff, or mypy configured at baseline.

## Fact / compatibility counts

| compatibility_group | facts |
|---------------------|------:|
| actual_expense | 195,435 |
| budget_expense | 67,111 |
| cash_outflow | 46,740 |
| commitment | 16,255 |
| gfs_revenue | 3,757 |
| gfs_liability | 1,677 |
| gdp | 47 |

GDP measures in DB:

| measure_type | n | min amount_aud | max amount_aud |
|--------------|--:|---------------:|---------------:|
| gdp_current | 28 | 3.7e9 | 2.8e12 |
| gdp_chain_volume | 10 | 9e5 | 2.7e12 |
| gsp_current | 8 | 3.5e10 | 8.6e11 |
| tax_to_gdp_ratio | 1 | **24.33** | **24.33** |

`tax_to_gdp_ratio` is stored in `amount_aud` (percent points mis-typed as currency).

## Semantic defects reproduced

### 1. GDP mode mixes incompatible measures

`GET /v2/dashboard/tree?mode=gdp&level=federal&year=2024-25` → **200**.

Root value ≈ **`$16,623,231,000,024`** — sums industry GVA lines with `GDP (current prices)` / expenditure children and includes ratio-scale pollution risk. Single filter `compatibility_group='gdp'` (dashboard `_mode_filters`).

### 2. PBS year inference unsafe

[`scripts/ingest/extractors/pbs_programs_all.py`](../scripts/ingest/extractors/pbs_programs_all.py): `years = YEARS_DEFAULT[-len(nums):]` with fixed `YEARS_DEFAULT` 2024–25…2029–30. No header parsing.

### 3. Revenue double-count risk

ABS taxation remapped into `gfs_revenue` alongside GFS Table 1 (`m_gdp_tax.py`). Revenue tree returns 200 with children; no reconciliation warning metadata.

### 4. Debt mixed valuation incomplete

State debt tree returns `valuation_basis` (singular) and `mixed_observation_dates` but **no** `valuation_bases[]` / `mixed_valuation_bases` on response (collected in builder, not exposed).

### 5. Combined misleading total

Frontend `SpendingChart` always formats `Total: $sum(nodes)` even when Combined banner says levels are not consolidated (`combineTrees.ts` root value 0).

### 6. Tests depend on production DB

API/ingest tests set `FACTS_DB_PATH` → `data/facts.db`. `test_federal_actuals_depth.py` can `return` if DB missing (silent soft-pass pattern present).

### 7. README obsolete

Still titled Phase 1 / `spending.db` pilot.

### 8. Coverage audit heuristics

`ingestion_coverage_audit.py` uses source_id token scrape + hard-coded alias sets, not lineage.

## API smoke (baseline)

| Endpoint | Status | Note |
|----------|--------|------|
| Actuals federal 2024–25 | (covered by existing tests) | OK control |
| GDP federal 2024–25 | 200 | **Unsafe mixed total** |
| Revenue federal 2024–25 | 200 | No double-count guard |
| Debt state 2024–25 | 200 | Missing mixed valuation fields |

## Next

PR1 — semantic schema + compatibility engine.
