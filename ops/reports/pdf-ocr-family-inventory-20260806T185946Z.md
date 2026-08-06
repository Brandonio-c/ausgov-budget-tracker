# TAS TAFR tabular PDF sub-shape: family inventory (Task 3)

Generated: 2026-08-06T18:59:46Z.

## File identities

| financial_year | file | SHA-256 | pages |
|---|---|---|---|
| 2010-11 | `TAF-2010-11.pdf` | `5232bbfa3260339c32a9ca61e9e641256425cc0810329558d73338625011ea61` | 140 |
| 2011-12 | `2011-12-Treasurers-Annual-Financial-Report.pdf` | `f9ff0f1e7bfec510dfe104b975d70e8602e8da1f48f469fe71aac8b2297c2e2c` | 148 |
| 2012-13 | `2012-13-Treasurers-Annual-Financial-Report.pdf` | `64f49d20efb774d327b810beec76da92cc7d6a071526bf3b54e657477f71ebe8` | 148 |

All 3 paths under
`data/raw/state/tas_treasurer_annual_financial_reports/snapshots/20260724T170239Z/files/`.

## OCR/text-extractability status

**No OCR required.** `pypdf`'s `extract_text()` (`data_only`-equivalent
for PDF - real embedded text, not a scanned image) produces clean,
row-major text for the target pages in all 3 editions - confirmed by
direct inspection, not assumed. The population is **table-dominant**
on the target pages (a labelled 2-D grid rendered as sequential text
lines) with narrative prose only in the surrounding commentary
paragraphs, which are not extracted as facts.

## Page/table identification - a real extraction-robustness finding

Both the "Key Financial Indicators" (page 6 in all 3 editions) and
"Summary of Operating Result" tables exist in **two variants per
edition**: a **General Government Sector** version (which this
milestone targets) and a **Total State Sector** version (out of scope
- a different sector aggregation that must never be conflated with
`tas_ggs_*`, which is explicitly General-Government-Sector-scoped per
its own `economic_meaning` text).

Naively searching page text for the literal substring `"general
government sector summary of operating result"` **fails for the
2010-11 edition** - its heading wraps across a line break
(`"...Sector Summary of Operating \nResult"`), so the substring never
appears contiguously, and the search would incorrectly resolve to the
*Total State Sector*'s own later table instead (a real bug caught
during this inventory pass, not assumed away). The reliable,
verified-correct rule instead: **the General Government Sector table
always appears strictly before the Total State Sector table in page
order, in all 3 editions** - confirmed directly (GGS Operating Result
table at page 7/8/8; Total State's own equivalent at page 11/later for
2010-11). The extractor takes the **first** matching table on this
basis, not a title-text match alone.

## Row inventory (General Government Sector only)

### "Key Financial Indicators" table (page 6, all 3 editions)

| row label | present in tas_ggs_* semantics? |
|---|---|
| Net Operating Surplus/(Deficit) | yes - `tas_ggs_net_operating_balance` |
| Underlying Net Operating Surplus/(Deficit) (2011-12, 2012-13 only) | **no** - a distinct concept (excludes one-off Commonwealth funding impacts) not modelled by any `tas_ggs_*` measure - excluded from extraction, documented not silently dropped |
| Fiscal Surplus/(Deficit) | yes - `tas_ggs_fiscal_balance` (confirmed via the source's own definition: "A Fiscal Surplus indicates a government is saving more than enough to finance its investment spending" - identical concept to the GGS xlsx's "Fiscal Balance", just an older name) |
| Net Debt | yes - `tas_ggs_net_debt` |
| Net Worth | yes - `tas_ggs_net_worth` |
| Net Financial Liabilities | yes - `tas_ggs_net_financial_liabilities` |

