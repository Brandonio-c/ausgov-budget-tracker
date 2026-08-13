# MFS Note 3 (Total expense by function) workbook load - item 7.1, workbook 2 of 5

Generated: 2026-08-13T21:20:37Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 7.1: "Implement one workbook at a time" across the five acquired MFS
sibling workbooks (Note 3 function statement, operating statement, balance sheet, tax
Notes 1/2, monthly profiles). This report closes the second of five - the first,
`federal_mfs_aggregates`, was completed in an earlier milestone.

## Previous behavior

`data/raw/federal/federal_mfs_note3_function/` held an acquired, checksummed `.xlsx`
(21 sheets, FY2005-06 through FY2025-26) with zero extractor or loader - confirmed via
`find` before writing anything (the four other siblings - operating statement, balance
sheet, tax Notes 1/2, monthly profiles - are in the identical acquired-but-unadapted
state and remain untouched by this milestone).

## Baseline verification (before any Note 3 work)

Re-ran `load_mfs_aggregates.py --dry-run` against the live database first: 3,354 rows
extracted, 3,354 already-present idempotent skips, 0 conflicts - confirmed the existing,
proven MFS pipeline was unaffected before touching anything.

## Changes

- **Shared extractor infrastructure** (`scripts/ingest/extractors/mfs_common.py`, new):
  factored the column-header/footnote-row parsing out of `mfs_aggregates.py` into a
  reusable module, since all five sibling workbooks share the same sheet shape - a real,
  evidenced duplication risk given three more siblings remain. `mfs_aggregates.py` now
  delegates to it; its public API (`extract_workbook`) is unchanged and its 4 existing
  tests plus the full loader/revision-policy suite (27 tests total) pass unchanged, and a
  dry-run against the live database still matches all 3,354 existing facts idempotently -
  the refactor is provably behavior-preserving.
- **Two real structural quirks found and fixed while building the shared module**,
  verified directly against the real Note 3 file before assuming anything:
  - `HEADER_RE` widened to tolerate leading whitespace before the month token (the real
    FY2013-14..FY2015-16 sheets have `" July"` with a leading space instead of `"July"`
    or `"YTD July"`).
  - A second header shape discovered: FY2005-06 through FY2011-12 spread the header
    across four separate physical rows (status/financial_year/month/unit, one each) with
    data starting at row 5, instead of one combined cell at row 1 with data at row 2 (the
    shape every later year and the whole Aggregates workbook use). `mfs_common.py`
    detects which shape a sheet uses per-sheet (not by a fixed year cutoff) and combines
    the four-row case into the same string shape the existing regex already parses - no
    parallel parsing logic.
