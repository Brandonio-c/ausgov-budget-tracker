# VIC AFS deferred-sheet inventory and disposition (20260807T175300Z)

## Selection and source

This is canonical queue position 7. All six remaining sheets were directly
inspected in the already-verified 2024-25 DTF Annual Financial Statements xlsx
(SHA-256 `307aac748b06aa7d2c1197ca370e0df07c20449f4b2fa564673888e04511c0f3`).
The previously loaded Operating Statement, Balance Sheet, and Cash Flow
Statement are not reopened.

## Complete six-sheet inventory

| sheet | dimensions | shape and semantic domain |
|---|---:|---|
| Statement of Changes in Equity | 16 x 5 | Two equity components plus total; opening, movement, and closing stock rows across two sequential years; contains machinery-of-government transfers. |
| Departmental Outputs Schedule | 41 x 12 | Four departmental output columns, each with 2025/2024, plus departmental totals; mixes controlled income/expense flows with asset/liability stocks. |
| Annual Appropriations | 47 x 10 | Two year-blocks; controlled/administered rows across seven authority/application columns plus variance, followed by an embedded annotated-income subtable with another layout. |
| Special Appropriations | 23 x 5 | Authority and purpose dimensions with two year columns; administered appropriations applied, including transfers, pensions, grants and refunds. |
| Administered Income & Expenses | 32 x 3 | Two annual columns; administered income, expense, net-result, and other-comprehensive-income flows on behalf of the State. |
| Administered Assets & Liab | 22 x 3 | Two point-in-time columns; administered asset/liability components and net administered assets. |

Every sheet is genuinely structured and numeric in `$ thousand`; access and
parsing are not blocked. Direct inspection also confirms that the set is not a
single reusable table shape:

- changes in equity is a rolling stock/movement reconciliation;
- outputs is a two-dimensional output-by-measure schedule;
- annual appropriations contains two different embedded tables and authority,
  application, variance, controlled/administered dimensions;
- special appropriations is legislation/purpose detail;
- the two administered statements share a simple two-year column shape but
  require administered (on-behalf-of-State) semantics distinct from DTF's
  already-loaded controlled operations.

Several totals repeat concepts already present elsewhere in the same workbook:
Departmental Outputs repeats the controlled statement totals; Annual
Appropriations' `Appropriations applied` values feed the financial statements;
and administered/special-appropriation totals cross-reference one another.
Loading all rows as siblings would create additive duplicates.

## Disposition

**Deferred as multiple future subfamilies, not one adapter extension.** The
queue description calls this a broader/more-varied remainder, and inspection
confirms it. A safe implementation must first choose among at least four
semantic products (equity reconciliation, output allocation, appropriation
compliance, and administered statements), define cross-table duplicate edges
or exclusions, and decide whether administered State-level balances belong in
a DTF departmental view. Bundling those decisions into this loop would violate
the instruction not to bulk-edit unrelated shapes.

The tightest future candidate is the pair `Administered Income & Expenses` +
`Administered Assets & Liab`, using sheet-scoped measures and an isolated
administered compatibility group. It should be ranked as its own item rather
than treated as completion of all six sheets.

No extractor, semantic YAML, database, API, or UI changed. Backup/load,
idempotency, frontend, and production checks are not applicable. Counts remain
289,315 facts, 133 source documents, 222,575 nodes, and 0 edges; the clean Task
9 and dashboard `20260807T174624Z` baselines remain valid.

This six-sheet queue item is explicitly addressed and deferred, not marked
complete ingestion coverage.
