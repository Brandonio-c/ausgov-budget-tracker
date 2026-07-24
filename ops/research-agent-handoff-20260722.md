# Research Agent Handoff — Additional Australian Government Data Sources

Date: 2026-07-22  
Project: **AusGov Budget Tracker** (`/home/vibe-server/vibe-factory/ausgov-budget-tracker`)  
Companion doc: `ops/procurement-acquisition-report-20260722.md`

---

## Your mission

Conduct **background and literature research** to identify **additional official, publicly downloadable datasets** that would strengthen Australian federal, state, territory, and local government **budget, spending, grants, contracts, and financial returns** coverage.

You are **not** being asked to download files or write code. Deliver a **structured research report** of candidate sources with enough detail that a human or coding agent can add them to `config/procurement_sources.yaml` and attempt acquisition.

---

## Project context

**AusGov Budget Tracker** aims to visualize government spending across all levels with **click-through traceability** to original government documents/datasets. Phase 1 proved the pipeline on three sources; a broader **procurement registry** of 76 candidate sources was researched and an acquisition pass completed **2026-07-20 through 2026-07-22**.

### What the registry tracks

Each source entry describes an **official publisher dataset** with:

- `source_family` — e.g. `gfs_actuals`, `state_budget`, `procurement_contracts`, `grant_awards`, `local_financial_returns`
- `measure_types` — budget estimates, accrual expenses, contract values, grant awards, recipient counts, etc.
- `accounting_basis` — GFS, AASB, appropriation, commitment, count
- `traceability_tier` (1–5) — aggregate → invoice-level
- `access_method` — `direct_file`, `ckan_api`, `ocds_api`, `socrata_api`, `landing_page_discovery`, `web_portal`, `manual`

**Critical rule:** Never sum budget estimates, appropriations, accrual expenses, cash payments, contract values, grant awards, counts, or forecasts unless an explicit reconciliation defines the bridge (`measure_separation_rule` in registry header).

### Storage convention

Acquired files live at `data/raw/<government_level>/<source_id>/latest.json` with provenance (URL, retrieved_at, checksums).

---

## What we already have (69 / 76 sources)

See **`ops/procurement-acquisition-report-20260722.md`** for the full 69-source catalog (~6.1 GB, 2,220 files).

### Strong coverage areas

| Domain | Coverage |
|---|---|
| **ABS GFS annual** | Commonwealth + all states/territories + all local (Tables 130, 231–238, 331–337) + full workbook ZIP |
| **Commonwealth budget cycle** | BP1/BP2/BP3/BP4 extracts, PBS index, selected portfolio PBS, FBO appendix, monthly statements, CFS |
| **NDIS** | Participant datasets, payment datasets, quarterly reports, sustainability reports (~3.2 GB) |
| **DSS / income support** | Monthly income support, JobSeeker profile, demographics, payments by LGA |
| **Federal procurement** | AusTender OCDS historical API (884 MB); GrantConnect quarterly award xlsx (Jul 2023–Jul 2026) |
| **State budgets & actuals** | Full budget paper sets + RSF/ASF equivalents for NSW, QLD, SA, TAS, VIC, WA |
| **Territory budgets & actuals** | ACT (budget + publications + notifiable invoices), NT (budget + 45 treasury ARs) |
| **Local government** | NSW OLG time series; TAS CDC zips; VIC VGC/ABS packs + model budgets; QLD QAO 2025 audit report; ABS local GFS tables |
| **State procurement (partial)** | NSW buy.nsw notice CSVs; NT awarded contracts xlsx (date-bounded) |
| **QLD grants/expenditure** | QGIP consolidated expenditure CSVs (all FY 2012-13–2024-25) |

---

## Known gaps (7 registry sources not on disk)

These were investigated; treat as **starting points**, not exhaustive proof of impossibility.

| ID | Gap type | Notes for your research |
|---|---|---|
| `sa_councils_in_focus` | Portal + WAF | Dashboard at councilsinfocus.sa.gov.au; data from SA LGGC. Is there a bulk LGGC return dataset elsewhere (data.sa.gov.au, LGGC reports, FOIA)? |
| `sa_tenders_contracts` | Portal + WAF | www.tenders.sa.gov.au — agency-scoped awarded contracts. Any OCDS/API mirror? |
| `wa_tenders` | Portal only | tendersonline.nt.gov.au-style hidden export endpoint? WA open data procurement datasets? |
| `wa_mycouncil` | Portal only | data.wa.gov.au MyCouncil catalogue entry exists but lists **no downloads**. API/XML resource? |
| `nt_local_grants_commission_return` | Login portal | gcannualreturn.nt.gov.au — council submission system. Published aggregate returns elsewhere? |
| `federal_austender_weekly_export` | Deprecated | Superseded by OCDS API — confirm no incremental weekly feed worth adding |
| `tas_procurement` | Incomplete | 18 links discovered on treasury.tas.gov.au eTendering page but not fetched — research whether TAS has AusTender-style export |

