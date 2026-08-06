# QLD/TAS next backlog ranking (Task 1)

Generated: 2026-08-06T17:15:37Z.

## Ground truth verified before ranking

- `git status --short`: clean. Branch `main`. `HEAD` and `origin/main`
  both at `e965f24`.
- `ops/reports/current-state.md`: general project overview, no
  QLD/TAS-specific detail affecting this ranking.
- `ops/reports/next-backlog-ranking-20260805T161821Z.md` (the prior VIC
  BPO milestone's own re-ranking) had already flagged
  `qld_report_on_state_finances_actuals` and `tas_treasurer_annual_
  financial_reports` as the two named "mixed-format population"
  candidates for this next round - matching the current mission's
  framing exactly - but explicitly deferred deep triage of either to a
  future milestone. This report performs that triage.
- `config/procurement_sources.yaml`: both entries confirmed
  `handoff_already_on_disk: true`, `access_method: landing_page_
  discovery`, formats `xlsx, xlsx, pdf` (the registry's own formats list
  is a hint, not verified ground truth - actual per-file inspection
  below is what the ranking is based on).
- `config/canonical_datasets.yaml` (actually `config/lineage/canonical_
  datasets.yaml`): only tracks already-fully-ingested canonical
  datasets, none of which are QLD/TAS state-actuals families yet.

## Per-family file inventory (real files on disk, not filenames)

| source_id | total files | pdf | xlsx | csv | json | notes |
|---|---:|---:|---:|---:|---:|---|
| `tas_treasurer_annual_financial_reports` | 178 | 76 | 1 | 0 | 0 | The 1 xlsx is `GGS-Key-Fiscal-Measures-Time-Series.xlsx` - directly inspected, genuinely structured |
| `tas_treasurers_annual_financial_reports` (alt key, same population) | 453 | 76 | 0 | 0 | 0 | Superset snapshot of the same underlying reports; no additional xlsx |
| `qld_report_on_state_finances_actuals` | 378 | 187 | 1 | 0 | 0 | The 1 xlsx is `MOG-Transfer-Sign-off-Form-2018-Proforma.xlsx` - directly opened: a **blank template** (104x10, almost entirely `NaN`, a form title and an `(insert year)` placeholder cell) - not data |
| `qld_report_on_state_finances` (alt key, same population) | 953 | 187 | 0 | 0 | 0 | No structured files at all |
| `qld_qgip_expenditure` | 55 | 1 | 0 | 14 | 40 | Structured, but grant/funding-agreement-level detail, not state fiscal aggregates - directly opened, confirmed off-topic |
| `qld_contract_disclosure_agency_datasets` | 481 | 0 | 4 | 235 | 242 | Structured, but per-contract procurement disclosure records, not fiscal aggregates - off-topic |
| `qld_on_time_payment_reports` | 77 | 0 | 0 | 42 | 35 | Structured, but supplier payment-timing compliance metrics, not fiscal aggregates - off-topic |
| `tas_tascorp_annual_report_2024_25` | - | - | - | - | - | Already has adapter coverage via `scripts/ingest/debt_reconciliation.py` - not a fresh candidate |

## Re-ranking against the mission's 6 criteria

1. **Structured source availability**: `tas_treasurer_annual_financial_
   reports` wins decisively - its 1 xlsx is genuine, clean tabular data;
   both QLD "report on state finances" registry entries have **zero**
   usable structured files (the QLD xlsx is a blank sign-off form
   template, confirmed by opening it, not assumed from the filename).
2. **Engineering effort**: TAS's file is a single 24-row x 12-column
   sheet - minimal effort, one adapter, no PDF/OCR pipeline needed.
3. **Dashboard value**: TAS's file contains 10 genuine general-
   government-sector fiscal aggregates (Revenue from Transactions,
   Expenses from Transactions, Net Operating Balance, Fiscal Balance,
   Infrastructure Investment, Net Debt, GFS Net Debt, Net Worth, Net
   Financial Liabilities, Cash Surplus/Deficit) across Actual, Revised
   Budget, and Forward Estimate vintages, 2013-14 to 2028-29 - directly
   comparable in kind to the VIC BPO/AFS/MFS work already shipped, and
   currently **zero** `tas_*`-prefixed measure_type coverage exists in
   `data/facts.db` (verified: only ABS's own independently-compiled
   `abs_gfs_state_tas_236`/`abs_state_accounts_tas_*` series and
   TASCORP debt data exist for TAS today).
4. **One adapter covering multiple editions**: TAS's single file
   already spans 16 years and 3 vintage types in one workbook - the
   best possible ratio of adapter effort to coverage in this entire
   candidate set.
5. **Semantic risk**: Real, but manageable and fully scoped in Task 3/4
   - non-breaking-space thousands separators (e.g. `'1\xa0273.4\xa0'`),
   footnote-marker digits appended directly to year labels with no
   separator (e.g. `'2016-171'` = FY "2016-17" + footnote "1"), and the
   need to keep this Treasury-published series in its own
   compatibility_group family, never conflated with the ABS's
   independently-compiled GFS series for the same jurisdiction (a
   different publisher, different methodology, different vintage
   granularity).
6. **Already partially supported**: No - zero existing `tas_*`
   measure/adapter presence, confirmed by DB inspection.

The QLD "report on state finances" entries are **excluded outright**
this milestone (not merely deferred) on structured-source-availability
grounds - the ground rules explicitly say to prefer structured sources
and not start a broad PDF family unless triage proves there is no
better structured candidate. That triage is exactly what this report
performs, and it proves TAS's file is a clearly better structured
candidate.

The other QLD structured candidates (`qld_qgip_expenditure`,
`qld_contract_disclosure_agency_datasets`, `qld_on_time_payment_
reports`) are genuinely structured but are a different topic domain
entirely (grant expenditure, procurement contracts, payment-timing
compliance) - not state-level fiscal aggregates, and not a natural
continuation of the state-actuals dashboard theme this and the prior
two milestones have been building (VIC BPO/SOCE/Admin, MFS). Deferred
as candidates for a future, separate procurement/contracts-focused
milestone, not excluded as duplicates.

## Recommended order

1. `tas_treasurer_annual_financial_reports` (GGS Key Fiscal Measures
   Time Series) - **selected this milestone**.
2. `qld_report_on_state_finances_actuals` / `qld_report_on_state_
   finances` - PDF/OCR triage required before any adapter work; a
   future milestone's investigation slot, not implementation.
3. `qld_qgip_expenditure`, `qld_contract_disclosure_agency_datasets`,
   `qld_on_time_payment_reports` - structured but off-topic for the
   fiscal-aggregate dashboard theme; candidates for a future
   procurement/contracts-focused milestone.

Full table: `ops/reports/qld-tas-next-backlog-ranking-20260806T171537Z.csv`.

## Next

Task 2: formal scope-selection report confirming
`tas_treasurer_annual_financial_reports` (specifically its `GGS Key
Fiscal Measures Time Series` workbook) as the selected family.
