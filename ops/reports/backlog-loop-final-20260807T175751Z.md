# Backlog loop final report (20260807T175751Z)

## 1. Canonical queue and final disposition

Source queue: `ops/reports/backlog-loop-queue-20260807T172453Z.md`, derived
from the consolidated ranking and later completion evidence. QLD MYFER was
already complete when the loop queue was created and was not reopened.

| loop order | item | type | final disposition |
|---:|---|---|---|
| 1 | TAS TAFR narrative era | PDF | Safe 2007-08–2009-10 transition cluster complete; incompatible 2003-04–2006-07 prose/chart generation explicitly deferred. |
| 2 | VIC Output Performance | xlsx | Seven `$ million` total-output-cost rows complete; 70 non-dollar KPIs deferred. |
| 3 | Generalized PBS per-source lineage | maintenance | Complete; existing citations now drive truthful per-source audit counts. |
| 4 | QLD Consolidated Fund Financial Reports | PDF | All 46 inventoried and text-tested; deferred to an isolated cash/Public Account product milestone. |
| 5 | QLD on-time payment reports | CSV | All 42 assets/header shapes inventoried; deferred to contextual procurement/compliance work. |
| 6 | VIC AFS six deferred sheets | xlsx | All six directly inspected; split/deferred because they are at least four distinct semantic products, not one adapter family. |
| 7 | QLD CFFR bulletins | PDF | Superseded as a duplicate: the 25 CFFR files are Consolidated Fund Financial Reports already counted in item 4, not Commonwealth-relations reports. |
| 8 | Pre-2019 FBO | PDF/layout | All 21 FBOs text-tested; deferred after the existing adapter demonstrably selected unrelated revenue tables. |
| 9 | 1985-87 Trove hunt | external acquisition | External; no verified local Budget Paper No. 1 / Statement No. 2 source. |
| 10 | Cloudflare nested hard route | external infrastructure | External; no selected data item depended on it. |

The first item processed was **TAS TAFR narrative-era**. The last in-repository
item processed was **historical pre-2019 FBO layout triage**. The final two
actionable queue entries are external only.

## 2. Files changed across the loop

Implementation/config/test files:

- `config/lineage/canonical_datasets.yaml`
- `config/measure-semantics/tas_tafr_narrative_backfill.yaml`
- `config/measure-semantics/vic_output_performance.yaml`
- `scripts/ingest/extractors/tas_tafr_narrative_backfill.py`
- `scripts/ingest/reload_tas_tafr_narrative_backfill.py`
- `scripts/ingest/extractors/vic_output_performance.py`
- `scripts/ingest/reload_vic_output_performance.py`
- `scripts/ingest/migrations/016_vic_output_performance_measures.sql`
- `scripts/ingest/ingestion_coverage_audit.py`
- `tests/ingest/test_tas_tafr_narrative_backfill.py`
- `tests/ingest/test_vic_output_performance.py`
- `tests/unit/test_registry_invariants.py`

Queue/inventory/implementation reports:

- `backlog-loop-queue-20260807T172453Z.md`
- `tas-tafr-narrative-inventory-20260807T173100Z.{csv,md}` and
  `tas-tafr-narrative-implementation-20260807T173331Z.md`
- `vic-output-performance-inventory-20260807T173700Z.{csv,md}` and
  `vic-output-performance-implementation-20260807T173750Z.md`
- `pbs-per-source-lineage-implementation-20260807T174640Z.md`
- `qld-consolidated-fund-inventory-20260807T174900Z.md`
- `qld-on-time-payment-inventory-20260807T175100Z.md`
- `vic-afs-deferred-sheets-inventory-20260807T175300Z.md`
- `qld-cffr-identity-triage-20260807T175500Z.md`
- `fbo-historical-archive-triage-20260807T175900Z.md`
- this final report.

Generated evidence retained in the loop consists of coverage audits
`20260807T173300Z`, `20260807T173725Z`, and `20260807T174612Z`, plus dashboard
audits `20260807T173313Z`, `20260807T173731Z`, and `20260807T174624Z` (each as
JSON and Markdown).

No facts database, raw file, staging file, backup, WAL/SHM file, browser
profile, or frontend build output is committed.

## 3. Database before/after by item

| item | facts | source documents | nodes | edges |
|---|---:|---:|---:|---:|
| TAS TAFR | 289,271 → 289,301 (+30) | 132 → 132 | 222,568 → 222,568 | 0 → 0 |
| VIC Output Performance | 289,301 → 289,315 (+14) | 132 → 133 (+1) | 222,568 → 222,575 (+7) | 0 → 0 |
| PBS lineage maintenance | 289,315 → 289,315 | 133 → 133 | 222,575 → 222,575 | 0 → 0 |
| Each inventory/deferral/supersession item | 289,315 → 289,315 | 133 → 133 | 222,575 → 222,575 | 0 → 0 |

Backups were made before both writes:

- `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T173230Z.db`
- `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T173656Z.db`

Both have adjacent backup reports. No backup was needed for read-only
maintenance/inventory items.

## 4. Published and quarantined rows

| item | extracted/selected | published | quarantined | explicitly deferred |
|---|---:|---:|---:|---:|
| TAS TAFR transition cluster | 30 | 30 | 0 | four older editions |
| VIC total output costs | 14 | 14 | 0 | 70 non-dollar KPI rows |
| PBS lineage | 17,482 existing facts attributed across 60 retained origin IDs | no new facts | 0 | one separate zero-yield NDIA source noted |
| Remaining inventory items | read-only | 0 | 0 | as itemized in section 1 |

