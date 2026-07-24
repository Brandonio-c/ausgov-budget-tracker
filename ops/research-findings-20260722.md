# AusGov Budget Tracker — Research Findings

Date: 2026-07-22

Integrated into `config/procurement_sources.yaml` as six new registry entries (82 sources total). Acquisition run `20260722T065324Z` applied immediately after integration.

## Acquisition outcomes (2026-07-22)

| Source ID | Priority | Status | Notes |
|---|---|---|---|
| `nsw_procurement_ocds_registry` | P1 | **downloaded** (22 JSONL.GZ) | OCP publication 11; ~63 MB on disk |
| `federal_historical_cn_data_1999_2020` | P3 | **downloaded** (15 files) | ~746 MB CSV/XLSX/ZIP archive |
| `qld_contract_disclosure_agency_datasets` | P1 | **partial** (1/249) | CKAN discover OK; AWS WAF HTTP 202 on most file URLs |
| `qld_on_time_payment_reports` | P2 | **partial** (1/43) | Same WAF pattern as QGIP |
| `sa_lggc_council_database_reports` | P2 | **blocked** | Cloudflare 403; browser session confirms challenge |
| `nt_grants_commission_annual_reports` | P3 | **blocked** | Landing page behind Cloudflare; 0 assets discovered |

### Code changes supporting integration

- `scripts/procure/adapters/ckan.py` — `package_search` crawl with pagination, per-package latest CSV
- `scripts/procure/discovery.py` — suffix detection from query-param filenames (`?name=2024.jsonl.gz`)
- `scripts/procure/validation.py` — gzip magic-byte detection and validation
- `scripts/procure_browser_session.py` — navigation race fix before reading page content
- `federal_austender_weekly_export` — marked deprecated; use OCDS API + historical CN archive

### Next steps for partial/blocked sources

**QLD (249 + 43 URLs staged):**

```bash
# URLs already exported:
# data/manual_inbox/qld_contract_disclosure_agency_datasets/urls.json
# data/manual_inbox/qld_on_time_payment_reports/urls.json

python scripts/procure_browser_session.py \
  --source-id qld_contract_disclosure_agency_datasets \
  --urls-file data/manual_inbox/qld_contract_disclosure_agency_datasets/urls.json
# Clear AWS WAF challenge in the headed browser window, then batch downloads proceed.
python scripts/procure_manual_import_batch.py --source-id qld_contract_disclosure_agency_datasets
```

**SA LGGC PDF:**

```bash
python scripts/procure_browser_session.py \
  --source-id sa_lggc_council_database_reports \
  --no-discover \
  --url "https://dit.sa.gov.au/__data/assets/pdf_file/0003/1542027/2023-24-Database-Reports.pdf"
```

**NT Grants Commission:**

```bash
python scripts/procure_browser_session.py --source-id nt_grants_commission_annual_reports
# Discover Territory Stories PDF links after Cloudflare clearance
```

---

## A. Executive summary

Top findings, ranked by value:

1. **NSW eTendering full OCDS bulk export via the Open Contracting Partnership Data Registry** — every NSW government contract, downloadable as JSON/Excel/CSV, standards-based. This is a materially better source than the existing `nsw_buy_register` (which only covers `can`/`son` notice types from buy.nsw). **P1.**
2. **Queensland per-agency Contract Disclosure Reports on data.qld.gov.au (CKAN, API+CSV)** — dozens of individual agency datasets (Treasury, TMR, DESBT, Health divisions, etc.), each with a stable CKAN API endpoint, all under the tag `Contract Disclosure`. Also a consolidated **"Queensland Government contracts directory — awarded contracts"** dataset. **P1.**
3. **Queensland per-agency "On-Time Payment Report" datasets on data.qld.gov.au** — CSV, published each financial year per department, a genuine payment-timing/invoice-adjacent transparency series not currently in the registry. **P2.**
4. **SA LGGC "Database Reports" (council-by-council financial and general data)** published as PDF directly on dit.sa.gov.au — a real bulk, no-login substitute for the `sa_councils_in_focus` dashboard gap, though PDF rather than CSV. **P2, closes a registry gap.**
5. **NT Grants Commission Annual Reports (Territory Stories / dhlgcd.nt.gov.au)** — Schedule 1 population and grant-allocation-by-council tables, publicly downloadable PDFs — a partial substitute for the `nt_local_grants_commission_return` login-portal gap. **P3.**
6. **Historical Australian Government contract data on data.gov.au** — pre-OCDS Contract Notice (CN) data 1999–2020, useful for extending time depth behind the current OCDS API coverage. **P3.**

Coverage improvement matrix (qualitative):

| Domain | Before | After proposed additions |
|---|---|---|
| NSW procurement | Partial (2 notice types) | Full contract lifecycle via OCDS |
| QLD procurement | None | Broad agency-level contract disclosure + payment timing |
| SA local government | Dashboard only, no bulk | PDF bulk council database reports |
| NT local government | Aggregate GFS only | + Grants Commission allocation-by-council PDFs |
| Federal procurement historical depth | 2004–present (OCDS) | + 1999–2020 legacy CN archive |

No new bulk sources were found for **WA tenders/MyCouncil**, **SA tenders.sa.gov.au**, **VIC procurement contracts**, or **TAS procurement** beyond what the acquisition report already found blocked or portal-only — these remain genuine gaps.

## C. Gap closure analysis (7 missing registry sources)

| ID | Finding | Verdict |
|---|---|---|
| `sa_councils_in_focus` | LGGC publishes annual **Database Reports** (PDF) with council-by-council financial/general data directly on dit.sa.gov.au | **(b) Partial substitute** — same underlying data as the dashboard, but PDF not CSV |
| `sa_tenders_contracts` | No CKAN/OCDS/bulk export found for tenders.sa.gov.au | **(c) No better official source found** |
| `wa_tenders` | No current bulk export | **(c) No better official source for current data** |
| `wa_mycouncil` | Confirmed no downloadable files behind the catalogue entry | **(c) No better official source exists** |
| `nt_local_grants_commission_return` | NT Grants Commission Annual Reports publish allocation and population schedules by council on Territory Stories | **(b) Partial substitute** |
| `federal_austender_weekly_export` | Confirmed superseded; use OCDS API + 1999–2020 historical CN archive | **(a) Direct substitute already covered** |
| `tas_procurement` | tenders.tas.gov.au remains a search/browse portal; no CSV/API export found | **(c) No better official source exists** |

## D. Negative results (don't re-research)

- **WA MyCouncil**: catalogue entry on data.wa.gov.au confirmed to list no downloadable resources.
- **SA tenders.sa.gov.au / WA tenders.wa.gov.au**: Cloudflare/legacy-portal search interfaces with no CSV/API.
- **TAS procurement**: no official bulk export at treasury.tas.gov.au, purchasing.tas.gov.au, or tenders.tas.gov.au.
- **VIC contract-level bulk export**: Buying for Victoria portal only; no CKAN/CSV bulk file identified.
- **Federal weekly AusTender export**: confirmed dead; do not re-attempt.
