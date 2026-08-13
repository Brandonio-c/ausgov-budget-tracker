# Item 6.1 completion: full explorer backend contract (tree/facets/item/search)

Generated: 2026-08-13T02:22:17Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.1: finish the reusable explorer backend API. This report closes the
increment opened in `ops/reports/explorer-registry-20260812T064145Z.md`, which shipped
the registry, `GET /v2/explorers`, and `GET /v2/explorers/{family}/availability` but
deliberately left `tree`, `facets`, `item`, and `search` for a following pass.

## Gap analysis (before this pass)

Checked against the plan's own explicit list for item 6.1:

| Plan requirement | State before this pass |
| --- | --- |
| `GET /v2/explorers` | done (prior increment) |
| `GET /v2/explorers/{family}/availability` | done (prior increment) |
| `GET /v2/explorers/{family}/tree?year=&path=&cursor=&limit=` | **missing** |
| `GET /v2/explorers/{family}/facets` | **missing** |
| `GET /v2/explorers/{family}/item/{fact_id}` | **missing** |
| cursor pagination | done via `/v2/tree`, not yet reachable per-family |
| hierarchical path browsing | not evaluated - needed a real answer, not an assumption |
| full-result totals separate from page totals | done via `/v2/tree`, not yet reachable per-family |
| search | **missing entirely**, including on the pre-existing `/v2/tree` |
| facets for year/jurisdiction/source edition/measure/basis/status | partial (`source_breakdown` only) |
| citations/evidence | done for list rows, no scoped single-item lookup |
| unit-safe values | done (inherited, `amount_aud` never rescaled) |
| source-native hierarchy only | not yet enforced anywhere |

Before writing any hierarchy-related code, checked directly against the database whether
any of the five completed families (`contracts`, `grants`, `vic_output_performance`,
`act_invoices`, `pbs`) have real `node_edges` hierarchy beneath their nodes:

```
grants:                   2,486 nodes sampled, 0 node_edges
vic_output_performance:       7 nodes sampled, 0 node_edges
act_invoices:                900 nodes sampled (of 40,509), 0 node_edges
pbs:                          900 nodes sampled (of 2,799), 0 node_edges
contracts (all 4 sources): up to 900 nodes sampled per source, 0 node_edges
```

**None of the five families have any source-native hierarchy beneath their flat fact
list** - every node is a single formatted-string label (e.g. contracts'
`AGENCY / SUPPLIER-OR-DESCRIPTION`), not real parent/child graph structure. This settles
the design question for `tree?path=`: splitting the label string to fake a tree would
violate the standing rule against inferring hierarchy from label structure/similarity.
The only truthful implementation is to reject a non-empty `path` explicitly.

## Changes

- `src/backend/routers/v2/query.py`: extracted the existing `/v2/tree` query body into
  `build_flat_tree_response()`, a shared function now used by both `GET /v2/tree` and the
  new `GET /v2/explorers/{family}/tree` - avoiding a second, parallel query-building
  implementation that could drift out of sync on quarantine exclusion, cursor semantics,
  or the truthful-totals-independent-of-limit invariant. Also added an optional `search`
  parameter (case-insensitive substring match on the published node name, applied
  server-side to the same quarantine-safe scope before totals/pagination, with `%`/`_`
  escaped so a literal percent sign in a search term can't widen the match).
- `src/backend/routers/v2/explorers.py`: three new endpoints -
  - `GET /v2/explorers/{family_id}/tree?financial_year=&estimate_status=&path=&q=&cursor=&limit=`:
    delegates to `build_flat_tree_response()` using the registry's compatibility triple
    and `source_key`. Rejects `estimate_status` values outside the family's registered
    list (400) and rejects any non-empty `path` (400, explaining why, rather than
    fabricating or silently ignoring it).
  - `GET /v2/explorers/{family_id}/facets`: year/estimate_status/source_key/measure_type
    breakdowns over the family's full registered scope (all years, all its estimate
    statuses) - `accounting_basis` is registry-fixed per family (a single value, not a
    real facet with more than one option) and is reported on `family`, not duplicated as
    a facet list.
  - `GET /v2/explorers/{family_id}/item/{fact_id}`: citation-bearing single-fact lookup,
    scoped to the family's exact compatibility triple/`source_key`. A `fact_id` that is
    real and publishable in a *different* family still 404s here - family boundaries are
    enforced at the query level, not left as a UI convenience.
