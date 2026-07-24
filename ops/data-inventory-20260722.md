# AusGov Budget Tracker — Exhaustive Data Inventory

Generated: 2026-07-22T22:58:02Z
Scope: `ausgov-budget-tracker/` registry + everything under `data/`

## Executive summary

| Metric | Value |
|---|---|
| Registry sources | **82** |
| Sources with `latest.json` assets | **73** (89%) |
| Empty sources | **9** |
| Assets recorded in latest.json | **2,538** |
| Files under `data/raw` (excl. latest.json) | **9,178** |
| Raw data bytes | **8.10 GB** |
| Full `data/` tree (du) | **~8.2 GB** |
| Quarantine | **~0.47 GB** / 1,024 files |
| Manual `_downloads` staging | **135.1 MB** / 8 files |

## Disk by government level (`data/raw`)

| Level | Sources | Assets | Size |
|---|---:|---:|---:|
| federal | 26 | 1412 | 6.21 GB |
| state | 25 | 976 | 1.55 GB |
| territory | 8 | 74 | 0.21 GB |
| local | 12 | 74 | 0.12 GB |
| cross_level | 2 | 2 | 0.01 GB |

## Priority coverage

| Priority | With data / total | Raw bytes | Assets |
|---|---|---:|---:|
| P1 | 28/30 | 0.74 GB | 352 |
| P2 | 42/44 | 6.54 GB | 2159 |
| P3 | 2/3 | 0.81 GB | 25 |
| P4 | 1/5 | 0.01 GB | 2 |

## Asset format mix (from latest.json filenames)

| Extension | Count |
|---|---:|
| `.pdf` | 1377 |
| `.csv` | 489 |
| `.xlsx` | 430 |
| `.docx` | 175 |
| `.zip` | 22 |
| `.jsonl.gz` | 22 |
| `.xls` | 15 |
| `.doc` | 4 |
| `.cs` | 2 |
| `.htm` | 2 |

## Files placed in `data/manual_inbox/_downloads` (analysed)

| File | Size | ~Rows | Maps to | Status | Notes |
|---|---:|---:|---|---|---|
| `contract-disclosure-historical-data-2010-2020.csv` | 89.3 MB | 506927 | `qld_contract_disclosure_agency_datasets` | Already in latest.json | QLD historical contract disclosure 2010–2020 (~531k rows); also listed in contract disclosure manifest |
| `dyj-contract-disclosure-18dec-2023-30apr-2024.csv` | 39.2 MB | 2427 | `qld_contract_disclosure_agency_datasets` | Already in latest.json | Already imported earlier this session as families rewrite of dcssds URL |
| `rdmw-contract-disclosures-for-2021-22.csv` | 0.0 MB | 106 | `qld_contract_disclosure_agency_datasets` | Already in latest.json | Already imported via Wayback |
| `notices-report.csv` | 6.5 MB | 17178 | `nsw_buy_register` | New / needs review | NSW eTendering notices export columns (Department/Agency, Notice ID, …) |
| `queensland-treasury-corporation-contracts-disclosure-2025-261-4.csv` | 0.1 MB | 220 | `qld_contract_disclosure_agency_datasets` | Already in latest.json | QTC contract disclosure FY2025–26 style columns |
| `upcoming_cs_conferences_2026-2027_v2.csv` | 0.0 MB | 118 | `—` | Out of scope | NOT procurement — upcoming CS conferences calendar; out of scope for budget tracker |

### Detail on user drops

1. **`contract-disclosure-historical-data-2010-2020.csv`** (~89 MB, ~507k rows) — QLD historical contract disclosure columns (`year,month,contract value,procuremethod,supplier…`). Already committed under `qld_contract_disclosure_agency_datasets`.
2. **`dyj-contract-disclosure-18dec-2023-30apr-2024.csv`** (~39 MB) — standard QLD disclosure template; already imported (families host rewrite).
3. **`rdmw-contract-disclosures-for-2021-22.csv`** (~26 KB, 106 rows) — already imported (Wayback recovery).
4. **`queensland-treasury-corporation-contracts-disclosure-2025-261-4.csv`** (~55 KB, 220 rows) — QTC disclosure; already in latest.json.
5. **`notices-report.csv`** (~6.5 MB) — NSW eTendering notice export. **SHA-256 identical** to existing `nsw_buy_register__contract_awards_notice_report_2020-2026.csv` (already on disk). No new import needed.
6. **`upcoming_cs_conferences_2026-2027_v2.csv`** (~41 KB, 118 rows) — CS conference calendar. **Not a budget/procurement source**; leave unimported or delete from inbox.