---

## Priority research questions

Answer these with **specific URLs, dataset names, formats, update frequency, and publisher**.

### 1. Council-level financial returns (biggest geographic gap)

We have **jurisdiction-level ABS GFS local tables** but thin **council-by-council** coverage outside NSW (OLG), TAS (CDC), and VIC (VGC).

| Jurisdiction | Research targets |
|---|---|
| **SA** | LGGC annual return data behind Councils in Focus; `data.sa.gov.au` local government datasets; ESCOSA advice scheme data |
| **WA** | MyCouncil underlying data; DLGSC/local government statistics; WALGA publications |
| **QLD** | Beyond QAO audit report — DLGRMA council reporting, QLD Treasury local government statistics |
| **NT** | NT Grants Commission published aggregates (not the submission portal) |
| **ACT** | ACT local government / territory equivalents if any |

**Question:** For each state/territory, is there an official **CSV/XLSX/ZIP of all councils × years × line items** comparable to NSW OLG time series or TAS CDC?

### 2. State/Territory procurement contracts (beyond NSW + partial NT)

| Jurisdiction | Research targets |
|---|---|
| **VIC** | Buying for Victoria / VGPB contract disclosure, data.vic.gov.au procurement |
| **QLD** | QTenders awarded contracts export, Queensland Contracts Directory open data |
| **SA** | tenders.sa.gov.au export paths, data.sa.gov.au |
| **WA** | tenders.wa.gov.au advanced search export, data.wa.gov.au procurement |
| **TAS** | tasmanianet.gov.au / treasury eTendering contract registers |
| **ACT** | ACT Procurement Solutions contract listings |
| **NT** | Full historical ExportTenderers (we have date-bounded xlsx only) |

**Question:** Does any state publish **OCDS**, **CSV bulk exports**, or **data.gov.au CKAN packages** for awarded contracts?

### 3. Grants and grant-like payments (beyond GrantConnect + QGIP)

| Research targets |
|---|
| Commonwealth grants on data.gov.au not covered by GrantConnect (e.g. department-specific open data) |
| State grant registers: NSW Grants, VIC grants portal, QLD GrantConnect equivalent |
| Disaster/recovery payment datasets |
| FA Grants (Financial Assistance Grants) — SA LGGC publishes allocation PDFs; machine-readable anywhere? |
| National Recovery and Disaster Resilience grants |

### 4. Invoice-level / payment transparency

| Already have | Research for more |
|---|---|
| ACT Notifiable Invoices (Socrata) | NSW, QLD, VIC, WA, SA, TAS, NT invoice disclosure registers |
| | Commonwealth Contract Notices (have OCDS) vs **payment** data (Finance monthly statements only) |
| | Whole-of-government credit card/expense disclosures |

### 5. Entity / agency actuals beyond PBS

| Research targets |
|---|
| Individual agency annual reports not captured via Transparency Portal crawl |
| GBE (government business enterprise) financial statements |
| State government trading enterprises |
| Audit office reports (ANAO, state auditors) with machine-readable appendices |

### 6. Historical depth and cross-year series

Many acquisitions target **2024-25 / 2026-27** budget cycles. Research:

- Long-run budget paper archives with stable download patterns
- ABS GFS time series beyond latest release (we have 2024-25 tables)
- Pre-2013 AusTender / GrantConnect historical dumps

### 7. API / standards-based feeds

Prefer sources with:

- CKAN (`data.gov.au`, `data.qld.gov.au`, `data.nsw.gov.au`, `data.sa.gov.au`, `data.wa.gov.au`, `data.vic.gov.au`)
- OCDS / AusTender API patterns
- Socrata / OData (like ACT)
- ABS API (SDMX) for GFS

---

## Access constraints (must respect)

The acquisition pipeline **deliberately does not**:

- Solve CAPTCHAs programmatically
- Spoof browser fingerprints or bypass WAFs
- Retry-storm blocked endpoints

