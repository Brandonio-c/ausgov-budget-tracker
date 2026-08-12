# Grants explorer (Wave 4, item 6.3)

Generated: 2026-08-12T03:57:05Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.3, second migration: "Grants — portfolio/program -> award/recipient, never
additive to expenditure."

## Previous behavior

2,486 GrantConnect award facts (`federal_grantconnect_awards`, `measure_type: grant_award`,
`compatibility_group: commitment`, `estimate_status: award`, FY2024-25) have been loaded
and live, but no frontend page existed to surface them - confirmed by a repository-wide
search finding only an unrelated legend-label string ("grants": "Grants") in
`HomeClient.tsx`, no real page.

## Changes

- Added `src/frontend/app/explorers/grants/page.tsx`, closely mirroring the just-fixed
  contracts explorer's proven pagination pattern - it shares the exact same
  `compatibility_group`/`accounting_basis` (`commitment`) and only the `estimate_status`
  differs (`award` vs `contract`), so the same `/v2/tree` cursor-pagination endpoint
  applies directly with no backend change.
- Registered in `src/frontend/app/explorers/page.tsx`'s index.
- Explicit page copy states grant awards are never additive to expenditure in the annual
  tree, per the plan's exact wording for this migration - an award commitment and its
  eventual cash expense are different measures with different timing.
- Simplified away a searchParams-resync effect present in the contracts page (which
  reacts to `searchParams` changing after mount, e.g. browser back/forward) since
  duplicating it here would have added a second `react-hooks/set-state-in-effect`
  violation to this repo's eslint baseline; year/filter are still correctly seeded from
  the URL once at mount via the `useState` initializer.

## Validation

- `npx tsc --noEmit`: passed.
- `npm run lint:ci`: passed at the existing accepted baseline (25 errors / 13 warnings,
  unchanged - the initial attempt using the contracts page's resync-effect pattern
  verbatim did add one new violation, fixed as described above before this was accepted).
- `npm run build`: passed, 14 static routes (was 13).
- `npm run test:unit`: passed.
- **Live browser verification** (Playwright against `next dev` + a local backend bound to
  the real `data/facts.db`): confirmed the true total ("2,486 grant awards for 2024-25,
  total value $35,965,945,219 — 200 loaded"), a working Load-more (400 loaded, total
  unchanged), a correct citation
  (`grantconnect:2024-25:program:Comprehensive Primary Health Care`), and zero console
  errors.

## Data impact

None. No backend, database, or API contract change.

## Dashboard impact

Once deployed (see the production-deployment-lag finding recorded elsewhere in this
ledger), all 2,486 FY2024-25 grant awards become reachable, paginated truthfully, and
explicitly labeled as non-additive to expenditure.

## Remaining risks

Hierarchical portfolio/program -> award/recipient depth (the plan's fuller ask) and
server-side search are not attempted here - both belong to the larger item 6.1 reusable
explorer API, matching the same scope boundary already recorded for the contracts fix.
