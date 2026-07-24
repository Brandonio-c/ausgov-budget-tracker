# Missing-data acquisition report

**Date:** 2026-07-23  
**Scope:** Part A new sources (A1–A5) + NT Grants Commission re-fetch  
**Non-goals:** Part B re-downloads; facts.db ingest / mapping

## Summary

| Source id | Status | Bytes / files | Notes |
|---|---|---:|---|
| `federal_budget_statement_11_historical` | **Downloaded** | 650 KB / 1 PDF | `direct_file` via `procure_sources.py` |
| `abs_gfs_previous_releases` | **Partial** | 23.4 MB / 7 zips | Modern ABS scheme **2017-18 → 2023-24** OK; pre-2017 AUSSTATS subscriber links return *Attachment Not Found* |
| `federal_budget_archive_function_series` | **Partial** | 241 MB / 36 PDFs | FBO appendix/full PDFs for selected years + pre-FBO budget papers 1983–95 (gaps remain) |
| `federal_defence_pbs_2026_27` | **Blocked** | 0 | HTTP/2 reset + landing timeout; reclassified `manual` |
| `federal_education_pbs_2026_27` | **Blocked** | 0 | Same hang class as Defence; reclassified `manual` |
| `nt_grants_commission_annual_reports` | **Blocked** | 0 | Cloudflare challenge; needs headed human browser session (`DISPLAY` unavailable here) |

Registry now has **90** sources (was 85). Schema updated to accept legacy `P0` / `ckan`.

## What was done

1. Appended YAML for A1–A5 to [`config/procurement_sources.yaml`](../../config/procurement_sources.yaml).
2. Fixed registry validation (`P0`, `ckan` → `ckan_api` alias) so `procure_sources.py` can load.
3. Added [`scripts/procure_historical_backfill.py`](../../scripts/procure_historical_backfill.py) for multi-year ABS / FBO / pre-FBO crawls.
4. Ran downloads per plan §E order (NT → direct PBS/S11 → ABS → FBO → pre-FBO).

## Detail by source

### A2 — Statement 11 (success)

- URL: `https://budget.gov.au/content/bp1/download/bp1_bs-11.pdf`
- Path: `data/raw/federal/federal_budget_statement_11_historical/snapshots/20260723T024822Z/files/bp1_bs-11.pdf`

### A4 / A5 — Defence & Education PBS (blocked)

- Confirmed HTTP/2 `INTERNAL_ERROR` / silent hang on `defence.gov.au` and `education.gov.au` from this host (same signature as DSS PBS).
- Playwright headless: Defence landing `TimeoutError` at 90s; no file saved.
- Entries reclassified to `access_method: manual` with notes.
- **Next:** interactive `python scripts/procure_browser_session.py --source-id federal_defence_pbs_2026_27` (and education) with a human-cleared session, or drop PDFs into `data/manual_inbox/_downloads/`.

### A1 — ABS GFS previous releases (partial)

Downloaded All-workbooks.zip:

| FY | Status |
|---|---|
| 2017-18 … 2023-24 | Downloaded |
| 2007-08 … 2016-17 | Failed — modern URL 404; AUSSTATS `subscriber.nsf` links resolve to *Attachment Not Found* |
| Wayback CDX | 503 at time of run |

Path: `data/raw/cross_level/abs_gfs_previous_releases/`

### A3 — FBO / archive function series (partial)

**FBO-era PDFs on disk (year tags):**  
1999-00, 2004-05, 2006-07, 2008-09, 2009-10, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24  

(Plus existing `federal_fbo_2024_25_function_subfunction` for 2024-25 — not re-fetched.)

**Still missing FBO years** (no resolvable public PDF URL found this pass):  
1996-97–1998-99, 2000-01–2003-04, 2005-06, 2007-08, 2010-11–2018-19  

Directory listings under `archive.budget.gov.au/<fy>/fbo/` often return **403**; acquisition relies on known filename probes.

**Pre-FBO (1983-84 → 1995-96):** 26 PDFs downloaded (budget papers / statements). Missing candidates for **1985-86** and **1986-87** only. Files are OCR/ingest candidates only.

Path: `data/raw/federal/federal_budget_archive_function_series/`

### NT Grants (blocked)

```text
challenge page in headless mode — re-run without --headless so a human can clear it
```

Report: `data/.procurement/reports/browser-session-20260723T024854Z.json`

## Commands used

```bash
python scripts/procure_sources.py \
  --source-ids federal_defence_pbs_2026_27,federal_education_pbs_2026_27,federal_budget_statement_11_historical \
  --read-timeout 180

python scripts/procure_browser_session.py --source-id nt_grants_commission_annual_reports --headless

python scripts/procure_historical_backfill.py --series abs_gfs --years 2007-08:2023-24
python scripts/procure_historical_backfill.py --series fbo_archive --years 1996-97:2023-24
python scripts/procure_historical_backfill.py --series fbo_archive \
  --years 1999-00,2004-05,2006-07,2008-09,2009-10,2022-23
python scripts/procure_historical_backfill.py --series pre_fbo_budget --years 1983-84:1995-96
```

## Follow-ups (not done here)

1. Headed browser acquisition for Defence PBS, Education PBS, NT Grants.
2. Alternate discovery for missing FBO years (Treasury contact / manual archive browse / Wayback when available).
3. Pre-2017 ABS: find live mirrors or recover via Wayback when CDX is up; do not treat dead AUSSTATS log-agent URLs as acquired.
4. Ingestion/mapping for on-disk Part B corpora (DSS PBS Age Pension, state budgets, etc.) — separate from this acquisition run.
