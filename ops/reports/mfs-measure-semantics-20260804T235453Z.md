# MFS measure semantics (Task 3)

Generated: 2026-08-04T23:54:53Z. Full declarative decision table:
`config/measure-semantics/mfs.yaml`. Evidence base: Task 2's corpus
inventory (`ops/reports/mfs-corpus-inventory-20260804T234455Z.md`),
verified directly against all 26 sheets of the real Aggregates workbook -
nothing below is assumed.

## 15 measure types, one compatibility_group each

| measure_type | flow_or_stock | compatibility_group | published since |
|---|---|---|---|
| `mfs_ytd_revenue` | flow | `mfs_ytd_revenue` | FY2000-01 |
| `mfs_ytd_expense` | flow | `mfs_ytd_expense` | FY2000-01 |
| `mfs_ytd_net_operating_balance` | balance | `mfs_ytd_net_operating_balance` | FY2000-01 |
| `mfs_ytd_net_capital_investment` | flow | `mfs_ytd_net_capital_investment` | FY2007-08 |
| `mfs_ytd_fiscal_balance` | balance | `mfs_ytd_fiscal_balance` | FY2000-01 |
| `mfs_ytd_receipts` | flow | `mfs_ytd_receipts` | FY2011-12 |
| `mfs_ytd_payments` | flow | `mfs_ytd_payments` | FY2011-12 |
| `mfs_ytd_net_future_fund_earnings` | flow | `mfs_ytd_net_future_fund_earnings` | FY2013-14..2019-20 only |
| `mfs_ytd_underlying_cash_balance` | balance | `mfs_ytd_underlying_cash_balance` | FY2000-01 |
| `mfs_ytd_headline_cash_balance` | balance | `mfs_ytd_headline_cash_balance` | FY2000-01 |
| `mfs_stock_total_assets` | stock | `mfs_stock_total_assets` | FY2000-01 |
| `mfs_stock_total_liabilities` | stock | `mfs_stock_total_liabilities` | FY2000-01 |
| `mfs_stock_net_worth` | stock_balance | `mfs_stock_net_worth` | FY2000-01 (gap: FY2005-06) |
| `mfs_stock_net_debt` | stock_balance | `mfs_stock_net_debt` | FY2010-11 |
| `mfs_stock_cash_and_deposits` | stock | `mfs_stock_cash_and_deposits` | reserved, not loaded (no extractor for Balance Sheet) |

**Each measure_type is its own compatibility_group** (1:1), the strongest
possible guarantee that `src/backend/routers/v2/dashboard.py`'s generic
`compatibility_group`-keyed queries can never pull an MFS fact into any
existing annual additive tree, or pull two different MFS measures
together into one additive series - this is a direct, deliberate response
to the exact contamination mechanism found and fixed in Task 1 (a shared
`compatibility_group` was the entire reason that bug was possible).

## Why balances aren't just "flows"

`net_operating_balance`, `fiscal_balance`, `underlying_cash_balance`, and
`headline_cash_balance` are marked `flow_or_stock: balance` (not `flow`)
specifically so nothing ever treats them as summable raw flows - the
mission's rule "Balances may not be summed into revenue or expense
totals" is encoded as their own third category, not just documentation.
`net_worth` and `net_debt` get `stock_balance` for the same reason on the
stock side (derived from other stocks, never summed with them).

## Two genuinely different "as at" mechanics

- **Flows** (`mfs_ytd_*`): `period_start` = 1 July of the financial year,
  `period_end` = the reporting month's last day - a true YTD accumulation.
- **Stocks** (`mfs_stock_*`): `period_start` = null (a stock has no
  accumulation window), `period_end` = the reporting month's last
  calendar day, meaning "as at that date" - confirmed this is exactly how
  the separate Balance Sheet workbook's own column headers say it
  (`"ACTUAL\nas at\n31 July 2015\n$m"`), even though the Aggregates
  workbook's shared column-header format doesn't say "as at" explicitly
  for its own Total assets/Total liabilities/Net worth/Net debt rows - the
  distinction lives in `flow_or_stock`, not in parsing the header text
  differently per row.

## Label-variant mapping is exhaustive and evidence-based, not fuzzy

Every `source_label_variants` list is the **complete, literal set** of
wordings that measure has actually used across all 26 sheets (Task 2's
row-by-row inventory), stripped of trailing footnote markers only. No
fuzzy matching, substring matching, or "closest match" logic anywhere -
`mfs_ytd_payments`, for example, explicitly lists all five of `Payments`,
`Payments(b)`, `Payments(c)`, `less Payments(b)`, `less Payments(c)`,
`Underlying Cash Payments`, individually, because all five were found in
the real corpus. A label not in any list is quarantined by the Task 5
loader (`unrecognized_label` quarantine rule) - never guessed.

## Absent-year gaps are declared, not defaulted

`not_published_before_financial_year` (`mfs_ytd_net_capital_investment`,
`mfs_ytd_receipts`, `mfs_ytd_payments`, `mfs_stock_net_debt`),
`only_published_financial_years` (`mfs_ytd_net_future_fund_earnings`), and
`known_gap_financial_years` (`mfs_stock_net_worth`, FY2005-06
specifically) are each declared explicitly per measure. The Task 5 loader
must not backfill, interpolate, or zero-fill any of these - simply no
fact exists for that measure/year, which any API consumer must be able to
tell apart from "measure exists but happened to be zero."

## Nine global rules, enforced at both load time (Task 5) and API time (Task 8)

See `config/measure-semantics/mfs.yaml`'s `global_rules` block for the
full text of each. Summary: YTD-vs-YTD only at the same elapsed period;
stocks compared only at compatible dates; balances never summed with
flows or with each other; every MFS measure has its own
compatibility_group so it can never enter an annual additive group;
MFS is never registered under any existing dashboard `mode_to_family`
mapping (`config/compatibility/view_families.yaml`) - it is exposed only
through its own dedicated API, never `/v2/dashboard/tree`; unit
conversion always preserves the original source unit alongside the
converted AUD amount; bare (non-YTD) month headers are quarantined except
July; label synonyms are individually enumerated, never inferred; and an
absent year is absent, never zero.

## Six quarantine rules for the Task 5 loader

`unrecognized_label`, `unrecognized_column_header`,
`ambiguous_bare_month`, `undetermined_unit`, `missing_source_cell`, and
the structural exclusion of the title row and the trailing
footnote-explanation row (which starts with `(<letter>)` at the *start*
of the label, distinct from a data row's *trailing* footnote marker -
same distinction `mfs_aggregates.py`'s existing `FOOTNOTE_ROW` vs
`TRAILING_FOOTNOTE_MARK` regexes already draw).

## Next

Task 4: run `mfs_aggregates.py` across the full corpus (no DB writes) and
produce the row-level staging audit, classifying every extracted row
against this semantic model - confirming every publishable row resolves
to exactly one of the 15 measures above via its `source_label_variants`,
with nothing left ambiguously matched.
