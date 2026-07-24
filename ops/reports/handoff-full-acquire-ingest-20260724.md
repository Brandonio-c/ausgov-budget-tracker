# Handoff full acquire + ingest coverage

Generated: 2026-07-24T17:19:33.242508+00:00

## Totals

- Handoff rows: **281**
- Already on disk (confirmed present): **133**
- Newly downloaded / imported: **50**
- Missing (no latest.json): **98**
- Blocked/manual unresolved: **0**
- Reference-only (no file expected): **0**
- Rows with ≥1 facts keyed to source: **42**

## Acceptance checklist

| Criterion | Status |
|---|---|
| ABS Table_1 GFS revenue in facts (all jurisdictions) | PASS — `gfs_revenue` facts present |
| Commonwealth Debt securities ring 3+ Bonds/TIBs/Notes (AOFM) | PASS — API debt tree max depth 4 |
| PBS program facts beyond prior 75 | PASS — 6,551 `federal_pbs_programs_all` facts |
| Tax-by-type + GDP/GVA with revenue/gdp modes | PASS — tax_revenue + gdp_current; modes live |
| Statement 11 net debt / CGS face value queryable | PASS |
| Per-row status report | PASS — this file + `handoff-download-status.md` |
| GitHub free of data/raw / facts.db | PASS — gitignore unchanged (`data/new/` added earlier) |

### Notes
- Host curl cannot reach `aofm.gov.au`; AOFM files acquired via Cursor browser → `127.0.0.1:8765` upload receiver.
- Many agency PBS 2026–27 hosts still `network_error`/`blocked_auth`; Transparency Portal 2025–26 PBS set already on disk was extracted instead.
- Remaining missing rows are mostly landing-page discovery / WAF-blocked optional manuals — listed below with status `missing`.

## Measure family counts in facts.db

| measure_type | compatibility_group | facts |
|---|---|---:|
| actual_accrual_expense | actual_expense | 189816 |
| invoice_paid | cash_outflow | 46714 |
| contract_value | commitment | 16255 |
| budget_estimate | budget_expense | 7315 |
| gfs_expense | actual_expense | 5294 |
| gfs_revenue | gfs_revenue | 1220 |
| gfs_liability | gfs_liability | 1120 |
| tax_revenue | gfs_revenue | 690 |
| monthly_actuals | actual_expense | 288 |
| gross_debt_face_value | gfs_liability | 60 |
| net_debt | gfs_liability | 60 |
| aofm_cgs_outstanding | gfs_liability | 50 |
| cash_payment | cash_outflow | 26 |
| gdp_current | gdp | 19 |

## Per-source status