## Empty registry sources

| ID | Priority | Level | Access method | Title |
|---|---|---|---|---|
| `federal_austender_weekly_export` | P2 | federal | ckan_api | AusTender Contract Notice Export |
| `wa_mycouncil` | P1 | local | landing_page_discovery | MyCouncil local government information and comparison |
| `wa_tenders` | P4 | state | landing_page_discovery | Tenders WA awarded contracts |
| `sa_councils_in_focus` | P1 | local | manual | Councils in Focus |
| `sa_tenders_contracts` | P4 | state | manual | SA Tenders and Contracts |
| `tas_procurement` | P4 | state | landing_page_discovery | Tasmanian purchasing and eTendering |
| `nt_local_grants_commission_return` | P4 | local | landing_page_discovery | Northern Territory Grants Commission Annual Return |
| `sa_lggc_council_database_reports` | P2 | local | direct_file | SA LGGC Database Reports (council financial and general data) |
| `nt_grants_commission_annual_reports` | P3 | local | landing_page_discovery | NT Grants Commission Annual Reports (council allocation and population schedules) |

Notes:
- `federal_austender_weekly_export` — deprecated / superseded by OCDS + historical CN.
- `sa_councils_in_focus`, `sa_tenders_contracts`, `wa_mycouncil`, `wa_tenders`, `tas_procurement`, `nt_local_grants_commission_return` — classified no_bulk / browse-only or no machine export.
- `sa_lggc_council_database_reports`, `nt_grants_commission_annual_reports` — Cloudflare-blocked from this host; browser session still required.

## Top 15 sources by size

| # | Source ID | Level | Assets | Size |
|---:|---|---|---:|---:|
| 1 | `ndis_financial_sustainability_reports` | federal | 368 | 1477.6 MB |
| 2 | `ndis_quarterly_reports` | federal | 379 | 1471.2 MB |
| 3 | `federal_austender_ocds_api` | federal | 18 | 886.5 MB |
| 4 | `federal_historical_cn_data_1999_2020` | federal | 15 | 782.6 MB |
| 5 | `ndis_participant_datasets` | federal | 233 | 675.1 MB |
| 6 | `ndis_payment_datasets` | federal | 233 | 675.0 MB |
| 7 | `qld_contract_disclosure_agency_datasets` | state | 239 | 332.5 MB |
| 8 | `qld_qgip_expenditure` | state | 15 | 209.6 MB |
| 9 | `tas_treasurers_annual_financial_reports` | state | 89 | 174.4 MB |
| 10 | `nt_treasury_annual_reports` | territory | 45 | 168.1 MB |
| 11 | `qld_report_on_state_finances` | state | 187 | 144.2 MB |
| 12 | `wa_annual_report_state_finances_2024_25` | state | 99 | 112.8 MB |
| 13 | `nsw_report_on_state_finances` | state | 24 | 94.0 MB |
| 14 | `tas_budget_2026_27` | state | 40 | 80.8 MB |
| 15 | `qld_budget_2026_27` | state | 50 | 74.1 MB |

## Complete registry coverage (all 82)

