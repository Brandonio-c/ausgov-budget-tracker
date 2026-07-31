# Adapter repair plan — 20260731T202041Z

Source audit: `ingestion-coverage-20260731T201730Z.json`

Total `adapter_missing` registry sources: 247

Already served by an existing family adapter (federal PBS generalized extractor, `pbs_programs_all` - see `ops/reports/pbs-reprocessing-20260731T193413Z.md`), pending Task 6 registry linkage so the audit reflects it directly: **67**

Genuinely un-adapted, acquired-on-disk sources remaining: **180**

All 247 `adapter_missing` sources have `acquisition_status: acquired` with at least one file on disk - none of this backlog is blocked on acquisition; every item below is ready for adapter engineering today.

## Methodology

Grouped by `(source_family, jurisdiction, government_level)` as a proxy for "one adapter handles this whole family's editions". Ranked by a composite score: `avg(viz_value_rank) * 2 - format_effort * 10 + min(count, 20)` - dashboard-value-weighted up, PDF/OCR-reliant work weighted down relative to structured (csv/xlsx) data already on disk, and multi-edition families rewarded for adapter-reuse potential. `format_effort`: csv/xlsx=1, docx/zip/html=2, pdf=3 (lower is better/cheaper).

## Ranked families

| rank | category | source_family | jurisdiction | level | count | avg_viz_rank | formats | score |
|---|---|---|---|---|---|---|---|---|
| 1 | contextual_other | handoff_gdp_tax_federal | Commonwealth | federal | 7 | 90.0 | csv,pdf,xlsx | 177.0 |
| 2 | historical_actuals | handoff_actuals_state | VIC | state | 6 | 90.0 | pdf,xlsx | 176.0 |
| 3 | historical_actuals | handoff_actuals_cross_level | Australia | cross_level | 5 | 90.0 | xlsx,zip | 175.0 |
| 4 | historical_actuals | handoff_actuals_state | NSW | state | 4 | 90.0 | pdf,xlsx | 174.0 |
| 5 | historical_actuals | handoff_actuals_state | QLD | state | 2 | 90.0 | pdf,xlsx | 172.0 |
| 6 | contextual_other | state_budget_open_data | NSW | state | 1 | 90.0 | pdf,xlsx | 171.0 |
| 7 | contextual_other | procurement_contracts | NSW | state | 1 | 90.0 | csv | 171.0 |
| 8 | historical_actuals | entity_actuals | VIC | state | 1 | 90.0 | pdf,xlsx | 171.0 |
| 9 | contextual_other | state_budget | WA | state | 1 | 90.0 | pdf,xlsx | 171.0 |
| 10 | historical_actuals | state_actuals | WA | state | 1 | 90.0 | pdf,xls,xlsx | 171.0 |
| 11 | contextual_other | state_budget | TAS | state | 1 | 90.0 | docx,pdf,xlsx | 171.0 |
| 12 | contextual_other | territory_budget | ACT | territory | 1 | 90.0 | pdf,xlsx | 171.0 |
| 13 | contextual_other | payment_timing_disclosure | QLD | state | 1 | 90.0 | csv | 171.0 |
| 14 | historical_actuals | handoff_actuals_state | TAS | state | 1 | 90.0 | pdf,xlsx | 171.0 |
| 15 | historical_actuals | handoff_actuals_cross_level | States and territories | cross_level | 1 | 90.0 | xlsx | 171.0 |
| 16 | contextual_other | handoff_reference_cross_level | Australia | cross_level | 3 | 90.0 | zip | 163.0 |
| 17 | historical_actuals | gfs_actuals | Australia | cross_level | 1 | 90.0 | zip | 161.0 |
| 18 | contextual_other | state_budget | NSW | state | 1 | 90.0 | docx,pdf | 161.0 |
| 19 | historical_actuals | handoff_actuals_federal | Commonwealth | federal | 5 | 82.0 | pdf,xlsx | 159.0 |
| 20 | historical_actuals | handoff_actuals_local | ACT | local | 9 | 90.0 | pdf | 159.0 |
| 21 | contextual_other | handoff_debt_federal | Commonwealth | federal | 6 | 90.0 | pdf | 156.0 |
| 22 | contextual_other | entity_annual_reports | Commonwealth | federal | 2 | 90.0 | pdf | 152.0 |
| 23 | contextual_other | procurement_contracts | Commonwealth | federal | 2 | 80.0 | csv,pdf,xlsx,zip | 152.0 |
| 24 | historical_actuals | handoff_actuals_territory | NT | territory | 2 | 90.0 | pdf | 152.0 |
| 25 | historical_actuals | handoff_actuals_state | SA | state | 2 | 90.0 | pdf | 152.0 |
| 26 | contextual_other | budget_measures | Commonwealth | federal | 1 | 90.0 | pdf | 151.0 |
| 27 | contextual_other | intergovernmental_transfers | Commonwealth and states | cross_level | 1 | 90.0 | pdf | 151.0 |
| 28 | contextual_other | agency_resourcing | Commonwealth | federal | 1 | 90.0 | pdf | 151.0 |
| 29 | historical_actuals | state_actuals | NSW | state | 1 | 90.0 | pdf | 151.0 |
| 30 | contextual_other | state_budget | VIC | state | 1 | 90.0 | pdf | 151.0 |
| 31 | historical_actuals | state_actuals | VIC | state | 1 | 90.0 | pdf | 151.0 |
| 32 | contextual_other | state_budget | QLD | state | 1 | 90.0 | pdf | 151.0 |
| 33 | historical_actuals | state_actuals | QLD | state | 1 | 90.0 | pdf | 151.0 |
| 34 | contextual_other | state_budget | SA | state | 1 | 90.0 | pdf | 151.0 |
| 35 | historical_actuals | state_actuals | TAS | state | 1 | 90.0 | pdf | 151.0 |
| 36 | contextual_other | procurement_contracts | TAS | state | 1 | 90.0 | pdf | 151.0 |
| 37 | historical_actuals | territory_actuals | ACT | territory | 1 | 90.0 | pdf | 151.0 |
| 38 | contextual_other | territory_budget | NT | territory | 1 | 90.0 | pdf | 151.0 |
| 39 | historical_actuals | territory_actuals | NT | territory | 1 | 90.0 | pdf | 151.0 |
| 40 | contextual_other | handoff_debt_state | ACT | state | 1 | 90.0 | pdf | 151.0 |
| 41 | historical_actuals | handoff_actuals_state | WA | state | 1 | 90.0 | pdf | 151.0 |
| 42 | contextual_other | recipient_statistics | Commonwealth | federal | 4 | 70.0 | csv,xlsx | 134.0 |
| 43 | contextual_other | grant_awards | Commonwealth | federal | 1 | 70.0 | xlsx | 131.0 |
| 44 | contextual_other | payment_aggregates | Commonwealth | federal | 1 | 70.0 | csv,docx,pdf,xls,xlsx,zip | 131.0 |
| 45 | contextual_other | participant_statistics | Commonwealth | federal | 1 | 70.0 | csv,docx,pdf,xls,xlsx,zip | 131.0 |
| 46 | historical_actuals | program_actuals | Commonwealth | federal | 1 | 70.0 | docx,pdf,xls,xlsx | 131.0 |
| 47 | contextual_other | program_forecast | Commonwealth | federal | 1 | 70.0 | docx,pdf,xls,xlsx | 131.0 |
| 48 | commonwealth_mfs | handoff_actuals_federal | Commonwealth | federal | 2 | 60.0 | xlsx | 112.0 |
| 49 | commonwealth_mfs | handoff_debt_federal | Commonwealth | federal | 2 | 60.0 | xlsx | 112.0 |
| 50 | commonwealth_mfs | handoff_gdp_tax_federal | Commonwealth | federal | 2 | 60.0 | xlsx | 112.0 |
| 51 | local_structured | handoff_local_local | VIC | local | 7 | 50.0 | xlsx | 97.0 |
| 52 | local_structured | handoff_local_local | NSW | local | 2 | 50.0 | xls,xlsx | 92.0 |
| 53 | local_structured | handoff_local_local | WA | local | 2 | 50.0 | xlsx | 92.0 |
| 54 | local_structured | local_budget | VIC | local | 1 | 50.0 | pdf,xlsx | 91.0 |
| 55 | local_structured | handoff_actuals_local | Australia | local | 1 | 50.0 | xlsx | 91.0 |
| 56 | contextual_other | handoff_gdp_tax_federal | Australia | federal | 11 | 39.1 | xlsx,zip | 79.2 |
| 57 | local_structured | handoff_local_local | SA | local | 1 | 50.0 | pdf | 71.0 |
| 58 | local_structured | handoff_local_local | TAS | local | 1 | 50.0 | pdf | 71.0 |
| 59 | state_structured | handoff_actuals_state | QLD | state | 19 | 40.0 | pdf | 69.0 |
| 60 | debt_super | handoff_debt_federal | Commonwealth | federal | 10 | 30.5 | csv,pdf,xlsx | 61.0 |
| 61 | state_structured | handoff_actuals_state | SA | state | 4 | 40.0 | pdf | 54.0 |
| 62 | state_structured | handoff_actuals_state | TAS | state | 4 | 40.0 | pdf | 54.0 |
| 63 | state_structured | handoff_actuals_territory | NT | territory | 3 | 40.0 | pdf | 53.0 |
| 64 | state_structured | handoff_actuals_state | WA | state | 3 | 40.0 | pdf | 53.0 |
| 65 | debt_super | handoff_debt_state | VIC | state | 2 | 30.0 | csv,xlsx | 52.0 |
| 66 | debt_super | handoff_debt_state | WA | state | 2 | 30.0 | pdf,zip | 42.0 |
| 67 | contextual_other | handoff_gdp_tax_cross_level | Australia | cross_level | 5 | 22.0 | xlsx,zip | 39.0 |
| 68 | debt_super | handoff_debt_state | TAS | state | 2 | 30.0 | pdf | 32.0 |
| 69 | debt_super | handoff_debt_state | NT | state | 1 | 30.0 | pdf | 31.0 |
| 70 | debt_super | handoff_debt_state | SA | state | 1 | 30.0 | pdf | 31.0 |

