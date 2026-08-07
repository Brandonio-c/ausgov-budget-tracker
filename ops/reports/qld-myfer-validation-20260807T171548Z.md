# Queensland MYFER load and validation

Generated: 2026-08-07T17:15:48Z  
Starting commit: `9275d07` (`main`, equal to `origin/main` after fetch)

## Selection and implementation

The selected cluster is the six text-extractable compact General Government
Sector key-fiscal-aggregate tables from MYFER 2015-16, 2016-17, 2017-18,
2018-19, 2019-20, and 2025-26. One reusable adapter publishes the current-year
MYFER/revised column for five common measures: revenue, expenses, net operating
balance, purchases of non-financial assets, and fiscal balance.

The cluster was selected because all six editions share one bounded six-value
row shape and exact PDF/table locators. The adapter includes bounded repairs
for split thousands and split labels. The remaining editions have materially
different detailed-table shapes; the 2002-03 file has an unusable character map
and requires OCR. Borrowing/debt rows were excluded because the concepts and
sector coverage drift across editions. Budget Update publications were not
silently treated as MYFER successors.

MYFER remains isolated from RSF: these are in-year revised estimates, not
estimated-actual or audited-actual outcomes. Each measure has a dedicated
`qld_myfer_*` compatibility group. Revenue, expense, and capital purchases are
financial-year flows; net operating balance and fiscal balance are non-additive
financial-year balances. Native AUD millions are multiplied by 1,000,000.

## Backup and load

The repository backup utility was run before the first write:

- database: `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T165442Z.db`
- report: `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T165442Z.backup-report.json`
- backup `PRAGMA integrity_check`: `ok`
- backup counts: 289,241 facts; 131 source documents; 222,563 nodes; 0 node
  edges; 0 lineage edges

SQLite's online backup produced a logically equivalent, normalized database,
not a byte-identical file; integrity and all pre-write counts were verified.

First-load delta:

| object | before | after | delta |
|---|---:|---:|---:|
| facts | 289,241 | 289,271 | +30 |
| source documents | 131 | 132 | +1 |
| nodes | 222,563 | 222,568 | +5 |
| node edges | 0 | 0 | 0 |
| lineage edges | 0 | 0 | 0 |

The first load extracted and published 30 rows, inserted 30 facts and five
measure nodes, and quarantined zero rows. Each of the five measure types has six
facts. No unrelated fact was updated or superseded.

The repeated loader run reported 30 extracted, 30 published, 0 quarantined,
0 facts inserted, 0 facts updated, 0 facts superseded, 30 idempotent skips,
0 nodes inserted, 0 edges inserted, and 0 semantic changes.

## Validation results

- Targeted Python tests: 13 passed (one dependency deprecation warning).
- Full Python suite: 541 tests collected; exit status 0.
- SQL integrity audit: 0 hard failures, 0 unresolved duplicate facts, 0 orphan
  facts, 0 orphan nodes, and 0 orphan edges. The three previously known dangling
  borrowing source documents remain unchanged.
- Ingestion coverage and lineage audits completed. Canonical status counts did
  not regress; the observed source count increased for the new dedicated source.
- MYFER quarantine: 0. The global 36,417 quarantine records are pre-existing.
- Revenue reconciliation: baseline result retained (`n=9`, 8 warnings); this
  isolated family did not change an authoritative revenue total.
- Debt reconciliation: all seven authorities passed; MYFER debt/borrowing rows
  are out of scope.
- Frontend production build: passed, including TypeScript and all 12 static
  pages.
- Browser suite: 21 passed, including the MYFER revised-estimate vintage,
  period, and exact PDF citation regression test. The first local attempt was
  invalid because the verification origin was not included in
  `CORS_EXTRA_ORIGINS`; rerunning with the documented origin allowance passed.
- `npm run lint`: 25 errors and 13 warnings, all matching the repository's
  pre-existing ESLint baseline. `npm run lint:ci` passed by confirming exactly
  that baseline. No new lint finding was introduced by MYFER.
- Local dashboard audit (`20260807T170708Z`): six paths, seven PBS crosswalk
  cases, 0 hard failures, 0 transport failures, and 0 rounding warnings.
- Production dashboard audit (`20260807T170921Z`): the same six paths and seven
  crosswalk cases, 0 hard failures, 0 transport failures, and 0 rounding
  warnings.

## Production verification

The self-hosted backend image was rebuilt and restarted. The public API now
returns five MYFER measure definitions and six revenue facts; the sampled
2015-16 fact exposes financial-year period, revised-estimate status, publication
vintage, and its exact page/table/row/column locator.

The production frontend build and Wrangler deployment succeeded as Worker
version `3bd6f36e-8c45-4ac0-9f77-1460fe94a789`. The public nested GFS explorer
URL still serves the root application shell, so a public-browser MYFER assertion
cannot reach that page. This reproduces the known external Cloudflare
nested-route defect documented before this milestone; it is not caused by the
MYFER adapter, API, database, or static build. The local production-equivalent
static export passes the MYFER browser test.

Cloudflare therefore stayed external to the ranked MYFER data work. It was used
only for the requested frontend deployment, and its pre-existing nested-route
defect remains unresolved. Strict acceptance items requiring a clean raw
`npm run lint` and successful public nested-route browser verification remain
blocked by those two known baselines; all MYFER-specific and dashboard semantic
checks pass.

## Artifacts

- `ops/reports/myfer-corpus-inventory-20260807T165025Z.csv`
- `ops/reports/myfer-corpus-inventory-20260807T165025Z.md`
- `ops/reports/myfer-semantic-decision-20260807T165025Z.md`
- `config/measure-semantics/qld_myfer.yaml`
- `scripts/ingest/extractors/qld_myfer.py`
- `scripts/ingest/reload_qld_myfer.py`
- `scripts/ingest/migrations/015_qld_myfer_measures.sql`
- `src/backend/routers/v2/qld_myfer.py`
- `src/frontend/app/explorers/gfs/page.tsx`
- `src/frontend/lib/api.ts`
- `tests/ingest/test_qld_myfer.py`
- `tests/api/test_qld_myfer_api.py`
- `src/frontend/tests-e2e/qld-myfer-explorer.spec.ts`
