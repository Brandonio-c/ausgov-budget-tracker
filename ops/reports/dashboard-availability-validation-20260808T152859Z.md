# Dashboard per-year availability validation

Generated: `2026-08-08T15:28:59Z`

## Scope

Plan item 3.2: stop applying one federal accounting-basis preference to the whole time series, retain the legacy string year endpoint, expose basis/source metadata, and ensure every advertised year is queryable.

## Result

- Federal actual availability now contains 30 years, from FY 1996–97 through FY 2025–26.
- FY 2005–06, 2006–07 and 2007–08 are offered and select `accrual`, because no GFS facts exist for those years.
- FY 2008–09 selects `gfs` and reports both `accrual` and `gfs` as available.
- FY 2024–25 also selects `gfs` when both bases exist.
- FY 2025–26 selects the only available basis, `accrual`.
- Every year returned by `/v2/dashboard/years?mode=actuals&level=federal` returned HTTP 200 from the matching tree request and declared either `gfs` or `accrual` as its selected basis.

## API contract

`GET /v2/dashboard/availability` returns ordered objects with:

- `financial_year`;
- `selected_basis`;
- `available_bases`;
- `source_families`.

`GET /v2/dashboard/years` remains an ordered `string[]` and is now projected from the same availability calculation. Availability applies mode-specific measure filters and excludes rejected/quarantined facts. GFS preference is evaluated separately for each actual year.

## Frontend behavior

- The selector consumes availability metadata and labels each option with its selected basis.
- The selected year displays a basis note, including alternative bases where present and an explicit GFS-unavailable disclosure for accrual-only actual years.
- If deployed temporarily against an older backend without `/availability`, the client falls back to the legacy `/years` endpoint.

## Validation

- Focused dashboard/API contract suite: 16 passed.
- Full backend suite: 574 passed, one dependency deprecation warning.
- Ruff: passed.
- Frontend semantic unit tests: passed.
- TypeScript: passed.
- Frontend lint baseline: unchanged at 25 errors / 13 warnings.
- Production build: passed, 12 static pages.

## Data impact

None. Availability is read-only and performs no migration or ingestion.
