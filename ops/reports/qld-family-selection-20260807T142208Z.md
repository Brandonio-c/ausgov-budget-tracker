# QLD family selection (Task 2)

Generated: 2026-08-07T14:22:08Z.

## Cloudflare status

Unchanged, external, out of scope. The selected family (below) will be
exposed via the existing, already-working GFS/jurisdiction explorer
(`/explorers/gfs`) - the same page VIC AFS, VIC BPO, VIC BPO SOCE/
Admin, and TAS GGS already use successfully via in-app client-side
navigation. No new route is introduced, so this milestone does not
depend on the Cloudflare hard-navigation issue. It remains tracked as
an external infrastructure follow-up, not touched here.

## Selected family

**QLD "Report on State Finances" - Summary of Key UPF Financial
Aggregates table, 2018-19 to 2024-25 (7 editions)** - source_family
`handoff_actuals_state`, source_id `qld_report_on_state_finances_
actuals`, jurisdiction QLD, government_level state.

## Why chosen

- **Real files already on disk**, directly inspected across all 7
  target editions (not assumed from filenames):
  `2018-19-Report-on-State-Finances.pdf`,
  `20-077-FG-Report-on-State-Finances-2019-20-Full.pdf`,
  `Report-on-State-Finances-2020-21.pdf`,
  `Report-on-State-Finances-2021-22.pdf`,
  `Report-on-State-Finances-2022-23.pdf`,
  `Report-on-State-Finances-2023-24.pdf`,
  `Report-on-State-Finances-2024-25.pdf`.
- **Genuinely text-extractable, no OCR needed**: `pypdf` extracts
  clean, row-major text for the target "Summary of Key UPF Financial
  Aggregates" table page in every one of the 7 editions - no font-
  encoding corruption found on any target page (the corruption
  previously flagged in the prior milestone's spot-check was on a
  cover page, never on a data table).
- **A stable, repeated 8-row structure confirmed across all 7
  editions** (not one sample): Revenue, Expenses, Net operating
  balance, Capital purchases, Fiscal balance, Borrowing with QTC,
  Leases and similar arrangements, Securities and derivatives - each
  with 3 sector-pairs (6 numeric columns), General Government Sector
  reliably the first pair, cross-verified against each edition's own
  narrative commentary.
- **A genuinely new, sizeable family**: zero existing `qld_*`-prefixed
  measure_type coverage confirmed via direct `data/facts.db`
  inspection - fills a real gap (every other jurisdiction already has
  its own Treasury-published fiscal-aggregate family: MFS for federal,
  VIC AFS/BPO for Victoria, TAS GGS for Tasmania; QLD currently has
  none).
- **Does not depend on the Cloudflare issue** (see above).
- **No access blocker**: all 7 files are already acquired and on disk;
  no further download/discovery is needed.

## Why runners-up were deferred

| candidate | why deferred |
|---|---|
| QLD Report on State Finances, older generations (2002-03 to 2017-18, 16+ editions) | Confirmed real format drift across at least 3 further distinct label-vocabulary/column generations - a genuine coverage-gap opportunity, but requiring its own dedicated per-generation triage pass, not safely foldable into this milestone's single adapter. Deferred, documented, not silently dropped. |
| Mid-Year Fiscal and Economic Review (~20 files) | In-year budget-revision snapshots, not final actuals - lower priority, consistent with how TAS's own Revised Estimates Reports were deprioritised relative to final-outcome reports. |
| Consolidated Fund Financial Report (~35 files) | A different, narrower concept (cash-basis Public Account transactions), not the GGS accrual fiscal aggregates this dashboard otherwise tracks. |
| CFFR quarterly bulletins (~25 files) | A different topic entirely (Commonwealth-Federal-Relations payment tracking to QLD, not QLD's own fiscal aggregates). |
| Policy/procedure/handbook documents (~50+ files) | Not data-bearing at all (Financial Accountability Handbook volumes, Non-Current Asset Policies, audit committee guidelines, etc.) - excluded outright, not deferred. |

## Format classification

**PDF, text-extractable (no OCR required)** - confirmed directly via
`pypdf`'s `extract_text()` across all 7 target editions; no scanned-
image pages, no font-encoding corruption on the target tables.

## Reusable adapter status

**A new adapter is needed** - no existing extractor, loader, or
semantic model references any QLD Treasury-published fiscal-aggregate
source (confirmed: no `qld_report_on_state_finances*`-specific files
under `scripts/ingest/extractors/`, `scripts/ingest/reload_*.py`, or
`config/measure-semantics/`). `m7_qld_procurement.py` and `m_qld_sds_
fixtures.py` are unrelated families and are not touched.

## Route/UI scope

In scope: wiring into the existing `/explorers/gfs` page as a new
toggle (mirroring the VIC AFS/BPO/TAS GGS pattern) - no new page, no
new route. Not in scope: any Cloudflare-related repo change.

## Next

Task 3: deep-dive inventory of the 7 selected PDF editions' exact
pages, tables, rows, SHA-256 hashes, and text-extractability
characteristics before writing any adapter code.
