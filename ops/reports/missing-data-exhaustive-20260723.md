# Exhaustive missing-data & drill-down gap report

**Generated:** 2026-07-23  
**Scope:** `data/facts.db` + `data/raw` vs dashboard Actuals/Budget drill-down  
**Trigger example:** Actuals FY 2024-25 → Social protection → Assistance to the aged → **Support for seniors (~$65B)** stops — no deeper published grain is wired yet, even though richer sources already sit on disk.

---

## Executive verdict

| Question | Answer |
|---|---|
| Why does Support for seniors stop? | Ingest stops at **PBS program total**. DSS PBS PDF already publishes **Program 1.3 components** (Age Pension ≈ $65.25B + Energy Supplement). Not extracted. |
| Is $1M+ always breakable further? | **No** — published additive tables often stop at purpose/sub-function/program. Deeper grain is often **recipient counts**, **contracts**, or **agency PBS components** (different measure families). |
| Why only back to ~2015? | **ABS GFS** in DB starts **2015-16**. Finance Note 3 goes to **2005-06**. **1980s/90s not acquired.** |
| Why Budget ≪ Actuals? | Actuals load full ABS GFS (all jurisdictions) + Finance series. Budget is **one federal cycle** of Statement 6 + thin PBS bridges (+ 2 SA rows). State budget PDFs are on disk, almost unused. |

**facts.db (measured 2026-07-23):** **258,438** facts · **35** source_documents · **2,767** breakdown edges (562 same_group / 2,205 related) · **28** federal raw folders (24 with no matching `source_documents` row).

| Compatibility group | Facts | Notes |
|---|---:|---|
| `actual_expense` | 194,705 | Dominated by QLD QGIP (~181k) + GFS + Finance |
| `cash_outflow` | 46,714 | ACT invoices |
| `commitment` | 16,255 | State contracts |
| `budget_expense` | **764** | Almost all federal Statement 6 / thin PBS |

---

## 1. The Support for seniors ($65B) dead-end

### What the dashboard can do today

```
ABS Social protection ($286.6B, GFS actual 2024-25)
  └─ related → S6 Assistance to the aged → Support for seniors ($65.315B EA 2025-26)
       └─ same_group → PBS “Support for Seniors” ($65.312B)   ← duplicate bridge, same dollars
            └─ STOP  (no Age Pension / Energy Supplement / recipient split)
```

Confirmed in `facts.db`: node `…/Support for seniors` (id 214866) only has `same_group` edges to the PBS bridge twin — **zero deeper children**.

### What is already on disk but not in facts

| Asset | Path | What it would add |
|---|---|---|
| DSS PBS 2026-27 PDF | `data/raw/federal/federal_dss_pbs_2026_27/.../portfolio-budget-statements-2026-27-social-services.pdf` | **Table 2.1.2** Program 1.3: Age Pension ≈ $65.25B, Energy Supplement (CSHC) ≈ $62M |
| Health / Disability / Ageing PBS | `data/raw/federal/federal_health_disability_ageing_pbs_2026_27/...` | Real **Aged Care Services** program tree (Support at Home, residential, quality entities) under the $41.4B aged-care leaf |
| DSS Income Support monthly | `data/raw/federal/dss_income_support_monthly/` | Age Pension **recipient** time series (counts, not $) |
| DSS payments by LGA | `data/raw/federal/dss_payments_by_lga/` | Age Pension geography |
| DSS payment demographics | `data/raw/federal/dss_payment_demographics_quarterly/` | Demographics |
| Services Australia annual reports | `data/raw/federal/services_australia_annual_reports/` | Delivery / admin context |

**Honest bound:** Age Pension **outlays** at payment-rule / individual level are not in open additive tables. Next published dollars are **PBS components**; next non-dollar grain is **DSS recipient/LGA datasets**.

---

## 2. Actuals vs Budget imbalance

### Compatibility groups in facts.db

| Group | Facts | FY span | Role |
|---|---:|---|---|
| `actual_expense` | **194,705** | 2000–2099* | ABS GFS + Finance + locals + QGIP flood |
| `budget_expense` | **764** | **2024-25 → 2029-30** | Statement 6 + DSS/Health PBS bridges + SA headline |
| `cash_outflow` | 46,714 | 2005–2026 | ACT invoices |
| `commitment` | 16,255 | 2019–2026 | State contracts |

\*QGIP has dirty future FYs; ignore for fiscal history. Of Commonwealth rows: **901** actual_expense vs **762** budget_expense — the UI “Actuals-heavy” feel is mostly GFS jurisdiction breadth + deep QLD project rows, not deeper federal COFOG.

### Federal Budget sources (entire set)

| source_key | Facts | Years |
|---|---:|---|
| `federal_budget_statement_6_a61` | 432 | 2024-25…2029-30 |
| `federal_budget_statement_6_components` | 225 | 2025-26…2029-30 |
| `federal_dss_pbs_programs` | 60 | 2025-26…2029-30 |
| `federal_budget_statement_6_2026_27` | 30 | 2025-26…2026-27 |
| `federal_health_pbs_programs` | 15 | 2025-26…2029-30 |
| `sa_budget_headline_expenses` | **2** | 2025-26…2026-27 |