- **`scripts/ingest/extractors/mfs_note3_function.py`** (new): thin, source_id-bound
  wrapper around the shared extractor. Verified against all 21 real sheets before writing
  any label mapping: 13 COFOG-style function rows, 5 "Other purposes" line items, a
  "Total expenses" row (always the source's own stated cell, never computed here), a
  genuinely separate "Asset Sales" row only in FY2005-06..FY2007-08 (folded into
  Contingency reserve from FY2008-09 per the source's own footnote - never merged or
  backfilled), and real label drift requiring explicit variant mapping (not case-folding):
  "Mining and Mineral Resources (other than fuels); Manufacturing and Construction"
  (..FY2008-09) vs "Mining, manufacturing and construction" (FY2009-10+); "Agriculture,
  Forestry and Fishing" (title case, ..FY2016-17) vs sentence case (FY2017-18+).
- **`config/measure-semantics/mfs.yaml`**: 20 new `mfs_note3_*` measure types (13
  functions + 5 "Other purposes" items + Asset Sales + Total expenses), each with its own
  dedicated `compatibility_group` (1:1, matching the established MFS discipline - no
  `mfs_note3_*` measure can ever share a group with an annual GFS/PBS measure or an
  Aggregates `mfs_ytd_*`/`mfs_stock_*` measure). The 18 function-level measures are
  `root_total_allowed: 1` (genuinely, source-published additive components of Total
  expenses); Total expenses itself is `root_total_allowed: 0` (already the derived total).
- **`scripts/ingest/migrations/020_mfs_note3_measures.sql`** (new): registers the 20
  measure_definitions rows.
- **`scripts/ingest/load_mfs_note3_function.py`** (new): mirrors `load_mfs_aggregates.py`'s
  structure and revision-conflict discipline exactly. `build_label_index` is scoped to
  `mfs_note3_*` only, so it can never claim an Aggregates label even though both files
  share one semantics file. `classify_and_validate` additionally enforces
  `only_published_financial_years` (used by `mfs_note3_asset_sales`).

## A duplicate-fact false-positive investigation, resolved before touching live

Loading onto a disposable copy first surfaced 43 `unresolved_duplicate_facts` hard
failures from `task9_sql_integrity_checks.py` - all new (the unmodified live database has
0). Investigated individually rather than assumed: `duplicate_facts()` groups by
`(node, source_key, financial_year, measure_type, estimate_status, amount_aud)`, which
does not include `reporting_month`. Three genuinely lumpy, irregular-flow measures
(Contingency reserve, Natural disaster relief, Nominal superannuation interest) are
flat across several consecutive reporting months in a given year - verified directly
against the raw workbook for representative years (e.g. FY2005-06 Contingency reserve:
`0` for all 11 months; FY2011-12 Natural disaster relief:
`3.651,9.559,9.823,0.371,0.371,2.765,2.765,1902.765,1902.765,1902.765,3.076` $m, flat for
2-3 months at a stretch, matching every flagged sub-group exactly). This is the identical
false-positive class already documented for two `mfs_ytd_net_capital_investment` groups
in the Aggregates milestone. All 43 classified `query_false_positive` and added to
`config/audit/reviewed_duplicate_facts.yaml` (exact-match per field, so a genuinely new or
different duplicate-look-alike group still falls through to a hard failure) - see
[`mfs-note3-duplicate-fact-investigation-20260813T180000Z.md`](mfs-note3-duplicate-fact-investigation-20260813T180000Z.md)
for full per-group evidence.

## Validation

- **Tests**: 16 new (4 `mfs_common.py` header-shape tests, 6 Note 3 extractor tests, 6
  Note 3 loader tests covering label-index scoping and `only_published_financial_years`
  gating). Full backend suite: 692 passed (676 + 16 new), 0 regressions.
- **Disposable-copy-first discipline**: extractor dry-run (4,413 rows, 0 quarantined) →
  apply on a disposable copy (4,413 inserted, 20 nodes) → second apply on the same copy
  (0 inserted, all 4,413 idempotent skips - proves idempotency) →
  `task9_sql_integrity_checks.py --db <copy>` (0 hard failures after the reviewed-
  duplicates registry update) → `dashboard_depth_audit.py --db <copy> --check-fixture`
  (the only diff against the golden fixture was the `database` path string itself and a
  timestamp field - a manual field-by-field diff confirmed `projections`/`graph` content
  is byte-identical, i.e. zero canonical-tree impact) - only then applied to live.
- **Live apply**: backup taken first (`facts-20260813T175305Z.db`). Facts 288,636 ->
  293,049 (+4,413, exact match to prediction); nodes 219,777 -> 219,797 (+20). Second
  apply on live: 0 new inserts (idempotent). `task9_sql_integrity_checks.py` (no `--db`,
  live default): 0 hard failures. `dashboard_depth_audit.py --check-fixture` (live,
  default db): `fixture_matches: true`.
- **API/frontend**: zero backend or frontend code changes were needed for the new
  measures to become reachable - `/v2/mfs/measures` is driven entirely by
  `config/measure-semantics/mfs.yaml` (confirmed: 35 measures now returned, up from 15,
  via `test_mfs_api.py::test_measures_lists_all_35`), and the existing MFS explorer page's
  measure dropdown (`apiMfs.measures().then(setMeasures)`, unfiltered `.map()`) already
  renders whatever the API returns. Live-verified via Playwright: the dropdown lists all
  35 measures including "MFS Note 3: Defence", selecting it charts real data, zero console
  errors.

## Data impact

`data/facts.db`: +4,413 facts (all `federal_mfs_note3_function`), +20 nodes (one per new
measure_type), +1 source_document. Zero facts changed or removed for any existing source.
Backup: `facts-20260813T175305Z.db`.

## Dashboard impact

None on the canonical annual tree (confirmed via `dashboard_depth_audit.py`'s fixture
match and `test_annual_dashboard_total_unaffected_by_mfs_facts`). The dedicated MFS
explorer (`/explorers/mfs`) gains 20 new selectable series with zero code changes.

## Remaining risks

Four MFS sibling workbooks remain unadapted: operating statement, balance sheet, tax
Notes 1/2, monthly profiles (plan's own stated order). `mfs_note3_asset_sales` and the
four other `only_published_financial_years`-gated Aggregates measures intentionally have
no facts outside their real publication window - not a gap, a correctly-scoped absence.
The production deployment lag continues to apply to the code changes in this milestone
(the data itself reaches production immediately via the bind mount, per the existing
top-of-ledger callout).

## Next item

Continue item 7.1 with the next sibling workbook in the plan's stated order (Operating
Statement), or reassess Wave 5 priority against QLD QGIP (item 7.2, has known data
defects blocking its own explorer) given both are independent, parallel-eligible efforts.
