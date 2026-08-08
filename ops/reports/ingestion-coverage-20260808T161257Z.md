# Ingestion coverage audit (20260808T161257Z)

- Registry sources: **367**
- Audit rows (registry + orphans): **367**
- facts.db total facts: **289,315**
- Mapping YAML files: **126**

## Status counts

- `fully_ingested`: **44**
- `partially_ingested`: **67**
- `adapter_missing`: **172**
- `adapter_broken`: **29**
- `reference_only`: **5**
- `duplicate_source`: **31**
- `officially_unavailable`: **7**
- `not_acquired`: **12**
- `not_acquired`: **12**

## Priority backlog (top 40)

| rank | status | source_id | viz_bucket | facts | next |
|---:|---|---|---|---:|---|
| 10 | `adapter_broken` | `federal_pbs_2026_27_ndia` | commonwealth_pbs_program_depth | 0 | fix_or_re_run_adapter |
| 20 | `adapter_missing` | `abs_asna_all_workbooks_2024_25` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_asna_income_gdp_2024_25` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_broken` | `abs_asna_key_aggregates_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_missing` | `abs_qna_all_workbooks_mar_2026` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_qna_expenditure_current_price_mar_2026` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_qna_expenditure_volume_mar_2026` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_qna_industry_gva_annual_mar_2026` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_qna_industry_gva_current_price_mar_2026` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_qna_industry_gva_mar_2026` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_broken` | `abs_qna_key_aggregates_mar_2026` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_act_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_missing` | `abs_state_accounts_all_2024_25` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_state_accounts_aus_2024_25` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_missing` | `abs_state_accounts_gsp_all_2024_25` | gdp_gva_gsp | 0 | build_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_nsw_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_nt_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_qld_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_sa_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_tas_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_vic_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 20 | `adapter_broken` | `abs_state_accounts_wa_2024_25` | gdp_gva_gsp | 0 | fix_or_re_run_adapter |
| 25 | `adapter_missing` | `abs_taxation_revenue_all_downloads_2024_25` | tax_revenue_detail | 0 | build_adapter |
| 25 | `adapter_missing` | `abs_taxation_revenue_detailed_tables_2024_25` | tax_revenue_detail | 0 | build_adapter |
| 25 | `adapter_broken` | `abs_taxation_revenue_key_tables_2024_25` | tax_revenue_detail | 0 | fix_or_re_run_adapter |
| 30 | `adapter_missing` | `aofm_foreign_holdings` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_missing` | `aofm_portfolio_aggregate_dealt` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_missing` | `aofm_portfolio_aggregate_settlement` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_missing` | `aofm_portfolio_executive_summary_dealt` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_missing` | `aofm_register_government_borrowing` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_missing` | `aofm_stock_ags_csv` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_broken` | `aofm_treasury_bonds_dealt` | debt_instruments | 0 | fix_or_re_run_adapter |
| 30 | `adapter_missing` | `aofm_treasury_bonds_settlement` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_broken` | `aofm_treasury_indexed_bonds_dealt` | debt_instruments | 0 | fix_or_re_run_adapter |
| 30 | `adapter_missing` | `aofm_treasury_indexed_bonds_settlement` | debt_instruments | 0 | build_adapter |
| 30 | `adapter_broken` | `aofm_treasury_notes_dealt` | debt_instruments | 0 | fix_or_re_run_adapter |
| 30 | `adapter_missing` | `aofm_treasury_notes_settlement` | debt_instruments | 0 | build_adapter |
| 30 | `partially_ingested` | `nsw_tcorp_bonds_on_issue` | debt_instruments | 36 | continue_canonical_dataset_ingestion |
| 30 | `adapter_broken` | `nsw_tcorp_weekly_bonds` | debt_instruments | 0 | fix_or_re_run_adapter |
| 30 | `adapter_missing` | `nt_nttc_annual_report_2024_25` | debt_instruments | 0 | build_adapter |