| Status | P | Level | Source ID | Assets | Size | Method | Publisher |
|---|---|---|---|---:|---:|---|---|
| have | P1 | cross_level | `federal_financial_relations_bp3_2026_27` | 1 | 5.1 MB | direct_file | Australian Government Treasury |
| have | P1 | cross_level | `abs_gfs_annual_all_workbooks` | 1 | 4.4 MB | direct_file | Australian Bureau of Statistics |
| have | P2 | federal | `ndis_financial_sustainability_reports` | 368 | 1477.6 MB | landing_page_discovery | Australian Government |
| have | P2 | federal | `ndis_quarterly_reports` | 379 | 1471.2 MB | landing_page_discovery | Australian Government |
| have | P2 | federal | `federal_austender_ocds_api` | 18 | 886.5 MB | ocds_api | Australian Government Department of Finance |
| have | P3 | federal | `federal_historical_cn_data_1999_2020` | 15 | 782.6 MB | ckan_api | Australian Government Department of Finance |
| have | P2 | federal | `ndis_participant_datasets` | 233 | 675.1 MB | landing_page_discovery | Australian Government |
| have | P2 | federal | `ndis_payment_datasets` | 233 | 675.0 MB | landing_page_discovery | Australian Government |
| have | P2 | federal | `federal_transparency_portal` | 16 | 66.3 MB | landing_page_discovery | Australian Government Department of Finance |
| have | P2 | federal | `federal_cfs_2024_25` | 1 | 62.5 MB | manual | Australian Government Department of Finance |
| have | P2 | federal | `federal_grantconnect` | 13 | 35.7 MB | web_portal | Australian Government Department of Finance |
| have | P2 | federal | `services_australia_annual_reports` | 6 | 22.5 MB | manual | Australian Government |
| have | P2 | federal | `dss_jobseeker_monthly_profile` | 81 | 18.1 MB | ckan_api | Australian Government |
| have | P1 | federal | `federal_monthly_financial_statements` | 10 | 6.8 MB | ckan_api | Australian Government Department of Finance |
| have | P1 | federal | `federal_agency_resourcing_bp4_2026_27` | 1 | 6.2 MB | direct_file | Australian Government Department of Finance |
| have | P1 | federal | `federal_social_services_pbs_2025_26_archive` | 1 | 4.1 MB | manual | Australian Government Department of Social Services |
| have | P1 | federal | `federal_health_disability_ageing_pbs_2026_27` | 1 | 4.0 MB | manual | Australian Government Department of Health, Disability and Ageing |
| have | P2 | federal | `dss_payment_demographics_quarterly` | 21 | 3.8 MB | ckan_api | Australian Government |
| have | P1 | federal | `federal_dss_pbs_2026_27` | 1 | 3.2 MB | manual | Australian Government Department of Social Services |
| have | P2 | federal | `dss_payments_by_lga` | 5 | 2.7 MB | ckan_api | Australian Government |
| have | P2 | federal | `federal_budget_measures_bp2_2026_27` | 1 | 2.1 MB | direct_file | Australian Government Treasury |
| have | P1 | federal | `federal_dva_pbs_2026_27` | 1 | 1.9 MB | manual | Australian Government Department of Veterans' Affairs |
| have | P1 | federal | `federal_pbs_index_2026_27` | 2 | 1.5 MB | landing_page_discovery | Australian Government Treasury |
| have | P2 | federal | `dss_income_support_monthly` | 1 | 0.9 MB | ckan_api | Australian Government |
| have | P1 | federal | `federal_budget_statement_6_2026_27` | 1 | 0.8 MB | direct_file | Australian Government Treasury |
| have | P1 | federal | `federal_ndia_pbs_2026_27` | 1 | 0.4 MB | manual | National Disability Insurance Agency |
| have | P1 | federal | `federal_fbo_2024_25_function_subfunction` | 1 | 0.3 MB | direct_file | Australian Government Department of the Treasury |
| have | P1 | federal | `abs_gfs_commonwealth_130` | 1 | 0.2 MB | direct_file | Australian Bureau of Statistics |
| missing | P2 | federal | `federal_austender_weekly_export` | 0 | — | ckan_api | Australian Government Department of Finance |
| have | P1 | local | `nsw_local_olg_time_series` | 31 | 41.1 MB | landing_page_discovery | NSW Office of Local Government |
| have | P1 | local | `tas_local_cdc` | 2 | 30.3 MB | manual | Tasmanian Department of Premier and Cabinet |
| have | P3 | local | `vic_local_budget_and_reporting_models` | 10 | 27.4 MB | manual | Local Government Victoria |
| have | P2 | local | `qld_local_qao_2025` | 13 | 13.0 MB | landing_page_discovery | Queensland Audit Office |
| have | P1 | local | `vic_local_vgc_abs_returns` | 11 | 3.4 MB | manual | Local Government Victoria / Victoria Grants Commission |
| have | P1 | local | `abs_gfs_local_nt_337` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P1 | local | `abs_gfs_local_nsw_331` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P1 | local | `abs_gfs_local_tas_336` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P1 | local | `abs_gfs_local_sa_334` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P1 | local | `abs_gfs_local_qld_333` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P1 | local | `abs_gfs_local_vic_332` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P1 | local | `abs_gfs_local_wa_335` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| missing | P3 | local | `nt_grants_commission_annual_reports` | 0 | — | landing_page_discovery | NT Department of Housing, Local Government and Community Development |
| missing | P4 | local | `nt_local_grants_commission_return` | 0 | — | landing_page_discovery | Northern Territory Grants Commission |
| missing | P1 | local | `sa_councils_in_focus` | 0 | — | manual | South Australian Department for Infrastructure and Transport |
| missing | P2 | local | `sa_lggc_council_database_reports` | 0 | — | direct_file | SA Department for Infrastructure and Transport (Local Government Grants Commission) |
| missing | P1 | local | `wa_mycouncil` | 0 | — | landing_page_discovery | Western Australian Government |
| have | P1 | state | `qld_contract_disclosure_agency_datasets` | 239 | 332.5 MB | ckan_api | Queensland Government (per-agency) |
| have | P1 | state | `qld_qgip_expenditure` | 15 | 209.6 MB | manual | Queensland Government |
| have | P2 | state | `tas_treasurers_annual_financial_reports` | 89 | 174.4 MB | landing_page_discovery | Tasmanian Department of Treasury and Finance |
| have | P2 | state | `qld_report_on_state_finances` | 187 | 144.2 MB | landing_page_discovery | Queensland Treasury |
| have | P2 | state | `wa_annual_report_state_finances_2024_25` | 99 | 112.8 MB | landing_page_discovery | Western Australian Treasury |
| have | P2 | state | `nsw_report_on_state_finances` | 24 | 94.0 MB | landing_page_discovery | NSW Treasury |
| have | P2 | state | `tas_budget_2026_27` | 40 | 80.8 MB | landing_page_discovery | Tasmanian Department of Treasury and Finance |
| have | P2 | state | `qld_budget_2026_27` | 50 | 74.1 MB | landing_page_discovery | Queensland Treasury |
| have | P2 | state | `wa_budget_2026_27` | 106 | 67.3 MB | landing_page_discovery | Western Australian Treasury |
| have | P1 | state | `nsw_procurement_ocds_registry` | 22 | 64.9 MB | landing_page_discovery | NSW Treasury (via Open Contracting Partnership Data Registry) |
| have | P2 | state | `nsw_budget_2026_27` | 13 | 60.3 MB | landing_page_discovery | NSW Treasury |
| have | P2 | state | `sa_budget_2026_27` | 8 | 41.1 MB | manual | South Australian Department of Treasury and Finance |
| have | P2 | state | `nsw_budget_open_data_2026_27` | 16 | 28.9 MB | landing_page_discovery | NSW Treasury |
| have | P2 | state | `vic_budget_2026_27` | 8 | 24.9 MB | manual | Victorian Department of Treasury and Finance |
| have | P2 | state | `sa_final_budget_outcome_and_cfr` | 2 | 11.8 MB | manual | South Australian Department of Treasury and Finance |
| have | P2 | state | `vic_dtf_annual_report_bpo` | 7 | 10.0 MB | manual | Victorian Department of Treasury and Finance |
| have | P2 | state | `vic_financial_report_2024_25` | 1 | 9.5 MB | manual | Victorian Department of Treasury and Finance |
| have | P4 | state | `nsw_buy_register` | 2 | 7.7 MB | manual | NSW Government |
| have | P2 | state | `qld_on_time_payment_reports` | 42 | 0.2 MB | ckan_api | Queensland Government (per-agency) |
| have | P2 | state | `abs_gfs_state_tas_236` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P2 | state | `abs_gfs_state_qld_233` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P2 | state | `abs_gfs_state_vic_232` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P2 | state | `abs_gfs_state_sa_234` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P2 | state | `abs_gfs_state_nsw_231` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P2 | state | `abs_gfs_state_wa_235` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| missing | P4 | state | `sa_tenders_contracts` | 0 | — | manual | South Australian Government |
| missing | P4 | state | `tas_procurement` | 0 | — | landing_page_discovery | Tasmanian Department of Treasury and Finance |
| missing | P4 | state | `wa_tenders` | 0 | — | landing_page_discovery | Western Australian Government |
| have | P2 | territory | `nt_treasury_annual_reports` | 45 | 168.1 MB | manual | Northern Territory Department of Treasury and Finance |
| have | P2 | territory | `act_budget_2026_27` | 23 | 22.7 MB | manual | ACT Treasury |
| have | P1 | territory | `act_notifiable_invoices` | 1 | 15.9 MB | socrata_api | ACT Government |
| have | P2 | territory | `nt_budget_2026_27` | 1 | 4.4 MB | manual | Northern Territory Treasury |
| have | P2 | territory | `act_actual_financial_publications` | 1 | 0.8 MB | manual | ACT Treasury |
| have | P1 | territory | `nt_awarded_government_contracts` | 1 | 0.3 MB | direct_file | Northern Territory Government |
| have | P2 | territory | `abs_gfs_state_act_238` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |
| have | P2 | territory | `abs_gfs_state_nt_237` | 1 | 0.1 MB | direct_file | Australian Bureau of Statistics |

