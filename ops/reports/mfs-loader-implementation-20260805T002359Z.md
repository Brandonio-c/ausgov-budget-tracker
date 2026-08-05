# MFS loader implementation (Task 5)

Generated: 2026-08-05T00:23:59Z.

## Measure definitions

`scripts/ingest/migrations/007_mfs_measures.sql` (new migration, applied
via the existing `schema_migrate.migrate()` - auto-discovered by
`discover_file_migrations()`'s glob, no code change needed elsewhere)
seeds all 15 `mfs_*` measure types from `config/measure-semantics/mfs.yaml`
into `measure_definitions`, each with its own dedicated
`compatibility_group` (1:1) and `additive_across_time = 0`.
`root_total_allowed = 0` for the six already-derived balance/stock_balance
measures (`net_operating_balance`, `fiscal_balance`,
`underlying_cash_balance`, `headline_cash_balance`, `net_worth`,
`net_debt`); `view_family` is intentionally `NULL` for all 15 - MFS is
never registered under any existing `mode_to_family` mapping
(`config/compatibility/view_families.yaml`), matching the mission's
"never insert into existing annual additive dashboard trees" requirement
literally.

Verified against a fresh temp database (not the real one): all 15 rows
insert cleanly, correct `compatibility_group`/`root_total_allowed` values
confirmed by direct query.

## A live landmine found and removed first

Before writing the new loader, traced Task 1's stray-preload
contamination to its exact origin: `scripts/ingest/m6_monthly_ocds.py`'s
`export_federal_monthly()` - an M6-milestone "demo" loader (its own code
comment: "Take last 3 FY sheets for manageable monthly grain demo +
coverage") that used `measure_type='monthly_actuals'`,
`compatibility_group='actual_expense'` - confirmed via exact title/
source_id/measure_type/node-naming match. Removed that function and its
`main()` call entirely, plus the orphaned, tracked
`config/mappings/federal_monthly_financial_statements.yaml` mapping file
it generated (same unsafe pattern). Left `export_nsw_ocds()` (this file's
other, unrelated function) untouched. Full pytest suite (261 tests)
still passes - nothing referenced either removed artifact.

## The loader: `scripts/ingest/load_mfs_aggregates.py`

Reads the existing, unmodified `mfs_aggregates.extract_workbook()`
output, classifies every row against `config/measure-semantics/mfs.yaml`
(`build_label_index()` - identical logic to Task 4's staging-audit
script, now the single source of truth the audit script should be
considered a one-off precursor to), and validates each classified row
against every check the mission requires before it may be inserted:

| requirement | how it is enforced |
|---|---|
| measure type exists | `label_index.get(label)` - `None` -> quarantined `unrecognized_label` |
| compatibility group exists | 1:1 with measure_type, guaranteed by migration 007 |
| flow_or_stock classification exists | read directly from the measure's spec |
| period start/end valid | `month_to_period_end()`/`financial_year_start()` - stocks get `period_start=None` by design (no accumulation window), flows require both |
| reporting month valid | must be one of the 12 real month names (the extractor itself already refuses ambiguous bare-month columns before a row ever reaches this loader) |
| period granularity valid | constant `'month'`, matches the `facts.period_granularity` CHECK constraint |
| unit conversion deterministic | `source_unit` must be `$m` or `$b` (the only two ever found - Task 2/4) |
| citation resolves to the real workbook and cell | `locator`/`cached_copy_path` must both be present AND the cached file must exist on disk (`source_file.is_file()`) - not just non-empty strings |

Rows failing any check are written to
`data/staging/quarantine/mfs_load_quarantine.jsonl` with an explicit
`reason`, never inserted.

## Stable fact key

```
{source_family}|{financial_year}|{reporting_month}|{measure_type}|{accounting_basis}|{estimate_status}|{jurisdiction}
```

`measure_type` alone already disambiguates the semantic concept (each
maps 1:1 to a `compatibility_group`) - a separate "semantic label"
component would be redundant, so it is intentionally omitted, consistent
with this repo's other `fact_key` conventions (e.g.
`federal_pbs_programs_all`'s
`source_id|fy|node_name|measure_type|estimate_status`). `jurisdiction`
and `source_family` are both structurally constant for this source
(`Commonwealth`/`federal_mfs_aggregates`) but included per the mission's
explicit requirement and for consistency with datasets that do vary.

## Node model

One node per measure_type (`canonical_key = "federal_mfs_aggregates|node|<measure_type>"`,
named from `measure_definitions.label`), with every financial_year x
reporting_month fact for that measure attached via `fact_nodes`
(`dimension_role='primary'`) - the same "one node, many time-series
facts" pattern already used elsewhere in this schema (e.g. the "Defence"
node across many years). This makes Task 8's API trivial to implement
directly against `facts.measure_type`, without needing tree traversal at
all.

## Revision-conflict detection (Task 6 groundwork)

For every classified, valid row, the loader checks whether a fact with
the same `fact_key` already exists: if none, insert; if one exists with
the same amount (within 1 cent), skip as an idempotent no-op; if one
exists with a **different** amount, refuse to overwrite and quarantine
it as `amount_conflict_with_existing_fact` instead - "never let
processing order decide silently," applied literally. `federal_mfs_
aggregates` has exactly one acquired snapshot (Task 2), so this path
cannot trigger against the real corpus today; Task 6's dedicated report
and synthetic fixture tests exercise it directly.

## Dry-run verified against the real database (read-only)

```
rows_extracted: 3354
rows_quarantined_by_extractor: 27
rows_validated_publishable: 3354
rows_quarantined_by_loader: 0
facts_to_insert: 3354
revision_conflicts_quarantined: 0
```

Matches Task 4's staging audit exactly (3,354 publishable, 0 unrecognized
labels) - the loader's classification logic is the audit script's logic,
now load-bearing rather than advisory.

## A note on migration sequencing

Running the loader even in `--dry-run` mode calls `schema_migrate.
migrate()` first (as every other loader/script in this repo already
does), which applied migration `007_mfs_measures` to the real
`data/facts.db` - 15 new, currently-unreferenced `measure_definitions`
catalog rows, zero fact-data changes (confirmed: `mfs_%` fact count is
still 0 after this). This is schema/catalog metadata, not fact data - the
same unconditional-migration pattern every existing script in this repo
already follows (`build_fixture_db.py`, every `m*.py` loader, etc.), and
is `INSERT OR IGNORE`-idempotent by construction. A fresh backup was
taken immediately afterward (`facts-20260805T002340Z.db`) so a clean
recovery point exists before Task 7's actual fact-data load. Confirmed
no dashboard impact: the live production API's federal actuals total for
FY2024-25 is unchanged (`745,030,000,000`, same as Task 9's verification).

## Next

Task 6: write up the revision/duplicate policy decision explicitly (the
mechanism above) and add synthetic-fixture tests for overlapping/revised
source files. Task 7: back up again immediately before running
`--apply`, run the load once, record before/after counts, run it a
second time and confirm zero new duplicates/nodes/edges.
