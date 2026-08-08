# Flat generic tree pagination validation

Generated: `2026-08-08T15:45:39Z`

## Scope

Plan item 3.4: preserve the compatibility `/v2/tree` route while making its flat shape, full-scope totals, publication filter and pagination contract explicit and truthful. Hierarchical exploration remains a separate Wave 4 API.

## Result

- The response now declares `shape: flat`.
- `total_count`, `total_value` and the compatibility root `value` are calculated over the complete filtered scope, independently of `limit` and cursor position.
- Pages use an opaque, versioned keyset cursor ordered by non-null amount descending, then fact ID; null amounts follow non-null amounts deterministically.
- `next_cursor` is returned only when another page exists.
- Both totals and page rows exclude `rejected` and `quarantined` facts with the same predicate.
- Citations are assembled from the page query rather than reopening the database once per fact.

## Real-data traversal

The bounded validation scope was `gfs_revenue / gfs / actual / 2024-25`:

- full count: **382** facts;
- full value: **$3,366,941,204,550.96**;
- page size: **17** for exhaustive cursor traversal;
- result: every accepted fact appeared exactly once and traversal terminated;
- a five-row request retained the same full count and value rather than reporting the five-row page sum.

The initially considered `actual_expense / accrual / actual / 2024-25` scope contains 87,348 publishable facts across government levels. It remains supported, but was not used for exhaustive regression traversal because doing so would needlessly slow every test run.

## Compatibility

The existing `name`, `value` and `children` fields remain. `value` now truthfully equals the full filtered `total_value`; callers that need page-local arithmetic can sum `children`. The frontend client accepts the added fields and can pass an optional cursor.

## Validation

- Focused tree pagination and citation suite: 5 passed.
- Full backend suite: 577 passed, one dependency deprecation warning.
- Ruff: passed.
- Frontend semantic unit tests: passed.
- TypeScript: passed.
- Frontend lint baseline: unchanged at 25 errors / 13 warnings.
- Production build: passed, 12 static pages.
- `git diff --check`: passed.

## Data impact

None. The endpoint and all audits are read-only; no migration, ingestion or database mutation was performed.