**Allowed:** Human clears challenge in real browser → session reused for fetch → upload to local receiver.

When proposing sources, **flag expected access friction**:

| Tag | Meaning |
|---|---|
| `open_api` | CKAN/OCDS/Socrata/direct file, high automation |
| `discoverable_bulk` | Bulk file exists but URL must be crawled |
| `waf_likely` | Cloudflare/Section.io/CloudFront/AWS WAF observed on similar sites |
| `portal_only` | Interactive search UI, no bulk export found |
| `login_required` | Registered user or council login needed |
| `foi_only` | Not routinely published; may require FOI |

---

## Do not duplicate

Before proposing a source, check it is **not already** in the registry or acquired list. Key existing IDs:

<details>
<summary>All 76 registry source IDs (click to expand)</summary>

```
abs_gfs_annual_all_workbooks, abs_gfs_commonwealth_130,
abs_gfs_local_nsw_331, abs_gfs_local_nt_337, abs_gfs_local_qld_333,
abs_gfs_local_sa_334, abs_gfs_local_tas_336, abs_gfs_local_vic_332,
abs_gfs_local_wa_335, abs_gfs_state_act_238, abs_gfs_state_nsw_231,
abs_gfs_state_nt_237, abs_gfs_state_qld_233, abs_gfs_state_sa_234,
abs_gfs_state_tas_236, abs_gfs_state_vic_232, abs_gfs_state_wa_235,
act_actual_financial_publications, act_budget_2026_27, act_notifiable_invoices,
dss_income_support_monthly, dss_jobseeker_monthly_profile,
dss_payment_demographics_quarterly, dss_payments_by_lga,
federal_agency_resourcing_bp4_2026_27, federal_austender_ocds_api,
federal_austender_weekly_export, federal_budget_measures_bp2_2026_27,
federal_budget_statement_6_2026_27, federal_cfs_2024_25,
federal_dss_pbs_2026_27, federal_dva_pbs_2026_27,
federal_fbo_2024_25_function_subfunction, federal_financial_relations_bp3_2026_27,
federal_grantconnect, federal_health_disability_ageing_pbs_2026_27,
federal_monthly_financial_statements, federal_ndia_pbs_2026_27,
federal_pbs_index_2026_27, federal_social_services_pbs_2025_26_archive,
federal_transparency_portal, ndis_financial_sustainability_reports,
ndis_participant_datasets, ndis_payment_datasets, ndis_quarterly_reports,
nsw_budget_2026_27, nsw_budget_open_data_2026_27, nsw_buy_register,
nsw_local_olg_time_series, nsw_report_on_state_finances,
nt_awarded_government_contracts, nt_budget_2026_27,
nt_local_grants_commission_return, nt_treasury_annual_reports,
qld_budget_2026_27, qld_local_qao_2025, qld_qgip_expenditure,
qld_report_on_state_finances, sa_budget_2026_27, sa_councils_in_focus,
sa_final_budget_outcome_and_cfr, sa_tenders_contracts,
services_australia_annual_reports, tas_budget_2026_27, tas_local_cdc,
tas_procurement, tas_treasurers_annual_financial_reports,
vic_budget_2026_27, vic_dtf_annual_report_bpo, vic_financial_report_2024_25,
vic_local_budget_and_reporting_models, vic_local_vgc_abs_returns,
wa_annual_report_state_finances_2024_25, wa_budget_2026_27,
wa_mycouncil, wa_tenders
```

</details>

---

## Required output format

Produce a markdown report with sections:

### A. Executive summary
- Top 5–10 highest-value new sources found
- Estimated coverage improvement (jurisdiction × domain matrix)

### B. Candidate source table

For **each** proposed source:

| Field | Required detail |
|---|---|
| `proposed_id` | snake_case, e.g. `vic_procurement_contracts_ocds` |
| `title` | Official name |
| `publisher` | Agency |
| `jurisdiction` | NSW / VIC / … / Commonwealth |
| `government_level` | federal / state / territory / local / cross_level |
| `source_family` | from existing families or propose new with justification |
| `landing_url` | Primary page |
| `resource_url` | Direct download or API endpoint if known |
| `formats` | csv, xlsx, pdf, json, zip, api |
| `access_method` | direct_file / ckan_api / ocds_api / socrata_api / landing_page_discovery / web_portal / manual |
| `automation` | high / medium / low / manual |
| `time_coverage` | e.g. 2015–present |
| `update_frequency` | annual / quarterly / monthly / ad hoc |
| `measure_types` | what numbers it contains |
| `accounting_basis` | gfs / aasb / commitment / count / … |
| `traceability_tier` | 1–5 |
| `granularity` | e.g. council, agency, contract, recipient |
| `access_friction` | open_api / waf_likely / portal_only / login_required |
| `fills_gap_for` | which missing registry ID or domain gap this addresses |
| `evidence` | URL + quote or screenshot description proving bulk download exists |
| `caveats` | scope limits, comparability issues |
| `priority` | P1–P4 recommendation |

