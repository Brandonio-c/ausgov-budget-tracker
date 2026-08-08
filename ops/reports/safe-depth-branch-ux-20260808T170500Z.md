# Safe-depth and related-branch UX validation

Generated: `2026-08-08T17:05:00Z`

## Scope

Plan item 4.4: expose selected versus available ring depth, make related source families explicit choices, and disclose relationship/year/basis/status semantics without hiding the canonical branch or changing totals.

## Changes

- Renamed the frontend traversal helper from `maxAdditiveDepth` to `maxVisibleDepth`; additive depth continues to come from typed projection metadata.
- Ring depth control now says `Safe levels`, displays selected/available/default values, and offers `Show maximum` when deeper levels exist.
- Canonical data is the default ring branch. The previous automatic Statement 6 preference was removed.
- Home and Combined dashboards enumerate available related families as explicit chips, including canonical actual, audited FBO, Budget Statement 6, contracts, grants, PBS and recipients where present.
- Selecting a family follows only that declared related navigation route when available; it never mixes related values into the canonical sibling total.
- Ring hover tooltips and the selected-node status row expose Additive/Related, Navigation/Data, selected year, source year, accounting basis and estimate status before the citation panel is opened.
- Debt uses the renamed visible-depth helper and retains canonical behavior.

## Semantic safeguards

- Canonical is always the initial/default choice.
- Related navigation folders remain excluded from pie/bar sibling sums.
- Ring layout scaling remains separate from reported values.
- Branch selection changes navigation only; published canonical totals and source facts are unchanged.
- A selected family unavailable in the current drill context falls back to canonical rendering rather than silently choosing another related family.

## Validation

- Chart semantic unit tests: passed, including canonical-default versus explicit FBO selection and relationship tooltip disclosures.
- TypeScript `tsc --noEmit`: passed.
- ESLint accepted baseline: unchanged at 25 errors / 13 warnings.
- Next.js production build: passed; 12 static pages generated.
- Repository search: zero remaining `maxAdditiveDepth` references and zero automatic Statement 6 preference paths.
- `git diff --check`: passed.

## Data and API impact

None. This is a frontend interpretation/control milestone using the existing typed projection and relationship contract.
