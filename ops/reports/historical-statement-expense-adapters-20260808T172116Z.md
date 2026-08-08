# Historical Budget Paper expense adapters

Generated: 2026-08-08T17:21:16Z
Plan item: 5.2

## Outcome

A single edition-configured adapter now extracts function, subfunction and published component tables from the three acquired historical Budget Paper No. 1 editions. It does not reuse current-edition page numbers or assume that every edition calls the expenses section Statement 6.

The mappings are deliberately marked `adapter_only_pending_graph_visibility`. They passed an isolated database ingestion/idempotency preflight, but are not deployed to the live facts database: the current generic budget query treats every compatible fact as a flat additive sibling. Publishing before item 5.4 would inflate dashboard totals instead of exposing a selected related branch.

## Edition contract

| Source | Published section / appendix | Published columns | Published estimate rows | Component tables |
| --- | --- | --- | ---: | ---: |
| March 2022-23 | Statement 5 / Table 5A.1 | FY2020-21 to FY2025-26 | 765 | 13 (`5.x.y`) |
| October 2022-23 | Statement 6 / Table 6A.1 | FY2021-22 to FY2025-26 | 616 | 13 (`6.x.y`) |
| 2023-24 | Statement 6 / Table 6A.1 (one continuation page is printed as `Table A1`) | FY2021-22 to FY2026-27 | 765 | 13 (`6.x.y`) |

The adapter excludes each table's historical `actual` column because audited actuals already belong to the FBO branch and `budget_estimate` would be a false measure type for those cells. It retains `estimated_actual`, `budget` and `forward_estimate` separately.

## Extracted shape

| Source | Function rows | Subfunction rows | Component rows | Grand-total rows | Unique component paths |
| --- | ---: | ---: | ---: | ---: | ---: |
| March 2022-23 | 70 | 340 | 350 | 5 | 70 |
| October 2022-23 | 56 | 272 | 284 | 4 | 71 |
| 2023-24 | 70 | 340 | 350 | 5 | 70 |

Counts are fact rows across retained financial-year columns. Every component path resolves to exactly one function/subfunction parent from its own edition appendix. There are zero duplicate `(financial year, category, estimate status)` identities.

## Published total checks

- March 2022-23: FY2021-22 $639.569b; FY2022-23 $628.469b; FY2023-24 $643.833b; FY2024-25 $665.369b; FY2025-26 $686.839b.
- October 2022-23: FY2022-23 $650.922b; FY2023-24 $666.465b; FY2024-25 $702.253b; FY2025-26 $730.960b.
- 2023-24: FY2022-23 $644.788b; FY2023-24 $684.085b; FY2024-25 $715.382b; FY2025-26 $743.324b; FY2026-27 $771.779b.

These assertions run against the acquired PDFs and freeze the distinct March/October vintages.

## Isolated ingestion preflight

The three mappings were run twice against a copy of `data/facts.db`:

- first and second passes: 765 + 616 + 765 published, zero quarantined, zero Gate 6 failures;
- second pass retained exactly 2,146 distinct fact keys;
- one exact source retrieval/checksum per edition;
- `PRAGMA integrity_check`: `ok`.
- Full backend regression suite: 605 passed, one dependency deprecation warning.

A live-load probe demonstrated why deployment is gated: without the item 5.4 crosswalk/visibility policy, the generic budget projection included these rows as independent additive paths and failed the golden fixture. The exact 2,146 probe facts and their three source documents/retrievals/nodes were removed, restoring the pre-probe live database. The restored dashboard audit matches its golden fixture with zero hard failures.

## Files

- Adapter: `scripts/ingest/extractors/historical_bp1_expenses.py`
- Edition regressions: `tests/ingest/test_historical_bp1_expenses.py`
- Mappings: `config/mappings/federal_budget_statement_6_2022_23_march.yaml`, `federal_budget_statement_6_2022_23_october.yaml`, `federal_budget_statement_6_2023_24.yaml`
- Generated staging CSVs remain under `data/staging/breakdowns/` and are reproducible from the acquired PDFs.

## Next item

Plan item 5.3: add edition fixtures to the generalized PBS classifier and extract the three acquired Treasury PBS representatives while preserving portfolio/entity/outcome/program/component path and publication vintage. Item 5.4 must define edge-scoped dashboard visibility before either historical family is deployed.
