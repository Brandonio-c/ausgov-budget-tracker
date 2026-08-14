# MFS remaining sibling workbooks - scoping investigation (Balance Sheet, Tax Notes 1-2, Monthly Profiles)

Generated: 2026-08-14T19:25:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Item 7.1 (MFS sibling workbooks) has one workbook fully loaded (Note 3 - Total expense
by function, `31c8b4d`) and one deliberately deferred with evidence (Operating Statement,
`e3bda20` - genuine multi-generation structural complexity). Three siblings remain
untouched: Balance Sheet, Tax Notes 1-2, Monthly Profiles. Before writing any extractor,
each was inspected directly against its real acquired workbook (same discipline as the
Operating Statement investigation) to check whether it follows Note 3's simple, stable,
flat-hierarchy pattern or Operating Statement's fragile multi-generation pattern.

**Finding: none of the three is a Note 3-style quick win.** Each has its own real,
distinct complication that would risk a `dashboard_treatment`/hierarchy/estimate_status
mistake if force-mapped without dedicated per-workbook design. None was built this pass.

## 1. Balance Sheet (`federal_mfs_balance_sheet`, `2.-balance-sheet.xlsx`, 21 year-sheets 2005-06..2025-26)

A stock (point-in-time balance), not a flow - each month's column is a snapshot as-at that
month-end, not a YTD cumulative sum, so the flat-YTD false-positive pattern already
documented for Note 3/Aggregates does not directly apply here, but a different risk does:

**Genuine multi-generation hierarchy and disclosure changes**, verified directly across
2005-06, 2012-13, 2019-20, and 2025-26 sheets:

- **Generation 1 (2005-06..~2011-12)**: line items `Cash`, `Receivables`, `Investments`,
  `Equity Accounted Investments`, `Accrued revenue`, `Other financial assets` under
  `Financial assets`; debt items grouped as `Debt` (`Government securities`, `Loans`,
  `Leases`, `Deposits`, `Overdrafts`, `Other debt`) -> `Total debt`. Bottom section is a
  `Net Assets (a)` reconciliation: `Operating Result`, `Asset revaluation reserve`,
  `Other movements`, `Closing net assets` - a *change-in-position* breakdown.
- **Generation 2 (2012-13..~2018-19)**: line items renamed (`Cash and deposits`,
  `Advances paid`, `Investments, loans and placements`, `Other receivables(a)`...); debt
  items regrouped under `Interest bearing liabilities` (`Deposits held`,
  `Government securities`, `Loans`, `Other borrowing`) -> `Total interest bearing
  liabilities`. The Generation 1 reconciliation section is **gone entirely**, replaced
  by four different summary measures: `Net worth`, `Net financial worth`,
  `Net financial liabilities`, `Net debt` - genuinely different disclosures, not a rename.
- **Generation 3 (2019-20 onward, post-AASB16 lease standard)**: `Other borrowing`
  becomes `Lease liabilities`, `Provisions` splits out as its own line item separate from
  `Other provisions and payables`.

A force-mapped single hierarchy would either invent a fake correspondence between
Generation 1's `Net Assets` reconciliation and Generation 2/3's four net-position measures
(violates the "never infer hierarchy from label similarity alone" rule), or silently drop
20+ years of one generation's disclosure. Needs a dedicated per-generation crosswalk
design, matching the Operating Statement recommendation.

## 2. Tax Notes 1-2 (`federal_mfs_tax_notes_1_2`, `4.-note-1-and-2.xlsx`, 21 year-sheets, two stacked tables per sheet)

Smaller and flatter than Balance Sheet (10-15 line items across both notes), and
correctly uses YTD cumulative columns matching Note 3's already-solved pattern - but has
its own genuine multi-generation defect risk, verified across 2005-06, 2012-13, 2019-20,
2025-26:

- **Note 1 (Income Tax), Generation 1 (2005-06..2011-12)**: `Fringe Benefits tax` is
  reported as a **separate line item listed after** the `Total Income tax` row - i.e.
  excluded from that total. An intermediate subtotal `Total income from other sources`
  (Company tax + Superannuation funds + Petroleum resource rent tax) feeds into the grand
  total.
