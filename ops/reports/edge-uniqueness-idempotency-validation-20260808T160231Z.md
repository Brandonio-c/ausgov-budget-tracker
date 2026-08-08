# Edge uniqueness and idempotency validation

Generated: `2026-08-08T16:02:31Z`

## Scope

Plan item 3.5: audit and enforce NULL-safe `breakdown_edges` identity, make production writers conflict-safe, and provide explicit reversible edge-set deletion/rebuild operations.

## Pre-migration audit

- Live edge rows: **14,167**.
- Duplicate groups using `(parent, child, kind, COALESCE(year, ''), COALESCE(crosswalk, ''))`: **0**.
- Because the audit was clean, applying migration 017 deleted **0** rows.

## Schema and writer changes

- Migration `017_breakdown_edge_uniqueness.sql` defensively retains the oldest row from any legacy duplicate group, then creates unique expression index `uq_breakdown_edges_identity` over the NULL-normalized identity.
- All four production insertion paths in `breakdown_pack.py` and `pbs_s6_crosswalk.py` now use `INSERT OR IGNORE`; check-then-insert races and ad hoc NULL handling are removed.
- A second live migration run reported migration 017 as `noop`.

## Reversible edge-pack command

`scripts/ingest/edge_pack.py` accepts exactly one operation and selector:

```text
python scripts/ingest/edge_pack.py (--delete | --rebuild) \
  (--edge-set EDGE_SET_ID | --crosswalk-id CROSSWALK_ID) [--apply]
```

Without `--apply`, the command is read-only and reports matched counts. With `--apply`, it runs in an immediate transaction: delete is scoped by registered edge kind, crosswalk and child source rules; rebuild deletes that scope, invokes its registered deterministic emitter, verifies the resulting scope count and commits atomically. Errors roll back the transaction.

The shared `cofog_to_budget_function` preview correctly resolved two independently scoped edge sets: 769 Statement 6 edges and 954 FBO edges.

## Disposable full rebuild audit

Every registered edge set was rebuilt on one disposable copy of the 631 MB live database. No disposable changes were copied back to live.

| edge set | before | after | interpretation |
| --- | ---: | ---: | --- |
| `statement_6_under_abs` | 769 | 1,162 | current emitter derives additional missing links |
| `fbo_2024_25_under_abs` | 954 | 954 | stable |
| `statement_6_source_native` | 106 | 107 | one derivable path edge missing from stored graph |
| `pbs_source_native` | 3,448 | 3,470 | current emitter derives additional path edges |
| `grants_source_native` | 2,492 | 2,496 | current emitter derives additional path edges |
| `contracts_source_native` | 142 | 142 | stable |
| `recipients_source_native` | 61 | 61 | stable |
| `pbs_programs_all_under_s6` | 5,107 | 5,107 | stable |
| `statement_6_components` | 53 | 53 | stable |
| `pbs_dss_bridge` | 453 | 448 | current rules omit five stored stale links |
| `pbs_under_component` | 7 | 7 | stable |
| `contracts_under_statement_6` | 3 | 3 | stable |
| `grants_under_pbs` | 487 | 478 | current rules omit nine stored stale links |
| `recipients_under_pbs` | 15 | 15 | stable |

The final disposable duplicate audit returned **0**. These deltas are surfaced explicitly: reversible means a pack can be removed and deterministically redeployed under current rules, not that rule drift is hidden. Reconciling the live graph to changed emitters is a separate, reviewable deployment decision.

## Live post-migration validation

- Live edge rows: **14,167** (unchanged).
- NULL-safe duplicate groups: **0**.
- `uq_breakdown_edges_identity`: present and unique.
- `PRAGMA integrity_check`: `ok`.
- Graph integrity audit: **0 hard failures**, 0 orphan edges, 0 cross-government additive edges and 0 cross-jurisdiction additive edges.
- Focused migration/pack/crosswalk/integrity suite: **60 passed**.
- Full backend suite: **581 passed**, one dependency deprecation warning.
- Ruff and `git diff --check`: passed.

## Data impact

Migration 017 and its unique index were applied to the ignored live `data/facts.db`. The migration recorded its schema version but did not delete or rebuild any live edge row. All destructive/rebuild validation ran only on temporary database copies.
