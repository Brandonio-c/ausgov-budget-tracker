# AusGov Budget Tracker — Data Sources Catalogue

**Generated:** 2026-07-23  
**Authoritative machine registry:** [`config/procurement_sources.yaml`](../config/procurement_sources.yaml)  
**Published facts:** `data/facts.db` → `source_documents`  
**Raw assets:** `data/raw/{federal,state,territory,local,cross_level}/<source_id>/`  

Catalogue of **what sources we have**, **where they came from**, and **what they inform**.

## Summary

| Metric | Count |
|---|---:|
| Registry sources | 90 |
| With non-empty raw files | 88 |
| With rows in facts.db | 29 |

| Status | Meaning |
|---|---|
| **In facts** | Parsed into `facts.db` |
| **On disk only** | Under `data/raw` but not ingested |
| **Registered only** | Registry entry; empty or blocked acquisition |

## Quick index

| ID | Level | Jurisdiction | Status | Priority | Informs (short) | Size |
|---|---|---|---|---|---|---|
| `abs_gfs_commonwealth_130` | federal | Commonwealth | In facts | P1 | Federal Actuals COFOG purpose tree | 156 KB |
| `dss_income_support_monthly` | federal | Commonwealth | On disk only | P2 | DSS Income Support Recipients - Monthly Time Series | 917 KB |
| `dss_jobseeker_monthly_profile` | federal | Commonwealth | On disk only | P2 | DSS JobSeeker Payment and Youth Allowance recipients - monthly profile | 17.1 MB |
| `dss_payment_demographics_quarterly` | federal | Commonwealth | On disk only | P2 | DSS Benefit and Payment Recipient Demographics - quarterly data | 3.6 MB |
| `dss_payments_by_lga` | federal | Commonwealth | On disk only | P2 | DSS Payments by Local Government Area | 2.6 MB |
| `federal_agency_resourcing_bp4_2026_27` | federal | Commonwealth | On disk only | P1 | Budget Paper No. 4: Agency Resourcing 2026-27 | 5.9 MB |
| `federal_austender_ocds_api` | federal | Commonwealth | On disk only | P2 | Historical Australian Government Contract Notice Data - OCDS API | 845.4 MB |
| `federal_austender_weekly_export` | federal | Commonwealth | On disk only | P2 | AusTender Contract Notice Export | 65 KB |
| `federal_budget_archive_function_series` | federal | Commonwealth | On disk only | P1 | Historical FBO / budget PDFs for function series + pre-FBO OCR candidates | 240.8 MB |
| `federal_budget_measures_bp2_2026_27` | federal | Commonwealth | On disk only | P2 | Budget Paper No. 2: Budget Measures 2026-27 | 2.0 MB |
| `federal_budget_statement_11_historical` | federal | Commonwealth | On disk only | P2 | Whole-of-government fiscal aggregates (Statement 11) | 651 KB |
| `federal_budget_statement_6_2026_27` | federal | Commonwealth | In facts | P1 | Budget Paper No. 1, Statement 6: Expenses and Net Capital Investment 2026-27 | 797 KB |
| `federal_cfs_2024_25` | federal | Commonwealth | On disk only | P2 | Commonwealth Consolidated Financial Statements 2024-25 | 59.6 MB |
| `federal_defence_pbs_2026_27` | federal | Commonwealth | On disk only | P2 | Defence PBS outcome/program detail (manual — blocked from server) | 306 B |
| `federal_dss_pbs_2026_27` | federal | Commonwealth | On disk only | P1 | Full DSS PBS PDF — Age Pension / program components | 3.1 MB |
| `federal_dva_pbs_2026_27` | federal | Commonwealth | On disk only | P1 | Department of Veterans' Affairs Portfolio Budget Statements 2026-27 | 1.8 MB |
| `federal_education_pbs_2026_27` | federal | Commonwealth | Registered only | P2 | Education PBS outcome/program detail (manual — blocked from server) | — |
| `federal_expense_by_function` | federal | Commonwealth | In facts | P0 | Australian Government GGS Monthly Financial Statements - Note 3 Function Stateme | 107 KB |
| `federal_fbo_2024_25_function_subfunction` | federal | Commonwealth | On disk only | P1 | Final Budget Outcome 2024-25, Appendix A: Expenses by function and sub-function | 271 KB |
| `federal_grantconnect` | federal | Commonwealth | On disk only | P2 | GrantConnect grant opportunities and awards | 34.0 MB |
| `federal_health_disability_ageing_pbs_2026_27` | federal | Commonwealth | On disk only | P1 | Health, Disability and Ageing Portfolio Budget Statements 2026-27 | 3.8 MB |
| `federal_historical_cn_data_1999_2020` | federal | Commonwealth | On disk only | P3 | Historical Australian Government Contract Notice data, 1999-2020 | 746.3 MB |
| `federal_monthly_financial_statements` | federal | Commonwealth | In facts | P1 | Australian Government General Government Sector Monthly Financial Statements - t | 6.5 MB |
| `federal_ndia_pbs_2026_27` | federal | Commonwealth | On disk only | P1 | National Disability Insurance Agency Portfolio Budget Statements 2026-27 | 415 KB |
| `federal_pbs_index_2026_27` | federal | Commonwealth | On disk only | P1 | Portfolio Budget Statements index 2026-27 | 1.4 MB |
| `federal_social_services_pbs_2025_26_archive` | federal | Commonwealth | On disk only | P1 | Social Services Portfolio Budget Statements 2025-26 | 3.9 MB |
| `federal_transparency_portal` | federal | Commonwealth | On disk only | P2 | Transparency Portal - Commonwealth annual reports and data | 63.2 MB |
| `ndis_financial_sustainability_reports` | federal | Commonwealth | On disk only | P2 | NDIS annual financial sustainability reports | 1.38 GB |
| `ndis_participant_datasets` | federal | Commonwealth | On disk only | P2 | NDIS participant datasets | 643.6 MB |
| `ndis_payment_datasets` | federal | Commonwealth | On disk only | P2 | NDIS payments datasets | 643.4 MB |
| `ndis_quarterly_reports` | federal | Commonwealth | On disk only | P2 | NDIS quarterly reports | 1.37 GB |
| `services_australia_annual_reports` | federal | Commonwealth | On disk only | P2 | Services Australia annual reports | 21.4 MB |
| `abs_gfs_state_nsw_231` | state | NSW | In facts | P2 | Table 231. General government - state - New South Wales | 78 KB |
| `nsw_budget_2026_27` | state | NSW | On disk only | P2 | NSW Budget Papers 2026-27 | 57.5 MB |
| `nsw_budget_open_data_2026_27` | state | NSW | On disk only | P2 | NSW Budget 2026-27 Open Data | 27.6 MB |
| `nsw_buy_register` | state | NSW | On disk only | P4 | buy.nsw register of notices | 7.4 MB |
| `nsw_procurement_ocds_registry` | state | NSW | In facts | P1 | NSW Government procurement — OCDS bulk data | 61.9 MB |
| `nsw_report_on_state_finances` | state | NSW | On disk only | P2 | NSW Report on State Finances | 89.7 MB |
| `abs_gfs_state_qld_233` | state | QLD | In facts | P2 | Table 233. General government - state - Queensland | 80 KB |
| `qld_budget_2026_27` | state | QLD | On disk only | P2 | Queensland Budget Papers 2026-27 | 70.6 MB |
| `qld_contract_disclosure_agency_datasets` | state | QLD | In facts | P1 | Queensland Government agency Contract Disclosure Reports | 317.0 MB |
| `qld_on_time_payment_reports` | state | QLD | On disk only | P2 | Queensland Government On-Time Payment Reports | 209 KB |
| `qld_qgip_expenditure` | state | QLD | In facts | P1 | Queensland Government Investment Portal expenditure data - consolidated view | 199.9 MB |
| `qld_report_on_state_finances` | state | QLD | On disk only | P2 | Queensland Report on State Finances | 137.3 MB |
| `abs_gfs_state_sa_234` | state | SA | In facts | P2 | Table 234. General government - state - South Australia | 79 KB |
| `sa_budget_2026_27` | state | SA | On disk only | P2 | South Australia Budget 2026-27 | 39.2 MB |
| `sa_final_budget_outcome_and_cfr` | state | SA | On disk only | P2 | South Australia Final Budget Outcome and Consolidated Financial Report | 11.3 MB |
| `sa_gfs_by_function` | state | SA | In facts | P0 | SA GFS expenses by function and by economic type | 84 KB |
| `sa_tenders_contracts` | state | SA | On disk only | P4 | SA Tenders and Contracts | 2 KB |
| `abs_gfs_state_tas_236` | state | TAS | In facts | P2 | Table 236. General government - state - Tasmania | 82 KB |
| `tas_budget_2026_27` | state | TAS | On disk only | P2 | Tasmanian Budget 2026-27 | 77.0 MB |
| `tas_procurement` | state | TAS | On disk only | P4 | Tasmanian purchasing and eTendering | 610 KB |
| `tas_treasurers_annual_financial_reports` | state | TAS | On disk only | P2 | Treasurer's Annual Financial Reports | 166.2 MB |
| `abs_gfs_state_vic_232` | state | VIC | In facts | P2 | Table 232. General government - state - Victoria | 79 KB |
| `vic_budget_2026_27` | state | VIC | On disk only | P2 | Victorian State Budget 2026-27 | 23.8 MB |
| `vic_dtf_annual_report_bpo` | state | VIC | On disk only | P2 | DTF Annual Report and Budget Portfolio Outcomes | 9.5 MB |
| `vic_financial_report_2024_25` | state | VIC | On disk only | P2 | Victoria Financial Report 2024-25 | 9.1 MB |
| `abs_gfs_state_wa_235` | state | WA | In facts | P2 | Table 235. General government - state - Western Australia | 77 KB |
| `wa_annual_report_state_finances_2024_25` | state | WA | On disk only | P2 | Western Australia Annual Report on State Finances 2024-25 | 107.4 MB |
| `wa_budget_2026_27` | state | WA | On disk only | P2 | Western Australia Budget Papers 2026-27 | 64.1 MB |
| `wa_tenders` | state | WA | On disk only | P4 | Tenders WA awarded contracts | 5 KB |
| `abs_gfs_state_act_238` | territory | ACT | In facts | P2 | Table 238. General government - state - Australian Capital Territory | 81 KB |
| `act_actual_financial_publications` | territory | ACT | On disk only | P2 | ACT Treasury financial publications | 807 KB |
| `act_budget_2026_27` | territory | ACT | On disk only | P2 | ACT Budget Papers and Statements 2026-27 | 21.6 MB |
| `act_notifiable_invoices` | territory | ACT | In facts | P1 | Notifiable Invoices Register | 15.2 MB |
| `abs_gfs_state_nt_237` | territory | NT | In facts | P2 | Table 237. General government - state - Northern Territory | 79 KB |
| `nt_awarded_government_contracts` | territory | NT | In facts | P1 | Awarded government contracts | 283 KB |
| `nt_budget_2026_27` | territory | NT | On disk only | P2 | Northern Territory Budget Papers 2026-27 | 4.2 MB |
| `nt_treasury_annual_reports` | territory | NT | On disk only | P2 | Northern Territory Treasury annual reports | 160.3 MB |
| `abs_gfs_local_nsw_331` | local | NSW | In facts | P1 | Table 331. General government - local - New South Wales | 80 KB |
| `nsw_local_olg_time_series` | local | NSW | In facts | P1 | Your council data and reports - time series | 39.2 MB |
| `abs_gfs_local_nt_337` | local | NT | In facts | P1 | Table 337. General government - local - Northern Territory | 83 KB |
| `nt_grants_commission_annual_reports` | local | NT | Registered only | P3 | NT Grants Commission Annual Reports (council allocation and population schedules | — |
| `nt_local_grants_commission_return` | local | NT | On disk only | P4 | Northern Territory Grants Commission Annual Return | 5 KB |
| `abs_gfs_local_qld_333` | local | QLD | In facts | P1 | Table 333. General government - local - Queensland | 79 KB |
| `qld_local_qao_2025` | local | QLD | On disk only | P2 | Local government 2025 report and dashboard | 12.4 MB |
| `abs_gfs_local_sa_334` | local | SA | In facts | P1 | Table 334. General government - local - South Australia | 79 KB |
| `sa_councils_in_focus` | local | SA | On disk only | P1 | Councils in Focus | 2 KB |
| `sa_lggc_council_database_reports` | local | SA | On disk only | P2 | SA LGGC Database Reports (council financial and general data) | 1 KB |
| `abs_gfs_local_tas_336` | local | TAS | In facts | P1 | Table 336. General government - local - Tasmania | 79 KB |
| `tas_local_cdc` | local | TAS | In facts | P1 | Council performance and Consolidated Data Collection | 28.9 MB |
| `abs_gfs_local_vic_332` | local | VIC | In facts | P1 | Table 332. General government - local - Victoria | 79 KB |
| `vic_local_budget_and_reporting_models` | local | VIC | On disk only | P3 | Council planning, budget and annual reporting guidance and models | 26.1 MB |
| `vic_local_govt_financial` | local | VIC | In facts | P0 | VAGO Local Government dashboard data | 771 KB |
| `vic_local_vgc_abs_returns` | local | VIC | In facts | P1 | Council raw VGC and ABS data packs | 3.3 MB |
| `abs_gfs_local_wa_335` | local | WA | In facts | P1 | Table 335. General government - local - Western Australia | 78 KB |
| `wa_mycouncil` | local | WA | On disk only | P1 | MyCouncil local government information and comparison | 1.2 MB |
| `abs_gfs_annual_all_workbooks` | cross_level | Australia | On disk only | P1 | Government Finance Statistics, Annual - all workbooks | 4.2 MB |
| `abs_gfs_previous_releases` | cross_level | Australia | On disk only | P1 | Historical ABS GFS workbooks (backfill; extends Actuals history) | 23.6 MB |
| `federal_financial_relations_bp3_2026_27` | cross_level | Commonwealth and states | On disk only | P1 | Budget Paper No. 3: Federal Financial Relations 2026-27 | 4.8 MB |
| `federal_budget_statement_6_a61` | (facts only) | — | In facts | — | Budget mode Statement 6 A.6.1 | — |
| `federal_budget_statement_6_components` | (facts only) | — | In facts | — | Budget mode Statement 6 components | — |
| `federal_dss_pbs_programs` | (facts only) | — | In facts | — | SSW Top-20 program bridge | — |
| `federal_health_pbs_programs` | (facts only) | — | In facts | — | Health Top-20 program bridge | — |
| `sa_budget_headline_expenses` | (facts only) | — | In facts | — | sa_budget_headline_expenses | — |
| `synthetic_demo` | (facts only) | — | In facts | — | synthetic_demo | — |

## New acquisitions (2026-07-23)

See [`ops/reports/missing-data-acquisition-20260723.md`](reports/missing-data-acquisition-20260723.md).

### `federal_budget_statement_11_historical`

- **Title:** Statement 11: Historical Australian Government Data
- **Publisher:** Australian Government Treasury
- **Status:** On disk only
- **Where from:** https://budget.gov.au/content/bp1/index.htm
- **Resource URL:** https://budget.gov.au/content/bp1/download/bp1_bs-11.pdf
- **Informs:** Whole-of-government fiscal aggregates (Statement 11)
- **Raw path:** `data/raw/federal/federal_budget_statement_11_historical/` · 3 files · 651 KB
- **Caveat:** Fiscal-aggregate history only — no function/sub-function breakdown for COFOG drill-down.
- **Caveat:** Use for whole-of-government context and top-level reconciliation, not expense-by-function trees.

### `abs_gfs_previous_releases`

- **Title:** Government Finance Statistics, Annual — previous releases (2007-08 through 2023-24)
- **Publisher:** Australian Bureau of Statistics
- **Status:** On disk only
- **Where from:** https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/latest-release
- **Informs:** Historical ABS GFS workbooks (backfill; extends Actuals history)
- **Raw path:** `data/raw/cross_level/abs_gfs_previous_releases/` · 12 files · 23.6 MB
- **Caveat:** AGFS15 classification changes effective 1 July 2017 create a basis break; do not treat pre/post 2017-18 as one continuous unadjusted series.
- **Caveat:** 2024-25 release remains under abs_gfs_annual_all_workbooks / abs_gfs_* table ids.
- **Caveat:** Pre-2017 AUSSTATS subscriber.nsf download links currently return Attachment Not Found (2026-07-23).

### `federal_budget_archive_function_series`

- **Title:** Historical Final Budget Outcome Appendix A (expenses by function and sub-function), 1996-97 to present
- **Publisher:** Australian Government Treasury / Department of Finance
- **Status:** On disk only
- **Where from:** https://archive.budget.gov.au/
- **Informs:** Historical FBO / budget PDFs for function series + pre-FBO OCR candidates
- **Raw path:** `data/raw/federal/federal_budget_archive_function_series/` · 42 files · 240.8 MB
- **Caveat:** Function/sub-function classification changed across this span; treat pre-and-post reclassification years as requiring a documented bridge.
- **Caveat:** 1983-84 through 1995-96 predates FBO Appendix A and needs OCR for ingest later.
- **Caveat:** 2024-25 Appendix A already acquired as federal_fbo_2024_25_function_subfunction.

### `federal_defence_pbs_2026_27`

- **Title:** Portfolio Budget Statements 2026-27, Budget Related Paper No. 1.4A (Defence)
- **Publisher:** Australian Government Department of Defence
- **Status:** On disk only
- **Where from:** https://www.defence.gov.au/about/accessing-information/budgets/budget-2026-27
- **Resource URL:** https://www.defence.gov.au/sites/default/files/2026-05/Defence-Portfolio-Budget-Statements-2026-27.pdf
- **Informs:** Defence PBS outcome/program detail (manual — blocked from server)
- **Raw path:** `data/raw/federal/federal_defence_pbs_2026_27/` · 1 files · 306 B
- **Caveat:** Capability acquisition program detail (e.g. AUKUS/Nuclear-Powered Submarines) sits below program level and may need a further drill-down source.
- **Caveat:** Server-side HTTP/2 stream-reset and landing-page timeout from this host (2026-07-23); same class as DSS PBS. Use procure_browser_session.py from an interactive session.

### `federal_education_pbs_2026_27`

- **Title:** Portfolio Budget Statements 2026-27, Budget Related Paper No. 1.5 (Education)
- **Publisher:** Australian Government Department of Education
- **Status:** Registered only
- **Where from:** https://www.education.gov.au/about-department/resources/202627-education-portfolio-budget-statements
- **Resource URL:** https://www.education.gov.au/download/20342/2026-27-education-portfolio-budget-statements/44709/2026-27-education-portfolio-budget-statements/pdf
- **Informs:** Education PBS outcome/program detail (manual — blocked from server)
- **Caveat:** education.gov.au hangs from server fetch (2026-07-23); browser session required.

### `nt_grants_commission_annual_reports`

- **Title:** NT Grants Commission Annual Reports (council allocation and population schedules)
- **Publisher:** NT Department of Housing, Local Government and Community Development
- **Status:** Registered only
- **Where from:** https://dhlgcd.nt.gov.au/local-government/local-government-funding/grants-commission
- **Informs:** NT Grants Commission Annual Reports (council allocation and population schedules)
- **Caveat:** Contains allocation outputs and population, not underlying council financial return line items.
- **Caveat:** Partial substitute for nt_local_grants_commission_return.
- **Caveat:** dhlgcd.nt.gov.au behind Cloudflare; browser session likely required.

## Related docs

- [`config/procurement_sources.yaml`](../config/procurement_sources.yaml)
- [`ops/reports/missing-data-acquisition-20260723.md`](reports/missing-data-acquisition-20260723.md)
- [`ops/reports/missing-data-exhaustive-20260723.md`](reports/missing-data-exhaustive-20260723.md)
