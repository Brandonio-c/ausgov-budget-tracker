# VIC DTF Budget Portfolio Outcomes - inventory (Task 3)

Generated: 2026-08-05T19:08:30Z.

## Source

`vic_budget_portfolio_outcomes_2024_25` - Victorian Department of
Treasury and Finance's own 2024-25 Budget Portfolio Outcomes statement
(an actual-vs-budget variance comparison, not a multi-year actuals
series like the already-loaded AFS family). `config/procurement_
sources.yaml` (priority P0, `handoff_actuals_state` family, same
underlying `handoff_repo_source_key: vic_dtf_annual_report_bpo` as AFS).
One acquired asset, verified:

- `data/raw/state/vic_budget_portfolio_outcomes_2024_25/snapshots/20260724T190604Z/files/Budget-portfolio-outcomes-2024-25.xlsx`
- 433,376 bytes; sha256 `a947a1bfe2dc7ec701acd8c03630010d7f55312d214aaf10cf273ca99809547e`
  (matches `latest.json` exactly).

## Workbook structure - genuinely different shape from AFS

6 sheets: `Cover`, `OS`, `BS`, `CFS`, `SOCE`, `Admin`. **This milestone
extracts 3 sheets only**: `OS`, `BS`, `CFS` - fully inspected all 6 this
time (the prior milestone had only partially inspected `OS`/`BS`/`Cover`
before deferring). Confirmed differences from AFS that required a
completely new extractor, not a reuse of `vic_afs.py`:

| | AFS | BPO |
|---|---|---|
| unit | `$ thousand` | `$ million` |
| columns | Notes, year1, year2 (two years, both actual) | Actual, Budget, Variance (one year, two estimate_status values) |
| header format | plain integers (`2025`, `2024`) | multi-line strings (`"2024-25\nActual"`, `"2024-25\nBudget (a)"`) needing regex parsing, sometimes with a trailing inline footnote marker |
| row-label footnotes | none inline | many labels have a trailing footnote marker, e.g. `"Output appropriations (a)"` - stripped before matching |
| sheet termination | a `"Source: ..."` footer line | no footer line - a lowercase-letter-parenthetical footnote block instead (e.g. `"(a) Higher actuals primarily reflect..."`), the same pattern MFS used |
| "Variance" column | n/a | **never extracted** - Actual minus Budget, entirely derivable, would double-count like a duplicate label if loaded |

`SOCE` (a rolling-balance-across-multiple-columns shape, same as AFS's
Statement of Changes in Equity) and `Admin` (Administered Items -
payments made **on behalf of the State**, a materially different
concept from the department's own controlled operations, at a
completely different scale - e.g. `$82 billion` administered income vs
`$466 million` controlled revenue) are **out of scope this milestone** -
deferred, not silently dropped.

## Two duplicate-by-design patterns found - the same pattern as AFS, in different labels

1. **BS**: `Net assets` (row 25) and `Total equity` (row 30) are
   numerically identical in both the Actual and Budget columns
   (`83/87` both times) - the same AASB-style cross-check pattern as
   AFS's `Net assets`/`Net worth`, just with a different second label.
   Only `Net assets` is loaded.
2. **OS**: `Net result` (row 22) and `Comprehensive result` (row 26) are
   numerically identical in both columns (`7/0` both times) - the same
   pattern as AFS's own `Net result`/`Comprehensive result` duplicate.
   Only `Net result` is loaded.

## Selected measures (11) - same conceptual set as AFS

| measure_type | source label | sheet |
|---|---|---|
| vic_bpo_revenue | Total revenue and income from transactions | OS |
| vic_bpo_expense | Total expenses from transactions | OS |
| vic_bpo_net_operating_balance | Net result from transactions (net operating balance) | OS |
| vic_bpo_net_result | Net result | OS |
| vic_bpo_total_assets | Total assets | BS |
| vic_bpo_total_liabilities | Total liabilities | BS |
| vic_bpo_net_assets | Net assets | BS |
| vic_bpo_net_cash_operating | Net cash flows from / (used in) operating activities | CFS |
| vic_bpo_net_cash_investing | Net cash flows from / (used in) investing activities | CFS |
| vic_bpo_net_cash_financing | Net cash flows from / (used in) financing activities | CFS |
| vic_bpo_cash_end_of_year | Cash and cash equivalents at the end of the financial year | CFS |

Each measure produces **2 facts** (estimate_status=`actual`,
estimate_status=`budget`) for the same financial_year (2024-25) -
verified directly (11 measures × 2 = 22 facts, zero duplicate
fact_keys).

Full semantic model, global rules, and forbidden/allowed comparisons:
`config/measure-semantics/vic_bpo.yaml`.

## Files added

- `config/measure-semantics/vic_bpo.yaml`
- `scripts/ingest/migrations/009_vic_bpo_measures.sql`
- `scripts/ingest/extractors/vic_bpo.py`
- `scripts/ingest/reload_vic_bpo.py`

## Verified before touching the real database

`--dry-run` against a scratch DB: `rows_extracted: 100`,
`rows_validated_publishable: 22`, `rows_quarantined_by_loader: 78`
(every other real line item on the 3 sheets, correctly left unpublished
this milestone), 0 revision conflicts. Direct per-measure count
confirms every one of the 11 measures has exactly 2 facts and zero
duplicate fact_keys.

## Next

Task 4: back up `data/facts.db`, load, prove idempotency, run
integrity/coverage checks.
