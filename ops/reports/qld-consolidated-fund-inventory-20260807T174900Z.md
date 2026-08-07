# QLD Consolidated Fund family inventory and disposition (20260807T174900Z)

## Selection

This is the next item after PBS lineage maintenance: QLD re-rank position 4
and canonical loop position 5. The source is the acquired
`qld_report_on_state_finances` population.

## Complete candidate inventory

The current acquisition manifest contains **46 unique Consolidated Fund PDF
assets**: **15 annual reports** and **31 quarterly reports**.

Annual editions:

- 2008-09, 2009-10, 2010-11, 2011-12, 2012-13, 2013-14, 2014-15,
  2015-16, 2016-17, 2017-18, 2018-19, 2019-20, 2021-22, 2023-24, and
  2024-25.

Quarterly editions:

- September 2008; December 2008; March 2009
- September 2009; December 2009; March 2010
- September 2010; December 2010; March 2011
- September 2011; December 2011; March 2012
- September 2012; December 2012; March 2013
- September 2013; December 2013; March 2014
- September 2014; December 2014; March 2015
- September 2015; December 2015; March 2016
- September 2016; December 2016; March 2017
- September 2017; December 2017
- December 2025; March 2026

Every candidate was opened with `pdfinfo` and `pdftotext -layout`. All 46 are
text-extractable without OCR. Page counts range from 4 to 29, and full-text
extractions range from 16,283 to 288,182 characters for the stable 2009-10
onward material (the older annual files also yield over 100,000 characters).

## Observed shapes and semantics

The repeated core is a `Statement of Receipts and Payments`, with receipts,
appropriations to departments, and balances. Annual reports also contain a
department-level Statement of Appropriations. The documents explicitly state
that they use a **gross cash basis** and record Public Account cash receipts or
issues, not GGS accrual fiscal aggregates.

The population combines:

- annual actuals and June-quarter amounts;
- September/December/March quarter and year-to-date columns;
- current-budget or prior-period comparator columns;
- department appropriation detail affected by machinery-of-government change;
- three large publication gaps in the acquired annual sequence and an
  eight-year gap in quarterly editions.

A safe future model therefore needs isolated cash-receipt, cash-payment,
appropriation, and fund-balance measures; explicit quarter versus YTD period
granularity; original/current budget-vintage semantics; and a compatibility
group that cannot be summed with existing accrual/GFS views.

## Disposition

**Deferred as a separate cash/Public Account milestone.** Text extraction is
not the blocker. The blocker is semantic and product scope: loading these rows
into the current accrual fiscal views would be misleading, while implementing
the required isolated cash view, period/vintage model, and department-history
policy would silently broaden this backlog loop item into a new product
surface. This agrees with the QLD family-selection report and the consolidated
ranking's explicit warning that this is a narrower, different concept.

No parser, semantic YAML, database, source document, node, edge, API, or UI was
changed. Consequently no database backup/load/idempotency run was applicable.
Database counts remain 289,315 facts, 133 source documents, 222,575 nodes, and
0 edges.

Validation inherited from the immediately preceding no-data-change milestone:
the Task 9 integrity check has 0 hard failures and the dashboard audit
`20260807T174624Z` has 0 hard failures. No frontend or production verification
is applicable.

This queue item is explicitly addressed and deferred; it is not represented as
complete ingestion coverage.