- **Note 1, Generation 2 (2012-13 onward)**: `Fringe benefits tax` moved to a line item
  **before** the renamed grand total `Total income taxation revenue`, and is now
  **included** in it. The `Total income from other sources` intermediate subtotal is gone
  - items sum directly into the grand total.
- A same-label total (`Total income tax` / `Total income taxation revenue`) means two
  different things (FBT excluded vs included) depending on generation - exactly the kind
  of same-label-different-value collision the Operating Statement investigation flagged
  as the concrete reason not to force-map.
- **Note 2 (Indirect Tax)**: Generation 1 has 3 line items (`Excise duty`, `Customs duty`,
  `Other indirect tax (including GST)` - GST bundled into "other"). Generation 2 splits
  GST out as its own line (`Goods and services tax`), adds `Wine equalisation tax` and
  `Luxury car tax`, and briefly adds `Carbon pricing mechanism` (present in 2012-13 only,
  gone by 2019-20) - a genuinely different, and non-monotonic, item set across years, not
  just an additive expansion.

Individual line items (`Gross income tax withholding`, `Company tax`,
`Superannuation fund(s) taxes`, `Petroleum resource rent tax`, `Excise duty`,
`Customs duty`) are themselves stable and could be loaded as standalone measures without
a fabricated grand-total crosswalk - a narrower, lower-risk scope than Balance Sheet, but
still requires deliberate per-generation design for the totals, not a direct Note 3 reuse.

## 3. Monthly Profiles (`federal_mfs_monthly_profiles`, `1.-aggregates-mp.xlsx`, 17 year-sheets 2009-10..2025-26)

**Not a duplicate of the already-loaded `federal_mfs_aggregates` actuals family** -
verified directly: only the **first column of each year is `ACTUAL`**; every subsequent
column in the same year-sheet is a **forward-looking forecast profile**
(`Budget Profile`, `MYEFO Profile`, and presumably `PEFO Profile` depending on year) that
is never later replaced with real actuals in this file. This is genuinely new information
(the originally-published budget-time monthly profile), not a redundant re-publication of
actuals - but it must be loaded with `estimate_status` values distinct from `actual`
(e.g. `budget_profile`/`myefo_profile`), never blended with the real
`federal_mfs_aggregates` actual series under the same measure/compatibility_group, or a
dashboard reader would see a stale, never-updated forecast presented as if it were an
up-to-date actual figure - a direct violation of this program's "never substitute a
future/forecast value for an actual" rule if mishandled.

Column headers are also a real parsing hazard: multi-line, inconsistently-spaced cell
text like `"Budget \nProfile\n2014-2015\nYTD October\n$m"` vs `"MYEFO Profile\nYTD
November  2009\n$m"` mixes the estimate-status label, the YTD/month label, the financial
year, and the unit into one unstructured cell - needs a dedicated parser, not a Note 3
reuse (Note 3's headers only ever carried a bare month name). A further real defect risk:
**the unit itself changes within the same file** - `$m` for most years, `$b` for 2025-26
(confirmed directly: sheet `2025-26`'s header row reads `$b`, not `$m`) - a per-year unit
must be read from the header, never hardcoded.

## Disposition

No extractor/loader code written for any of the three this pass - each needs its own
dedicated per-generation (Balance Sheet, Tax Notes) or estimate-status-aware header-parser
(Monthly Profiles) design, matching the discipline already established for the deferred
Operating Statement. Recommended order for a future dedicated pass, easiest first: Tax
Notes 1-2 (smallest, flattest, only the grand-total needs generation-aware logic - the
line items themselves could ship first without a fabricated total) -> Monthly Profiles
(new header parser + estimate_status dimension, no hierarchy risk) -> Balance Sheet
(largest surface, full 3-generation hierarchy crosswalk).

## Not investigated as part of this scoping pass

No values were loaded or validated against downstream totals for any of the three
workbooks - this is a pre-implementation structural scoping only, matching the Operating
Statement precedent.
