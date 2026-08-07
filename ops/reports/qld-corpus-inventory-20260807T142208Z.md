# QLD Report on State Finances (2018-19 to 2024-25): corpus inventory (Task 3)

Generated: 2026-08-07T14:22:08Z.

## File identities

| financial_year | file | SHA-256 | pages | target page (0-idx) |
|---|---|---|---|---|
| 2018-19 | `2018-19-Report-on-State-Finances.pdf` | `69d22565143590360b2284fea2c9ba25b50eea62d03f3ec212d359bdcc7bd005` | 125 | 9 |
| 2019-20 | `20-077-FG-Report-on-State-Finances-2019-20-Full.pdf` | `1a79245702dfb80f920f357368ad190d59d3afbe05b2e27ff9e43cf6dc3d3903` | 153 | 8 |
| 2020-21 | `Report-on-State-Finances-2020-21.pdf` | `07ba619d854efc4c2555b8e4aa00dc2843369fd6482767a7ff42e2df498a9136` | 143 | 7 |
| 2021-22 | `Report-on-State-Finances-2021-22.pdf` | `1a97b2bfc79af03621ed1ace6df00d12710867a64c2c87ea6c37854d3d4a67cb` | 142 | 9 |
| 2022-23 | `Report-on-State-Finances-2022-23.pdf` | `cb1655feeb2beef4eba6062aa3d73169fcf871b9c96bc5607a0b60f446e53ad0` | 134 | 9 |
| 2023-24 | `Report-on-State-Finances-2023-24.pdf` | `9a240d269d6db47878a6a8e95126349f86064ba3801e613b6e5a656e0a13e0fa` | 128 | 7 |
| 2024-25 | `Report-on-State-Finances-2024-25.pdf` | `b5b54b071309f87638bffecf9ef5ca0d6a031a99d8ee1cd95ac8709dc7ecad4a` | 127 | 8 |

All 7 paths under
`data/raw/state/qld_report_on_state_finances_actuals/snapshots/20260724T190604Z/files/`.
Target page differs per edition (the table's absolute page number
shifts as report length varies year to year) - the extractor must
locate the page by content, not a fixed page index.

## OCR/text-extractability status

**No OCR required.** `pypdf`'s `extract_text()` produces clean, row-
major text for the target table page in all 7 editions - confirmed by
direct inspection, table-dominant on the target page (narrative prose
surrounds it but is not extracted as facts). No font-encoding
corruption found on any target page in any of the 7 editions (the
corruption previously flagged in the prior milestone's spot-check was
confirmed to be on a cover-page decorative font only, never on this
data table).

## Row inventory - confirmed identical 8-row set across all 7 editions

| row label | measure concept |
|---|---|
| Revenue | GGS total revenue (flow) |
| Expenses | GGS total expenses (flow) |
| Net operating balance | Revenue less Expenses (derived balance) |
| Capital purchases | GGS capital expenditure (flow) |
| Fiscal balance | Net operating balance less net acquisition of non-financial assets (derived balance) |
| Borrowing with QTC | Borrowings from the Queensland Treasury Corporation (stock, a debt-instrument component) |
| Leases and similar arrangements | Lease liabilities (stock, a debt-instrument component) |
| Securities and derivatives | Securities and derivative liabilities (stock, a debt-instrument component) |

Two further rows - "Net Debt" (present from 2020-21 onward) and
"Borrowings"/"Borrowing" (a summary total, present from 2021-22
onward) - are **excluded from this milestone's scope**, since they are
not present in all 7 target editions; including them would break the
"one adapter, uniform row-set across the full cluster" design.
Documented as deferred, not silently dropped - a future milestone could
extend coverage for 2020-21 onward once explicitly scoped.

## Column shape - 6 numeric values per row, GGS is reliably the first pair

Every row has 6 numeric columns: 3 sector-pairs (General Government
Sector, Public Non-financial Corporations Sector, Non-financial Public
Sector), each pair being (`Est. Actual`, `Outcome`/`Actual`). **Only
the first pair (General Government Sector) is extracted** - confirmed
reliably first in every edition inspected by cross-referencing each
edition's own narrative Overview text against the table's first-pair
values (e.g. 2010-11's narrative "net worth decreased to $171.222
billion" matches that edition's own Net worth row's first-pair value;
2020-21's narrative "$62.732 billion" matches the Revenue row's own
first-pair second value `62,732`).

## Vintage semantics - a genuinely different concept from TAS's "budget"

The `Est. Actual` column is **not** an as-originally-published Budget
figure - the source's own narrative text describes it explicitly, e.g.
"compared to the estimated actual (Est. Actual) per the 2019-20
Budget" (2018-19 edition) and "compared to the estimated actual...per
the COVID-19 Fiscal and Economic Review" (2019-20 edition, a
different, ad hoc mid-year document that year). This is the
**estimated actual** figure for the reporting year as published in a
**later** budget-cycle document (not the original Budget) - a
materially different vintage concept from TAS's TAFR "Original Budget"
column. Maps to the schema's existing `estimated_actual` token (already
valid in the facts table's CHECK constraint), not `budget`. The
`Outcome`/`Actual` column maps to `actual`.

## Data-quality findings - real parsing considerations

1. **Comma-thousands-separator** (e.g. `60,068` = 60,068) - simpler
   than TAS's space/nbsp separator; no column-vs-in-number ambiguity.
2. **Parenthesized negatives** (e.g. `(2,677)` = -2,677) - standard
   accounting notation.
3. **Bare hyphen `-` placeholders** for nil/not-applicable values in
   some PNFC/NFPS columns (e.g. 2018-19's "Leases and similar
   arrangements 2,623 2,612 - - 2,623 2,612" - PNFC has no lease
   liabilities that year). Since only the GGS-only first pair is ever
   extracted (always real numbers in every edition checked), this
   never affects extraction directly - but it means the row's *total*
   token count varies (sometimes fewer than 6 real numbers), so the
   extractor's validation only requires **at least 2** numeric tokens
   (enough for the GGS pair), never an exact total count.
4. **Stray narrative false-positive**: a bare `"Revenue"` line (a
   subsection heading from the surrounding narrative, e.g. "General
   Government Sector \n Revenue") appears before/after the real
   `"Revenue <6 numbers>"` row in most editions - naturally quarantined
   by the same "at least 2 numeric tokens" rule (the bare heading line
   has zero trailing numbers).
5. **No footnote markers** on any row label in any of the 7 editions
   (unlike TAS's TAFR) - the table's own footnotes ("Numbers may not
   add due to rounding"; "Non-financial Public Sector consolidates...")
   are generic table-level notes, not row-specific markers requiring
   label-stripping logic.

## Publishability

All 8 rows x 7 editions x 2 estimate_status (estimated_actual, actual)
= 112 candidate facts are publishable once the page-location and
number-parsing logic above is applied correctly. No row is inherently
ambiguous in the source data itself.

## Current ingestion status

Not previously ingested - confirmed via `data/facts.db` inspection
(zero `qld_*`-prefixed `measure_type` rows exist today, zero
quarantine entries reference these files). No existing adapter,
loader, or semantic model references this PDF sub-shape.

## Next

Task 4: declarative semantic model
(`config/measure-semantics/qld_report_on_state_finances.yaml`) defining
all 8 measures' economic meaning, flow/stock/balance classification,
period semantics, the `estimated_actual`/`actual` vintage distinction,
unit conversion ($m -> AUD), and dedicated, isolated compatibility_group
per measure - explicitly kept separate from the ABS's independently-
compiled `abs_gfs_state_qld_233` series for the same jurisdiction.
