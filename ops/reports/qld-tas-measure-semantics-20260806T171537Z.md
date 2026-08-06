# TAS GGS Key Fiscal Measures: semantic model (Task 4)

Generated: 2026-08-06T17:15:37Z.

## Config

`config/measure-semantics/tas_ggs_key_fiscal_measures.yaml` - 10
measure types, each with its own dedicated `compatibility_group` (1:1),
`view_family` unset (never registered under any dashboard
`mode_to_family` mapping), verified parseable and correctly 1:1-mapped.

## Per-measure summary

| measure_type | flow_or_stock | accounting_basis | source_column |
|---|---|---|---|
| `tas_ggs_revenue` | flow | accrual | Revenue from Transactions |
| `tas_ggs_expense` | flow | accrual | Expenses from Transactions |
| `tas_ggs_net_operating_balance` | balance (derived) | accrual | Net Operating Balance |
| `tas_ggs_fiscal_balance` | balance (derived) | accrual | Fiscal Balance |
| `tas_ggs_infrastructure_investment` | flow | accrual | Infrastructure Investment |
| `tas_ggs_net_debt` | stock | accrual | Net Debt at 30 June |
| `tas_ggs_gfs_net_debt` | stock | gfs | GFS Net Debt at 30 June |
| `tas_ggs_net_worth` | stock_balance (derived) | accrual | Net Worth |
| `tas_ggs_net_financial_liabilities` | stock | accrual | Net Financial Liabilities |
| `tas_ggs_cash_surplus_deficit` | flow | cash | Cash Surplus/Deficit |

Every `economic_meaning` field is drawn verbatim (quoted) from the
workbook's own `Definitions for Key Measures` sheet - not invented.

## Revision policy (explicit, per the mission's requirement)

Documented as `global_rules.tas_ggs_revision_policy` in the YAML:

- `estimate_status` (`actual` / `revised_budget` / `forward_estimate`)
  is part of the fact_key's identity - a future re-acquisition that
  advances a year's vintage (e.g. 2025-26 moving from `revised_budget`
  to `actual` in next year's edition) produces a **new, additional**
  fact rather than overwriting the prior vintage's fact, which remains
  as an auditable historical record.
- If a future re-acquisition ever produces a **different amount** for
  the exact same identity (source_id + financial_year + measure_type +
  accounting_basis + estimate_status + jurisdiction), the loader
  refuses to silently overwrite - it is quarantined pending explicit
  review, matching every other family in this repo.
- **Vintage precedence for display**: `actual` > `revised_budget` >
  `forward_estimate` - documented for any future consumer that wants a
  single "best known" value per year, though the API/series endpoint
  itself returns all vintages (never silently drops one).

## Unit conversion

`scale_factor: 1000000` for every measure (`$m` -> AUD), applied
exactly once by the loader after the number-parsing step described in
Task 3's inventory (stripping non-breaking-space/whitespace thousands
separators from string-typed cells).

## Isolation from the ABS's own TAS GFS series

Every measure's `forbidden_comparisons` explicitly excludes
`abs_gfs_state_tas_*`/`abs_state_accounts_tas_*` - confirmed as a
distinct publisher/methodology in Task 1's DB inspection, never merged
or compared as equivalent even where names are similar (e.g.
`tas_ggs_gfs_net_debt` vs `abs_gfs_state_tas_236`'s own net debt
figure - same underlying GFS concept, independently compiled by two
different organisations, kept in separate compatibility_groups).

## Next

Task 5: build the extractor + loader (`scripts/ingest/extractors/
tas_ggs_key_fiscal_measures.py`, `scripts/ingest/reload_tas_ggs_key_
fiscal_measures.py`) implementing the number-parsing and year-label
footnote-stripping logic this semantic model depends on.