## Other `data/` contents

| Path | Files | Size | Role |
|---|---:|---:|---|
| `data/.procurement` | 382 | 41.4 MB | Browser profiles for headed/WAF downloads |
| `data/ausgov_budget_hierarchical_schema.sql` | 1 | 0.0 MB | Draft schema DDL |
| `data/ausgov_budget_source_research.md` | 1 | 0.0 MB | Research notes |
| `data/ausgov_budget_tracker_candidate_sources.yml` | 1 | 0.1 MB | Earlier candidate registry dump |
| `data/processed` | 1 | 4.2 MB | SQLite stub `spending.db` (4 MB) |
| `data/quarantine` | 1024 | 469.2 MB | Superseded/duplicate acquisition artefacts (not authoritative) |

### Manual inbox source folders

28 per-source staging directories under `data/manual_inbox/` (URL manifests, upload helpers). Largest:

| Folder | Files | Size |
|---|---:|---:|
| `qld_contract_disclosure_agency_datasets` | 15 | 0.2 MB |
| `qld_on_time_payment_reports` | 5 | 0.0 MB |
| `federal_health_disability_ageing_pbs_2026_27` | 1 | 0.0 MB |
| `federal_ndia_pbs_2026_27` | 1 | 0.0 MB |
| `federal_dss_pbs_2026_27` | 1 | 0.0 MB |
| `federal_social_services_pbs_2025_26_archive` | 1 | 0.0 MB |
| `federal_dva_pbs_2026_27` | 1 | 0.0 MB |
| `vic_local_vgc_abs_returns` | 1 | 0.0 MB |
| `tas_local_cdc` | 1 | 0.0 MB |
| `nt_treasury_annual_reports` | 1 | 0.0 MB |
| `qld_qgip_expenditure` | 1 | 0.0 MB |
| `act_actual_financial_publications` | 1 | 0.0 MB |
| `sa_councils_in_focus` | 1 | 0.0 MB |
| `federal_cfs_2024_25` | 1 | 0.0 MB |
| `sa_budget_2026_27` | 1 | 0.0 MB |

## Project artefacts outside `data/`

- `config/procurement_sources.yaml` — authoritative 82-source registry
- `reports/procurement/` — acquisition reconcile runs (~7.4 MB)
- `ops/` — handoffs, acquisition status, research findings
- `scripts/procure*.py` + `scripts/procure/` — acquisition, CKAN adapters, manual import, upload receiver

## Gaps still actionable

1. SA LGGC PDF + NT grants commission annual reports — Cloudflare; need headed browser
2. QLD contract disclosure: 8 manifest URLs permanently dead (6× data.qld 404/403, 3× retired dcdss hosts with no Wayback) — accept as coverage ceiling ~239/249
3. QLD on-time: 1 dead dcdss file — 42/43
4. Remove or ignore `upcoming_cs_conferences_2026-2027_v2.csv` from `_downloads`
5. Optional: delete duplicate unprefixed copies already in latest.json to reclaim ~135 MB staging

