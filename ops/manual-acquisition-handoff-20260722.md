# AusGov Budget Tracker — Manual Acquisition Handoff

Date: 2026-07-22
Scope: what's left in the 76-source procurement registry that automation
cannot get, and precisely why, so this can be picked up by a human (or a
future session) without re-litigating decisions already made.

## Where things stand

45 of 76 sources have real, validated data on disk, fetched and spot-checked
by the automated pipeline (`scripts/procure_sources.py`). This document
covers the rest: **24 sources needing manual browser download**, **5 sources
confirmed to have no bulk file at all**, and **1 source that's genuinely
unreliable**, not broken.

Every source below was reclassified to its current status only after an
independent, reproducible technical finding — not a guess, and not a first
failure taken at face value. Nothing here was left manual because it was
merely inconvenient to automate.

## The rule that applies to all 24 manual sources

Automation stops the moment a source shows a real access control signal —
a WAF challenge, a login wall, or a silent connection reset. No header
spoofing, browser-fingerprint mimicry, retry-storming, or CAPTCHA-solving is
attempted, regardless of how the request is framed. That is a deliberate,
standing constraint on this project, not a gap in the tooling.

## 24 sources needing manual download, grouped by why

### Cloudflare bot-mitigation (`cf-mitigated: challenge`, `server: cloudflare`) — 10 sources
Real HTTP 403, independently reproduced with two differently-fingerprinted
clients before being reclassified.

| Source | What we want | Landing page |
|---|---|---|
| `act_actual_financial_publications` | ACT Treasury financial publications | https://www.treasury.act.gov.au/publications |
| `act_budget_2026_27` | ACT Budget Papers and Statements 2026-27 | https://www.treasury.act.gov.au/budget/budget-2026-27/budget-papers-and-statements |
| `nt_budget_2026_27` | NT Budget Papers 2026-27 | https://budget.nt.gov.au/papers |
| `nt_treasury_annual_reports` | NT Treasury annual reports | https://treasury.nt.gov.au/publications/annual-reports |
| `sa_budget_2026_27` | SA Budget 2026-27 | https://treasury.sa.gov.au/budget/current-budget |
| `sa_councils_in_focus` | SA "Councils in Focus" local govt data | https://dit.sa.gov.au/local-government/councils-in-focus |
| `sa_final_budget_outcome_and_cfr` | SA Final Budget Outcome + Consolidated Financial Report | https://treasury.sa.gov.au/budget/current-budget/budget-papers |
| `sa_tenders_contracts` | SA Tenders and Contracts | https://www.tenders.sa.gov.au/ |
| `tas_local_cdc` | TAS council performance / Consolidated Data Collection | https://www.dpac.tas.gov.au/government-information/local-government/council-performance |
| `vic_local_budget_and_reporting_models` | VIC council budget/reporting model workbooks | https://www.localgovernment.vic.gov.au/council-innovation-and-performance/sector-guidance-planning-and-reporting |
| `vic_local_vgc_abs_returns` | VIC council raw VGC/ABS data packs | https://www.localgovernment.vic.gov.au/lgv-funding-programs/victoria-grants-commission/consultation-and-operations |

### Section.io edge block (`section-io-id` header, HTTP 403) — 3 sources
Same independent-reproduction standard as above, different edge vendor.

| Source | What we want | Landing page |
|---|---|---|
| `vic_budget_2026_27` | Victorian State Budget 2026-27 | https://www.dtf.vic.gov.au/2026-27-state-budget |
| `vic_dtf_annual_report_bpo` | VIC DTF Annual Report + Budget Portfolio Outcomes | https://www.dtf.vic.gov.au/2024-25-annual-report |
| `vic_financial_report_2024_25` | Victoria Financial Report 2024-25 | https://www.dtf.vic.gov.au/financial-report-inc-quarterly-financial-report-no-4 |

### CloudFront edge block ("Request blocked", HTTP 403) — 2 sources

| Source | What we want | Landing page |
|---|---|---|
| `nsw_buy_register` | buy.nsw register of notices | https://buy.nsw.gov.au/help/register-of-notices |
| `federal_grantconnect` | GrantConnect grant opportunities and awards | https://www.grants.gov.au/ |

### Silent HTTP/2 stream-reset (TLS completes, then `INTERNAL_ERROR`, zero response) — 6 sources
Not a timeout — raising the read timeout to 90s did not help. Same signature
already documented for pbo.gov.au before this session started.

| Source | What we want | Known exact file URL (try this directly in a browser) |
|---|---|---|
| `federal_cfs_2024_25` | Commonwealth Consolidated Financial Statements 2024-25 | (no single known URL — browse the landing page) |
| `federal_dss_pbs_2026_27` | Social Services PBS 2026-27 | https://www.dss.gov.au/system/files/documents/2026-05/portfolio-budget-statements-2026-27-social-services.pdf |
| `federal_dva_pbs_2026_27` | Veterans' Affairs PBS 2026-27 | https://www.dva.gov.au/sites/default/files/2026-05/dva-pbs-2026-27.pdf |
| `federal_health_disability_ageing_pbs_2026_27` | Health, Disability and Ageing PBS 2026-27 | https://www.health.gov.au/sites/default/files/2026-06/budget-2026-27-health-disability-and-ageing-portfolio-budget-statements.pdf |
| `federal_ndia_pbs_2026_27` | NDIA PBS 2026-27 | https://www.health.gov.au/sites/default/files/2026-06/budget_2026-27_national_disability_insurance_agency_2026-27_health_pbs.pdf |
| `federal_social_services_pbs_2025_26_archive` | Social Services PBS 2025-26 (archive) | https://www.dss.gov.au/system/files/documents/2025-03/2025-26social-servicespbsaccessible.pdf |
| `services_australia_annual_reports` | Services Australia annual reports | (no single known URL — browse the landing page) |

