# PDF/OCR scope selection (Task 2)

Generated: 2026-08-06T18:59:46Z.

## Cloudflare triage

The selected family (below) extends the already-shipped `tas_ggs_*`
measure family and will be exposed through the **same existing** "TAS
GGS" toggle on `/explorers/gfs` - no new route, no new page. Every real
user path this milestone needs (clicking through from the homepage or
`/explorers` index, or switching an already-loaded page's measure/
vintage) is client-side navigation, not hard navigation, so this
selected path does not depend on the Cloudflare hard-navigation issue.

**Decision: out of scope, unchanged.** No repo-side Cloudflare code
changes are made in this milestone; it remains an external
infrastructure follow-up. No Cloudflare regression test is added (Task
8 - not applicable, matching this decision).

## Selected family

**TAS Treasurer's Annual Financial Report (TAFR) - tabular Executive
Summary sub-shape, 2010-11 to 2012-13** (3 editions), from the
`tas_treasurer_annual_financial_reports` population, source_family
`handoff_actuals_state`, jurisdiction TAS, government_level state.

## Why chosen

- **Real files already on disk**, directly inspected (not assumed from
  filenames):
  `data/raw/state/tas_treasurer_annual_financial_reports/snapshots/*/files/TAF-2010-11.pdf`,
  `2011-12-Treasurers-Annual-Financial-Report.pdf`,
  `2012-13-Treasurers-Annual-Financial-Report.pdf`.
- **Genuinely text-extractable, not OCR-dependent**: `pypdf` extracts
  clean, row-major text (`Label value1 value2 value3` per line) with no
  font-encoding corruption, confirmed across all 3 editions.
- **A stable, repeated tabular shape**: "Table 2.1: Key Financial
  Indicators" (General Government Sector: Net Operating Surplus/
  (Deficit), Fiscal Surplus/(Deficit), Net Debt, Net Worth, Net
  Financial Liabilities) and a "Summary of Operating Result" table
  (Revenue from transactions, Expenses from transactions, Net Operating
  Balance, Fiscal Balance) - confirmed structurally identical labels
  and column layout across all 3 target editions by direct inspection
  of each one's own extracted text.
- **Directly extends an already-shipped, already-tested measure
  family**: 7 of the already-loaded `tas_ggs_*` measure types
  (`tas_ggs_revenue`, `tas_ggs_expense`, `tas_ggs_net_operating_
  balance`, `tas_ggs_fiscal_balance`, `tas_ggs_net_debt`, `tas_ggs_net_
  worth`, `tas_ggs_net_financial_liabilities`) have a 1:1 label match in
  these PDF tables - no new measure family needs to be invented, and no
  risk of accidentally creating a duplicate concept under a different
  name.
- **Zero overlap with already-loaded years**: the GGS xlsx covers
  2013-14 onward; these 3 PDF editions cover 2010-11 to 2012-13 - a
  clean, non-overlapping backward extension of the same time series.
- **Does not depend on the Cloudflare issue** (see above).
- **No access blocker**: all 3 files are already acquired and on disk;
  no further download/discovery is needed.

## Why runners-up were deferred

| candidate | why deferred |
|---|---|
| TAS TAFR narrative sub-shape (2003-04 to 2009-10) | Confirmed genuinely different, harder shape (measures embedded in running prose and mini bar-chart-adjacent number lists, not a labelled table) - real coverage-gap opportunity but materially higher risk of misattributing a value to the wrong year without individual per-edition review. Deferred as a documented, out-of-scope-this-milestone sub-population, not silently dropped. |
| TAS Revised Estimates/Preliminary Outcomes/Quarterly Reports (~11 files) | The GGS xlsx already captures the authoritative per-year vintage; these add in-year revision detail without clear incremental dashboard value for this milestone. |
| TAS off-topic economic-indicator briefs (~11 files) | Wrong topic domain (ABS-style economic statistics, not TAS Treasury's own fiscal aggregates) - consistent with how similarly off-topic structured QLD candidates were deferred in the prior milestone. |
| QLD Report on State Finances population (187 files) | Confirmed font-encoding corruption risk on at least one page, column-to-sector ambiguity in the main summary table requiring per-edition cross-referencing, no existing measure family to extend (would require designing one from scratch), and an unbounded number of relevant editions still requiring a full survey. A future, dedicated QLD PDF/OCR milestone is the right vehicle. |

## Format classification

**PDF, text-extractable (no OCR required)** - confirmed directly via
`pypdf`'s `extract_text()` across all 3 target editions; no scanned-
image pages, no font-encoding corruption in the target tables. This is
the "handle PDF/OCR carefully and explicitly" case from the ground
rules, not a true OCR case (no image-to-text step is needed).

## Reusable adapter status

No existing adapter/loader exists for this PDF sub-shape (confirmed:
no TAS-PDF-specific files under `scripts/ingest/extractors/` or
`scripts/ingest/reload_*.py`). A new extractor + loader will be built
in Task 5, targeting the **same** `config/measure-semantics/tas_ggs_
key_fiscal_measures.yaml` semantic model and the **same** 7
compatibility_groups already shipped - this is an extension/backfill of
the existing family, not a new one, and `reload_tas_ggs_key_fiscal_
measures.py` (the existing, already-shipped xlsx loader) is **not
modified** - a new, separate loader is built instead, mirroring the
pattern already established for VIC BPO SOCE/Admin (a new adapter
extending a sibling family without touching the original).

## Access blocker

None. All 3 files are already acquired
(`handoff_already_on_disk: true` in `config/procurement_sources.yaml`,
verified against the actual on-disk snapshots) - no download, no
landing-page discovery, no age-gate or consent flow is required.

## Next

Task 3: deep-dive inventory of the 3 selected PDF editions' exact
pages, tables, rows, and OCR/text-extractability characteristics before
writing any adapter code.
