# AusGov Budget Tracker — Procurement Acquisition Report

Date: 2026-07-22  
Registry: `config/procurement_sources.yaml` (76 sources)  
Reconcile run: `reports/procurement/20260722T063314Z/`  
Disk root: `data/raw/<government_level>/<source_id>/`

---

## Executive summary

| Metric | Value |
|---|---|
| Sources with validated data on disk | **69 / 76** (90.8%) |
| Total assets committed | **2,220 files** |
| Total bytes (reconcile) | **6.13 GB** committed / **6.45 GB** on disk |
| Automated pipeline (`unchanged`) | 37 sources |
| Acquired this acquisition pass (`downloaded`) | 32 sources |
| Not acquired | **7 sources** (see §Gaps) |

Acquisition methods used: direct HTTP/CKAN/OCDS/Socrata APIs, landing-page discovery with Playwright, and manual browser sessions with upload receiver for WAF-blocked sites.

**Policy:** No CAPTCHA solving, header spoofing, or WAF bypass automation. Human may clear challenges in a real browser; cookies/session reused for fetch + upload.

---

## Coverage by government level

| Level | Sources | Assets | Approx. size |
|---|---:|---:|---|
| Federal | 25 | 1,397 | 5.25 GB |
| Cross-level | 2 | 2 | 9.4 MB |
| State | 22 | 673 | 821 MB |
| Territory | 8 | 74 | 15.8 MB |
| Local | 12 | 74 | 40.1 MB |

---

## Coverage by source family

| Source family | Sources on disk | Notes |
|---|---:|---|
| `gfs_actuals` | 18 | ABS GFS annual tables (Commonwealth, all states/territories, all local) |
| `state_budget` | 5 | NSW, QLD, SA, TAS, VIC, WA budget papers |
| `state_actuals` | 5 | NSW/QLD/TAS/WA RSF or equivalent; SA FBO+CFR |
| `territory_budget` | 2 | ACT, NT |
| `territory_actuals` | 3 | ACT publications, NT treasury ARs |
| `local_financial_returns` | 4 | NSW OLG time series, TAS CDC, VIC VGC/ABS packs |
| `local_audit_actuals` | 1 | QLD QAO Local Government 2025 |
| `local_budget` | 1 | VIC council model budgets/reports |
| `procurement_contracts` | 3 | Federal OCDS, NSW buy.nsw, NT awarded |
| `grant_awards` | 1 | GrantConnect quarterly xlsx slices |
| `grant_and_service_payments` | 1 | QLD QGIP expenditure CSVs |
| `portfolio_budget_statements` | 6 | DSS, DVA, Health/NDIA, Social Services archive |
| `recipient_statistics` | 4 | DSS income support, JobSeeker, demographics, LGA |
| `participant_statistics` / `payment_aggregates` / `program_*` | 4 | NDIS datasets and reports |
| `monthly_actuals` | 1 | Commonwealth monthly financial statements |
| `agency_resourcing` / `budget_measures` / `budget_function_program` | 3 | BP1/BP2/BP4 extracts |
| `intergovernmental_transfers` | 1 | BP3 Federal Financial Relations |
| `final_budget_outcome` | 1 | Commonwealth FBO appendix |
| `whole_of_government_actuals` | 1 | Commonwealth CFS 2024-25 |
| `entity_annual_reports` | 2 | Transparency Portal PBS PDFs, Services Australia ARs |
| `invoice_payments` | 1 | ACT Notifiable Invoices Register |

---

## Full catalog — acquired sources (69)

Paths: `data/raw/<level>/<source_id>/latest.json` + `snapshots/`.

### Federal (25)

