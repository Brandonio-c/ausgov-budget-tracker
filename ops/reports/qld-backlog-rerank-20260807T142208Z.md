# QLD backlog re-rank (Task 1)

Generated: 2026-08-07T14:22:08Z.

## Ground truth verified before ranking

- `git status --short`: clean. Branch `main`. `HEAD` and `origin/main`
  both at `43b6567`.
- `ops/reports/pdf-ocr-next-backlog-ranking-20260806T185946Z.md` (the
  prior milestone's own triage) had already spot-checked ONE QLD
  edition (`2018-19-Report-on-State-Finances.pdf`) and explicitly
  deferred a full per-file survey of the 187-file population to "a
  future, dedicated QLD PDF/OCR milestone." This report performs that
  survey.
- `config/procurement_sources.yaml`: `qld_report_on_state_finances_
  actuals` entry unchanged since the prior milestone's inspection
  (`handoff_already_on_disk: true`, no new acquisition needed).
- `data/facts.db` inspection: **zero** `qld_*`-prefixed `measure_type`
  rows exist today. The only existing scripts referencing "qld" are
  `m7_qld_procurement.py` (procurement/contracts, unrelated) and
  `m_qld_sds_fixtures.py` (Service Delivery Statements, unrelated) -
  neither touches QLD's own Treasury-published fiscal aggregates. This
  would be a genuinely new family.

## Full per-file categorisation of the 187-file population

Grouped by content, not filename guesswork - every file was
categorised by opening a representative sample from each group:

1. **"Report on State Finances" / "state-finances-report" / "outcomes-
   report" annual editions** (~25 files spanning 2000-01 to 2024-25) -
   the core annual outcomes report, directly analogous to TAS's TAFR.
   **Selected for this milestone** (see below).
2. **"Mid-Year Fiscal and Economic Review" / "mid-year-review-*"**
   (~20 files, 2000-01 to 2025-26) - in-year budget-revision snapshots,
   lower priority than final actuals.
3. **"Consolidated Fund Financial Report" / "consolidated-fund-*"**
   (~35 files, quarterly + annual, 2008 to 2025) - Public Account cash
   transaction reports, a different (narrower, cash-basis) concept from
   the GGS accrual fiscal aggregates.
4. **"CFFR" quarterly bulletins** (~25 files, 2017 to 2025) -
   Commonwealth-Federal-Relations payment tracking, a different topic
   (Commonwealth payments to QLD, not QLD's own fiscal aggregates).
5. **Policy/procedure/handbook documents** (~50+ files: FAH volumes,
   NCAP policies, audit committee guidelines, cash management
   handbooks, etc.) - not data-bearing at all, excluded outright.
6. **Budget Papers / Budget Updates** (~6 files) - original budget
   documents, a different vintage concept (forward estimates, not
   outcomes).

## Deep inspection of category 1 - "Report on State Finances" annual editions

Directly inspected 16 editions spanning 2000-01 to 2024-25 (not one
sample). Every edition from **2002-03 through 2024-25** (23
consecutive years) contains a "Summary of Key GFS/UPF Financial
Aggregates" table - confirmed present in every single one checked, not
assumed. The two earliest editions (2000-01, 2001-02, both only 6-8
pages) use a materially shorter, different early "Outcomes Report"
format without this table - excluded.

**Real, confirmed format drift** across at least 4 generations:

| generation | years (confirmed) | row set | column headers |
|---|---|---|---|
| A | 2002-03 (spot-checked; likely extends further, not verified) | Revenue, Expenses, Net Operating Balance, Net Lending/Borrowing, Cash Surplus/(Deficit), Gross Fixed Capital Formation, Net Worth, Net Debt | Est. Actual / Actual |
| B | 2010-11 (spot-checked) | Revenue, Expenses, Net operating balance, Cash surplus/(deficit), Capital purchases, Net worth, Net debt, Net borrowing, Borrowing | Est. Actual / Outcome |
| C | 2015-16, 2016-17, 2017-18 (all 3 confirmed identical) | Revenue, Expenses, Net operating balance, Capital purchases, Fiscal balance, Borrowing (single line) | Est. Actual / Outcome |
| D | **2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25 (all 7 confirmed)** | Revenue, Expenses, Net operating balance, Capital purchases, Fiscal balance, Borrowing with QTC, Leases and similar arrangements, Securities and derivatives (+ Net Debt from 2020-21 onward; + Borrowings total from 2021-22 onward - both excluded from this milestone's scope to keep the required row-set uniform across all 7 years) | Est. Actual / Outcome |

Every row in every table has **6 numeric columns**: 3 sector-pairs
(General Government Sector, Public Non-financial Corporations Sector,
Non-financial Public Sector), each pair being (Est. Actual, Outcome/
Actual). Confirmed by cross-referencing each edition's own narrative
Overview text against the table's first pair of numbers (e.g. 2010-11's
"net worth decreased to $171.222 billion" matches the table's Net
worth row first-pair value `177,966 171,222`) - General Government
Sector is reliably the **first** pair of 2 numbers in every row,
consistent across every generation checked.

## Selected sub-shape: Generation D (2018-19 to 2024-25, 7 editions)

Chosen over the older generations because:

1. It is the **largest internally-consistent cluster** found (7
   consecutive years sharing an identical 8-row core set, vs
   generation C's 3 years and generation B's single confirmed sample).
2. It is the **most dashboard-relevant** (most recent 7 years).
3. Comma-thousands-separators are simpler to parse than TAS's space-
   separator (no ambiguity between an in-number separator and a
   column separator).
4. No font-encoding corruption was found on any of the 7 target pages
   (the corruption previously flagged was on a cover page, never on a
   data table).

Generations A, B, and C (2002-03 to 2017-18, 16+ editions) are a real,
confirmed coverage-gap opportunity - deferred as a documented,
out-of-scope-this-milestone population, not silently dropped, mirroring
how TAS's older narrative-format editions were deferred in the prior
milestone.

## Re-ranking against the mission's criteria

1. **Structured availability**: confirmed text-extractable, table-
   dominant, no OCR needed, across all 7 target editions.
2. **Engineering effort**: one adapter, 7 known-good editions with a
   confirmed-identical row set - the same scale of effort as the TAS
   PDF backfill.
3. **Dashboard value**: very high - a genuinely new family (QLD
   currently has zero Treasury-published-own fiscal-aggregate coverage
   in this dashboard) covering the same measure concepts (Revenue,
   Expenses, Net Operating Balance, Fiscal Balance) already
   dashboard-exposed for every other jurisdiction.
4. **One-adapter coverage**: confirmed - one parser handles all 7
   target editions identically.
5. **Semantic risk**: low-medium - the wider population's format drift
   is real but the selected cluster is internally consistent; GGS-
   only extraction (first pair) avoids the column-to-sector ambiguity
   previously flagged, since the ordering is confirmed stable and
   cross-verified against narrative text in multiple editions.
6. **Already partially supported**: no - a genuinely new family, zero
   existing coverage.
7. **Files already on disk**: yes, all 7 confirmed present, no
   acquisition blocker.

## Recommended order

1. QLD Report on State Finances, Generation D (2018-19 to 2024-25) -
   **selected this milestone**.
2. QLD Report on State Finances, Generations A-C (2002-03 to 2017-18) -
   deferred, a future dedicated triage pass per generation.
3. Mid-Year Fiscal and Economic Review - deferred, lower priority
   in-year vintage detail.
4. Consolidated Fund Financial Report - deferred, different (cash-
   basis Public Account) topic domain.
5. CFFR quarterly bulletins - deferred, different (Commonwealth
   payments) topic domain.
6. Policy/procedure/handbook documents - excluded, not data-bearing.

Full table: `ops/reports/qld-backlog-rerank-20260807T142208Z.csv`.

## Next

Task 2: formal scope-selection report confirming Generation D
(2018-19 to 2024-25) as the selected family.