Each row has 3 numeric columns: `<FY> Original Budget`, `<FY> Actual`,
`<prior FY> Actual`. Only the first two columns are extracted (Budget,
Actual for the report's own year) - the "Prior Year Actual" column is
excluded from extraction per the revision-policy decision below,
though it was used as a cross-check (e.g. 2011-12's Prior Year Actual
for Net Debt = -416, which equals 2010-11's own Actual = -416 -
confirmed matching, corroborating parser correctness without adding it
as a fact).

### "Summary of Operating Result" table (page 7 for 2010-11, page 8 for 2011-12/2012-13)

| row label | present in tas_ggs_* semantics? |
|---|---|
| Revenue from transactions | yes - `tas_ggs_revenue` |
| Expenses from transactions (2010-11, 2011-12) / Expense from transactions (2012-13) | yes - `tas_ggs_expense` (label wording varies slightly between editions - handled as label variants, not two different measures) |
| Net Operating Balance – Surplus/(Deficit) | yes - `tas_ggs_net_operating_balance` (cross-checked identical to the KFI table's own value in every edition) |
| Less Net acquisition of non-financial assets | not extracted - an intermediate derivation line, not a `tas_ggs_*` measure |
| Equals Fiscal Balance – Surplus/(Deficit) | yes - `tas_ggs_fiscal_balance` (cross-checked identical to the KFI table's own Fiscal Surplus/(Deficit) value in every edition) |

Each row has 4 numeric columns: `<FY> Original Budget`, `<FY> Actual`,
`Variation`, `Variation %`. Only the first two are extracted; the
derived variation columns are excluded (same principle as the VIC BPO
family's own excluded "Variance" column).

## Data-quality findings - the real parsing challenges

1. **Space-thousands-separator**: values like `13 130`, `4 638`,
   `14 211` use a plain space (not a comma) as a thousands separator -
   the same conceptual challenge as the GGS xlsx's non-breaking-space
   separator, solved with the same technique (strip internal whitespace
   before parsing to float), adapted for plain-text PDF extraction.
2. **Parenthesized negatives**: `(65)`, `(530)`, `(220)` - standard
   accounting negative notation, stripped and sign-flipped.
3. **Stray trailing `")"` artifacts**: some tokens extract with an
   unexpected trailing `)` with no matching `(` - e.g. `"2010-11)"` (a
   column-header year label) and `"69)"` (a positive value in the Total
   State Sector block of the 2010-11 KFI table) - confirmed as a
   `pypdf` text-extraction quirk from the source PDF's own internal
   cell/border structure, not a genuine parenthesized-negative
   indicator. The parser must only treat a token as negative if it has
   **both** a leading `(` and a trailing `)` - a lone trailing `)`
   with no opening `(` is stripped as noise, not treated as a sign
   marker.
4. **Sign consistency verified, not assumed**: 2012-13's Net Debt
   Original Budget value (`134`) is positive while its Actual (`(220)`)
   and Prior Year Actual (`(409)`) are both negative - confirmed as a
   genuine value in the source (not a parsing error) by cross-reading
   the surrounding narrative commentary, which discusses the actual
   outcome differing materially from the budgeted estimate.
5. **No footnote markers** found in either target table in any of the
   3 editions (confirmed by direct inspection) - unlike the GGS xlsx,
   no footnote-stripping logic is needed for this PDF sub-shape.
6. **Label wording drift across editions**: "Expenses from
   transactions" (2010-11, 2011-12) vs "Expense from transactions"
   (2012-13, singular) - both map to `tas_ggs_expense` via label
   variants, the same pattern already used throughout this repo for
   minor source-label wording differences across editions.

## Vintage/revision semantics

Each edition's own Budget/Actual pair maps to `estimate_status`
`actual` for the Actual column and `budget` for the Original Budget
column - **not** `revised_estimate` (that token is reserved for the
GGS xlsx's "Revised Budget" mid-cycle vintage; a TAFR's "Original
Budget" column is the as-originally-published Budget estimate for that
year, a distinct vintage concept). See Task 4 for the exact
`estimate_status` mapping decision.

## Publishability

All 7 rows × 3 editions × 2 columns (Budget, Actual) = 42 candidate
facts are publishable once the number-parsing and page-disambiguation
logic above is applied correctly. No row is inherently ambiguous in
the source data itself - "Underlying Net Operating Surplus/(Deficit)"
is deliberately excluded (a different concept, not ambiguous), and the
Total State Sector's parallel tables are deliberately excluded (a
different sector, not ambiguous once the page-order rule is applied
correctly).

## Current ingestion status

Not previously ingested - confirmed via `data/facts.db` inspection (no
existing fact references these 3 PDF files' `cached_copy_path`). No
existing adapter, loader, or semantic model references this PDF
sub-shape; it will publish into the **same** `tas_ggs_*`
`compatibility_group`s already shipped from the GGS xlsx, extending
(not duplicating) that family.

## Next

Task 4: extend `config/measure-semantics/tas_ggs_key_fiscal_measures.yaml`
with the PDF-sourced label variants and an explicit revision policy for
this cross-source (xlsx + PDF) situation.
