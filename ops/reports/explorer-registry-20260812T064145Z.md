# Explorer family registry and availability API (item 6.1, first increment)

Generated: 2026-08-12T06:41:45Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.1: "Add a family registry and endpoints" with capabilities including
cursor pagination (already built, item 3.4), a jurisdiction/source-edition facet (already
built this session, `source_breakdown`), and now a registry plus availability listing.

## Previous behavior

Each of the five completed Wave 4 family pages (contracts, grants, VIC output performance,
ACT invoices, PBS) hardcoded its own `compatibility_group`/`accounting_basis`/
`estimate_status`/`source_key` scope directly in its `page.tsx`, duplicated with no single
source of truth, and no endpoint existed to discover what families exist or which
financial years/estimate statuses actually have live data for a family without querying
`/v2/tree` once per candidate year.

## Changes

- `config/explorers/families.yaml`: declarative registry of the five completed families,
  each recording its exact compatibility triple, allowed estimate statuses (PBS: 4, VIC
  output performance: 2, the rest: 1), `source_key` where the triple is shared with
  unrelated sources, and an `additive_note` (e.g. contracts' jurisdiction-mix warning,
  grants' "never additive to expenditure"). Follows the same `version: 1` + fail-fast
  validation pattern as the existing `config/breakdowns/edge_sets.yaml` registry.
- `src/backend/explorer_registry.py`: loader with the same shape as
  `edge_set_policy.py` - `@lru_cache`d, validates `default_estimate_status` is a member
  of `estimate_statuses`, rejects empty `estimate_statuses`, rejects duplicate family IDs,
  requires `compatibility_group`/`accounting_basis`.
- `src/backend/routers/v2/explorers.py`: two new endpoints -
  `GET /v2/explorers` (lists all registered families with their full scope metadata) and
  `GET /v2/explorers/{family_id}/availability` (per financial_year × estimate_status,
  live count and value, honoring the family's `source_key` when set; 404 for an unknown
  family_id).
- Registered in `src/backend/routers/v2/__init__.py`.
- `tests/unit/test_explorer_registry.py` (8 tests): live-registry shape assertions plus
  registry-validation failure-mode tests mirroring `test_edge_set_policy.py`'s structure.
- `tests/api/test_v2_explorers.py` (4 tests): `/v2/explorers` returns all five families
  with correct metadata; PBS availability for 2024-25/actual matches a direct SQL query
  byte-for-byte; contracts availability (no `source_key` in the registry) matches
  `/v2/tree`'s multi-jurisdiction total exactly, proving the registry does not silently
  narrow a family that is legitimately multi-source; unknown family returns 404.

## Validation

- Full backend suite: 660 passed (12 new), 0 regressions.
- No frontend change in this increment - the five existing pages still hardcode their own
  scope and are unaffected by this addition; migrating them to consume `/v2/explorers` is
  deliberately deferred (see "Remaining risks").

## Data impact

None. No database write; both new endpoints are read-only.

## Dashboard impact

None yet - no frontend page consumes these endpoints. They establish the single source of
truth the plan's item 6.1 calls for, ready for the frontend shell and family-page
migration in a following increment.

## Remaining risks

This increment intentionally does not yet include: migrating the five existing pages to
read their scope from `/v2/explorers` instead of their own hardcoded constants; the
hierarchical `tree?path=` browsing, `facets`, `search`, or `item/{fact_id}` endpoints the
plan also lists under 6.1; or the generic frontend shell (item 6.2). Each remains
substantial, separable work - taking the family registry itself as the smallest correct
first step avoided bundling a large, harder-to-review change. The production deployment
lag continues to apply to this and every backend change since item 3.4.

## Next item

Continue item 6.1: either migrate the five existing pages onto `/v2/explorers` (removing
the now-duplicated hardcoded scope constants), or add the next capability (facets/search)
before item 6.2's generic shell.
