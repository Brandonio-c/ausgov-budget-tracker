# QLD RSF Net Debt / Borrowing triage

Generated: 2026-08-07T15:45:01Z.

## Decision

Path A: publish every Net Debt and gross Borrowing/Borrowings table row in
the editions where Queensland Treasury printed it. The rows are genuine,
semantically stable GGS stock facts. Their absence in other editions is a
bounded publication-shape change, not evidence that a printed row is
ambiguous. Edition applicability is therefore declared explicitly; no value
is inferred for an edition in which the row is absent.

Net Borrowing is not folded into either series. It is a transaction flow and
remains the existing distinct `qld_rsf_net_borrowing` measure.

## Rows and editions inspected

All 23 acquired summary-table pages were inspected from the cached source
PDFs. The 16-edition older cluster is not uniform:

| edition | Net Debt | Net Borrowing flow | gross Borrowing stock |
|---|---|---|---|
| 2002-03 | yes | no | no |
| 2003-04 | yes | no | no |
| 2004-05 | yes | no | no |
| 2005-06 | yes (`Net debt`) | no | no |
| 2006-07 | yes | yes | no |
| 2007-08 | yes | no | yes |
| 2008-09 | yes | yes | yes |
| 2009-10 | yes | yes | yes |
| 2010-11 | yes | yes | yes |
| 2011-12 | no | no | yes |
| 2012-13 | no | no | yes |
| 2013-14 | no | no | yes |
| 2014-15 | no | no | yes |
| 2015-16 | no | no | yes |
| 2016-17 | no summary-table row | no | yes |
| 2017-18 | no | no | yes |

Thus Net Debt occurs in 9 of 16 older editions, gross Borrowing in 11 of 16,
and the distinct Net Borrowing flow in 4 of 16. The seven newer editions
continue another bounded shape:

| edition | Net Debt | gross Borrowing total | instrument components |
|---|---|---|---|
| 2018-19 | no | no | yes |
| 2019-20 | no | no | yes |
| 2020-21 | yes | no | yes |
| 2021-22 | yes | yes (`Borrowings`) | yes |
| 2022-23 | yes | yes (`Borrowings`) | yes |
| 2023-24 | yes | yes (`Borrowings`) | yes |
| 2024-25 | yes | yes (`Borrowing`) | yes |

The newly publishable first-pair GGS values, in $ million
(`estimated_actual` / `actual`), are:

| edition | Net Debt | gross Borrowing |
|---|---:|---:|
| 2020-21 | 15,809 / 11,360 | absent |
| 2021-22 | 11,390 / 10,997 | 58,215 / 56,764 |
| 2022-23 | 5,852 / 2,615 | 54,693 / 53,726 |
| 2023-24 | 12,223 / 5,684 | 61,958 / 58,773 |
| 2024-25 | 22,092 / 16,727 | 74,843 / 72,864 |

## Semantic evidence

- Queensland's 2016-17 narrative calls the older summary measure “GGS gross
  borrowings at 30 June” and matches the table outcome of $33.260 billion.
- The 2021-22 table publishes Borrowings immediately after Borrowing with
  QTC, leases, and securities/derivatives. Its GGS outcome reconciles exactly:
  49,000 + 7,671 + 93 = 56,764 million. The 2022-23 and 2023-24 outcomes also
  reconcile exactly. The 2024-25 components sum to 72,865 million versus the
  published total of 72,864 million, a one-million-dollar rounding difference
  covered by the table's “numbers may not add due to rounding” note.
- Queensland defines Net Debt consistently as specified financial liabilities
  (including advances and borrowing) less specified financial assets. The
  2021-22 and 2024-25 narratives both define it this way and directly match
  their summary-table GGS outcomes.
- Both measures are point-in-time General Government Sector stocks at 30 June.
  Label case and singular/plural drift do not change economic meaning.

These checks establish continuity between the older and newer printed totals.
Gross Borrowing must not be treated as interchangeable with Borrowing with QTC
or added to its component rows. Net Debt must not be summed with flows or gross
Borrowing.

## Handling rule

`published_editions` lists now declare the exact applicability of Net Debt,
gross Borrowing, and Net Borrowing. The extractor ignores their labels outside
those editions and continues longest-label-first matching so generic Borrowing
cannot claim Borrowing with QTC. Both `Borrowing` and `Borrowings` map to the
same gross stock measure. Exact file, page, table, row, financial year, and
vintage remain in every citation locator.

Expected database effect: 18 new facts (10 Net Debt and 8 gross Borrowing),
zero new measure definitions, nodes, or edges. Existing API/UI paths are
dynamic and need no new surface.