**Status (disk truth, updated same day):** 6 of these 7 are already done —
imported 2026-07-22 from manually downloaded files (`federal_dss_pbs_2026_27`,
`federal_dva_pbs_2026_27`, `federal_health_disability_ageing_pbs_2026_27`,
`federal_ndia_pbs_2026_27`, `federal_social_services_pbs_2025_26_archive`,
`federal_cfs_2024_25`). Only `services_australia_annual_reports` remains
outstanding in this group. Also imported outside this table the same day:
`act_actual_financial_publications`, `nt_budget_2026_27`. See
`ops/manual-acquisition-status-20260722.md` for the live need/done queue.

### AWS WAF empty-challenge response (HTTP 202, empty body) — 1 source

| Source | What we want | Landing page |
|---|---|---|
| `qld_qgip_expenditure` | QLD Government Investment Portal expenditure, 14 files (one per FY 2012-13 through 2024-25) | https://www.data.qld.gov.au/dataset/queensland-government-investment-portal-expenditure-data-consolidated-view |

Discovery itself works fine here (the CKAN metadata API returns all 14 real
resource records) — only the actual file downloads are blocked.

### Genuinely no single file / multi-entity portal, not blocked — 1 source

| Source | What we want | Landing page |
|---|---|---|
| `act_actual_financial_publications` | (see Cloudflare table above — also blocked, listed once) | |

*(No unblocked "just needs the file grabbed" cases remain — every manual
source was checked directly this session; `federal_grantconnect` was the
last one assumed-but-unverified, and it turned out to be blocked too.)*

## Already resolved this session (for context, not action needed)

- **`federal_transparency_portal`** — was manual/`web_portal`, turned out to
  be a JS single-page app, not blocked. Installed Playwright + Chromium,
  reclassified to `landing_page_discovery` with browser rendering. 16/16
  real PBS PDFs downloaded and validated.

## 5 sources with no bulk file to acquire, manually or otherwise

These are not blocked — there is simply no single downloadable file behind
the page. Manual acquisition doesn't apply because there's nothing to
manually download; the underlying system is a live search/portal, not a
data export.

| Source | What's actually there |
|---|---|
| `nt_awarded_government_contracts` | CKAN resource points at a live search UI (`tendersonline.nt.gov.au/Tender/Search/Awarded`), not a file |
| `federal_austender_weekly_export` | CKAN dataset abandoned since 2013; live current equivalent is the already-working `federal_austender_ocds_api` source |
| `nt_local_grants_commission_return` | Static HTML has only nav/footer links; looks like a login/submission portal, no data-file links present |
| `wa_tenders` | Redirects (plain HTML meta-refresh, not JS) to a genuine Struts-based tender-search e-procurement system with no bulk-download link anywhere |
| `wa_mycouncil` | Landing page has no genuine bulk-download link — an earlier discovery bug briefly grabbed an unrelated page here, since fixed |

**One partial exception worth a real look:** `nt_awarded_government_contracts`'s
search UI (`tendersonline.nt.gov.au`) has a real `GET /Tender/ExportTenderers`
XHR endpoint in its own public JS that produces an actual `AwardedContractsExport.xlsx`
file — found by reading the site's JS, not executing it. This wasn't
implemented as a new source this session (that's a scope decision, not made
unilaterally) — flagging again here since it's a genuine "worth adding"
candidate, distinct from the other 4 in this table which have nothing to add.

## 1 source that's flaky, not blocked or working

| Source | What's happening |
|---|---|
| `qld_local_qao_2025` | QLD Audit Office local government report page. Across 10 attempts, resolved 13-14 real report PDFs only twice, returned a stripped 2-link page the other 8 times — same URL, same request, different server response each time. Reads as adaptive bot-mitigation (allow a few requests, then throttle), not a code bug. Deliberately not retried further, to avoid cherry-picking a favorable run. |

## Tools for picking this up

1. **One file at a time**, with exact provenance:
   ```bash
   conda activate ausgov-budget-tracker
   python scripts/procure_manual_import.py <source_id> <path> --source-url "<exact file URL>"
   ```
2. **Batch, after saving files into `data/manual_inbox/_downloads/`** named
   `<source_id>.<ext>` (or `<source_id>__anything.<ext>` for multi-file
   sources like `qld_qgip_expenditure`):
   ```bash
   python scripts/procure_manual_import_batch.py
   ```
   Safe to re-run repeatedly; skips any source_id with no file present yet.
3. Each source's `data/manual_inbox/<source_id>/README.md` has the specific
   landing URL, what was attempted, and a ready-to-fill import command.

## What will not change this outcome

Retrying with `wget`/`curl`/a different HTTP library, a "smarter" crawler,
or a from-scratch scraper against the site's internal JS API will not get
past a Cloudflare/Section.io/CloudFront challenge or a silent stream-reset —
those are server-side decisions, already confirmed independently for every
source in this document. The only thing that reliably gets through is a
real, human-driven browser session, which is exactly what the manual path
above is for.
