# TAS TAFR PDF backfill: semantic model (Task 4)

Generated: 2026-08-06T18:59:46Z.

## Config

`config/measure-semantics/tas_tafr_pdf_backfill.yaml` - 7 measures,
each reusing an already-shipped `tas_ggs_*` `measure_type`/
`compatibility_group` (from `scripts/ingest/migrations/011_tas_ggs_key_
fiscal_measures.sql`) rather than defining new ones. No new migration
is needed.

**Verified programmatically** that every shared field
(`compatibility_group`, `accounting_basis`, `flow_or_stock`,
`scale_factor`, `unit`) is byte-identical between this new PDF-specific
YAML and the existing `tas_ggs_key_fiscal_measures.yaml` for all 7
measures - 0 mismatches found. This is a self-contained, separate
config file (not a modification of the existing YAML), mirroring the
VIC BPO SOCE/Admin pattern of a new adapter extending a sibling family
without touching the original.

## Per-measure summary

| measure_type | source_table | pdf_row_label_variants |
|---|---|---|
| `tas_ggs_revenue` | Summary of Operating Result | Revenue from transactions |
| `tas_ggs_expense` | Summary of Operating Result | Expenses from transactions / Expense from transactions |
| `tas_ggs_net_operating_balance` | both tables | Net Operating Surplus/(Deficit) / Net Operating Balance – Surplus/(Deficit) |
| `tas_ggs_fiscal_balance` | both tables | Fiscal Surplus/(Deficit) / Equals Fiscal Balance – Surplus/(Deficit) |
| `tas_ggs_net_debt` | Key Financial Indicators | Net Debt |
| `tas_ggs_net_worth` | Key Financial Indicators | Net Worth |
| `tas_ggs_net_financial_liabilities` | Key Financial Indicators | Net Financial Liabilities |

## Revision policy (explicit, per the mission's requirement)

Documented as global_rules in the YAML:

- This adapter covers financial years 2010-11 to 2012-13 - **disjoint**
  from the GGS xlsx's 2013-14-onward coverage. No overlap exists today.
- The `estimate_status` mapping introduces `budget` (the TAFR's
  "Original Budget" column) as a genuinely new value for the
  `tas_ggs_*` family - distinct from `revised_estimate` (the xlsx's
  "Revised Budget" mid-cycle vintage) and `forward_estimate`. `budget`
  is already a valid value in the facts table's own CHECK constraint.
- If a future re-acquisition of either source ever produces
  overlapping years, the shared `fact_key` scheme means the loader's
  existing amount-conflict detection (refuse-and-quarantine, never
  silently overwrite) applies automatically - no new mechanism needed.
- "Underlying Net Operating Surplus/(Deficit)" is explicitly excluded -
  a distinct concept not modelled by any existing measure, not a
  duplicate of Net Operating Balance.
- The Total State Sector's parallel tables are explicitly excluded via
  a page-order rule (verified across all 3 editions, since title-text
  matching alone fails for the 2010-11 edition's wrapped heading).
- Net Operating Balance and Fiscal Balance each appear in both target
  tables per edition; both extractions resolve to the same fact_key,
  so the loader's existing idempotent-skip logic (not a new mechanism)
  handles the expected duplication correctly.

## Next

Task 5: build the PDF extractor and loader implementing the page-order
disambiguation, paired-parenthesis negative-number parsing, and
space-thousands-separator handling this semantic model depends on.
