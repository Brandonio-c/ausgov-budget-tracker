# AusGov Budget Tracker — Manual Acquisition Status (follow-up)

Date: 2026-07-22
Supplements: `ops/manual-acquisition-handoff-20260722.md`

## Pipeline delivered this session

| Tool | Role |
|---|---|
| `scripts/procure/storage.py` `update_latest(..., merge=True)` | Multi-file manuals accumulate in `latest.json` |
| `scripts/procure_manual_import.py` | Uses merge; records `retrieved_at` |
| `scripts/procure_manual_import_batch.py` | Passes `--source-url` from `.url` sidecars or `manifest.json` |
| `scripts/procure_acquisition_queue.py` | Live need/done/no_bulk/flaky/candidate queue |
| `scripts/procure_browser_session.py` | Headed/headless Playwright + persistent profiles; pauses on challenge; `--urls-file` |
| `scripts/procure_upload_receiver.py` | Browser → `127.0.0.1:8765` upload; unwraps multipart; `Access-Control-Allow-Private-Network` |
| `scripts/procure/validation.py` | CSV detect/read accepts cp1252/latin-1 (QGIP) |
| `scripts/procure_write_url_manifest.py` | Stage URL lists for human/browser downloads |
| NT `nt_awarded_government_contracts` | Reclassified to `direct_file` ExportTenderers |
| QAO `qld_local_qao_2025` | Sparse retries (`flaky_max_attempts` / `flaky_gap_seconds`) |

Policy unchanged: no CAPTCHA solving / header spoofing. Headed browser may pause for a human.

## Research integration (2026-07-22 afternoon)

Six sources added from `ops/research-findings-20260722.md` (registry now **82** sources).

| Source | Status | On disk |
|---|---|---|
| `nsw_procurement_ocds_registry` | **done** | 22 JSONL.GZ (~63 MB) — OCP pub 11 |
| `federal_historical_cn_data_1999_2020` | **done** | 15 files (~747 MB) |
| `qld_contract_disclosure_agency_datasets` | **near-complete** | **239** assets in `latest.json` (~331 MB). Remaining **8** are dead links (6× data.qld 404/403; 2× dcdss on retired cyjma/communities hosts — no Wayback). Agency leftovers acquired via host rewrites (`families`/`detsi`/`dwatsipm`) + Wayback for RDMW 2021–22. |
| `qld_on_time_payment_reports` | **near-complete** | **42/43** in `latest.json`. Only missing: `dcdss-ontimepayments.csv` (cyjma URL dead; no archive). |
| `sa_lggc_council_database_reports` | **need browser** | Cloudflare 403 from server; headed `procure_browser_session.py` required |
| `nt_grants_commission_annual_reports` | **need browser** | Landing page behind Cloudflare; 0 assets discovered server-side |

**Code:** CKAN `package_search` adapter, query-param suffix discovery, gzip validation.

**Queue counts (approx):** `done=73` (+4 new with ≥1 file), `no_bulk=6`, browser-pending SA/NT.

## Disk truth after full acquisition pass

**Queue counts (pre-research):** `done=69`, `no_bulk=6` (of 76 registry sources). No remaining `need` / `flaky`.

### Acquired this session (high-signal)

| Source | Assets (approx) | How |
|---|---|---|
| `act_budget_2026_27` | 23 | Cursor browser + upload |
| `nt_treasury_annual_reports` | 45 | Cursor browser + upload |
| `sa_budget_2026_27` | 8 | Cursor browser + upload |
| `vic_budget_2026_27` | 8 | Public S3 PDFs (server curl) |
| `vic_financial_report_2024_25` | 1 | Direct DTF file path |
| `vic_dtf_annual_report_bpo` | 7 | Direct DTF file paths |
| `qld_qgip_expenditure` | 15 | Cursor browser after data.qld.gov.au clearance |
| `services_australia_annual_reports` | 6 | Cursor browser + direct PDF paths |
| `sa_final_budget_outcome_and_cfr` | 2 | Cursor browser (2024-25 FBO + CFR) |
| `tas_local_cdc` | 2 | LIST open-data zip repositories |
| `vic_local_vgc_abs_returns` | 11 | Cursor browser (2024-25 + sample 2023-24) |
| `vic_local_budget_and_reporting_models` | 10 | Cursor browser (model budget/report + summaries) |
| `nsw_buy_register` | 2 | Notice-reports CSV export (awards + standing offers, 2020–2026) |
| `nt_awarded_government_contracts` | 1 | Date-bounded ExportTenderers xlsx |
| `qld_local_qao_2025` | 13 | Report PDF + appendices A–K (dashboard is interactive only) |
| `federal_grantconnect` | 13 | Quarterly Grant Award Published xlsx (publish date), FY2023–24 through Jul 2026 |
| `nsw_procurement_ocds_registry` | 22 | OCP NSW OCDS JSONL.GZ per-year exports |
| `federal_historical_cn_data_1999_2020` | 15 | data.gov.au historical CN archive |
| `qld_contract_disclosure_agency_datasets` | 1 | CKAN crawl; bulk blocked by WAF — browser batch pending |
| `qld_on_time_payment_reports` | 1 | Same WAF pattern |

### Remaining (no public bulk)

| Source | Status | Notes |
|---|---|---|
| `sa_councils_in_focus` | **no_bulk** | Interactive dashboard only |
| `sa_tenders_contracts` | **no_bulk** | Agency-by-agency browse |
| `federal_austender_weekly_export` | **no_bulk** | (pre-existing) |
| `nt_local_grants_commission_return` | **no_bulk** | (pre-existing) |
| `wa_tenders` | **no_bulk** | (pre-existing) |
| `wa_mycouncil` | **no_bulk** | (pre-existing) |
| `sa_lggc_council_database_reports` | **browser** | LGGC Database Reports PDF — Cloudflare |
| `nt_grants_commission_annual_reports` | **browser** | Territory Stories PDFs — Cloudflare landing |

### Completeness caveats

- `nt_awarded_government_contracts`: full unbounded export times out; current file is date-bounded.
- `nsw_buy_register`: two notice-report CSVs for notice types `can`/`son` over 2020-01-01–2026-07-22.
- `federal_grantconnect`: anonymous date-windowed exports (≤50k/query). Full FY often exceeds the cap; stored as quarterly publish-date slices. GrantConnect CSP blocks `fetch` to localhost — upload via multipart **form POST** (iframe) instead. Earlier years can be pulled the same way.
- `qld_local_qao_2025`: report + appendices; interactive dashboard has no bulk CSV/XLSX export discovered.

## Re-check

```bash
conda activate ausgov-budget-tracker
python scripts/procure_acquisition_queue.py
python scripts/procure_reconcile.py
```
