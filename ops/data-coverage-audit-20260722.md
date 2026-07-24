# AusGov Budget Tracker — Data Coverage Audit

**Generated:** 2026-07-22T23:10:34.354467Z
**Purpose:** Exhaustive inventory of holdings under `data/` for federal / state / territory / local, with year coverage where detectable, plus what the live website currently serves.

Companion: `ops/research-ingestion-handoff-20260722.md` (pipeline analysis + research brief).

---

## 1. Headline totals

| Metric | Value |
|---|---:|
| Raw corpus on disk | **8.1 GB** |
| Sources with `latest.json` / Phase 1 raw | **76** |
| Assets in latest.json (approx) | **2,541** |
| Disk files under source trees | **9,184** |
| Procurement registry entries | **82** |
| Phase 1 website registry entries | **3** |
| Sources ingested to website DB | **3** |
| Acquired but NOT on website | **73 sources / 8.099 GB** |
| Website `spending.db` rows | **3,974** |

> **Critical:** ~**99.99%** of acquired bytes are **not** in `spending.db`. The live dashboard only shows the 3 Phase 1 parsers.

### By government level (acquired raw)

| Level | Sources | Assets | Files | Size |
|---|---:|---:|---:|---:|
| federal | 27 | 1413 | 4779 | 6.212 GB |
| state | 26 | 977 | 3888 | 1.55 GB |
| territory | 8 | 74 | 155 | 0.212 GB |
| local | 13 | 75 | 319 | 0.117 GB |
| cross_level | 2 | 2 | 43 | 0.009 GB |

---

## 2. Website-served data (`data/processed/spending.db`) — authoritative years

