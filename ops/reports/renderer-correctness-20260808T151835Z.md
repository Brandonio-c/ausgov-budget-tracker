# Dashboard renderer correctness validation

Generated: `2026-08-08T15:18:35Z`

## Scope

Plan item 3.1: keep ECharts layout weights separate from published values, format every chart by semantic unit, prevent misleading percentages on related branches, and keep folded `Other` nodes semantically homogeneous.

## Defect reproduced

Nested sunburst children whose published values did not reconcile to their parent were rescaled for arc layout. The tooltip read ECharts `value`, so it displayed the rescaled layout weight rather than the cited fact. Pie, bar, ring and center formatting also used AUD-specific helpers even for typed non-AUD measures.

## Implemented contract

- `SunburstDatum.value` is layout weight only.
- `reportedValue` retains the exact fact or honest folded aggregate.
- `reportedUnit`, `reportedParentValue`, `relationship`, and `isRelated` travel with each datum.
- Scaling changes only `value`; it never mutates reported fields.
- Tooltips, labels, axes, center text and accessibility descriptions use reported values through `formatMeasureValue`.
- Percent-of-parent is calculated from reported values only for additive siblings in the same unit, compatibility group and source year.
- Related branches show an explicit non-comparability note and no percentage.
- Mixed-unit charts do not emit an AUD total.
- Tail folding partitions by edge/branch kind, presentation role, unit, source year, compatibility group and accounting basis. Synthetic aggregates retain relationship metadata and never wrap a singleton merely to satisfy a visual token limit.
- Navigation-folder selection uses relationship metadata, with a legacy `breakdown`/label fallback only when the optional relationship contract is absent during rollback.

## Automated validation

- `npm run test:unit`: passed. The executable assertions prove:
  - a child with published value 80 can have a different scaled layout weight while its tooltip still displays 80;
  - percentages and recipient counts never gain an AUD symbol;
  - related branches suppress percent-of-parent;
  - additive percentages use the reported semantic cohort;
  - mixed units produce no aggregate unit claim;
  - every synthetic `Other` contains one semantic signature and retains relationship metadata.
- `npx tsc --noEmit`: passed.
- `npm run lint:ci`: unchanged accepted baseline, 25 errors and 13 warnings.
- `npm run build`: passed; 12 static pages generated across 10 application routes plus framework routes.
- Backend regression baseline immediately before this frontend-only change: 572 passed, one dependency deprecation warning.

## Data and API impact

None. No database, ingestion, schema or API value changed. The renderer consumes the optional relationship fields added in the preceding projection-contract milestone and remains compatible with their absence.
