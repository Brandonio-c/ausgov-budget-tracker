# QLD Report on State Finances: semantic decision log (Task 4)

Generated: 2026-08-07T14:22:08Z.

## Config

`config/measure-semantics/qld_report_on_state_finances.yaml` - 8
measure types, each with its own dedicated `compatibility_group`
(1:1), `view_family` unset (never registered under any dashboard
`mode_to_family` mapping). Migration
`scripts/ingest/migrations/012_qld_rsf_measures.sql` defines the same
8 measure_types - verified programmatically that both files agree
exactly.

## Per-measure summary

| measure_type | flow_or_stock | row_label |
|---|---|---|
| `qld_rsf_revenue` | flow | Revenue |
| `qld_rsf_expense` | flow | Expenses |
| `qld_rsf_net_operating_balance` | balance (derived) | Net operating balance |
| `qld_rsf_capital_purchases` | flow | Capital purchases |
| `qld_rsf_fiscal_balance` | balance (derived) | Fiscal balance |
| `qld_rsf_borrowing_qtc` | stock | Borrowing with QTC |
| `qld_rsf_leases` | stock | Leases and similar arrangements |
| `qld_rsf_securities_derivatives` | stock | Securities and derivatives |

`accounting_basis: gfs` for all 8 measures - the source table is
explicitly UPF/GFS-framework branded ("Key UPF Financial Aggregates"),
unlike TAS's own more general "Key Fiscal Measures" naming.

## Key decision: `estimated_actual`, not `budget`

Documented as `global_rules.qld_rsf_estimate_status_estimated_actual_
not_budget`: QLD's "Est. Actual" column is a fundamentally different
vintage concept from TAS's TAFR "Original Budget" column - it is the
estimated outcome for the reporting year as published in a **later**
budget-cycle document (confirmed directly from each edition's own
narrative text, e.g. "compared to the estimated actual (Est. Actual)
per the 2019-20 Budget"). Mapped to the schema's existing
`estimated_actual` token (already valid in the facts table's CHECK
constraint), never `budget` - avoiding a real semantic error that
would have misrepresented the vintage.

## Scope exclusions, explicit and documented

- Public Non-financial Corporations Sector and Non-financial Public
  Sector columns (the 2nd and 3rd sector-pairs in the same table) -
  General Government Sector only, matching this project's convention
  throughout.
- "Net Debt" and "Borrowings" rows - present only from 2020-21/2021-22
  onward respectively, excluded to keep the adapter's required row-set
  uniform across the full 2018-19 to 2024-25 cluster.
- Older report generations (2002-03 to 2017-18) - a different label
  vocabulary, deferred per Task 1/2's findings.

## Revision policy

Each of the 7 target editions is the department's own final, audited
report for its stated year - no competing prior edition of the same
year exists today. The shared `fact_key` scheme (source_id +
financial_year + measure_type + accounting_basis + estimate_status +
jurisdiction) means any future re-acquisition producing a conflicting
amount is quarantined, never silently overwritten - the same mechanism
used by every other family in this repo.

## Next

Task 5: build the extractor + loader implementing the page-location-
by-content, GGS-only-first-pair extraction, and comma-thousands-
separator/parenthesized-negative parsing this semantic model depends
on.