### Federal Actuals that look “richer”

| source_key | FY span | Grain |
|---|---|---|
| ABS GFS Commonwealth (+ states/territories/local) | **2015-16 → 2024-25** | COFOG purpose / section |
| `federal_expense_by_function` (Finance Note 3) | **2005-06 → 2025-26** | Budget function (purpose only) |
| `federal_monthly_financial_statements` | 2008-09 → 2025-26 | High-level aggregates |

**Why the UI feels Actuals-heavy:** every ABS jurisdiction workbook is loaded for Actuals; Budget mode has almost no state/territory budget function trees.

### State/territory budget papers — on disk, not in facts

| Folder | Files | In facts? |
|---|---:|---|
| `state/nsw_budget_2026_27` + open data | 29 | no |
| `state/vic_budget_2026_27` | 8 | no |
| `state/qld_budget_2026_27` | 50 | no |
| `state/sa_budget_2026_27` | 8 | headline only (2 facts) |
| `state/wa_budget_2026_27` | 106 | no |
| `state/tas_budget_2026_27` | 40 | no |
| `territory/act_budget_2026_27` | 23 | no |
| `territory/nt_budget_2026_27` | 3 | no |

---

## 3. Historical depth (1980s / 1990s gap)

| Family | Earliest in DB | Latest | Gap |
|---|---|---|---|
| ABS GFS (all 16 tables) | **2015-16** | 2024-25 | **No pre-2015-16 GFS** |
| Finance Note 3 | **2005-06** | 2025-26 | No 1980s–2004 |
| Statement 6 / PBS packs | 2024-25 / 2025-26 | 2029-30 | No historical BP1 |
| Federal monthly | 2008-09 | 2025-26 | — |
| SA state GFS | 2012-13 | 2015-16 | Stops early |
| Contracts | ~2019 | 2026 | No federal AusTender in DB |

### Not acquired (needed for 1980s–90s)

1. **ABS GFS previous releases** / older 5512.0 time-series — https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual (Previous releases)  
2. **archive.budget.gov.au** — historical BP1 expense-by-function / FBO Appendix A across cycles — https://archive.budget.gov.au/  
3. **Parliament / Trove** budget paper deposits  
4. Multi-year FBO appendices (only 2024-25 FBO PDF is held, and it is **not ingested**)

**On disk today:** latest ABS 2024-25 workbooks only (`55120DO002_202425.xlsx`, All-workbooks.zip).

---

## 4. Federal drill-down depth by major spend

From `ops/reports/breakdown-coverage-20260723.md` + facts edges:

| ABS / Budget function | Deepest in DB | Max leaf (order) | Next published step |
|---|---|---|---|
| Social protection / SSW | **PBS program** | Support for Seniors **$65B**, NDIS **$54B** | DSS PBS Table 2.1.2 components; NDIS payment datasets |
| Health | **S6 component / PBS bridge** | Medical Benefits **~$35B**, Pharma, hospitals | Full Health PBS outcome/program tables |
| Education | **S6 sub-function** | Schools **~$33B** | Education PBS |
| Defence | **Function total** | **~$50–53B** | Defence PBS capability programs |
| Other purposes | **Sub-function** | GPIGT **~$100B+** | BP / FBO detail; not COFOG-additive |
| Public order, Housing, Transport, Recreation, Economic | **S6 sub-function** | varies | Portfolio PBS |
| GPS | **ABS section / related** | Public debt, other GPS | Superannuation / debt interest detail |

### High-value leaves ≥ $1M with no `same_group` children (illustrative)

True drill-stoppers (excluding headline “Total expenses” rows):

| Amount | FY | Leaf | Why stuck |
|---:|---|---|---|
| $65.3B | 2025-26 | Support for Seniors (PBS) | Need PBS 1.3.1 Age Pension component |
| $53.8B | 2025-26 | NDIS (PBS/component) | Need NDIA PBS + `ndis_payment_datasets` (~647MB on disk) |
| $52.9B | 2025-26 | Defence | Need Defence PBS |
| $50.2B | 2024-25 | ABS Defence | related only → S6 total |
| $41.4B | 2025-26 | Aged Care Services (PBS bridge) | Need Health/Ageing PBS Outcome 3 |
| $35.1B | 2025-26 | Medical Benefits | Health PBS program detail |
| $286.6B | 2024-25 | ABS Social protection | related→S6 only (by design, not rollup) |

**Rule of thumb for “$1M+ should go deeper”:**

- **Yes, if published:** PBS component tables, FBO Appendix A sub-functions, agency annual report program expenses.  
- **Related only (don’t sum into pie):** contracts (AusTender), grants (GrantConnect), recipient counts (DSS).  
- **Often impossible as additive $:** individual invoices for whole-of-function totals.

