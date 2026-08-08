# Historical FBO provenance repair and graph pack

Generated: `2026-08-08T16:55:00Z`

## Scope

Plan item 4.2: make the already-loaded FY2019-20 through FY2023-24 FBO Appendix A corpus exactly attributable, then deploy a reversible, idempotent, exact-only related graph pack without re-extracting or duplicating facts.

## Provenance repair

The source mapping now declares the acquired PDF path for each financial year. Shared ingestion selects and hashes that exact file per row. Retrieval upserts correct stale URL/path/content metadata when the same source-document SHA already exists.

- Facts reingested: **415**; published: **415**; quarantined: **0**; duplicated/replaced: **0**.
- Distinct retrievals: **5**, one per source year.
- Exact-year locator, landing URL, official resource URL, locator cached path, retrieval URL and retrieval local path: **415/415**.
- A second reingestion produced the same fact population and attribution.

The change was rehearsed first on a disposable database copy, where exact-year citation coverage moved from 0/415 to 415/415.

## Edge pack

- `fbo_archive_under_abs`: related, augmenting, exact-only, `fbo` branch, navigation presentation.
- `fbo_archive_source_native`: same-group, augmenting, exact-only, data presentation.
- Related ABS→FBO edges: **11** for ten mapped budget functions. Housing has two declared ABS inputs (`Housing and community amenities` and `Environmental protection`).
- Source-native function→subfunction edges: **75**. The five editions contain 71 path rows each, but four typographic label variants are distinct across the combined corpus.
- Explicit exceptions remain unwired: `Agriculture, forestry and fishing`, `labour and employment affairs`, and `Other purposes`.

The related builder supports declared factless navigation nodes only when exact-year fact-bearing descendants exist. Navigation-role related folders are excluded from additive totals by relationship metadata rather than folder-name heuristics.

## Reversibility and idempotency

On a disposable database and again live:

- first rebuild: 75 source-native and 11 related edges;
- second rebuild: deleted 75/11 and recreated 75/11;
- no duplicate semantic edges;
- pack deletion/rebuild remains scoped by edge-set ID.

## Validation

- Focused ingestion, edge-policy, API and projection suites: 32 passed.
- Dashboard semantic audit: 0 hard failures and 0 missing citations.
- FY2022-23 root: **$639.703b**, unchanged; exact FBO leaves cited: 69/69.
- FY2023-24 root: **$687.277b**, unchanged; exact FBO leaves cited: 69/69.
- Both years: additive depth 2, related depth 2, no fallback facts, 11 canonical functions with related routes.
- Graph/data integrity audit: 0 hard failures; 0 orphan facts, nodes or edges.
- SQLite integrity: `ok`.
- Ruff and diff checks passed.

## Data impact

The ignored live database now has correct per-edition retrieval attribution for the same 415 facts, 75 source-native edges, 11 related edges, and the navigation nodes required by those edges. No fact amount, fact key, year, semantic field, canonical ABS total, unrelated edge, or quarantined row changed.