| id | action | priority | status | facts | title |
|---|---|---|---|---:|---|
| `federal_pbs_2026_27_defence` |  | P0 | missing | 0 | 2026-27 Portfolio Budget Statements - Defence Portfolio |
| `federal_pbs_2026_27_education` |  | P0 | missing | 0 | 2026-27 Portfolio Budget Statements - Education Portfolio |
| `federal_pbs_2026_27_industry_science_resources` |  | P0 | missing | 0 | 2026-27 Portfolio Budget Statements - Industry, Science and Resources |
| `federal_pbs_2026_27_infrastructure_transport_regions` |  | P0 | missing | 0 | 2026-27 Portfolio Budget Statements - Infrastructure, Transport, Regional Develo |
| `act_issued_notes_may_2026` |  | P0 | missing | 0 | ACT Government issued notes outstanding May 2026 |
| `aofm_foreign_holdings` |  | P0 | downloaded | 0 | AOFM foreign holdings of Australian Government Securities |
| `aofm_portfolio_aggregate_dealt` |  | P0 | downloaded | 0 | AOFM portfolio aggregate - dealt |
| `aofm_portfolio_aggregate_settlement` |  | P0 | downloaded | 0 | AOFM portfolio aggregate - settlement |
| `aofm_portfolio_executive_summary_dealt` |  | P0 | downloaded | 0 | AOFM portfolio aggregate executive summary - dealt |
| `aofm_register_government_borrowing` |  | P0 | downloaded | 0 | AOFM register of Australian Government borrowing |
| `aofm_stock_ags_csv` |  | P0 | downloaded | 0 | AOFM stock of Australian Government Securities |
| `aofm_treasury_bonds_dealt` |  | P0 | downloaded | 32 | AOFM Treasury Bonds - dealt |
| `aofm_treasury_bonds_settlement` |  | P0 | downloaded | 0 | AOFM Treasury Bonds - settlement |
| `aofm_treasury_indexed_bonds_dealt` |  | P0 | downloaded | 8 | AOFM Treasury Indexed Bonds - dealt |
| `aofm_treasury_indexed_bonds_settlement` |  | P0 | downloaded | 0 | AOFM Treasury Indexed Bonds - settlement |
| `aofm_treasury_notes_dealt` |  | P0 | downloaded | 10 | AOFM Treasury Notes - dealt |
| `aofm_treasury_notes_settlement` |  | P0 | downloaded | 0 | AOFM Treasury Notes - settlement |
| `nsw_tcorp_bonds_on_issue` |  | P0 | missing | 0 | TCorp bonds on issue |
| `qld_qtc_aud_bond_outstandings` |  | P0 | missing | 0 | QTC AUD bond outstandings |
| `qld_qtc_weekly_outstandings_2026_07_17` |  | P0 | downloaded | 0 | QTC Weekly Outstandings Report as at 17 July 2026 |
| `sa_safa_weekly_funding_update` |  | P0 | missing | 0 | SAFA weekly funding update |
| `tas_tascorp_bond_programme` |  | P0 | missing | 0 | TASCORP bond programme |
| `vic_tcv_amount_on_issue` |  | P0 | missing | 0 | TCV amount on issue |
| `vic_tcv_benchmark_bond_outstandings` |  | P0 | missing | 0 | TCV domestic benchmark bond outstandings |
| `wa_watc_funding_sources` |  | P0 | missing | 0 | WATC funding sources |
| `abs_state_accounts_act_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Australian Capital Territory |
| `abs_asna_all_workbooks_2024_25` |  | P0 | downloaded | 0 | Australian System of National Accounts 2024-25 - all time series |
| `abs_asna_expenditure_gdp_2024_25` |  | P0 | downloaded | 0 | Australian System of National Accounts 2024-25 - Expenditure on GDP |
| `abs_asna_gva_industry_2024_25` |  | P0 | downloaded | 19 | Australian System of National Accounts 2024-25 - GVA by Industry |
| `abs_asna_income_gdp_2024_25` |  | P0 | downloaded | 0 | Australian System of National Accounts 2024-25 - Income from GDP |
| `abs_asna_key_aggregates_2024_25` |  | P0 | downloaded | 0 | Australian System of National Accounts 2024-25 - Key National Aggregates |
| `abs_qna_all_workbooks_mar_2026` |  | P0 | downloaded | 0 | National Accounts Mar 2026 - all time series workbooks |
| `abs_qna_expenditure_current_price_mar_2026` |  | P0 | downloaded | 0 | National Accounts Mar 2026 - Expenditure current price |
| `abs_qna_expenditure_volume_mar_2026` |  | P0 | downloaded | 0 | National Accounts Mar 2026 - Expenditure volume measures |
| `abs_qna_industry_gva_annual_mar_2026` |  | P0 | downloaded | 0 | National Accounts Mar 2026 - Industry GVA annual |
| `abs_qna_industry_gva_current_price_mar_2026` |  | P0 | downloaded | 0 | National Accounts Mar 2026 - Industry GVA current price |
| `abs_qna_industry_gva_mar_2026` |  | P0 | downloaded | 0 | National Accounts Mar 2026 - Industry GVA |
| `abs_qna_key_aggregates_mar_2026` |  | P0 | downloaded | 0 | National Accounts Mar 2026 - Key Aggregates |
| `abs_state_accounts_all_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - all time series |
| `abs_state_accounts_aus_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Australia comparison |
| `abs_state_accounts_gsp_all_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Gross State Product, all states |
| `abs_taxation_revenue_all_downloads_2024_25` |  | P0 | downloaded | 0 | Taxation Revenue, Australia 2024-25 - all downloads |
| `abs_taxation_revenue_detailed_tables_2024_25` |  | P0 | downloaded | 0 | Taxation Revenue, Australia 2024-25 - detailed tables |
| `abs_taxation_revenue_key_tables_2024_25` |  | P0 | downloaded | 690 | Taxation Revenue, Australia 2024-25 - Key Tables |
| `abs_state_accounts_nsw_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - New South Wales |
| `abs_state_accounts_nt_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Northern Territory |
| `abs_state_accounts_qld_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Queensland |
| `abs_state_accounts_sa_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - South Australia |
| `abs_state_accounts_tas_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Tasmania |
| `abs_state_accounts_vic_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Victoria |
| `abs_state_accounts_wa_2024_25` |  | P0 | downloaded | 0 | State Accounts 2024-25 - Western Australia |
| `act_actual_financial_publications` |  | P0 | already_on_disk | 0 | ACT Treasury actual financial publications |
| `abs_gfs_all_workbooks_2024_25` |  | P0 | already_on_disk | 0 | All ABS GFS Annual workbooks |
| `abs_gfs_commonwealth_2024_25` |  | P0 | already_on_disk | 230 | ABS GFS Commonwealth general government |
| `federal_fbo_appendix_a_2024_25` |  | P0 | already_on_disk | 83 | Final Budget Outcome 2024-25 Appendix A: expenses by function and sub-function |
| `federal_transparency_pbs_set_16` |  | P0 | already_on_disk | 0 | Transparency Portal PBS set - 16 PDFs already acquired |
| `nt_tafr_2024_25` |  | P0 | already_on_disk | 0 | Northern Territory Treasurer's Annual Financial Report 2024-25 |
| `qld_sds_2026_27_education` |  | P0 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Department of Education |
| `qld_sds_2026_27_health` |  | P0 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Queensland Health |
| `qld_sds_2026_27_state_development_infrastructure_planning` |  | P0 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - State Development, Infrastructu |
| `qld_sds_2026_27_transport_main_roads` |  | P0 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Transport and Main Roads |
| `sa_final_budget_outcome_cfr_2024_25` |  | P0 | already_on_disk | 0 | South Australia Final Budget Outcome and Consolidated Financial Report |
| `tas_treasurer_annual_financial_reports` |  | P0 | already_on_disk | 0 | Tasmanian Treasurer's Annual Financial Reports |
| `vic_annual_financial_statements_2024_25` |  | P0 | already_on_disk | 0 | Victoria annual financial statements 2024-25 |
| `vic_budget_portfolio_outcomes_2024_25` |  | P0 | already_on_disk | 0 | Victoria Budget Portfolio Outcomes 2024-25 |
| `vic_output_performance_measures_2024_25` |  | P0 | already_on_disk | 0 | Victoria output performance measures 2024-25 |
| `wa_annual_report_state_finances_2024_25` |  | P0 | already_on_disk | 0 | Western Australia Annual Report on State Finances 2024-25 |
| `federal_cfs_2024_25_notes` |  | P0 | already_on_disk | 0 | Commonwealth Consolidated Financial Statements 2024-25 |
| `nsw_local_time_series_2024_25` |  | P0 | already_on_disk | 2794 | NSW council time series data 2024-25 |
| `vic_local_abs2_3_balance_finance_2024_25` |  | P0 | already_on_disk | 889 | Victoria local government 2024-25 - ABS2 and 3 Balance Sheets and Other Finances |
| `vic_local_vgc1_revenue_expenditure_2024_25` |  | P0 | already_on_disk | 889 | Victoria local government 2024-25 - VGC1 Expenditure and Revenue |
| `federal_bp1_statement5_expenses_2025_26` |  | P1 | downloaded | 0 | 2025-26 Budget Paper 1 Statement 5: Expenses and Net Capital Investment |
| `federal_pbs_2024_25_agriculture_fisheries_and_forestry` |  | P1 | missing | 0 | 2024-25 PBS archive link - Agriculture, Fisheries and Forestry |
| `federal_pbs_2024_25_attorney_general_s_portfolio` |  | P1 | missing | 0 | 2024-25 PBS archive link - Attorney-General's Portfolio |
| `federal_pbs_2024_25_climate_change_energy_the_environment_and_water` |  | P1 | missing | 0 | 2024-25 PBS archive link - Climate Change, Energy, the Environment and Water |
| `federal_pbs_2024_25_defence_portfolio` |  | P1 | missing | 0 | 2024-25 PBS archive link - Defence Portfolio |
| `federal_pbs_2024_25_department_of_parliamentary_services` |  | P1 | missing | 0 | 2024-25 PBS archive link - Department of Parliamentary Services |
| `federal_pbs_2024_25_department_of_the_house_of_representatives` |  | P1 | missing | 0 | 2024-25 PBS archive link - Department of the House of Representatives |
| `federal_pbs_2024_25_department_of_the_senate_pbs` |  | P1 | missing | 0 | 2024-25 PBS archive link - Department of the Senate PBS |
| `federal_pbs_2024_25_education_portfolio` |  | P1 | missing | 0 | 2024-25 PBS archive link - Education Portfolio |
| `federal_pbs_2024_25_employment_and_workplace_relations` |  | P1 | missing | 0 | 2024-25 PBS archive link - Employment and Workplace Relations |
| `federal_pbs_2024_25_finance_portfolio` |  | P1 | missing | 0 | 2024-25 PBS archive link - Finance Portfolio |
| `federal_pbs_2024_25_foreign_affairs_and_trade` |  | P1 | missing | 0 | 2024-25 PBS archive link - Foreign Affairs and Trade |
| `federal_pbs_2024_25_health_disability_and_ageing` |  | P1 | missing | 0 | 2024-25 PBS archive link - Health, Disability and Ageing |
| `federal_pbs_2024_25_home_affairs_portfolio` |  | P1 | missing | 0 | 2024-25 PBS archive link - Home Affairs Portfolio |
| `federal_pbs_2024_25_industry_science_and_resources` |  | P1 | missing | 0 | 2024-25 PBS archive link - Industry, Science and Resources |
| `federal_pbs_2024_25_infrastructure_transport_regional_development_communications_sport_and_the_arts` |  | P1 | missing | 0 | 2024-25 PBS archive link - Infrastructure, Transport, Regional Development, Comm |
| `federal_pbs_2024_25_parliamentary_budget_office` |  | P1 | missing | 0 | 2024-25 PBS archive link - Parliamentary Budget Office |
| `federal_pbs_2024_25_prime_minister_and_cabinet` |  | P1 | missing | 0 | 2024-25 PBS archive link - Prime Minister and Cabinet |
| `federal_pbs_2024_25_social_services_portfolio` |  | P1 | missing | 0 | 2024-25 PBS archive link - Social Services Portfolio |
| `federal_pbs_2024_25_treasury_portfolio` |  | P1 | missing | 0 | 2024-25 PBS archive link - Treasury Portfolio |
| `federal_pbs_2024_25_veterans_affairs` |  | P1 | missing | 0 | 2024-25 PBS archive link - Veterans' Affairs |
| `federal_pbs_2025_26_agriculture_fisheries_and_forestry` |  | P1 | missing | 0 | 2025-26 PBS archive link - Agriculture, Fisheries and Forestry |
| `federal_pbs_2025_26_attorney_general_s_portfolio` |  | P1 | missing | 0 | 2025-26 PBS archive link - Attorney-General's Portfolio |
| `federal_pbs_2025_26_climate_change_energy_the_environment_and_water` |  | P1 | missing | 0 | 2025-26 PBS archive link - Climate Change, Energy, the Environment and Water |
| `federal_pbs_2025_26_defence_portfolio` |  | P1 | missing | 0 | 2025-26 PBS archive link - Defence Portfolio |
| `federal_pbs_2025_26_department_of_parliamentary_services` |  | P1 | missing | 0 | 2025-26 PBS archive link - Department of Parliamentary Services |
| `federal_pbs_2025_26_department_of_the_house_of_representatives` |  | P1 | missing | 0 | 2025-26 PBS archive link - Department of the House of Representatives |
| `federal_pbs_2025_26_department_of_the_senate_pbs` |  | P1 | missing | 0 | 2025-26 PBS archive link - Department of the Senate PBS |
| `federal_pbs_2025_26_education_portfolio` |  | P1 | missing | 0 | 2025-26 PBS archive link - Education Portfolio |
| `federal_pbs_2025_26_employment_and_workplace_relations` |  | P1 | missing | 0 | 2025-26 PBS archive link - Employment and Workplace Relations |
| `federal_pbs_2025_26_finance_portfolio` |  | P1 | missing | 0 | 2025-26 PBS archive link - Finance Portfolio |
| `federal_pbs_2025_26_foreign_affairs_and_trade` |  | P1 | missing | 0 | 2025-26 PBS archive link - Foreign Affairs and Trade |
| `federal_pbs_2025_26_health_disability_and_ageing` |  | P1 | missing | 0 | 2025-26 PBS archive link - Health, Disability and Ageing |
| `federal_pbs_2025_26_home_affairs_portfolio` |  | P1 | missing | 0 | 2025-26 PBS archive link - Home Affairs Portfolio |
| `federal_pbs_2025_26_industry_science_and_resources` |  | P1 | missing | 0 | 2025-26 PBS archive link - Industry, Science and Resources |
| `federal_pbs_2025_26_infrastructure_transport_regional_development_communications_sport_and_the_arts` |  | P1 | missing | 0 | 2025-26 PBS archive link - Infrastructure, Transport, Regional Development, Comm |
| `federal_pbs_2025_26_parliamentary_budget_office` |  | P1 | missing | 0 | 2025-26 PBS archive link - Parliamentary Budget Office |
| `federal_pbs_2025_26_prime_minister_and_cabinet` |  | P1 | missing | 0 | 2025-26 PBS archive link - Prime Minister and Cabinet |
| `federal_pbs_2025_26_social_services_portfolio` |  | P1 | downloaded | 0 | 2025-26 PBS archive link - Social Services Portfolio |
| `federal_pbs_2025_26_treasury_portfolio` |  | P1 | missing | 0 | 2025-26 PBS archive link - Treasury Portfolio |
| `federal_pbs_2025_26_veterans_affairs` |  | P1 | missing | 0 | 2025-26 PBS archive link - Veterans' Affairs |
| `federal_pbs_2026_27_agriculture` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Agriculture, Fisheries and Forestry |
| `federal_pbs_2026_27_attorney_general` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Attorney-General's Portfolio |
| `federal_pbs_2026_27_climate_energy_environment_water` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Climate Change, Energy, the Environment an |
| `federal_pbs_2026_27_employment_workplace` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Employment and Workplace Relations |
| `federal_pbs_2026_27_finance` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Finance Portfolio |
| `federal_pbs_2026_27_foreign_affairs_trade` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Foreign Affairs and Trade |
| `federal_pbs_2026_27_home_affairs` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Home Affairs Portfolio |
| `federal_pbs_2026_27_house_representatives` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Department of the House of Representatives |
| `federal_pbs_2026_27_parliamentary_budget_office` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Parliamentary Budget Office |
| `federal_pbs_2026_27_parliamentary_services` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Department of Parliamentary Services |
| `federal_pbs_2026_27_pmc` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Prime Minister and Cabinet |
| `federal_pbs_2026_27_senate` |  | P1 | missing | 0 | 2026-27 Portfolio Budget Statements - Department of the Senate PBS |
| `federal_pbs_2026_27_treasury` |  | P1 | downloaded | 0 | 2026-27 Portfolio Budget Statements - Treasury Portfolio |
| `qld_sds_machine_readable_2025_26` |  | P1 | missing | 0 | Queensland 2025-26 State Budget Service Delivery Statements - machine-readable d |
| `federal_bp1_statement10_history_2025_26` |  | P1 | downloaded | 0 | 2025-26 Budget Paper 1 Statement 10: Historical Data |
| `federal_bp1_statement6_debt_2025_26` |  | P1 | downloaded | 0 | 2025-26 Budget Paper 1 Statement 6: Debt Statement |
| `federal_bp1_statement7_debt_2024_25` |  | P1 | downloaded | 0 | 2024-25 Budget Paper 1 Statement 7: Debt Statement |
| `federal_bp1_statement7_debt_2026_27` |  | P1 | downloaded | 0 | Budget Paper 1 Statement 7: Debt Statement |
| `nsw_tcorp_weekly_bonds` |  | P1 | missing | 0 | TCorp weekly bonds report |
| `nt_nttc_annual_report_2024_25` |  | P1 | missing | 0 | NTTC Annual Report 2024-25 |
| `nt_nttc_borrowing_strategy` |  | P1 | missing | 0 | NTTC borrowing and financing strategies |
| `qld_qtc_benchmark_bonds` |  | P1 | missing | 0 | QTC AUD benchmark bonds |
| `sa_safa_funding_program_2026_27` |  | P1 | missing | 0 | SAFA FY2026-27 indicative funding program |
| `tas_tascorp_annual_report_2024_25` |  | P1 | missing | 0 | TASCORP Annual Report 2024-25 |
| `tas_tascorp_financial_markets` |  | P1 | missing | 0 | TASCORP financial markets |
| `vic_tcv_data_feeds` |  | P1 | missing | 0 | TCV data feeds |
| `wa_watc_annual_report_2025` |  | P1 | missing | 0 | WATC Annual Report 2025 |
| `wa_watc_investor_term_sheets` |  | P1 | missing | 0 | WATC investor term sheets |
| `federal_bp1_nominal_gdp_2026_27` |  | P1 | downloaded | 0 | Budget Paper 1 nominal GDP data |
| `federal_bp1_statement4_revenue_2025_26` |  | P1 | downloaded | 0 | 2025-26 Budget Paper 1 Statement 4: Revenue |
| `federal_bp1_statement5_revenue_2024_25` |  | P1 | downloaded | 0 | 2024-25 Budget Paper 1 Statement 5: Revenue |
| `federal_bp1_statement5_revenue_2026_27` |  | P1 | downloaded | 0 | Budget Paper 1 Statement 5: Revenue |
| `federal_revenue_machine_companions_2024_25` |  | P1 | missing | 0 | 2024-25 Budget revenue machine-readable companions |
| `federal_revenue_machine_companions_2025_26` |  | P1 | missing | 0 | 2025-26 Budget revenue machine-readable companions |
| `federal_revenue_machine_companions_2026_27` |  | P1 | missing | 0 | 2026-27 Budget revenue machine-readable companions |
| `nsw_local_grants_commission` |  | P1 | missing | 0 | NSW Local Government Grants Commission allocations and annual reports |
| `sa_lggc_annual_report_2024_25` |  | P1 | missing | 0 | SA Local Government Grants Commission Annual Report 2024-25 |
| `sa_lggc_publications_database_reports` |  | P1 | missing | 0 | SA Local Government Grants Commission publications and database reports |
| `wa_lggc_balance_budget_2024_25` |  | P1 | missing | 0 | WA Local Government Grants Commission Balance Budget 2024-25 |
| `wa_lggc_grant_schedules_2025_26` |  | P1 | missing | 0 | WA Local Government Grants Commission 2025-26 grant schedules |
| `abs_gfs_act_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS ACT general government |
| `act_budget_tables_2026_27` |  | P1 | already_on_disk | 0 | ACT Government 2026-27 Budget tables |
| `act_statement_a_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement A |
| `act_statement_b_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement B |
| `act_statement_c_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement C |
| `act_statement_d_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement D |
| `act_statement_e_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement E |
| `act_statement_f_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement F |
| `act_statement_g_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement G |
| `act_statement_h_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Budget Statement H |
| `act_summary_outputs_2026_27` |  | P1 | already_on_disk | 0 | ACT 2026-27 Summary of Outputs |
| `abs_gfs_all_levels_sector_2024_25` |  | P1 | already_on_disk | 0 | ABS GFS all levels by sector |
| `abs_gfs_australia_all_levels_2024_25` |  | P1 | already_on_disk | 0 | ABS GFS Australia all levels of government |
| `abs_gfs_control_nfd_2024_25` |  | P1 | already_on_disk | 0 | ABS GFS control not further defined total |
| `abs_gfs_key_tables_2024_25` |  | P1 | already_on_disk | 0 | ABS GFS Annual Key Tables |
| `abs_gfs_total_local_2024_25` |  | P1 | already_on_disk | 0 | ABS GFS total local government |
| `federal_agency_resourcing_bp4_2026_27` |  | P1 | already_on_disk | 0 | Budget Paper No. 4: Agency Resourcing 2026-27 |
| `federal_bp1_statement6_expenses_2024_25` |  | P1 | already_on_disk | 0 | 2024-25 Budget Paper 1 Statement 6: Expenses and Net Capital Investment |
| `federal_bp1_statement6_expenses_2026_27` |  | P1 | already_on_disk | 30 | Budget Paper 1 Statement 6: Expenses and Net Capital Investment |
| `federal_mfs_monthly_profiles` |  | P1 | already_on_disk | 288 | Monthly Financial Statements - Monthly Profiles |
| `federal_mfs_note3_function` |  | P1 | already_on_disk | 288 | Monthly Financial Statements - Note 3 Function Statement |
| `federal_pbs_2026_27_health_disability_ageing` |  | P1 | already_on_disk | 0 | 2026-27 Portfolio Budget Statements - Health, Disability and Ageing |
| `federal_pbs_2026_27_ndia` |  | P1 | already_on_disk | 0 | 2026-27 Portfolio Budget Statements - National Disability Insurance Agency entit |
| `federal_pbs_2026_27_social_services` |  | P1 | already_on_disk | 0 | 2026-27 Portfolio Budget Statements - Social Services Portfolio |
| `federal_pbs_2026_27_veterans_affairs` |  | P1 | already_on_disk | 0 | 2026-27 Portfolio Budget Statements - Veterans' Affairs |
| `abs_gfs_nsw_local_2024_25` |  | P1 | already_on_disk | 110 | ABS GFS NSW local government |
| `abs_gfs_nsw_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS NSW state general government |
| `nsw_bp4_agency_financial_statements_2026_27` |  | P1 | already_on_disk | 0 | NSW Budget Paper 4: Agency Financial Statements |
| `nsw_budgeted_financial_statements_2026_27` |  | P1 | already_on_disk | 0 | NSW 2026-27 budgeted financial statements |
| `nsw_economic_data_2026_27` |  | P1 | already_on_disk | 0 | NSW 2026-27 economic data |
| `nsw_historical_fiscal_indicators_2026_27` |  | P1 | already_on_disk | 0 | NSW 2026-27 historical fiscal indicators |
| `nsw_report_on_state_finances_actuals` |  | P1 | already_on_disk | 0 | NSW Report on State Finances |
| `abs_gfs_nt_local_2024_25` |  | P1 | already_on_disk | 110 | ABS GFS NT local government |
| `abs_gfs_nt_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS NT state general government |
| `nt_budget_paper2_2026_27` |  | P1 | already_on_disk | 0 | NT 2026-27 Budget Paper 2 |
| `nt_budget_paper3_2026_27` |  | P1 | already_on_disk | 0 | NT 2026-27 Budget Paper 3 |
| `nt_budget_paper4_2026_27` |  | P1 | already_on_disk | 0 | NT 2026-27 Budget Paper 4 |
| `nt_budget_speech_appropriation_2026_27` |  | P1 | already_on_disk | 0 | NT 2026-27 Budget Speech and Appropriation Bill |
| `abs_gfs_qld_local_2024_25` |  | P1 | already_on_disk | 110 | ABS GFS QLD local government |
| `abs_gfs_qld_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS QLD state general government |
| `qld_budget_strategy_outlook_2026_27` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Budget Strategy and Outlook |
| `qld_report_on_state_finances_actuals` |  | P1 | already_on_disk | 0 | Queensland Report on State Finances |
| `qld_sds_2026_27_corrective_services` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Queensland Corrective Services |
| `qld_sds_2026_27_customer_open_data_small_business` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Customer Services, Open Data an |
| `qld_sds_2026_27_environment_tourism_science_innovation` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Environment, Tourism, Science a |
| `qld_sds_2026_27_families_seniors_disability_child_safety` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Families, Seniors, Disability S |
| `qld_sds_2026_27_fire` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Queensland Fire Department |
| `qld_sds_2026_27_housing_public_works` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Housing and Public Works |
| `qld_sds_2026_27_justice` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Department of Justice |
| `qld_sds_2026_27_legislative_assembly` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Legislative Assembly of Queensl |
| `qld_sds_2026_27_local_government_water_volunteers` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Local Government, Water and Vol |
| `qld_sds_2026_27_natural_resources_mines_manufacturing_regions` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Natural Resources and Mines, Ma |
| `qld_sds_2026_27_police_emergency_inspector` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Queensland Police Service and I |
| `qld_sds_2026_27_premier_cabinet` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Department of the Premier and C |
| `qld_sds_2026_27_primary_industries` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Department of Primary Industrie |
| `qld_sds_2026_27_sport_racing_games` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Sport, Racing and Olympic and P |
| `qld_sds_2026_27_trade_employment_training` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Trade, Employment and Training |
| `qld_sds_2026_27_treasury` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Queensland Treasury |
| `qld_sds_2026_27_women_atsi_multicultural` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Women, Aboriginal and Torres St |
| `qld_sds_2026_27_youth_justice_victim_support` |  | P1 | already_on_disk | 0 | Queensland 2026-27 Service Delivery Statements - Youth Justice and Victim Suppor |
| `abs_gfs_sa_local_2024_25` |  | P1 | already_on_disk | 110 | ABS GFS SA local government |
| `abs_gfs_sa_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS SA state general government |
| `sa_agency_statements_v1_2026_27` |  | P1 | already_on_disk | 0 | South Australia 2026-27 Agency Statements Volume 1 |
| `sa_agency_statements_v2_2026_27` |  | P1 | already_on_disk | 0 | South Australia 2026-27 Agency Statements Volume 2 |
| `sa_agency_statements_v3_2026_27` |  | P1 | already_on_disk | 0 | South Australia 2026-27 Agency Statements Volume 3 |
| `sa_agency_statements_v4_2026_27` |  | P1 | already_on_disk | 0 | South Australia 2026-27 Agency Statements Volume 4 |
| `sa_budget_measures_2026_27` |  | P1 | already_on_disk | 0 | South Australia 2026-27 Budget Measures Statement |
| `sa_budget_statement_2026_27` |  | P1 | already_on_disk | 0 | South Australia 2026-27 Budget Statement |
| `abs_gfs_total_state_2024_25` |  | P1 | already_on_disk | 0 | ABS GFS total state and territory general government |
| `abs_gfs_tas_local_2024_25` |  | P1 | already_on_disk | 110 | ABS GFS TAS local government |
| `abs_gfs_tas_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS TAS state general government |
| `tas_budget_paper1_2026_27` |  | P1 | already_on_disk | 0 | Tasmania 2026-27 Budget Paper 1: Strategy and Estimates |
| `tas_budget_paper2_2026_27` |  | P1 | already_on_disk | 0 | Tasmania 2026-27 Budget Paper 2: Agency Information Appropriation Bill 1 |
| `tas_budget_paper3_2026_27` |  | P1 | already_on_disk | 0 | Tasmania 2026-27 Budget Paper 3: Agency Information Appropriation Bill 2 |
| `tas_budget_paper4_2026_27` |  | P1 | already_on_disk | 0 | Tasmania 2026-27 Budget Paper 4: Supplementary Budget Reports |
| `abs_gfs_vic_local_2024_25` |  | P1 | already_on_disk | 110 | ABS GFS VIC local government |
| `abs_gfs_vic_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS VIC state general government |
| `vic_department_performance_statement_2026_27` |  | P1 | already_on_disk | 0 | Victoria 2026-27 Department Performance Statement |
| `vic_service_delivery_2026_27` |  | P1 | already_on_disk | 0 | Victoria 2026-27 State Budget - Service Delivery |
| `vic_statement_finances_2026_27` |  | P1 | already_on_disk | 0 | Victoria 2026-27 State Budget - Statement of Finances |
| `abs_gfs_wa_local_2024_25` |  | P1 | already_on_disk | 110 | ABS GFS WA local government |
| `abs_gfs_wa_state_2024_25` |  | P1 | already_on_disk | 280 | ABS GFS WA state general government |
| `wa_agency_works_program_2026_27` |  | P1 | already_on_disk | 0 | WA 2026-27 Agency Works Program |
| `wa_budget_paper2_v1_2026_27` |  | P1 | already_on_disk | 0 | WA 2026-27 Budget Paper 2 Volume 1 |
| `wa_budget_paper2_v2_2026_27` |  | P1 | already_on_disk | 0 | WA 2026-27 Budget Paper 2 Volume 2 |
| `wa_budget_paper3_2026_27` |  | P1 | already_on_disk | 0 | WA 2026-27 Budget Paper 3 |
| `federal_bp1_statement11_history_2024_25` |  | P1 | already_on_disk | 34 | 2024-25 Budget Paper 1 Statement 11: Historical Data |
| `federal_bp1_statement11_history_2026_27` |  | P1 | already_on_disk | 34 | Budget Paper 1 Statement 11: Historical Australian Government Data |
| `federal_mfs_aggregates` |  | P1 | already_on_disk | 288 | Monthly Financial Statements - Aggregates |
| `federal_mfs_balance_sheet` |  | P1 | already_on_disk | 288 | Monthly Financial Statements - Balance Sheet |
| `federal_mfs_operating_statement` |  | P1 | already_on_disk | 288 | Monthly Financial Statements - Operating Statement |
| `federal_mfs_tax_notes_1_2` |  | P1 | already_on_disk | 288 | Monthly Financial Statements - Notes 1 and 2 taxation revenue |
| `nsw_local_time_series_historical_1994_2015` |  | P1 | already_on_disk | 2794 | NSW council historical time series 1994-2015 |
| `qld_qao_local_government_2025` |  | P1 | already_on_disk | 0 | Queensland Audit Office Local government 2025 report and dashboard |
| `tas_local_consolidated_data_collection` |  | P1 | already_on_disk | 2600 | Tasmanian Local Government Consolidated Data Collection |
| `vic_local_abs1_capital_2024_25` |  | P1 | already_on_disk | 889 | Victoria local government 2024-25 - ABS1 Capital Outlays and Sales |
| `vic_local_alg1_roads_2024_25` |  | P1 | already_on_disk | 889 | Victoria local government 2024-25 - ALG1 Road Length and Expenditure |
| `vic_local_lgv1_employment_2024_25` |  | P1 | already_on_disk | 889 | Victoria local government 2024-25 - LGV1 Council Employment |
| `vic_local_questionnaire_master_2024_25` |  | P1 | already_on_disk | 889 | Victoria local government 2024-25 - VLGGC Questionnaire master |
| `vic_local_vgc2_valuations_rates_2024_25` |  | P1 | already_on_disk | 889 | Victoria local government 2024-25 - VGC2 Valuations and Rates |
| `vic_local_vgc3_roads_2024_25` |  | P1 | already_on_disk | 889 | Victoria local government 2024-25 - VGC3 Local Roads |
| `dss_income_support_monthly_related_view` |  | P2 | already_on_disk | 0 | DSS Income Support Recipients - Monthly Time Series |
| `dss_jobseeker_monthly_profile_related_view` |  | P2 | already_on_disk | 0 | DSS JobSeeker and Youth Allowance monthly profile |
| `dss_payment_demographics_quarterly_related_view` |  | P2 | already_on_disk | 0 | DSS payment recipient demographics |
| `dss_payments_by_lga_related_view` |  | P2 | already_on_disk | 0 | DSS Payments by Local Government Area |
| `federal_austender_ocds_api_related_view` |  | P2 | already_on_disk | 0 | AusTender historical contract notices - OCDS |
| `federal_grantconnect_related_view` |  | P2 | already_on_disk | 0 | GrantConnect awards |
| `ndis_participant_datasets_related_view` |  | P2 | already_on_disk | 0 | NDIS participant datasets |
| `ndis_payment_datasets_related_view` |  | P2 | already_on_disk | 0 | NDIS payments datasets |
| `ndis_quarterly_reports_related_view` |  | P2 | already_on_disk | 0 | NDIS quarterly reports |
| `services_australia_annual_reports_related_view` |  | P2 | already_on_disk | 0 | Services Australia annual reports |
| `federal_financial_relations_bp3_2026_27` |  | P2 | already_on_disk | 0 | Budget Paper No. 3: Federal Financial Relations 2026-27 |
| `nt_local_grants_commission_reports` |  | P2 | missing | 0 | NT Grants Commission annual reports and council allocation schedules |
| `grantconnect_awards_by_agency` |  | P2 | already_on_disk | 0 | GrantConnect grants awarded data by agency |
| `commonwealth_balance_sheet_user_guide` |  | P2 | missing | 0 | Commonwealth Balance Sheet User Guide |
| `commonwealth_pss_css_long_term_cost_reports` |  | P2 | missing | 0 | PSS and CSS long-term cost reports |
| `commonwealth_superannuation_cost_reports` |  | P2 | missing | 0 | Commonwealth superannuation costs and reports |
| `csc_annual_report_archive` |  | P2 | missing | 0 | Commonwealth Superannuation Corporation annual report archive |
| `ato_corporate_tax_transparency_2023_24` |  | P2 | missing | 0 | Corporate tax transparency 2023-24 |
| `ato_gst_statistics_2022_23` |  | P2 | missing | 0 | ATO GST, WET and LCT statistics by year/month |
| `ato_taxation_statistics_index_2022_23` |  | P2 | missing | 0 | ATO Taxation statistics 2022-23 detailed table index |
| `sa_councils_in_focus` |  | P2 | missing | 0 | South Australia Councils in Focus |
| `wa_mycouncil` |  | P2 | missing | 0 | WA MyCouncil local government information and comparison |
| `abn_bulk_extract_resource_index` |  | P2 | missing | 0 | ABN Bulk Extract resource index |
| `abs_consumer_price_index` |  | P2 | missing | 0 | Consumer Price Index, Australia |
| `abs_population_national_state_territory` |  | P2 | missing | 0 | National, state and territory population |
| `abs_regional_population` |  | P2 | missing | 0 | Regional population |
| `anzsic_2006_revision_2` |  | P2 | missing | 0 | ANZSIC 2006 Revision 2 code titles |
| `cofog_a_classification` |  | P2 | missing | 0 | COFOG-A classification |