---

## 5. Acquired raw federal corpora not in facts.db

Approx **24** federal raw trees with no matching published `source_documents` row (or only partial bridge):

| Corpus | Approx size / note | Gap fill |
|---|---|---|
| `federal_dss_pbs_2026_27` | Full PDF | Program **components** |
| `federal_health_disability_ageing_pbs_2026_27` | Full PDF | Aged care / health programs |
| `federal_dva_pbs_2026_27` | Full PDF | Veterans under SSW |
| `federal_ndia_pbs_2026_27` | Full PDF | NDIS agency |
| `federal_social_services_pbs_2025_26_archive` | Prior PBS | History |
| `federal_transparency_portal` | Multi-portfolio PBS PDFs | Breadth |
| `federal_fbo_2024_25_function_subfunction` | Appendix A PDF | **Audited** sub-function actuals |
| `federal_cfs_2024_25` | CFS | Consolidated financials |
| `federal_budget_measures_bp2_2026_27` | BP2 | Measures (not COFOG tree) |
| `federal_agency_resourcing_bp4_2026_27` | BP4 | Agency resourcing |
| `dss_income_support_monthly` | ~1.1M | Age Pension recipients |
| `dss_jobseeker_monthly_profile` | ~19M | JobSeeker |
| `dss_payment_demographics_quarterly` | ~4M | Demographics |
| `dss_payments_by_lga` | ~2.8M | Geography |
| `ndis_payment_datasets` | ~647M | $ under NDIS leaf |
| `ndis_participant_datasets` | ~647M | Participants |
| `ndis_quarterly_reports` / FSR | ~1–1.4G | Context / forecasts |
| `federal_grantconnect` | ~35M | Grants |
| `federal_austender_*` + historical CN | ~1.6G+ | Contracts |
| `services_australia_annual_reports` | ~22M | Delivery |

**Still unacquired / blocked (research handoff):** SA/WA tender & council packs, NT LGC returns, deprecated AusTender weekly export, long-run budget archives.

---

## 6. Prioritized roadmap (where to go next)

### P0 — highest $/hour (closes the $65B question)

1. Extract **DSS PBS Table 2.1.2** Program 1.3 components (Age Pension, Energy Supplement) from the held PDF; link under Support for Seniors.  
2. Extract full **Outcome 1 component trees** (Families, DSP, Carers, Working Age, Students, DES) + Program 1.9.  
3. Ingest **Health Disability & Ageing PBS** aged-care programs under Aged Care Services ($41B).

### P1 — Actuals depth + Budget parity

4. Ingest **FBO 2024-25 Appendix A** as audited function/sub-function actuals (related or same budget-family as appropriate).  
5. Map **state/territory budget function tables** from the 8 budget folders already in `data/raw`.  
6. Wire **DSS Age Pension recipient / LGA** series as related (non-summing) under Support for Seniors.  
7. Ingest **NDIS payment datasets** under the NDIS leaf (related / payment measure).

### P1 — History

8. Acquire ABS GFS **previous releases** back as far as machine-readable packs allow.  
9. Acquire **archive.budget.gov.au** FBO + BP1 expense-by-function tables decade by decade toward **1990s / 1980s**.  
10. Extend Finance Note 3 ingestion documentation; it already covers **2005-06+** — don’t confuse with ABS start year.

### P2 — remaining large leaves

11. Defence PBS capability programs.  
12. Education PBS.  
13. Federal AusTender OCDS + GrantConnect as commitment/grant explorers (not function pie children).  
14. DVA PBS for veterans assistance under SSW.

---

## 7. Design constraints (do not “invent” dollars)

From product rules already in force:

- Never mix GFS actuals and budget estimates in one additive pie.  
- Contracts/invoices must not explain whole-of-function totals.  
- Nearest-FY fallback for unpublished component years must stay bannered (2024-25 Actuals → 2025-26 components).

---

## 8. Summary metrics

| Metric | Value |
|---|---|
| Total facts | 258,438 |
| Budget-family facts | 764 |
| ABS GFS earliest FY | 2015-16 |
| Finance Note 3 earliest FY | 2005-06 |
| Budget federal earliest FY | 2024-25 |
| Federal raw folders | 28 |
| State budget folders on disk unused | 8 jurisdictions |
| Support for Seniors deeper on disk? | **Yes** (PBS 1.3.2 / Age Pension) |
| Pre-2005 Commonwealth in DB? | **No** |

---

## Appendix — key file references

- Coverage matrix: `ops/reports/breakdown-coverage-20260723.md`  
- Broader audit: `ops/data-coverage-audit-20260722.md`  
- Research handoff: `ops/research-agent-handoff-20260722.md`  
- DSS PBS pack config: `config/breakdowns/pbs_programs_dss.yaml` (explicitly notes bridge until full PBS OCR)  
- M10 measure mixing lesson: `ops/reports/m10-pdf-pilot.md`
