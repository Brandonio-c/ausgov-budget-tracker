# M9 — Frontend explorers

## DoD

- Contracts + GFS/jurisdiction explorers with CitationPanel
- Default-view DOM/screenshot regression green (legacy unchanged)

## Verification

| Check | Result |
|---|---|
| `/explorers/contracts` | CitationPanel + commitment tree |
| `/explorers/gfs` | CitationPanel + GFS actual_expense tree |
| Default `app/page.tsx` | still uses `api.levels` / `api.tree` / SpendingChart; no apiV2 |
| `tests/frontend/test_default_view_regression.mjs` | ok |

## Artefacts

- `src/frontend/app/explorers/{page,contracts/page,gfs/page}.tsx`
- `src/frontend/lib/api.ts` (`apiV2` additive)