| ID | Priority | Assets | Size | Family | Method | Title |
|---|---|---:|---:|---|---|---|
| `abs_gfs_commonwealth_130` | P1 | 1 | 74 KB | gfs_actuals | direct_file | ABS Table 130 — Commonwealth general government |
| `federal_agency_resourcing_bp4_2026_27` | P1 | 1 | 6.2 MB | agency_resourcing | direct_file | Budget Paper 4: Agency Resourcing 2026-27 |
| `federal_budget_statement_6_2026_27` | P1 | 1 | 808 KB | budget_function_program | direct_file | BP1 Statement 6: Expenses and Net Capital Investment |
| `federal_dss_pbs_2026_27` | P1 | 1 | — | portfolio_budget_statements | manual | Social Services PBS 2026-27 |
| `federal_dva_pbs_2026_27` | P1 | 1 | — | portfolio_budget_statements | manual | DVA PBS 2026-27 |
| `federal_fbo_2024_25_function_subfunction` | P1 | 1 | 268 KB | final_budget_outcome | direct_file | FBO 2024-25 Appendix A (function/subfunction) |
| `federal_health_disability_ageing_pbs_2026_27` | P1 | 1 | — | portfolio_budget_statements | manual | Health, Disability and Ageing PBS 2026-27 |
| `federal_monthly_financial_statements` | P1 | 10 | 6.5 MB | monthly_actuals | ckan_api | Commonwealth monthly financial statements (data.gov.au) |
| `federal_ndia_pbs_2026_27` | P1 | 1 | — | entity_budget_statement | manual | NDIA PBS 2026-27 |
| `federal_pbs_index_2026_27` | P1 | 2 | 60 KB | portfolio_budget_statements_index | landing_page_discovery | PBS index 2026-27 |
| `federal_social_services_pbs_2025_26_archive` | P1 | 1 | — | portfolio_budget_statements | manual | Social Services PBS 2025-26 (archive) |
| `dss_income_support_monthly` | P2 | 1 | 882 KB | recipient_statistics | ckan_api | DSS Income Support Recipients — monthly |
| `dss_jobseeker_monthly_profile` | P2 | 81 | 16.2 MB | recipient_statistics | ckan_api | JobSeeker / Youth Allowance monthly profile |
| `dss_payment_demographics_quarterly` | P2 | 21 | 2.6 MB | recipient_statistics | ckan_api | DSS payment demographics — quarterly |
| `dss_payments_by_lga` | P2 | 5 | 2.5 MB | recipient_statistics | ckan_api | DSS payments by LGA |
| `federal_austender_ocds_api` | P2 | 18 | 884 MB | procurement_contracts | ocds_api | Historical AusTender contract data (OCDS) |
| `federal_budget_measures_bp2_2026_27` | P2 | 1 | 2.1 MB | budget_measures | direct_file | Budget Paper 2: Budget Measures 2026-27 |
| `federal_cfs_2024_25` | P2 | 1 | — | whole_of_government_actuals | manual | Commonwealth Consolidated Financial Statements 2024-25 |
| `federal_grantconnect` | P2 | 13 | ~35 MB | grant_awards | web_portal + manual | GrantConnect award xlsx (quarterly publish-date slices, Jul 2023–Jul 2026) |
| `federal_transparency_portal` | P2 | 16 | 66 MB | entity_annual_reports | landing_page_discovery | Transparency Portal PBS PDFs |
| `ndis_financial_sustainability_reports` | P2 | 368 | 1.47 GB | program_forecast | landing_page_discovery | NDIS financial sustainability reports |
| `ndis_participant_datasets` | P2 | 233 | 666 MB | participant_statistics | landing_page_discovery | NDIS participant datasets |
| `ndis_payment_datasets` | P2 | 233 | 666 MB | payment_aggregates | landing_page_discovery | NDIS payment datasets |
| `ndis_quarterly_reports` | P2 | 379 | 1.46 GB | program_actuals | landing_page_discovery | NDIS quarterly reports |
| `services_australia_annual_reports` | P2 | 6 | — | entity_annual_reports | manual | Services Australia annual reports |

### Cross-level (2)

| ID | Priority | Assets | Size | Family | Method | Title |
|---|---|---:|---:|---|---|---|
| `abs_gfs_annual_all_workbooks` | P1 | 1 | 4.4 MB | gfs_actuals | direct_file | ABS GFS annual — all workbooks ZIP |
| `federal_financial_relations_bp3_2026_27` | P1 | 1 | 5.0 MB | intergovernmental_transfers | direct_file | Budget Paper 3: Federal Financial Relations 2026-27 |

### State (22)