- `tests/api/test_v2_tree_pagination.py`: 3 new tests for `search` (narrows totals and
  matches direct SQL; LIKE-wildcard characters in a search term don't leak; omitted
  preserves existing behaviour).
- `tests/api/test_v2_explorers.py`: 12 new tests covering `tree` (matches direct
  `/v2/tree` with `source_key`; rejects an unregistered `estimate_status`; rejects `path`;
  does not narrow a legitimately multi-source family; search narrows within the family
  scope; unknown family 404), `facets` (single-source for PBS, multi-jurisdiction for
  contracts, unknown family 404), and `item` (matches its own tree's row; **family
  boundary enforced even for a real fact_id from another family**; unknown fact_id 404;
  unknown family 404).

## Validation

- Full backend suite: 676 passed (16 new this pass, 660 carried from the prior
  increment), 0 regressions.
- Live verification against a freshly-confirmed `uvicorn` process (new PID checked before
  and after, per this session's earlier lesson about stale dev-server processes masking
  changes): `/v2/explorers`, `/v2/explorers/pbs/tree` (with and without `q=health`,
  correctly narrowing to real Veterans' Affairs / Health portfolio rows),
  `/v2/explorers/pbs/tree?path=foo` (400, correct message),
  `/v2/explorers/contracts/facets` (4 real jurisdiction source_keys, not narrowed), and
  the cross-family `item` boundary (`grants` fact_id: 200 under `grants`, 404 under
  `pbs`) all confirmed directly via `curl`, not only via `TestClient`.
- No frontend change in this pass - same deliberate boundary as the prior increment.

## Data impact

None. All five new/extended endpoints are read-only. `search` on `/v2/tree` is optional
and additive; every existing caller is unaffected (proven by a dedicated
omitted-preserves-behaviour test).

## Dashboard impact

None yet - no frontend page consumes these endpoints. The backend explorer contract the
plan describes for item 6.1 is now complete end-to-end for all five registered families.

## Remaining risks / explicit scope boundary

- **Frontend migration is deliberately still not done.** The five existing pages
  (contracts, grants, VIC output performance, ACT invoices, PBS) still hardcode their own
  scope constants rather than reading from `/v2/explorers`. This is item 6.2 territory
  (the generic frontend shell) by the plan's own ordering - migrating pages now, ahead of
  building the shell they'd migrate onto, would mean redoing the work twice. The registry
  and per-family endpoints are shaped consistently and are ready to be consumed once 6.2
  starts.
- **Hierarchical path browsing genuinely has nothing to serve yet.** This is a data-model
  gap (no family has `node_edges` beneath its nodes), not an API gap. If a future family
  or reprocessing pass adds real hierarchy, `path` support can be added to
  `build_flat_tree_response()` without changing any existing caller's contract.
- A minor, unrelated data-quality observation surfaced while spot-checking `/facets`:
  the contracts family's `years` facet includes a `financial_year` value of `"2022-20"`
  alongside well-formed years - a pre-existing malformed value in the underlying contract
  disclosure data, not introduced by this change and out of scope for item 6.1. Left
  visible rather than silently filtered, since hiding it would be exactly the kind of
  "weaken validation to show more/cleaner-looking rings" this program's rules forbid;
  flagged here for a future data-quality pass.
- The production deployment lag (top-of-ledger callout) continues to apply to every
  backend change made this session, including this one.

## Next item

Item 6.1 is complete against the plan's own explicit endpoint/capability list. Item 6.2
(generic frontend explorer shell: `ExplorerShell.tsx`, `lib/explorerApi.ts`,
`app/explorers/[family]/page.tsx`) is next, followed by migrating the five existing family
pages onto it per the plan's established 6.3 order.
