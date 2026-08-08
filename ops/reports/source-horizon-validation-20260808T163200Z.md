# Source-aware fiscal-year horizon validation

Generated: `2026-08-08T16:32:00Z`

## Scope

Plan item 3.7: investigate the published FY `2099-00` state-actual outlier, add source-declared publication-horizon validation rather than a global maximum, and quarantine unexplained outliers with machine-readable reasons.

## Root cause

The defect was systematic QGIP column confusion, not a legitimate future observation:

- the exporter chose the first normalized column containing “financial year”;
- `Financial year expenditure` therefore competed with the actual `Financial Year` column;
- amount 2,099 was formatted as FY `2099-00`; amount 2,000 was formatted as FY `2000-01`;
- locators for affected rows explicitly name `Financial year expenditure` as the amount column while pointing to source files from FY2012-13 through FY2024-25.

The preflight found **4,198** published outliers across **80** impossible years. Four were `2099-00`; 3,842 were `2000-01`.

## Prevention

- QGIP now prefers exact year-column names and excludes amount/expenditure/value/total columns from fuzzy year matching.
- Its mapping declares `publication_horizon.min_financial_year: 2012-13` and `max_financial_year: 2024-25`, matching the acquired resource editions.
- The generic validation pipeline applies a horizon only when the source mapping declares one; there is no repository-wide arbitrary maximum.
- Outliers receive a stable reason such as:

```text
source_horizon_outlier:financial_year=2099-00;allowed=2012-13..2024-25
```

## Existing-data remediation

`scripts/ops/quarantine_source_horizon_outliers.py` defaults to a read-only preview. Applied mode runs in an immediate transaction, copies complete fact/source/retrieval provenance to `facts_pending_attribution`, deletes the invalid published fact, and removes only nodes left unreferenced and unedged by that exact quarantine set.

- Published outliers moved to quarantine: **4,198**.
- Exclusive orphan nodes removed: **3,522**.
- Published QGIP facts remaining: **176,719**.
- Remaining published QGIP range: **FY2012-13 through FY2024-25**.
- Horizon-quarantined facts: **4,198**, spanning the original FY2000-01 through FY2099-00 labels.
- Second applied run: 0 candidate facts, 0 quarantined facts, 0 deleted nodes.

The facts remain recoverable from quarantine with their original fact key, amount, source document/retrieval IDs, locator JSON, publication/retrieval timestamps and machine reason. Re-publication requires corrected year attribution, which belongs to the broader QGIP repair in item 7.2.

## Validation

- Focused extractor/horizon/quarantine suite: 9 passed.
- Real registry invariant suite: 11 passed.
- Full backend suite: 591 passed, one dependency deprecation warning.
- Repository graph/data integrity audit: 0 hard failures; 0 orphan facts, nodes or edges.
- Live `PRAGMA integrity_check`: `ok`.
- Ruff and `git diff --check`: passed.

## Data impact

The ignored live database changed from 289,315 to 285,117 published facts. Exactly 4,198 QGIP facts were moved to quarantine rather than discarded, and 3,522 nodes supported only those invalid facts and no graph edge. No valid-range fact, shared node, edge, citation, amount or source document changed.