### C. Gap closure analysis

For each of the **7 missing registry sources**, state whether your research found:
- (a) a **direct substitute** with bulk download,
- (b) a **partial substitute**,
- (c) **no better official source** exists.

### D. Negative results

Sources commonly assumed to exist but **don't** (or aren't public). Document these to avoid re-research.

### E. Suggested registry YAML snippets

Provide 1–3 ready-to-paste YAML blocks for the highest-priority findings (schema in `config/procurement_sources.schema.json`).

---

## Key files to read first

| File | Purpose |
|---|---|
| `config/procurement_sources.yaml` | Full 76-source registry with research notes |
| `ops/procurement-acquisition-report-20260722.md` | What was downloaded |
| `ops/manual-acquisition-handoff-20260722.md` | Why manual/WAF sources were blocked |
| `ops/manual-acquisition-status-20260722.md` | Session outcomes |
| `reports/procurement/20260722T063314Z/sources.csv` | Machine-readable status per source |
| `reports/procurement/20260722T063314Z/errors.jsonl` | Missing source reasons |

---

## Search starting points

### Open data portals

- https://data.gov.au
- https://data.nsw.gov.au
- https://www.data.qld.gov.au
- https://data.vic.gov.au
- https://data.sa.gov.au
- https://catalogue.data.wa.gov.au
- https://data.act.gov.au
- https://data.nt.gov.au (if exists)

### Procurement / grants

- https://www.tenders.gov.au (AusTender)
- https://www.grants.gov.au (GrantConnect)
- State tender portals (NSW buy.nsw, VIC, QLD QTenders, SA, WA, TAS, ACT)
- https://www.data.gov.au/data/dataset?tags=procurement
- https://www.data.gov.au/data/dataset?tags=grants

### Local government

- NSW OLG: https://www.olg.nsw.gov.au/public/your-council-data-and-reports
- SA Councils in Focus / LGGC: https://dit.sa.gov.au/local-government/grants-commission
- WA MyCouncil: https://www.mycouncil.wa.gov.au
- VIC LGV: https://www.localgovernment.vic.gov.au
- QLD DLGRMA / QAO
- TAS CDC: https://www.dpac.tas.gov.au/government-information/local-government/council-performance

### Standards / literature

- ABS Government Finance Statistics methodology
- COAG/Federal Financial Relations reports
- OGP Australia National Action Plan open data commitments
- ANAO performance audit reports listing data systems
- Productivity Commission reports on local government revenue

---

## Example registry entry (template)

```yaml
- priority: P2
  id: example_vic_procurement_disclosure
  jurisdiction: VIC
  government_level: state
  publisher: Victorian Government
  title: Victorian Government contract disclosure export
  landing_url: https://example.vic.gov.au/contracts
  resource_url: https://example.vic.gov.au/api/contracts.csv
  formats: [csv]
  access_method: direct_file
  automation: high
  update_frequency: monthly
  time_coverage: 2018-present
  measure_types: [contract_value]
  accounting_basis: [commitment]
  granularity: [contract, agency, supplier]
  parser_strategy: Download CSV, preserve contract ID and award date.
  caveats:
    - Commitments not cash paid.
  traceability_tier: 4
  source_family: procurement_contracts
```

---

## Success criteria

Your research succeeds if it delivers:

1. **Actionable** new sources (not just "portal exists" — specify export path or API)
2. **De-duplicated** against the 76-source registry
3. **Honest** about access friction and measure-type limitations
4. **Prioritized** — P1/P2 candidates that close council-level or procurement gaps rank highest
5. **YAML-ready** snippets for top findings

---

## Contact / handback

Return the report as markdown. Ideal filename: `ops/research-findings-<YYYYMMDD>.md`.

If proposing registry additions, note which existing gap each closes and whether acquisition likely needs `manual` (browser) vs automated fetch.