This is what [vibefactory.app/ausgov-budget-tracker](https://vibefactory.app/ausgov-budget-tracker/) actually displays today.

**Schema columns:** `id, financial_year, level_of_government, jurisdiction, category, subcategory, department, amount_aud, source_document_name, source_url, retrieved_at, source_context_json`

**Source-context JSON keys (traceability):** `source_type, sheet_name, cell_range, columns, rows, highlight, unit, note`

### 2.1 Federal (Commonwealth) — GGS expense by function

| Financial year | Rows | Amount (AUD, as stored) |
|---|---:|---:|
| 2005-06 | 19 | $190.03B |
| 2006-07 | 19 | $204.26B |
| 2007-08 | 19 | $253.16B |
| 2008-09 | 18 | $285.92B |
| 2009-10 | 18 | $303.75B |
| 2010-11 | 18 | $318.10B |
| 2011-12 | 18 | $331.79B |
| 2012-13 | 18 | $343.50B |
| 2013-14 | 18 | $370.30B |
| 2014-15 | 18 | $376.50B |
| 2015-16 | 18 | $388.06B |
| 2016-17 | 18 | $405.33B |
| 2017-18 | 18 | $416.90B |
| 2018-19 | 18 | $436.83B |
| 2019-20 | 18 | $512.13B |
| 2020-21 | 18 | $590.67B |
| 2021-22 | 18 | $559.02B |
| 2022-23 | 18 | $568.65B |
| 2023-24 | 18 | $610.72B |
| 2024-25 | 18 | $664.60B |
| 2025-26 | 18 | $724.90B |

**Source document:** Dept of Finance Note 3 Function Statement (xlsx). **Jurisdiction:** Commonwealth only. **Years:** 2005-06 → 2025-26 (21 years).

### 2.2 State — South Australia GFS

| Financial year | Rows | Amount |
|---|---:|---:|
| 2012-13 | 535 | $16.28B |
| 2013-14 | 451 | $16.41B |
| 2014-15 | 443 | $16.74B |
| 2015-16 | 464 | $17.06B |

**Jurisdiction:** SA only. **Years:** 2012-13 → 2015-16 (4 years). No other states on the website.

### 2.3 Local — Victorian councils (VAGO)

| Financial year | Council entities (incl. averages) | Rows | Amount (sum of entities) |
|---|---:|---:|---:|
| 2014-15 | 85 | 340 | $8.22B |
| 2015-16 | 85 | 340 | $8.41B |
| 2016-17 | 85 | 340 | $8.77B |
| 2017-18 | 85 | 340 | $9.18B |
| 2018-19 | 85 | 340 | $9.70B |

**Years:** 2014-15 → 2018-19 (5 years). ~85 VIC councils + sector averages per year. No NSW/QLD/SA/WA/TAS/NT local on website.

### 2.4 Territory

**Nothing on the website.** Territory data exists only in the acquisition corpus.

---

## 3. Federal — acquired corpus (mostly NOT on website)

**27 sources · 1413 assets · 6.212 GB**

**Formats on disk:** `.pdf`×813, `.xlsx`×205, `.csv`×195, `.docx`×165, `.zip`×19, `.xls`×8, `.doc`×4, `.cs`×2, `.htm`×2, `.json`×0, `.part`×0

| On site? | Priority | Size | Assets | Family | Jurisdiction | Source ID | Title |
|---|---|---:|---:|---|---|---|---|
| no | P2 | 1477.6 MB | 368 | `program_forecast` | Commonwealth | `ndis_financial_sustainability_reports` | NDIS annual financial sustainability reports |
| no | P2 | 1471.2 MB | 379 | `program_actuals` | Commonwealth | `ndis_quarterly_reports` | NDIS quarterly reports |
| no | P2 | 886.5 MB | 18 | `procurement_contracts` | Commonwealth | `federal_austender_ocds_api` | Historical Australian Government Contract Notice Data - OCDS API |
| no | P3 | 782.6 MB | 15 | `procurement_contracts` | Commonwealth | `federal_historical_cn_data_1999_2020` | Historical Australian Government Contract Notice data, 1999-2020 |
| no | P2 | 675.1 MB | 233 | `participant_statistics` | Commonwealth | `ndis_participant_datasets` | NDIS participant datasets |
| no | P2 | 675.0 MB | 233 | `payment_aggregates` | Commonwealth | `ndis_payment_datasets` | NDIS payments datasets |
| no | P2 | 66.3 MB | 16 | `entity_annual_reports` | Commonwealth | `federal_transparency_portal` | Transparency Portal - Commonwealth annual reports and data |
| no | P2 | 62.5 MB | 1 | `whole_of_government_actuals` | Commonwealth | `federal_cfs_2024_25` | Commonwealth Consolidated Financial Statements 2024-25 |
| no | P2 | 35.7 MB | 13 | `grant_awards` | Commonwealth | `federal_grantconnect` | GrantConnect grant opportunities and awards |
| no | P2 | 22.5 MB | 6 | `entity_annual_reports` | Commonwealth | `services_australia_annual_reports` | Services Australia annual reports |
| no | P2 | 18.1 MB | 81 | `recipient_statistics` | Commonwealth | `dss_jobseeker_monthly_profile` | DSS JobSeeker Payment and Youth Allowance recipients - monthly profile |
| no | P1 | 6.8 MB | 10 | `monthly_actuals` | Commonwealth | `federal_monthly_financial_statements` | Australian Government General Government Sector Monthly Financial Statements - tables and  |
| no | P1 | 6.2 MB | 1 | `agency_resourcing` | Commonwealth | `federal_agency_resourcing_bp4_2026_27` | Budget Paper No. 4: Agency Resourcing 2026-27 |
| no | P1 | 4.1 MB | 1 | `portfolio_budget_statements` | Commonwealth | `federal_social_services_pbs_2025_26_archive` | Social Services Portfolio Budget Statements 2025-26 |
| no | P1 | 4.0 MB | 1 | `portfolio_budget_statements` | Commonwealth | `federal_health_disability_ageing_pbs_2026_27` | Health, Disability and Ageing Portfolio Budget Statements 2026-27 |
| no | P2 | 3.8 MB | 21 | `recipient_statistics` | Commonwealth | `dss_payment_demographics_quarterly` | DSS Benefit and Payment Recipient Demographics - quarterly data |
| no | P1 | 3.2 MB | 1 | `portfolio_budget_statements` | Commonwealth | `federal_dss_pbs_2026_27` | Social Services Portfolio Budget Statements 2026-27 |
| no | P2 | 2.7 MB | 5 | `recipient_statistics` | Commonwealth | `dss_payments_by_lga` | DSS Payments by Local Government Area |
| no | P2 | 2.1 MB | 1 | `budget_measures` | Commonwealth | `federal_budget_measures_bp2_2026_27` | Budget Paper No. 2: Budget Measures 2026-27 |
| no | P1 | 1.9 MB | 1 | `portfolio_budget_statements` | Commonwealth | `federal_dva_pbs_2026_27` | Department of Veterans' Affairs Portfolio Budget Statements 2026-27 |
| no | P1 | 1.5 MB | 2 | `portfolio_budget_statements_index` | Commonwealth | `federal_pbs_index_2026_27` | Portfolio Budget Statements index 2026-27 |
| no | P2 | 0.9 MB | 1 | `recipient_statistics` | Commonwealth | `dss_income_support_monthly` | DSS Income Support Recipients - Monthly Time Series |
| no | P1 | 0.8 MB | 1 | `budget_function_program` | Commonwealth | `federal_budget_statement_6_2026_27` | Budget Paper No. 1, Statement 6: Expenses and Net Capital Investment 2026-27 |
| no | P1 | 0.4 MB | 1 | `entity_budget_statement` | Commonwealth | `federal_ndia_pbs_2026_27` | National Disability Insurance Agency Portfolio Budget Statements 2026-27 |
| no | P1 | 0.3 MB | 1 | `final_budget_outcome` | Commonwealth | `federal_fbo_2024_25_function_subfunction` | Final Budget Outcome 2024-25, Appendix A: Expenses by function and sub-function |
| no | P1 | 0.2 MB | 1 | `gfs_actuals` | Commonwealth | `abs_gfs_commonwealth_130` | Table 130. General government - Commonwealth |
| YES | P1-phase1 | 0.1 MB | 1 | `phase1_website` | Commonwealth | `federal_expense_by_function` | Australian Government general government sector Monthly Financial Statements - Note 3 Func |

### By source family

#### `procurement_contracts` — 2 source(s), 1669.1 MB

- `federal_austender_ocds_api` (886.5 MB, 18 assets) — measures: contract_value
- `federal_historical_cn_data_1999_2020` (782.6 MB, 15 assets) — measures: contract_value, supplier, agency

#### `program_forecast` — 1 source(s), 1477.6 MB

- `ndis_financial_sustainability_reports` (1477.6 MB, 368 assets) — measures: forecast, participant_payment

#### `program_actuals` — 1 source(s), 1471.2 MB

- `ndis_quarterly_reports` (1471.2 MB, 379 assets) — measures: participant_payment, actual_accrual_expense, recipient_count

#### `participant_statistics` — 1 source(s), 675.1 MB

- `ndis_participant_datasets` (675.1 MB, 233 assets) — measures: recipient_count

#### `payment_aggregates` — 1 source(s), 675.0 MB

- `ndis_payment_datasets` (675.0 MB, 233 assets) — measures: participant_payment

#### `entity_annual_reports` — 2 source(s), 88.8 MB

- `federal_transparency_portal` (66.3 MB, 16 assets) — measures: audited_actual, actual_accrual_expense, consultancy, supplier
- `services_australia_annual_reports` (22.5 MB, 6 assets) — measures: audited_actual, actual_accrual_expense

#### `whole_of_government_actuals` — 1 source(s), 62.5 MB

- `federal_cfs_2024_25` (62.5 MB, 1 assets) — measures: audited_actual, actual_accrual_expense, assets, liabilities

#### `grant_awards` — 1 source(s), 35.7 MB

- `federal_grantconnect` (35.7 MB, 13 assets) — measures: grant_award

#### `recipient_statistics` — 4 source(s), 25.5 MB

- `dss_jobseeker_monthly_profile` (18.1 MB, 81 assets) — measures: recipient_count
- `dss_payment_demographics_quarterly` (3.8 MB, 21 assets) — measures: recipient_count
- `dss_payments_by_lga` (2.7 MB, 5 assets) — measures: recipient_count
- `dss_income_support_monthly` (0.9 MB, 1 assets) — measures: recipient_count

#### `portfolio_budget_statements` — 4 source(s), 13.2 MB

- `federal_social_services_pbs_2025_26_archive` (4.1 MB, 1 assets) — measures: budget_estimate, estimated_actual, appropriation_authority
- `federal_health_disability_ageing_pbs_2026_27` (4.0 MB, 1 assets) — measures: budget_estimate, estimated_actual, appropriation_authority
- `federal_dss_pbs_2026_27` (3.2 MB, 1 assets) — measures: budget_estimate, estimated_actual, appropriation_authority
- `federal_dva_pbs_2026_27` (1.9 MB, 1 assets) — measures: budget_estimate, estimated_actual, appropriation_authority

#### `monthly_actuals` — 1 source(s), 6.8 MB

- `federal_monthly_financial_statements` (6.8 MB, 10 assets) — measures: actual_accrual_expense, revised_estimate

#### `agency_resourcing` — 1 source(s), 6.2 MB

- `federal_agency_resourcing_bp4_2026_27` (6.2 MB, 1 assets) — measures: appropriation_authority, budget_estimate

#### `budget_measures` — 1 source(s), 2.1 MB

- `federal_budget_measures_bp2_2026_27` (2.1 MB, 1 assets) — measures: budget_estimate, policy_measure

#### `portfolio_budget_statements_index` — 1 source(s), 1.5 MB

- `federal_pbs_index_2026_27` (1.5 MB, 2 assets) — measures: budget_estimate, appropriation_authority

#### `budget_function_program` — 1 source(s), 0.8 MB

- `federal_budget_statement_6_2026_27` (0.8 MB, 1 assets) — measures: budget_estimate, revised_estimate, actual_accrual_expense, cash_payment

#### `entity_budget_statement` — 1 source(s), 0.4 MB

- `federal_ndia_pbs_2026_27` (0.4 MB, 1 assets) — measures: budget_estimate, estimated_actual, appropriation_authority

#### `final_budget_outcome` — 1 source(s), 0.3 MB

- `federal_fbo_2024_25_function_subfunction` (0.3 MB, 1 assets) — measures: actual_accrual_expense, budget_estimate

#### `gfs_actuals` — 1 source(s), 0.2 MB

- `abs_gfs_commonwealth_130` (0.2 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance

#### `phase1_website` — 1 source(s), 0.1 MB

- `federal_expense_by_function` (0.1 MB, 1 assets) — measures: expense_by_function

---

## 4. State — acquired corpus

**26 sources · 977 assets · 1.55 GB**

**Formats on disk:** `.pdf`×462, `.csv`×293, `.xlsx`×191, `.jsonl.gz`×22, `.docx`×8, `.xls`×1, `.json`×0

| On site? | Priority | Size | Assets | Family | Jurisdiction | Source ID | Title |
|---|---|---:|---:|---|---|---|---|
| no | P1 | 332.5 MB | 239 | `procurement_contracts` | QLD | `qld_contract_disclosure_agency_datasets` | Queensland Government agency Contract Disclosure Reports |
| no | P1 | 209.6 MB | 15 | `grant_and_service_payments` | QLD | `qld_qgip_expenditure` | Queensland Government Investment Portal expenditure data - consolidated view |
| no | P2 | 174.4 MB | 89 | `state_actuals` | TAS | `tas_treasurers_annual_financial_reports` | Treasurer's Annual Financial Reports |
| no | P2 | 144.2 MB | 187 | `state_actuals` | QLD | `qld_report_on_state_finances` | Queensland Report on State Finances |
| no | P2 | 112.8 MB | 99 | `state_actuals` | WA | `wa_annual_report_state_finances_2024_25` | Western Australia Annual Report on State Finances 2024-25 |
| no | P2 | 94.0 MB | 24 | `state_actuals` | NSW | `nsw_report_on_state_finances` | NSW Report on State Finances |
| no | P2 | 80.8 MB | 40 | `state_budget` | TAS | `tas_budget_2026_27` | Tasmanian Budget 2026-27 |
| no | P2 | 74.1 MB | 50 | `state_budget` | QLD | `qld_budget_2026_27` | Queensland Budget Papers 2026-27 |
| no | P2 | 67.3 MB | 106 | `state_budget` | WA | `wa_budget_2026_27` | Western Australia Budget Papers 2026-27 |
| no | P1 | 64.9 MB | 22 | `procurement_contracts` | NSW | `nsw_procurement_ocds_registry` | NSW Government procurement — OCDS bulk data |
| no | P2 | 60.3 MB | 13 | `state_budget` | NSW | `nsw_budget_2026_27` | NSW Budget Papers 2026-27 |
| no | P2 | 41.1 MB | 8 | `state_budget` | SA | `sa_budget_2026_27` | South Australia Budget 2026-27 |
| no | P2 | 28.9 MB | 16 | `state_budget_open_data` | NSW | `nsw_budget_open_data_2026_27` | NSW Budget 2026-27 Open Data |
| no | P2 | 24.9 MB | 8 | `state_budget` | VIC | `vic_budget_2026_27` | Victorian State Budget 2026-27 |
| no | P2 | 11.8 MB | 2 | `state_actuals` | SA | `sa_final_budget_outcome_and_cfr` | South Australia Final Budget Outcome and Consolidated Financial Report |
| no | P2 | 10.0 MB | 7 | `entity_actuals` | VIC | `vic_dtf_annual_report_bpo` | DTF Annual Report and Budget Portfolio Outcomes |
| no | P2 | 9.5 MB | 1 | `state_actuals` | VIC | `vic_financial_report_2024_25` | Victoria Financial Report 2024-25 |
| no | P4 | 7.7 MB | 2 | `procurement_contracts` | NSW | `nsw_buy_register` | buy.nsw register of notices |
| no | P2 | 0.2 MB | 42 | `payment_timing_disclosure` | QLD | `qld_on_time_payment_reports` | Queensland Government On-Time Payment Reports |
| YES | P1-phase1 | 0.1 MB | 1 | `phase1_website` | SA | `sa_gfs_by_function` | South Australian Government Finance Statistics - general government sector expenses by fun |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | TAS | `abs_gfs_state_tas_236` | Table 236. General government - state - Tasmania |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | QLD | `abs_gfs_state_qld_233` | Table 233. General government - state - Queensland |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | VIC | `abs_gfs_state_vic_232` | Table 232. General government - state - Victoria |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | SA | `abs_gfs_state_sa_234` | Table 234. General government - state - South Australia |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | NSW | `abs_gfs_state_nsw_231` | Table 231. General government - state - New South Wales |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | WA | `abs_gfs_state_wa_235` | Table 235. General government - state - Western Australia |

### By source family

#### `state_actuals` — 6 source(s), 546.7 MB

- `tas_treasurers_annual_financial_reports` (174.4 MB, 89 assets) — measures: audited_actual, actual_accrual_expense
- `qld_report_on_state_finances` (144.2 MB, 187 assets) — measures: audited_actual, actual_accrual_expense
- `wa_annual_report_state_finances_2024_25` (112.8 MB, 99 assets) — measures: audited_actual, actual_accrual_expense
- `nsw_report_on_state_finances` (94.0 MB, 24 assets) — measures: audited_actual, actual_accrual_expense
- `sa_final_budget_outcome_and_cfr` (11.8 MB, 2 assets) — measures: audited_actual, actual_accrual_expense
- `vic_financial_report_2024_25` (9.5 MB, 1 assets) — measures: audited_actual, actual_accrual_expense

#### `procurement_contracts` — 3 source(s), 405.1 MB

- `qld_contract_disclosure_agency_datasets` (332.5 MB, 239 assets) — measures: contract_value, procurement_method, variation_flag
- `nsw_procurement_ocds_registry` (64.9 MB, 22 assets) — measures: contract_value, award_date, supplier, procurement_method
- `nsw_buy_register` (7.7 MB, 2 assets) — measures: contract_value

#### `state_budget` — 6 source(s), 348.5 MB

- `tas_budget_2026_27` (80.8 MB, 40 assets) — measures: budget_estimate, appropriation_authority
- `qld_budget_2026_27` (74.1 MB, 50 assets) — measures: budget_estimate, appropriation_authority
- `wa_budget_2026_27` (67.3 MB, 106 assets) — measures: budget_estimate, appropriation_authority
- `nsw_budget_2026_27` (60.3 MB, 13 assets) — measures: budget_estimate, appropriation_authority
- `sa_budget_2026_27` (41.1 MB, 8 assets) — measures: budget_estimate, appropriation_authority
- `vic_budget_2026_27` (24.9 MB, 8 assets) — measures: budget_estimate, appropriation_authority

#### `grant_and_service_payments` — 1 source(s), 209.6 MB

- `qld_qgip_expenditure` (209.6 MB, 15 assets) — measures: cash_payment, grant_payment

#### `state_budget_open_data` — 1 source(s), 28.9 MB

- `nsw_budget_open_data_2026_27` (28.9 MB, 16 assets) — measures: budget_estimate, revised_estimate

#### `entity_actuals` — 1 source(s), 10.0 MB

- `vic_dtf_annual_report_bpo` (10.0 MB, 7 assets) — measures: audited_actual, actual_accrual_expense, output_performance

#### `gfs_actuals` — 6 source(s), 0.6 MB

- `abs_gfs_state_tas_236` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_state_qld_233` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_state_vic_232` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_state_sa_234` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_state_nsw_231` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_state_wa_235` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance

#### `payment_timing_disclosure` — 1 source(s), 0.2 MB

- `qld_on_time_payment_reports` (0.2 MB, 42 assets) — measures: invoice_count, on_time_percentage

#### `phase1_website` — 1 source(s), 0.1 MB

- `sa_gfs_by_function` (0.1 MB, 1 assets) — measures: expense_by_function

---

## 5. Territory — acquired corpus

**8 sources · 74 assets · 0.212 GB**

**Formats on disk:** `.pdf`×69, `.xlsx`×4, `.csv`×1, `.json`×0

| On site? | Priority | Size | Assets | Family | Jurisdiction | Source ID | Title |
|---|---|---:|---:|---|---|---|---|
| no | P2 | 168.1 MB | 45 | `territory_actuals` | NT | `nt_treasury_annual_reports` | Northern Territory Treasury annual reports |
| no | P2 | 22.7 MB | 23 | `territory_budget` | ACT | `act_budget_2026_27` | ACT Budget Papers and Statements 2026-27 |
| no | P1 | 15.9 MB | 1 | `invoice_payments` | ACT | `act_notifiable_invoices` | Notifiable Invoices Register |
| no | P2 | 4.4 MB | 1 | `territory_budget` | NT | `nt_budget_2026_27` | Northern Territory Budget Papers 2026-27 |
| no | P2 | 0.8 MB | 1 | `territory_actuals` | ACT | `act_actual_financial_publications` | ACT Treasury financial publications |
| no | P1 | 0.3 MB | 1 | `procurement_contracts` | NT | `nt_awarded_government_contracts` | Awarded government contracts |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | ACT | `abs_gfs_state_act_238` | Table 238. General government - state - Australian Capital Territory |
| no | P2 | 0.1 MB | 1 | `gfs_actuals` | NT | `abs_gfs_state_nt_237` | Table 237. General government - state - Northern Territory |

### By source family

#### `territory_actuals` — 2 source(s), 168.9 MB

- `nt_treasury_annual_reports` (168.1 MB, 45 assets) — measures: audited_actual, actual_accrual_expense
- `act_actual_financial_publications` (0.8 MB, 1 assets) — measures: audited_actual, actual_accrual_expense

#### `territory_budget` — 2 source(s), 27.1 MB

- `act_budget_2026_27` (22.7 MB, 23 assets) — measures: budget_estimate, appropriation_authority
- `nt_budget_2026_27` (4.4 MB, 1 assets) — measures: budget_estimate, appropriation_authority

#### `invoice_payments` — 1 source(s), 15.9 MB

- `act_notifiable_invoices` (15.9 MB, 1 assets) — measures: invoice_paid

#### `procurement_contracts` — 1 source(s), 0.3 MB

- `nt_awarded_government_contracts` (0.3 MB, 1 assets) — measures: contract_value

#### `gfs_actuals` — 2 source(s), 0.2 MB

- `abs_gfs_state_act_238` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_state_nt_237` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance

---

## 6. Local — acquired corpus

**13 sources · 75 assets · 0.117 GB**

**Formats on disk:** `.xlsx`×33, `.pdf`×32, `.xls`×6, `.docx`×2, `.zip`×2, `.json`×0

| On site? | Priority | Size | Assets | Family | Jurisdiction | Source ID | Title |
|---|---|---:|---:|---|---|---|---|
| no | P1 | 41.1 MB | 31 | `local_financial_returns` | NSW | `nsw_local_olg_time_series` | Your council data and reports - time series |
| no | P1 | 30.3 MB | 2 | `local_financial_returns` | TAS | `tas_local_cdc` | Council performance and Consolidated Data Collection |
| no | P3 | 27.4 MB | 10 | `local_budget` | VIC | `vic_local_budget_and_reporting_models` | Council planning, budget and annual reporting guidance and models |
| no | P2 | 13.0 MB | 13 | `local_audit_actuals` | QLD | `qld_local_qao_2025` | Local government 2025 report and dashboard |
| no | P1 | 3.4 MB | 11 | `local_financial_returns` | VIC | `vic_local_vgc_abs_returns` | Council raw VGC and ABS data packs |
| YES | P1-phase1 | 0.8 MB | 1 | `phase1_website` | VIC | `vic_local_govt_financial` | Victorian Auditor-General's Office - Results of Audits: Local Government dashboard data |
| no | P1 | 0.1 MB | 1 | `gfs_actuals` | NT | `abs_gfs_local_nt_337` | Table 337. General government - local - Northern Territory |
| no | P1 | 0.1 MB | 1 | `gfs_actuals` | NSW | `abs_gfs_local_nsw_331` | Table 331. General government - local - New South Wales |
| no | P1 | 0.1 MB | 1 | `gfs_actuals` | TAS | `abs_gfs_local_tas_336` | Table 336. General government - local - Tasmania |
| no | P1 | 0.1 MB | 1 | `gfs_actuals` | SA | `abs_gfs_local_sa_334` | Table 334. General government - local - South Australia |
| no | P1 | 0.1 MB | 1 | `gfs_actuals` | QLD | `abs_gfs_local_qld_333` | Table 333. General government - local - Queensland |
| no | P1 | 0.1 MB | 1 | `gfs_actuals` | VIC | `abs_gfs_local_vic_332` | Table 332. General government - local - Victoria |
| no | P1 | 0.1 MB | 1 | `gfs_actuals` | WA | `abs_gfs_local_wa_335` | Table 335. General government - local - Western Australia |

### By source family

#### `local_financial_returns` — 3 source(s), 74.8 MB

- `nsw_local_olg_time_series` (41.1 MB, 31 assets) — measures: actual_accrual_expense, revenue, service_indicator
- `tas_local_cdc` (30.3 MB, 2 assets) — measures: actual_accrual_expense, revenue, service_indicator
- `vic_local_vgc_abs_returns` (3.4 MB, 11 assets) — measures: actual_accrual_expense, revenue, capital_outlay, assets, liabilities

#### `local_budget` — 1 source(s), 27.4 MB

- `vic_local_budget_and_reporting_models` (27.4 MB, 10 assets) — measures: budget_estimate, actual_accrual_expense

#### `local_audit_actuals` — 1 source(s), 13.0 MB

- `qld_local_qao_2025` (13.0 MB, 13 assets) — measures: audited_actual, financial_ratio

#### `phase1_website` — 1 source(s), 0.8 MB

- `vic_local_govt_financial` (0.8 MB, 1 assets) — measures: expense_by_function

#### `gfs_actuals` — 7 source(s), 0.7 MB

- `abs_gfs_local_nt_337` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_local_nsw_331` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_local_tas_336` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_local_sa_334` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_local_qld_333` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_local_vic_332` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance
- `abs_gfs_local_wa_335` (0.1 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance

---

## 7. Cross-level — acquired corpus

**2 sources · 2 assets · 0.009 GB**

**Formats on disk:** `.zip`×1, `.pdf`×1, `.json`×0

| On site? | Priority | Size | Assets | Family | Jurisdiction | Source ID | Title |
|---|---|---:|---:|---|---|---|---|
| no | P1 | 5.1 MB | 1 | `intergovernmental_transfers` | Commonwealth and states | `federal_financial_relations_bp3_2026_27` | Budget Paper No. 3: Federal Financial Relations 2026-27 |
| no | P1 | 4.4 MB | 1 | `gfs_actuals` | Australia | `abs_gfs_annual_all_workbooks` | Government Finance Statistics, Annual - all workbooks |

### By source family

#### `intergovernmental_transfers` — 1 source(s), 5.1 MB

- `federal_financial_relations_bp3_2026_27` (5.1 MB, 1 assets) — measures: budget_estimate, cash_payment, grant_payment

#### `gfs_actuals` — 1 source(s), 4.4 MB

- `abs_gfs_annual_all_workbooks` (4.4 MB, 1 assets) — measures: actual_accrual_expense, revenue, assets, liabilities, fiscal_balance

---

## 8. Measure-type mix (registry metadata × on-disk bytes)

| Measure type | Sources | Assets | Size |
|---|---:|---:|---:|
| `participant_payment` | 3 | 980 | 3.624 GB |
| `actual_accrual_expense` | 37 | 940 | 2.464 GB |
| `recipient_count` | 6 | 720 | 2.172 GB |
| `contract_value` | 6 | 297 | 2.075 GB |
| `forecast` | 1 | 368 | 1.478 GB |
| `supplier` | 3 | 53 | 0.914 GB |
| `audited_actual` | 13 | 491 | 0.89 GB |
| `agency` | 1 | 15 | 0.783 GB |
| `budget_estimate` | 21 | 287 | 0.461 GB |
| `procurement_method` | 2 | 261 | 0.397 GB |
| `appropriation_authority` | 15 | 257 | 0.397 GB |
| `variation_flag` | 1 | 239 | 0.333 GB |
| `cash_payment` | 3 | 17 | 0.216 GB |
| `grant_payment` | 2 | 16 | 0.215 GB |
| `revenue` | 20 | 61 | 0.081 GB |
| `assets` | 19 | 29 | 0.072 GB |
| `liabilities` | 19 | 29 | 0.072 GB |
| `service_indicator` | 2 | 33 | 0.071 GB |
| `consultancy` | 1 | 16 | 0.066 GB |
| `award_date` | 1 | 22 | 0.065 GB |
| `revised_estimate` | 3 | 27 | 0.037 GB |
| `grant_award` | 1 | 13 | 0.036 GB |
| `invoice_paid` | 1 | 1 | 0.016 GB |
| `estimated_actual` | 5 | 5 | 0.014 GB |
| `financial_ratio` | 1 | 13 | 0.013 GB |
| `output_performance` | 1 | 7 | 0.01 GB |
| `fiscal_balance` | 17 | 17 | 0.006 GB |
| `capital_outlay` | 1 | 11 | 0.003 GB |
| `policy_measure` | 1 | 1 | 0.002 GB |
| `expense_by_function` | 3 | 3 | 0.001 GB |
| `invoice_count` | 1 | 42 | 0.0 GB |
| `on_time_percentage` | 1 | 42 | 0.0 GB |

## 9. Source-family mix

| Family | Sources | Assets | Size |
|---|---:|---:|---:|
| `procurement_contracts` | 6 | 297 | 2.075 GB |
| `program_forecast` | 1 | 368 | 1.478 GB |
| `program_actuals` | 1 | 379 | 1.471 GB |
| `participant_statistics` | 1 | 233 | 0.675 GB |
| `payment_aggregates` | 1 | 233 | 0.675 GB |
| `state_actuals` | 6 | 402 | 0.547 GB |
| `state_budget` | 6 | 225 | 0.348 GB |
| `grant_and_service_payments` | 1 | 15 | 0.21 GB |
| `territory_actuals` | 2 | 46 | 0.169 GB |
| `entity_annual_reports` | 2 | 22 | 0.089 GB |
| `local_financial_returns` | 3 | 44 | 0.075 GB |
| `whole_of_government_actuals` | 1 | 1 | 0.062 GB |
| `grant_awards` | 1 | 13 | 0.036 GB |
| `state_budget_open_data` | 1 | 16 | 0.029 GB |
| `local_budget` | 1 | 10 | 0.027 GB |
| `territory_budget` | 2 | 24 | 0.027 GB |
| `recipient_statistics` | 4 | 108 | 0.025 GB |
| `invoice_payments` | 1 | 1 | 0.016 GB |
| `portfolio_budget_statements` | 4 | 4 | 0.013 GB |
| `local_audit_actuals` | 1 | 13 | 0.013 GB |
| `entity_actuals` | 1 | 7 | 0.01 GB |
| `monthly_actuals` | 1 | 10 | 0.007 GB |
| `agency_resourcing` | 1 | 1 | 0.006 GB |
| `gfs_actuals` | 17 | 17 | 0.006 GB |
| `intergovernmental_transfers` | 1 | 1 | 0.005 GB |
| `budget_measures` | 1 | 1 | 0.002 GB |
| `portfolio_budget_statements_index` | 1 | 2 | 0.001 GB |
| `phase1_website` | 3 | 3 | 0.001 GB |
| `budget_function_program` | 1 | 1 | 0.001 GB |
| `entity_budget_statement` | 1 | 1 | 0.0 GB |
| `final_budget_outcome` | 1 | 1 | 0.0 GB |
| `payment_timing_disclosure` | 1 | 42 | 0.0 GB |

## 10. Registry sources still empty on disk

- `federal_austender_weekly_export`
- `nt_grants_commission_annual_reports`
- `nt_local_grants_commission_return`
- `sa_councils_in_focus`
- `sa_lggc_council_database_reports`
- `sa_tenders_contracts`
- `tas_procurement`
- `wa_mycouncil`
- `wa_tenders`

## 11. Caveats on year detection for acquired files

Filename/URL year heuristics are **indicative only** (PDFs named with budget year, OCDS dumps spanning ranges, NDIS reports with multiple dates). Authoritative website years are in §2. For acquired sources, treat declared `time_coverage` in `config/procurement_sources.yaml` and document metadata as primary; use filename years as a secondary hint for prioritization.