| ID | Priority | Assets | Size | Family | Method | Title |
|---|---|---:|---:|---|---|---|
| `qld_qgip_expenditure` | P1 | 15 | — | grant_and_service_payments | manual | QLD Government Investment Portal expenditure (all FY CSVs + dictionary) |
| `abs_gfs_state_nsw_231` | P2 | 1 | 69 KB | gfs_actuals | direct_file | ABS Table 231 — NSW state government |
| `abs_gfs_state_qld_233` | P2 | 1 | 72 KB | gfs_actuals | direct_file | ABS Table 233 — QLD state government |
| `abs_gfs_state_sa_234` | P2 | 1 | 71 KB | gfs_actuals | direct_file | ABS Table 234 — SA state government |
| `abs_gfs_state_tas_236` | P2 | 1 | 73 KB | gfs_actuals | direct_file | ABS Table 236 — TAS state government |
| `abs_gfs_state_vic_232` | P2 | 1 | 71 KB | gfs_actuals | direct_file | ABS Table 232 — VIC state government |
| `abs_gfs_state_wa_235` | P2 | 1 | 69 KB | gfs_actuals | direct_file | ABS Table 235 — WA state government |
| `nsw_budget_2026_27` | P2 | 13 | 57 MB | state_budget | landing_page_discovery | NSW Budget Papers 2026-27 |
| `nsw_budget_open_data_2026_27` | P2 | 16 | 28 MB | state_budget_open_data | landing_page_discovery | NSW Budget 2026-27 Open Data |
| `nsw_report_on_state_finances` | P2 | 24 | 93 MB | state_actuals | landing_page_discovery | NSW Report on State Finances |
| `qld_budget_2026_27` | P2 | 50 | 73 MB | state_budget | landing_page_discovery | Queensland Budget Papers 2026-27 |
| `qld_report_on_state_finances` | P2 | 187 | 139 MB | state_actuals | landing_page_discovery | Queensland Report on State Finances |
| `sa_budget_2026_27` | P2 | 8 | — | state_budget | manual | SA Budget 2026-27 |
| `sa_final_budget_outcome_and_cfr` | P2 | 2 | — | state_actuals | manual | SA FBO + Consolidated Financial Report 2024-25 |
| `tas_budget_2026_27` | P2 | 40 | 77 MB | state_budget | landing_page_discovery | Tasmanian Budget 2026-27 |
| `tas_treasurers_annual_financial_reports` | P2 | 89 | 180 MB | state_actuals | landing_page_discovery | Treasurer's Annual Financial Reports (TAS) |
| `vic_budget_2026_27` | P2 | 8 | — | state_budget | manual | Victorian State Budget 2026-27 |
| `vic_dtf_annual_report_bpo` | P2 | 7 | — | entity_actuals | manual | DTF Annual Report + Budget Portfolio Outcomes |
| `vic_financial_report_2024_25` | P2 | 1 | — | state_actuals | manual | Victoria Financial Report 2024-25 |
| `wa_annual_report_state_finances_2024_25` | P2 | 99 | 109 MB | state_actuals | landing_page_discovery | WA Annual Report on State Finances 2024-25 |
| `wa_budget_2026_27` | P2 | 106 | 65 MB | state_budget | landing_page_discovery | WA Budget Papers 2026-27 |
| `nsw_buy_register` | P4 | 2 | ~13 MB | procurement_contracts | manual | buy.nsw notice-report CSVs (contract awards + standing offers, 2020–2026) |

### Territory (8)

| ID | Priority | Assets | Size | Family | Method | Title |
|---|---|---:|---:|---|---|---|
| `act_notifiable_invoices` | P1 | 1 | 15.7 MB | invoice_payments | socrata_api | ACT Notifiable Invoices Register |
| `nt_awarded_government_contracts` | P1 | 1 | — | procurement_contracts | direct_file | NT awarded contracts (date-bounded ExportTenderers xlsx) |
| `abs_gfs_state_act_238` | P2 | 1 | 72 KB | gfs_actuals | direct_file | ABS Table 238 — ACT |
| `abs_gfs_state_nt_237` | P2 | 1 | 71 KB | gfs_actuals | direct_file | ABS Table 237 — NT |
| `act_actual_financial_publications` | P2 | 1 | — | territory_actuals | manual | ACT Treasury financial publications |
| `act_budget_2026_27` | P2 | 23 | — | territory_budget | manual | ACT Budget Papers and Statements 2026-27 |
| `nt_budget_2026_27` | P2 | 1 | — | territory_budget | manual | NT Budget Papers 2026-27 |
| `nt_treasury_annual_reports` | P2 | 45 | — | territory_actuals | manual | NT Treasury annual reports |

### Local (12)

| ID | Priority | Assets | Size | Family | Method | Title |
|---|---|---:|---:|---|---|---|
| `nsw_local_olg_time_series` | P1 | 31 | 40 MB | local_financial_returns | landing_page_discovery | NSW OLG council data time series |
| `tas_local_cdc` | P1 | 2 | 30 MB | local_financial_returns | manual | TAS LGA CDC data repository zips (2000–2015, 2015–2025) |
| `vic_local_vgc_abs_returns` | P1 | 11 | — | local_financial_returns | manual | VIC council VGC/ABS raw data packs |
| `abs_gfs_local_nsw_331` | P1 | 1 | 71 KB | gfs_actuals | direct_file | ABS Table 331 — NSW local government |
| `abs_gfs_local_nt_337` | P1 | 1 | 73 KB | gfs_actuals | direct_file | ABS Table 337 — NT local government |
| `abs_gfs_local_qld_333` | P1 | 1 | 69 KB | gfs_actuals | direct_file | ABS Table 333 — QLD local government |
| `abs_gfs_local_sa_334` | P1 | 1 | 71 KB | gfs_actuals | direct_file | ABS Table 334 — SA local government |
| `abs_gfs_local_tas_336` | P1 | 1 | 71 KB | gfs_actuals | direct_file | ABS Table 336 — TAS local government |
| `abs_gfs_local_vic_332` | P1 | 1 | 70 KB | gfs_actuals | direct_file | ABS Table 332 — VIC local government |
| `abs_gfs_local_wa_335` | P1 | 1 | 70 KB | gfs_actuals | direct_file | ABS Table 335 — WA local government |
| `qld_local_qao_2025` | P2 | 13 | ~11 MB | local_audit_actuals | manual | QLD QAO Local Government 2025 report + appendices A–K |
| `vic_local_budget_and_reporting_models` | P3 | 10 | — | local_budget | manual | VIC council model budget/report workbooks |

