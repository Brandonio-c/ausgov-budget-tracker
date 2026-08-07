# TAS TAFR PDF backfill: UI exposure (Task 7)

Generated: 2026-08-06T19:16:38Z.

## No frontend or backend router code change was needed

The already-shipped `/v2/tas-ggs/series?measure_type=...` endpoint
(`src/backend/routers/v2/tas_ggs.py`) queries
`SELECT * FROM facts WHERE measure_type = ? ORDER BY financial_year`
with no source-document or vintage filter - it already returns every
year for a given measure_type regardless of which adapter (xlsx or
PDF) published it. Verified directly against the real, now-backfilled
database:

```
GET /v2/tas-ggs/series?measure_type=tas_ggs_net_debt
-> 22 facts: 2010-11 (budget+actual) ... 2028-29
```

The existing "TAS GGS" toggle on `/explorers/gfs` (added in the prior
milestone) already renders every fact returned by this endpoint as a
row labelled `<financial_year> (<estimate_status>) — <label>`, and
`estimate_status` already includes `budget` as a valid, correctly-
displayed value (the row-mapping code does
`f.estimate_status.replace("_", " ")`, which is a no-op for `budget`
since it contains no underscore).

## Real-browser verification

Confirmed in a real browser (Playwright against a real `next build`
static export + a real backend + the real, now-backfilled
`data/facts.db` - matching this repo's established discipline, not
`next dev`): selecting "TAS GGS net debt (stock)" shows the new
`2010-11 (budget)` row with the correct value (309,000,000), its
citation resolves to `table:Key Financial Indicators` (the PDF
source), and the pre-existing `2024-25 (actual)` row (from the xlsx
source) remains unaffected alongside it in the same list.

## Conclusion

This is the "wire into an existing explorer" case explicitly
anticipated by the mission's Task 7 instructions, taken to its logical
conclusion: because the new facts share the exact same measure_type/
compatibility_group/API contract as the already-exposed family, the
existing generic-by-measure_type endpoint and UI already handle the
extension correctly with zero code changes. No commit is needed for
this task beyond this report.

## Next

Task 8: additional tests (already covered extensively in Task 5's 30
tests - this task adds any remaining gaps, e.g. an API-level check
confirming the extended years are reachable through the existing
router with no route change).
