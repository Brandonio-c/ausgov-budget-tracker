# Data Expansion Close-Out — 2026-07-23

Inputs: Data Expansion Plan (post acquisition-run), `ops/reports/missing-data-acquisition-20260723.md`, `ops/DATA_SOURCES.md`.

## Done this pass

### 1. FBO discovery fix (crawler bug, not data gap)

`scripts/procure_historical_backfill.py` `discover_fbo_year` now prefers index-page / `fbo/` HTML link parsing over fixed filename probes.

**Confirmed downloaded** (official `archive.budget.gov.au` URLs) for previously “missing” years including:

- 2000-01, 2001-02, 2002-03, 2003-04, 2005-06, 2007-08
- 2010-11 → 2018-19 (all nine; includes `FBO-2015-16-Consolidated.pdf.pdf` doubled extension)
- 1998-99 via NLA/Trove webarchive (`FinalBudgetOutcome98-99.pdf`)

Pre-2019 consolidated FBOs are **on disk**; digital Appendix A Table A.1 extract currently covers **2019-20 → 2023-24** (+ separate 2024-25 mapping). Earlier consolidated years remain OCR / layout-pilot work.

### 2. Pre-FBO 1985-86 / 1986-87

`downloads/Budget_<fy>.pdf` and `index.htm` are **404** for both years.

Wayback CDX for `archive.budget.gov.au/1985-86/*` and `/1986-87/*` only ever recorded:

- `https://archive.budget.gov.au/1985-86/1985-86_Budget_Paper_No.7.pdf` (**live 200**)
- `https://archive.budget.gov.au/1986-87/1986-87_Budget_Paper_No.7.pdf` (**live 200**)

Those PDFs are **Budget Paper No. 7 — Payments to or for the States…**, not Budget Statements / function outlays. Downloaded into `federal_budget_archive_function_series` snapshot `20260723T034700Z`.

**Verdict:** function-series PDFs for 1985-86 / 1986-87 are **not on archive.budget.gov.au** (live or historically in CDX). Next search should be Trove digitised books / parliamentary papers for Budget Paper No. 1 / Statement No. 2 — not more filename probes on the archive host.

`discover_pre_fbo_year` now also probes root-level `{fy}_Budget_Paper_No.{1,7}.pdf` patterns.

### 3. 1996-97 / 1997-98 function series (BP1, not FBO Appendix A)

Standalone FBO begins 1998-99 (Charter of Budget Honesty). Retrospective **cash outlays by function** exist in BP1 statistical appendix **Table I**:

| FY | Source PDF | Rows published |
|---|---|---|
| 1996-97 | `bp1_1997-98.pdf` Table I | 13 function totals |
| 1997-98 | `bp1_1998-99.pdf` Table I | 13 function totals |

Extractor: `scripts/ingest/extractors/bp1_outlays_by_function.py`  
Mapping: `config/mappings/bp1_outlays_by_function_pre_fbo.yaml` → **26 facts** (`cash_payment` / `estimated_actual`).

### 4. ABS GFS previous releases → `facts.db`

All-workbooks zips **2017-18 → 2023-24** melted via shared `melt_table4` (xlrd for `.xls`). Deduped by fy+category preferring latest release; staged **only FYs before 2015-16** to avoid overlapping `abs_gfs_commonwealth_130`.

Mapping: `config/mappings/abs_gfs_previous_releases.yaml` → **161 facts**, FYs **2008-09 → 2014-15**.

**Wayback CDX** for pre-2017 modern ABS landing pages is up again (HTTP 200) but returned empty for a sample 2012-13 path; **not required** for Commonwealth Table_4 coverage back to 2008-09 given previous-release workbooks. Pre-2008 still open if needed later.

### 5. Ingestion for this run’s new sources

| Source | Staging → published |
|---|---|
| `federal_budget_statement_11_historical` | 34 (Table 11.6 aggregates) |
| `federal_budget_archive_function_series` | 415 (Appendix A 2019-20→2023-24) |
| `federal_fbo_2024_25_function_subfunction` | 83 (earlier this session) |
| `abs_gfs_previous_releases` | 161 (2008-09→2014-15) |
| `bp1_outlays_by_function_pre_fbo` | 26 (1996-97 / 1997-98) |

## Still blocked / human-required

### Headed browser sessions (no `DISPLAY` on this host)

```bash
python scripts/procure_browser_session.py --source-id federal_defence_pbs_2026_27
python scripts/procure_browser_session.py --source-id federal_education_pbs_2026_27
python scripts/procure_browser_session.py --source-id nt_grants_commission_annual_reports
```

Needs an interactive sitting on a machine with a display (Defence/Education: HTTP/2 stream-reset; NT: Cloudflare challenge). `xvfb-run` is not available here.

## Remaining engineering backlog (not acquisition)

1. **OCR / layout extract** for pre-2019 consolidated FBO PDFs now on disk (function Appendix A equivalents).
2. **Trove** hunt for 1985-86 / 1986-87 Budget Statements (function series).
3. **Part B on-disk extraction** still outstanding (DSS PBS Age Pension under Support for Seniors, Health PBS, state budgets, etc.).
4. Redeploy API/frontend if the live site should surface the new `facts.db` rows.

## Integrity notes

- Statement 11 = whole-of-government aggregates only; do not mix into COFOG pies with FBO/GFS function rows.
- BP1 Table I is **cash outlays**; FBO Appendix A / Statement 11 are **accrual** — keep measure_type / accounting_basis separate in UI.
- ABS previous releases and `abs_gfs_commonwealth_130` share GFS purpose taxonomy but different `source_key`s; FY ranges were partitioned to avoid double-counting the same year.
