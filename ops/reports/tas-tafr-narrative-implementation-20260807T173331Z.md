# TAS TAFR narrative-era implementation

Generated: 2026-08-07T17:33:31Z  
Queue item: 1 (highest-ranked open item after QLD MYFER completion)  
Status: **complete for the safe transition cluster; four earlier editions explicitly deferred**

## Selection and changes

The seven-edition 2003-04 to 2009-10 corpus is fully text-extractable and
requires no OCR. Direct page inspection selected 2007-08, 2008-09, and
2009-10 because they expose labelled General Government Sector tables with
explicit Original Budget and final Actual columns. One edition-manifest-driven
adapter publishes revenue, expenses, net operating balance, fiscal balance,
and net debt into the existing `tas_ggs_*` compatibility groups.

The 2003-04 through 2006-07 prose/chart editions remain deferred. The 2007-08
source explicitly says the affected time series was recast for AASB 1049, so
loading the older printed values into the recast compatibility groups would be
an unsupported comparison.

## Database and idempotency

Backup before write:
`/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T173230Z.db`
with report `facts-20260807T173230Z.backup-report.json`; backup counts matched
the pre-load database and its integrity check passed.

| object | before | after | delta |
|---|---:|---:|---:|
| facts | 289,271 | 289,301 | +30 |
| source documents | 132 | 132 | 0 |
| nodes | 222,568 | 222,568 | 0 |
| node edges | 0 | 0 | 0 |

First load: 30 extracted, 30 published, 0 quarantined, 30 facts inserted,
0 updated, 0 superseded, 0 nodes, and 0 edges. Second load: 0 facts/nodes/edges
inserted, 30 idempotent skips, and 0 semantic changes.

## Validation

- New adapter tests: 7 passed.
- Targeted TAS ingestion/API suite: 46 passed, one dependency warning.
- SQL integrity: 0 hard failures, unresolved duplicates, orphan facts, orphan
  nodes, or orphan edges.
- Ingestion coverage statuses remained unchanged because this extends an
  already-covered source family.
- New quarantine rows: 0; global pre-existing quarantine count: 36,417.
- Dashboard audit `20260807T173313Z`: six paths and seven PBS crosswalk cases,
  0 hard failures and 0 rounding warnings.
- Frontend lint/build/browser tests: not rerun for this item because no API
  schema, route, or frontend file changed. The existing TAS GGS endpoint and
  explorer automatically expose the extended years.
- Production: no rebuild or deploy required; `data/facts.db` is bind-mounted
  read-only. The public API returned the new 2007-08 budget and actual revenue
  facts with exact file/page/row citations.

## Artifacts

- `ops/reports/tas-tafr-narrative-inventory-20260807T173100Z.{csv,md}`
- `config/measure-semantics/tas_tafr_narrative_backfill.yaml`
- `scripts/ingest/extractors/tas_tafr_narrative_backfill.py`
- `scripts/ingest/reload_tas_tafr_narrative_backfill.py`
- `tests/ingest/test_tas_tafr_narrative_backfill.py`
