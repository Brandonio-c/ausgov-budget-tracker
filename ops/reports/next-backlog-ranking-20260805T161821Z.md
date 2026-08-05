# Next backlog ranking - structured state-budget pack (Task 2)

Generated: 2026-08-05T16:18:21Z.

## Source

Used the existing ranked backlog from the prior milestone
(`ops/reports/adapter-repair-plan-20260731T202041Z.{md,csv}`) - not a
fresh speculative ranking. That plan already established: 247
`adapter_missing` registry sources, all acquired-on-disk (none blocked
on acquisition), grouped into 6 preferred categories including
`commonwealth_mfs` (now complete - the prior milestone) and
`state_structured`/relevant `historical_actuals` entries for state
budget packs.

## Re-ranking the remaining structured state-budget candidates

Filtered the prior plan's CSV to `handoff_actuals_state`/
`handoff_actuals_territory` families (the ones the mission's "structured
state-budget pack" category maps to) and re-sorted by the mission's
5 criteria (structured-source availability, effort, dashboard value,
multi-edition adapter reuse potential, semantic risk) - excluding
PDF/OCR-first entries where a structured (xlsx/csv) alternative exists,
per the mission's ground rules.

Full table: `ops/reports/next-backlog-ranking-20260805T161821Z.csv`.

**#1 pick: `vic_annual_financial_statements_2024_25`** (VIC Department of
Treasury and Finance's own annual financial statements, 2024-25).
Verified directly (not assumed from the filename):

- Real file on disk:
  `data/raw/state/vic_annual_financial_statements_2024_25/snapshots/20260724T190604Z/files/Annual-financial-statements-2024-25.xlsx`
  (51,743 bytes).
- 10 sheets; the 3 core financial statements (`Operating Statement`,
  `Balance Sheet`, `Cash Flow Statement`) share one consistent,
  directly-parseable layout: a title row naming the statement and
  financial year, a `($ thousand)` unit row, a header row
  (`Notes | 2025 | 2024`), then labelled line items with two years of
  **already-numeric** comparative data (no string parsing, no
  parenthesized negatives - expenses are already signed negative
  floats).
- `Statement of Changes in Equity` has a genuinely different shape (a
  rolling-balance waterfall across multiple equity components, not a
  simple label+2-years table) - out of scope for this milestone's
  adapter (documented, not silently dropped).

## Why this one, over the alternatives

| candidate | why not picked (this milestone) |
|---|---|
| `vic_budget_portfolio_outcomes_2024_25` | Same jurisdiction/department, but a genuinely different statement shape: `$ million`, one year only, columns `Actual / Budget / Variance` (not multi-year actuals). Forcing one adapter across both would violate the mission's "one adapter per family unless a single adapter clearly covers a tightly related cluster of editions" rule - the shapes aren't tightly related enough. Ranked #2 for a future pick. |
| `vic_output_performance_measures_2024_25` | Genuinely structured, but non-financial (output/performance KPIs by portfolio, not $ revenue/expense/balance-sheet figures) - a poor fit for this dashboard's $-value focus. Deferred. |
| `nsw_economic_data_2026_27` | Real xlsx, but likely duplicates existing GDP/economic-indicator dashboard coverage. Deferred pending a closer duplicate check. |
| `nsw_historical_fiscal_indicators_2026_27` | Directly inspected `Table D.1`: a plain historical Revenue/Expense `$b` time series, 2000-01 to present - structurally identical to what existing NSW state-actuals/GFS coverage already provides. **Excluded** (not merely deferred) as a likely duplicate, per the mission's exclusion rule. |
| `qld_report_on_state_finances_actuals`, `tas_treasurer_annual_financial_reports` | Both are large, **mixed**-format populations (188 and 90 assets, `pdf;xlsx`) - real candidates, but need their own dedicated per-file triage pass to separate the structured subset from the PDF/OCR subset before any adapter work can be scoped safely. Too large an investigation to also fold into this milestone's implementation slot; documented as the next round's strongest candidates. |
| `qld_sds_2026_27_*` (17 Service Delivery Statements) | PDF-only. Excluded outright per the mission's "prefer structured over PDF/OCR" / "exclude PDF/OCR-first families if a structured workbook exists" ground rules - a structured alternative (the VIC pick above) exists and was prioritised instead. |

## Selected family

**`vic_annual_financial_statements_2024_25`** (source_family
`handoff_actuals_state`, jurisdiction VIC, government_level state) -
Operating Statement, Balance Sheet, and Cash Flow Statement sheets only
this milestone. Statement of Changes in Equity, Budget Portfolio
Outcomes, and Output Performance Measures are documented above as
scoped-out, not silently dropped.