No ambiguous PDF row was guessed into the database.

## 5. Idempotency

- TAS repeat: 0 inserts/updates/supersessions/nodes/edges, 30 skips.
- VIC repeat: 0 inserts/updates/supersessions/nodes/edges, 14 skips.
- PBS audit repeat: identical status totals and unchanged database counts.
- Read-only triage items performed no load and therefore have no applicable
  loader idempotency operation.

## 6. Integrity and coverage

Final Task 9 SQL integrity result: **0 hard failures, 0 unresolved duplicate
facts, 0 duplicate edges, and 0 orphan facts/nodes/edges**. Six reviewed false
positive duplicate groups and three pre-existing dangling source-document
warnings remain documented and unchanged.

The final coverage audit (`20260807T174612Z`) reports 52 fully ingested, 59
partially ingested, 174 adapter-missing, 29 adapter-broken, 29 duplicate, 5
reference-only, 7 officially unavailable, and 12 not acquired registry rows.
The previous top-40 PBS zero-fact tie is gone. Six byte-identical legacy PBS
IDs are explicit aliases and the HTML-only index is reference material.

## 7. Pytest

- PBS maintenance targeted invariant suite: **10 passed**.
- Full suite in the repository's Conda environment: **553 passed, 1 dependency
  deprecation warning in 115.29 seconds**.
- An initial full-suite attempt in the active base environment failed during
  collection because that environment lacks declared runtime dependencies
  (`pandas`, `duckdb`). It was rerun with
  `conda run -n ausgov-budget-tracker`, which is the repository's configured
  environment, and passed completely.

Earlier per-item targeted evidence: TAS 7 new tests and 46 targeted tests
passed; VIC 4 new tests and 69 targeted tests passed.

## 8. Frontend lint/build/test

- `npm run lint:ci`: passed at the checked-in baseline (**25 errors, 13
  warnings**, exactly matching the accepted baseline).
- `npm run build`: passed; 12 static pages generated.
- `npm run test:e2e`: first invocation correctly reported connection refused
  because the required static server was not running. After serving the built
  export under `/ausgov-budget-tracker/` on port 3313 and starting the real
  backend with matching CORS on port 8000: **21/21 passed in 42.5 seconds**.
- Both temporary test servers were stopped after the run.

## 9. Dashboard audits

- TAS audit `20260807T173313Z`: 0 hard failures, 0 rounding warnings.
- VIC audit `20260807T173731Z`: 0 hard failures, 0 rounding warnings.
- PBS/no-data-change audit `20260807T174624Z`: 0 hard failures across 6 paths
  and 7 crosswalk cases, 0 rounding warnings.

## 10. Production verification

- TAS: the public API returned new 2007-08 budget/actual revenue facts with
  exact file/page/row citations; bind-mounted DB required no rebuild/deploy.
- VIC: the public compatibility-scoped tree returned seven output nodes and
  the $459.3 million actual total with complete workbook citations; no
  container rebuild was needed.
- PBS maintenance and all later triage items changed no live facts or route,
  so production deployment/verification was not required.
- The final real-browser suite exercised the built frontend against the real
  local database/API, including the new QLD MYFER explorer test.

## 11. Unresolved limitations and deferred work

- TAS 2003-04–2006-07 predates the AASB 1049 recast and remains unsafe to
  merge into the recast series without a bridge.
- VIC Output Performance's 70 non-dollar KPIs need separate typed semantics.
- `federal_pbs_2026_27_ndia` is acquired but yields zero facts and now appears
  truthfully as `adapter_broken`; it was not a ranked family in this loop.
- QLD Consolidated Fund needs an isolated cash/Public Account period/vintage
  product.
- QLD on-time payments need a contextual compliance product.
- VIC AFS remainder needs separately ranked subfamilies; the administered
  statement pair is the smallest coherent next candidate.
- Pre-2019 FBO needs generation-specific page/table parsers; the current broad
  adapter is proven unsafe on those consolidated documents.

These are explicit future backlog/refinement notes, not silently claimed
complete ingestion.

## 12. External-only remainder and Cloudflare

There is no unaddressed item left in the canonical in-repository loop: every
ranked item was completed, explicitly deferred with evidence, or superseded.
The only remaining active queue actions are external:

1. acquire verified 1985-86/1986-87 Budget Paper No. 1 / Statement No. 2
   function-series material via Trove or parliamentary papers; and
2. inspect/purge the Cloudflare dashboard's nested hard-navigation cache/rule
   state or escalate to Cloudflare support.

Cloudflare was not in scope for any data item, did not block any adapter or
validation run, and received no repository workaround.

## 13. Classification of the last/next work

The last in-repository work was **PDF/layout triage** (pre-2019 FBO). The next
queue actions are **external acquisition/infrastructure**, not structured-data
or PDF implementation inside this repository.

## 14. Commits

The loop produced eleven focused commits from queue construction through FBO
triage, followed by this final close-out commit. The implementation milestones
are `4bb91a8`/`76df7f1` (TAS), `3fc2424`/`be83dd4` (VIC), and `25fd223` (PBS
lineage); the remaining commits are bounded queue/disposition reports.

## 15. Working tree and branch

The final target is clean `main`; `data/facts.db` remains intentionally
uncommitted/ignored. At report creation, local `main` and `origin/main` both
resolved to `aeacee3`; this report's final commit advances local `main` by one
commit until pushed.

## 16. Push command

```bash
git push origin main
```