---

## Acquisition methods breakdown

| Method | Sources | Description |
|---|---:|---|
| `direct_file` | 20 | Known stable URLs (ABS, budget.gov.au) |
| `ckan_api` / `ocds_api` / `socrata_api` | 7 | Open-data APIs (data.gov.au, ACT Open Data, AusTender OCDS) |
| `landing_page_discovery` | 24 | Automated crawl + Playwright for JS portals |
| `manual` / `web_portal` | 18 | Human browser session + upload receiver (`127.0.0.1:8765`) |

### Manual / browser-acquired highlights (2026-07-22 pass)

- **Cloudflare:** ACT budget/publications, NT budget/ARs, SA budget/FBO
- **Section.io:** VIC budget, financial report, DTF annual/BPO (also direct S3/file paths)
- **CloudFront:** NSW buy.nsw notice reports, GrantConnect award exports
- **AWS WAF:** QLD QGIP expenditure CSVs (all financial years)
- **Stream reset:** Commonwealth PBS PDFs, CFS, Services Australia ARs
- **Direct open data:** TAS CDC zips from LIST, VIC budget PDFs from public S3

---

## Gaps — not acquired (7 sources)

| ID | Status | Why | Alternative already on disk |
|---|---|---|---|
| `federal_austender_weekly_export` | no_public_bulk_export | data.gov.au weekly CSV abandoned ~2013 | `federal_austender_ocds_api` (884 MB OCDS) |
| `nt_local_grants_commission_return` | no_public_bulk_export | Council submission/login portal, no public dump | `abs_gfs_local_nt_337` (aggregate GFS only) |
| `wa_mycouncil` | no_public_bulk_export | Interactive portal; data.wa.gov.au catalogue has no files | `abs_gfs_local_wa_335` |
| `wa_tenders` | no_public_bulk_export | Struts search portal; ~30-day HTML table, no export | — |
| `sa_councils_in_focus` | manual_required | Cloudflare block + dashboard-only (no CSV) | `abs_gfs_local_sa_334`; LGGC PDFs on dit.sa.gov.au |
| `sa_tenders_contracts` | manual_required | Cloudflare block + agency-by-agency browse | — |
| `tas_procurement` | discovered_only | 18 URLs found on landing page, 0 bytes downloaded | — |

---

## Completeness caveats (acquired but partial)

| Source | Caveat |
|---|---|
| `nt_awarded_government_contracts` | Full unbounded export times out; stored file is date-bounded |
| `nsw_buy_register` | Two notice types (`can`, `son`) for 2020-01-01–2026-07-22; other types/windows available |
| `federal_grantconnect` | Quarterly publish-date slices only; 50k row cap per query; pre-2023 quarters not yet pulled |
| `qld_local_qao_2025` | Report PDFs only; interactive dashboard has no bulk export |
| `vic_local_vgc_abs_returns` | Latest years imported; older year packs still on LGV site |
| Manual imports with `0 B` in reconcile | Files on disk; byte counts not backfilled in reconcile CSV for manual runs |

---

## Storage layout

```
data/raw/<government_level>/<source_id>/
  latest.json              # merged asset manifest (run_id, updated_at, assets[])
  snapshots/
    <run_id>/
      files/               # downloaded bytes
      headers/             # HTTP metadata where captured

data/manual_inbox/_downloads/   # staging for browser uploads
  <source_id>__<filename>       # multi-file convention
  <source_id>__<filename>.url   # provenance sidecar
```

Key scripts: `scripts/procure_sources.py`, `scripts/procure_manual_import.py`, `scripts/procure_manual_import_batch.py`, `scripts/procure_acquisition_queue.py`, `scripts/procure_reconcile.py`, `scripts/procure_upload_receiver.py`, `scripts/procure_browser_session.py`.

---

## Re-check commands

```bash
conda activate ausgov-budget-tracker
cd ausgov-budget-tracker
python scripts/procure_acquisition_queue.py
python scripts/procure_reconcile.py
```
