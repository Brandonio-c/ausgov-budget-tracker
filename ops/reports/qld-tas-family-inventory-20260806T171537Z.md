# TAS GGS Key Fiscal Measures Time Series: family inventory (Task 3)

Generated: 2026-08-06T17:15:37Z.

## File identity

- Path: `data/raw/state/tas_treasurer_annual_financial_reports/snapshots/20260724T170239Z/files/GGS-Key-Fiscal-Measures-Time-Series.xlsx`
- SHA-256: `1434b003c1c789afc8c1c150a7b3f018ce6f2c21e4195dc478ade0b2c834f0f2`
- Original source URL (from `latest.json`):
  `https://www.treasury.tas.gov.au/Documents/GGS%20Key%20Fiscal%20Measures%20Time%20Series.xlsx`
- HTTP `Last-Modified`: `Mon, 20 Apr 2026 23:22:40 GMT`; sheet's own
  stated vintage (cell `L24`): `"Last updated: Feb 2026"`. Both are
  recorded; the sheet's own stated vintage is used as the human-facing
  publication note since it is the publisher's own claim about content
  currency (the HTTP header reflects server-side file-touch time, which
  can differ slightly, e.g. a metadata-only re-save).
- 2 sheets: `Time Series` (24 rows x 12 columns of real content; the
  raw `ws.dimensions` reports `A1:AH55` but every cell beyond row 24 /
  column L is confirmed empty via direct `openpyxl` iteration - stray
  template formatting, not data) and `Definitions for Key Measures` (51
  rows x 1 column, prose only).

## `Time Series` sheet shape

Row 1: title (`General Government Key Fiscal Measures 2013-14 to
2028-29`). Row 2: column headers (`Year | Data Type | Revenue from
Transactions | Expenses from Transactions | Net Operating Balance... |
Fiscal Balance... | Infrastructure Investment | Net Debt at 30 June |
GFS Net Debt at 30 June | Net Worth | Net Financial Liabilities | Cash
Surplus/Deficit`). Row 3: unit row, `$m` in every measure column. Rows
4-19: one row per financial year, 2013-14 through 2028-29 (16 years).
Row 20: `Note:` label. Rows 21-23: 3 numbered footnotes. Row 24, column
L only: `Last updated: Feb 2026`.

## Data-type inventory - the real parsing challenge (verified with `openpyxl`, `data_only=True`, not `pandas`'s type-inferred view)

Cell values in the 10 measure columns are **not uniformly typed**:
most are native `int`/`float`, but many - especially the entire
`Infrastructure Investment` column, and scattered cells in `Net
Operating Balance`, `Fiscal Balance`, `Net Debt`, `GFS Net Debt` - are
Excel **strings** with a leading space and a trailing non-breaking
space (`\xa0`), e.g. `' 324\xa0'`. Some larger values use an **embedded
non-breaking space as a thousands separator inside the string**, e.g.
`'1\xa0273.4\xa0'` (one thousand two hundred seventy-three point four)
and `'1 874.6\xa0'` (a literal space, not `\xa0`, used the same way in
at least one cell - both separators must be handled). This is real
source data quality, not a copy artifact of pandas - confirmed by
reading with `openpyxl` directly. The adapter's number parser must:

1. Strip leading/trailing whitespace and `\xa0`.
2. Remove any embedded whitespace/`\xa0` used as a thousands separator
   within the remaining string.
3. Parse the result as a float.
4. Never guess a value it cannot confidently parse - quarantine
   instead (ground rule: quarantine ambiguous rows rather than
   guessing).

## Year-label footnote markers - appended with no separator

Two year labels have a footnote-reference digit appended **directly to
the year string with no space**: `'2016-171'` (financial year
`2016-17` + footnote `1`, referencing the Mersey Community Hospital
one-off payment) and `'2020-212'` (financial year `2020-21` + footnote
`2`, referencing the rounding-convention change from nearest million to
nearest $100,000). Several other year labels carry a trailing
non-breaking space with no footnote digit (e.g. `'2023-24\xa0'`). The
adapter must parse the true `YYYY-YY` financial year from the messy
label without silently misreading `2016-171` as an invalid or
out-of-range year - handled via a regex that captures the `YYYY-YY`
pattern first and treats any trailing digit(s) as a footnote marker,
never as part of the year.

## Vintage (`Data Type` column) - a per-year label, not a same-year comparison

Unlike the VIC BPO family (same year, two columns: Actual vs Budget),
this workbook gives **each year exactly one `Data Type`**: `Actual` for
2013-14 through 2024-25 (12 years), `Revised Budget` for 2025-26 (1
year), `Forward Estimate` for 2026-27 through 2028-29 (3 years). This
is recorded as `estimate_status` per fact, matching the sheet's own
stated values exactly (mapped to lowercase-with-underscore tokens:
`actual`, `revised_budget`, `forward_estimate`) - never inferred from
year position alone.

## Flow vs. stock classification (confirmed against the `Definitions for Key Measures` sheet's own prose, not assumed)

| column | flow_or_stock | why |
|---|---|---|
| Revenue from Transactions | flow | "recognised when an increase in future economic benefits... has arisen" - an in-year transaction flow |
| Expenses from Transactions | flow | same, expense side |
| Net Operating Balance | balance (derived flow) | "Revenue from transactions less Expenses from transactions" |
| Fiscal Balance | balance (derived flow) | Net Operating Balance-like measure, additionally net of non-financial asset investment |
| Infrastructure Investment | flow | in-year capital spending |
| Net Debt at 30 June | stock | explicitly "at 30 June" - a point-in-time balance |
| GFS Net Debt at 30 June | stock | same, ABS-GFS-consistent variant excluding lease/service-concession liabilities |
| Net Worth | stock_balance | "Total assets less Total liabilities" - a derived point-in-time balance |
| Net Financial Liabilities | stock | "Total liabilities less Financial assets" - point-in-time |
| Cash Surplus/Deficit | flow | "net cash flows from operating activities plus net cash flows from investments" - an in-year cash flow measure |

## Publishability

All 10 measure columns across all 16 years are publishable once the
number-parsing and year-label-footnote-stripping logic above is
applied correctly. No row is inherently ambiguous in the source data
itself - the only "ambiguity" is in raw cell representation (string vs
numeric), which is fully resolved by a deterministic parser, not a
guess. If the parser ever encounters a cell it cannot confidently
resolve to a number (e.g. unexpected non-numeric text), it quarantines
that cell rather than guessing, per the ground rules.

## Current ingestion status

Not previously ingested - confirmed via `data/facts.db` inspection
(zero `tas_*`-prefixed `measure_type` rows exist today). No existing
adapter, loader, or semantic model references this file.

## Next

Task 4: declarative semantic model
(`config/measure-semantics/tas_ggs_key_fiscal_measures.yaml`) defining
each of these 10 measures' economic meaning (using the source's own
`Definitions for Key Measures` sheet text), flow/stock classification,
period semantics, vintage/estimate_status handling, unit conversion
($m -> AUD), and a dedicated, isolated compatibility_group per measure
- consistent with every other family in this repo, and explicitly kept
separate from the ABS's independently-compiled `abs_gfs_state_tas_236`
series for the same jurisdiction.
