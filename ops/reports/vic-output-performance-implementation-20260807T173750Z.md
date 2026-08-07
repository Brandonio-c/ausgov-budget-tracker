# VIC Output Performance implementation

Generated: 2026-08-07T17:37:50Z  
Queue item: 2  
Status: **complete for dollar output costs; non-dollar KPIs explicitly deferred**

## Selection

The one acquired workbook contains 77 performance rows across seven output
sheets. The selected coherent subfamily is one `$ million` `Total output cost`
row per sheet, each with numeric 2024-25 actual and target values. This yields
14 facts. Target is represented as `budget`, while actual remains `actual`.

The remaining 70 rows mix counts, dates, percentages, ratios, threshold
strings, and unavailable values. They remain deferred rather than coerced into
dollar amounts or a lossy generic quantity type.

## Database and idempotency

Backup: `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T173656Z.db`
and its adjacent backup report.

| object | before | after | delta |
|---|---:|---:|---:|
| facts | 289,301 | 289,315 | +14 |
| source documents | 132 | 133 | +1 |
| nodes | 222,568 | 222,575 | +7 |
| node edges | 0 | 0 | 0 |

First load: 14 extracted/published, 0 quarantined, 14 facts and seven output
nodes inserted. Repeat loads: 0 facts/nodes/edges inserted, 14 idempotent
skips, 0 updates, supersessions, conflicts, or semantic changes.

## Validation

- New tests: 4 passed.
- Targeted VIC ingestion/API suite: 69 passed, one dependency warning.
- SQL integrity: 0 hard failures, unresolved duplicates, orphans, or graph
  contamination.
- Coverage: source moved from `adapter_missing` to `fully_ingested`; totals are
  now 52 fully ingested and 164 adapter missing.
- Dashboard audit `20260807T173731Z`: six paths and seven PBS crosswalk cases,
  0 hard failures and 0 rounding warnings.
- Frontend: not changed; no frontend build/deploy required. The family remains
  isolated from whole-of-government additive trees.
- Production: no container rebuild was required because the database is
  bind-mounted. The public compatibility-guarded tree endpoint returns seven
  actual output nodes totalling $459.3 million with complete workbook sheet and
  cell citations. Source landing and canonical resource URLs are populated.

## Artifacts

- `ops/reports/vic-output-performance-inventory-20260807T173700Z.{csv,md}`
- `config/measure-semantics/vic_output_performance.yaml`
- `scripts/ingest/migrations/016_vic_output_performance_measures.sql`
- `scripts/ingest/extractors/vic_output_performance.py`
- `scripts/ingest/reload_vic_output_performance.py`
- `tests/ingest/test_vic_output_performance.py`
