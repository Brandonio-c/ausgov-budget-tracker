# VIC DTF Annual Financial Statements - inventory (Task 3)

Generated: 2026-08-05T16:45:12Z.

## Source

`vic_annual_financial_statements_2024_25` - Victorian Department of
Treasury and Finance's own 2024-25 annual financial statements.
`config/procurement_sources.yaml:5416` (priority P0, `handoff_actuals_state`
family). One acquired asset, verified:

- `data/raw/state/vic_annual_financial_statements_2024_25/snapshots/20260724T190604Z/files/Annual-financial-statements-2024-25.xlsx`
- 51,743 bytes; sha256 `307aac748b06aa7d2c1197ca370e0df07c20449f4b2fa564673888e04511c0f3`
  (matches `hashes.json` and `latest.json` exactly).
- Real government URL: `https://www.dtf.vic.gov.au/sites/default/files/2025-10/Annual-financial-statements-2024-25.xlsx`,
  HTTP 200, `validation_status: valid`.

## Workbook structure

10 sheets: `Introduction`, `Operating Statement`, `Balance Sheet`,
`Statement of Changes in Equity`, `Cash Flow Statement`, `Departmental
Outputs Schedule`, `Annual Appropriations`, `Special Appropriations`,
`Administered Income & Expenses`, `Administered Assets & Liab`.

**This milestone extracts 3 sheets only**: `Operating Statement`,
`Balance Sheet`, `Cash Flow Statement`. All three share one consistent,
directly-parseable layout, verified by direct inspection of every row:

- Row 0: title (financial year embedded in text, not parsed - the
  header row's year values are authoritative).
- Row 1: unit row, always exactly `"($ thousand)"` in the last column.
- Row 2: header row (`Notes | <year1> | <year2>`, e.g. `2025 | 2024`
  meaning "year ended 30 June 2025" = FY2024-25, and "year ended 30 June
  2024" = FY2023-24).
- Rows 3+: labelled line items, two years of **already-numeric**
  comparative data (no string parsing; expenses are already signed
  negative floats, not parenthesized text).
- A `Source: 2024-25 DTF Annual Report (...)` footer row terminates the
  sheet.

`Statement of Changes in Equity`, `Departmental Outputs Schedule`,
`Annual Appropriations`, `Special Appropriations`, `Administered Income &
Expenses`, `Administered Assets & Liab` are **out of scope this
milestone** - `Statement of Changes in Equity` has a fundamentally
different rolling-balance-across-multiple-columns shape; the others
were not inspected in depth (deferred, not silently dropped).

## Two duplicate-by-design patterns found and handled

Both verified by direct row-level inspection, not assumed:

1. **Balance Sheet**: `Net assets` (row 21, immediately after the
   Liabilities section) and `Net worth` (row 25, immediately after the
   Equity section) are numerically identical in every period
   (`81829/75173` both times) - an AASB-style cross-check that total
   equity reconciles to net assets, not two distinct figures. Only `Net
   assets` is loaded.
2. **Operating Statement**: `Net result` (row 20) and `Comprehensive
   result` (row 21) are also numerically identical (`6656/961` both
   times) - this entity has no items of other comprehensive income
   distinct from net result. Only `Net result` is loaded. **Found via
   the loader's own dry-run** (see Task 4's report) - my first pass at
   `config/measure-semantics/vic_afs.yaml` mistakenly listed both as
   variants of the same measure, which a dry-run immediately surfaced as
   24 publishable rows instead of the expected 22; fixed before any
   `--apply`.

## Cash Flow Statement's embedded notes appendix

Beyond row 28 (`Cash and cash equivalents at end of financial year`,
the primary statement's last line), the sheet continues with numbered
notes sections (`7.2 Cash flow information and balances`, `7.2.1
Reconciliation of net result for the year to cash flows from operating
activities`) that **restate primary-statement totals** under the same
or a different label as cross-checks - e.g. `Net cash flows from/(used
in) operating activities` appears twice with the identical value, once
in the primary statement and once in the `7.2.1` reconciliation note.
The extractor (`scripts/ingest/extractors/vic_afs.py`) stops at the
first row matching a numbered-note-heading pattern (`^\d+\.\d+`),
keeping only the primary statement's own rows.

## Selected measures (11)

| measure_type | source label | sheet | flow_or_stock |
|---|---|---|---|
| vic_afs_revenue | Total income from transactions | Operating Statement | flow |
| vic_afs_expense | Total expenses from transactions | Operating Statement | flow |
| vic_afs_net_operating_balance | Net result from transactions (net operating balance) | Operating Statement | balance |
| vic_afs_net_result | Net result | Operating Statement | balance |
| vic_afs_total_assets | Total assets | Balance Sheet | stock |
| vic_afs_total_liabilities | Total liabilities | Balance Sheet | stock |
| vic_afs_net_assets | Net assets | Balance Sheet | stock_balance |
| vic_afs_net_cash_operating | Net cash flows from/(used in) operating activities | Cash Flow Statement | flow |
| vic_afs_net_cash_investing | Net cash flows from/(used in) investing activities | Cash Flow Statement | flow |
| vic_afs_net_cash_financing | Net cash flows from/(used in) financing activities | Cash Flow Statement | flow |
| vic_afs_cash_end_of_year | Cash and cash equivalents at end of financial year | Cash Flow Statement | stock |

Full semantic model, global rules, and forbidden/allowed comparisons:
`config/measure-semantics/vic_afs.yaml`.

## Scope note: department-level, not whole-of-government

Every figure here is the **Department of Treasury and Finance's own**
departmental financial statements - not whole-of-Victorian-government.
This is a genuinely new granularity level, distinct from any existing
GFS/state-actuals family covering VIC, and must never be merged into or
compared against those totals as if equivalent.

## Files added

- `config/measure-semantics/vic_afs.yaml`
- `scripts/ingest/migrations/008_vic_afs_measures.sql`
- `scripts/ingest/extractors/vic_afs.py`
- `scripts/ingest/reload_vic_afs.py`

## Next

Task 4: back up `data/facts.db`, load, prove idempotency, run integrity/
coverage/reconciliation checks - see
`ops/reports/vic-afs-loader-20260805T164512Z.md`.
