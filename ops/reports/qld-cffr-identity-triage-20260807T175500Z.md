# QLD CFFR identity triage (20260807T175500Z)

## Finding

Canonical queue position 8 is **not a separate data family**. The ranking
reports describe “CFFR quarterly Commonwealth-Federal-Relations bulletins,”
but direct source inspection proves that `CFFR` in these filenames means
**Consolidated Fund Financial Report**.

For example, `CFFR-March-2025.pdf` begins “This Quarterly Statement for the
Consolidated Fund” and its primary table is `STATEMENT OF RECEIPTS AND PAYMENTS
FOR THE QUARTER ENDED 31 MARCH 2025`. Its rows are Consolidated Fund balances,
department collections, investment interest, appropriations, and other Public
Account cash transactions. The 2018 and annual 2020-21/2022-23 files show the
same identity. No asset in the acquisition manifest has a Commonwealth- or
federal-financial-relations filename.

## Complete inventory relationship

There are **25 CFFR-named PDFs**:

- March/September/December 2018 (3)
- March/September/December 2019 (3)
- March/September/December 2020 (3)
- 2020-21 final plus March/September/December 2021 (4)
- March/September/December 2022 plus 2022-23 final (4)
- March/September/December 2023 (3)
- March/September/December 2024 (3)
- March/September 2025 (2)

All 25 are the same files already included in the 46-asset Consolidated Fund
inventory at
`ops/reports/qld-consolidated-fund-inventory-20260807T174900Z.md`; they are not
25 additional assets. Twenty-four are directly text-extractable (20,356 to
98,572 characters). `cffr-sept-2025.pdf` yields only five characters and is the
one OCR/image-layout exception.

## Disposition and supersession

This queue entry is **superseded as a duplicate** by canonical position 5,
QLD Consolidated Fund Financial Reports. The content-based label in
`qld-backlog-rerank-20260807T142208Z.{md,csv}` and the consolidated report's
merged queue is contradicted by the primary documents. The earlier reports are
still historical ranking artifacts, but their CFFR topic interpretation must
not drive implementation.

The 25 assets inherit the explicit cash/Public Account semantic deferral in the
Consolidated Fund inventory. They must not be separately ingested, which would
double-count the same source files.

No repository code, data, database, API, or UI changed. Counts remain 289,315
facts, 133 source documents, 222,575 nodes, and 0 edges. Backup/load,
idempotency, frontend, dashboard rerun, and production verification are not
applicable to a documentary supersession finding.