## Preferred category order (directive) vs actual ranking

- **Federal Monthly Financial Statements** (`commonwealth_mfs`): 3 families, 6 sources
- **Structured state budget / financial-statement packs** (`state_structured`): 5 families, 33 sources
- **Structured local-government files** (`local_structured`): 7 families, 15 sources
- **Debt / superannuation-liability files** (`debt_super`): 6 families, 18 sources
- **Historical actuals / archival series** (`historical_actuals`): 21 families, 48 sources
- **Lower-value contextual sources** (`contextual_other`): 28 families, 60 sources

## Sample source_ids per family (top 10 families)

### handoff_gdp_tax_federal (Commonwealth/federal) - score 177.0
- `federal_bp1_nominal_gdp_2026_27`
- `federal_bp1_statement4_revenue_2025_26`
- `federal_bp1_statement5_revenue_2024_25`
- `federal_bp1_statement5_revenue_2026_27`
- `federal_revenue_machine_companions_2024_25`

### handoff_actuals_state (VIC/state) - score 176.0
- `vic_annual_financial_statements_2024_25`
- `vic_budget_portfolio_outcomes_2024_25`
- `vic_output_performance_measures_2024_25`
- `vic_department_performance_statement_2026_27`
- `vic_service_delivery_2026_27`

### handoff_actuals_cross_level (Australia/cross_level) - score 175.0
- `abs_gfs_all_workbooks_2024_25`
- `abs_gfs_all_levels_sector_2024_25`
- `abs_gfs_australia_all_levels_2024_25`
- `abs_gfs_control_nfd_2024_25`
- `abs_gfs_key_tables_2024_25`

### handoff_actuals_state (NSW/state) - score 174.0
- `nsw_bp4_agency_financial_statements_2026_27`
- `nsw_economic_data_2026_27`
- `nsw_historical_fiscal_indicators_2026_27`
- `nsw_report_on_state_finances_actuals`

### handoff_actuals_state (QLD/state) - score 172.0
- `qld_budget_strategy_outlook_2026_27`
- `qld_report_on_state_finances_actuals`

### state_budget_open_data (NSW/state) - score 171.0
- `nsw_budget_open_data_2026_27`

### procurement_contracts (NSW/state) - score 171.0
- `nsw_buy_register`

### entity_actuals (VIC/state) - score 171.0
- `vic_dtf_annual_report_bpo`

### state_budget (WA/state) - score 171.0
- `wa_budget_2026_27`

### state_actuals (WA/state) - score 171.0
- `wa_annual_report_state_finances_2024_25`

