# PBS per-source lineage maintenance (20260807T174640Z)

## Selection and scope

This was canonical queue rank 4, after the completed QLD MYFER, TAS TAFR
narrative-transition, and VIC Output Performance items. It is maintenance of
the already-covered generalized Commonwealth PBS PDF family, not a new data
load.

The generalized loader publishes PBS facts under
`federal_pbs_programs_all`, while each fact already retains its originating
registry source as `source_id:<id>` in `source_locator_json.locator`. The
coverage audit previously ignored that retained origin and showed individual
portfolio PDFs as zero-fact `improve_per_source_lineage` items.

## Change

- Added declarative `origin_lineage: locator_source_id` metadata to the PBS
  canonical-family definition.
- Added a scoped coverage-audit aggregation over only family source keys that
  opt in to that lineage method.
- Per-source PBS rows now report their own fact counts, measures, and hierarchy
  depth, remain truthfully `partially_ingested`, and use
  `maintain_family_adapter` rather than appearing in the priority backlog.
- Recorded six byte-identical 2026-27 handoff IDs as duplicate aliases. Their
  `latest.json` SHA-256 values match the named canonical registry entries.
- Classified the HTML-only PBS downloads index as reference material.
- Excluded maintenance-only family rows from the generated priority backlog.

No fact, source document, node, edge, authoritative total, citation, or UI/API
code was changed.

## Evidence and counts

| check | before | after |
|---|---:|---:|
| facts | 289,315 | 289,315 |
| source documents | 133 | 133 |
| nodes | 222,575 | 222,575 |
| node edges | 0 | 0 |
| PBS facts with parsed origin lineage | 0 reported per source | 17,482 across 60 retained origin IDs |
| generalized PBS rows in priority top 40 | 40 | 0 |

Of the 60 retained origin IDs, 59 current registry sources are represented as
family-maintenance rows; one older ID is deliberately classified through the
existing duplicate-alias rule.

There was no database write, so no database backup or loader run was required.
Repeated coverage-audit runs produced the same status totals and left all four
database counts unchanged. The latest generated audit is
`ops/reports/ingestion-coverage-20260807T174612Z.{json,md}`.

## Validation

- `python -m pytest tests/unit/test_registry_invariants.py -q`: **10 passed**.
- `python scripts/ops/task9_sql_integrity_checks.py`: **0 hard failures, 0
  unresolved duplicates, 0 orphan facts/nodes/edges**. Three pre-existing
  dangling source-document warnings remain unchanged.
- Dashboard audit `20260807T174624Z`: **0 hard failures** across 6 paths and 7
  crosswalk cases; 0 accepted source-rounding warnings.
- Frontend lint/build/tests: not applicable; this maintenance changes only
  lineage configuration, the reporting audit, and its unit coverage.
- Production verification: not required; published facts and live surfaces did
  not change.

## Remaining limitation

`federal_pbs_2026_27_ndia` is a real acquired PDF whose generalized adapter
currently yields zero published facts. It now appears explicitly as
`adapter_broken` rather than being falsely credited by aggregate family facts.
That parser/content issue is not the per-source-lineage maintenance item and is
deferred rather than silently broadened into this change.

## Disposition

The ranked PBS per-source lineage maintenance item is **complete**. The change
is confined to coverage attribution for the already-covered PBS family.
