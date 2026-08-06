# QLD/TAS scope selection (Task 2)

Generated: 2026-08-06T17:15:37Z.

## Cloudflare triage

The affected symptom (hard navigation to a static route under
`vibefactory.app/ausgov-budget-tracker/*` can render the wrong content
or 404, per `ops/reports/vic-bpo-soce-admin-production-verification-
20260806T170227Z.md`'s finding that this now also affects the root
path) is a Cloudflare-edge-routing issue external to this repository.
The selected family (below) will be wired into the **existing**
`/explorers/gfs` page - the same already-working nested route the VIC
AFS/VIC BPO/VIC SOCE-Admin families already use successfully via
in-app client-side navigation. No new route is introduced, and every
real user path this milestone needs (clicking through from the
homepage or `/explorers` index, or switching an already-loaded page's
measure dropdown) is client-side navigation, not hard navigation.

**Decision: out of scope, unchanged.** No repo-side Cloudflare code
changes are made in this milestone; it remains an external
infrastructure follow-up. No Cloudflare regression test is added (Task
8 - not applicable, matching this decision).

## Selected family

**`tas_treasurer_annual_financial_reports`** - specifically its `GGS
Key Fiscal Measures Time Series` workbook (`GGS-Key-Fiscal-Measures-
Time-Series.xlsx`), source_family `handoff_actuals_state`, jurisdiction
TAS, government_level state.

## Why chosen

- **Real file already on disk**, directly inspected (not assumed from
  the filename): `data/raw/state/tas_treasurer_annual_financial_
  reports/snapshots/20260724T170239Z/files/GGS-Key-Fiscal-Measures-
  Time-Series.xlsx`.
- **Structured**: a single `Time Series` sheet, 24 rows x 12 columns -
  `Year | Data Type | Revenue from Transactions | Expenses from
  Transactions | Net Operating Balance | Fiscal Balance |
  Infrastructure Investment | Net Debt at 30 June | GFS Net Debt at 30
  June | Net Worth | Net Financial Liabilities | Cash Surplus/Deficit`,
  unit `$m` throughout, plus a `Definitions for Key Measures` sheet (51
  rows, prose definitions only - not extracted as facts, used only to
  inform the semantic model's `economic_meaning` fields in Task 4).
- **16 years, 3 vintages, one workbook**: 2013-14 through 2028-29,
  covering `Actual` (2013-14 to 2024-25), `Revised Budget` (2025-26),
  and `Forward Estimate` (2026-27 to 2028-29) - the best coverage-per-
  adapter ratio of any candidate inspected.
- **Zero existing coverage**: confirmed via direct `data/facts.db`
  inspection - no `tas_*`-prefixed measure_type exists today. TAS's
  only current coverage is the ABS's own independently-compiled
  `abs_gfs_state_tas_236`/`abs_state_accounts_tas_*` series (a
  different publisher and methodology) and TASCORP debt-instrument data
  (`tas_tascorp_annual_report_2024_25`, already used by `debt_
  reconciliation.py`). This is a genuinely new family, not a duplicate.
- **Does not depend on the Cloudflare issue** (see above) - it will be
  wired into the already-working `/explorers/gfs` page.
- **No access blocker**: the file is already acquired and on disk; no
  further download/discovery is needed.

## Why runners-up were deferred

| candidate | why deferred |
|---|---|
| `qld_report_on_state_finances_actuals` / `qld_report_on_state_finances` | Both are PDF-only in practice - the QLD population's single `xlsx` is a **blank Machinery-of-Government transfer sign-off form template**, confirmed by directly opening it (104x10, almost entirely `NaN`, an `(insert year)` placeholder cell, no financial data whatsoever). Building an adapter here would require full PDF/OCR extraction across dozens of report editions - excluded this milestone per the ground rule to prefer structured sources; a future, dedicated PDF/OCR triage milestone is the right vehicle. |
| `qld_qgip_expenditure`, `qld_contract_disclosure_agency_datasets`, `qld_on_time_payment_reports` | Genuinely structured (csv/json/xlsx) but a different topic domain entirely - grant/funding-agreement expenditure detail, per-contract procurement disclosure, and supplier payment-timing compliance, respectively. None are state-level revenue/expense/balance aggregates; none continue the state-actuals dashboard theme this and the prior two milestones have built. Deferred as candidates for a future procurement/contracts-focused milestone, not excluded as duplicates. |
| `tas_tascorp_annual_report_2024_25` | Already has adapter coverage (`debt_reconciliation.py`) - not a fresh candidate. |

## Format classification

**Structured** (not mixed, not hybrid) for the specific file being
implemented - `GGS-Key-Fiscal-Measures-Time-Series.xlsx` is a clean,
directly-parseable xlsx with no PDF/OCR component. The **population**
it belongs to (`tas_treasurer_annual_financial_reports`, 178 files) is
itself a mixed population (76 PDFs + this 1 xlsx) - per the mission's
instruction to "split the triage by shape and only implement the
shape(s) that are clearly supported," only the structured xlsx shape is
implemented this milestone. The 76 PDF siblings (individual annual
Treasurer's Financial Report documents) are out of scope, documented
here as deferred (not silently dropped) for a future PDF/OCR-focused
milestone.

## Reusable adapter status

No existing adapter/loader/semantic model exists for this family
(confirmed: no `tas_*` files under `scripts/ingest/extractors/`,
`scripts/ingest/reload_*.py`, or `config/measure-semantics/`). A new,
single adapter (extractor + loader + semantic YAML) will be built in
Task 3/4/5.

## Access blocker

None. The file is already acquired (`handoff_already_on_disk: true` in
`config/procurement_sources.yaml`, verified against the actual on-disk
snapshot) - no download, no landing-page discovery, no age-gate or
consent flow is required.

## Next

Task 3: deep-dive inventory of the selected workbook's exact rows,
columns, units, and vintage semantics before writing any adapter code.
