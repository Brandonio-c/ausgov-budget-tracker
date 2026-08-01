# Final handoff — AusGov Budget Tracker autonomous session, 2026-07-31/08-01

Branch: `agent/continue-data-ingestion-20260731`, based on `main` at `77c346a`.
Ending commit: `f13fab7`. 11 commits, all reviewed above in sequence; none
force-pushed, none amended.

## Commits (in order)

1. `8af1691` fix(audit): correct source availability and legacy snapshot detection
2. `739d45c` chore(ops): add SQLite backup API script and pre-ingestion baseline
3. `6d7255a` feat(ingest): generalize PBS program extraction
4. `c155244` fix(ingest): stop two PBS data-corruption bugs found during full-corpus verification
5. `794f34f` feat(hierarchy): make PBS reload idempotent, purge stale pre-fix facts
6. `16b4459` docs(ops): add ranked adapter-repair queue for the 247 adapter_missing sources
7. `a35ece6` feat(ingest): add tested extractor for Federal MFS Aggregates (Task 5, batch 1)
8. `ab03827` feat(audit): wire canonical_datasets.yaml into coverage audit, add registry invariant tests
9. `f811a65` docs(ops): verify QLD machine-readable resource manifests, re-confirm WAF blocker
10. `848ba04` test(dashboard): add API traversal audit + Playwright UI regression suite
11. `f13fab7` docs(ops): run full Task 9 reconciliation pass

## Database changes

- `data/facts.db` and all raw downloaded data are **intentionally not
  committed** to git (`data/raw/**`, `data/facts.db`, WAL/SHM files are all
  gitignored, per the standing policy) - a clean clone of this branch does
  **not** reproduce the current production dataset. Reproducing it requires
  running the ingestion pipeline against the raw files that are only
  present in this environment's `data/raw/` tree.
- Facts: **324,984 → 321,950** (net **-3,034**). Entirely attributable to
  `federal_pbs_programs_all`: 56,117 pre-existing (partially corrupted, from
  2026-07-24, before any of this session's fixes) → 53,083 verified-correct
  after Task 3's extractor fixes and Task 3.5's `replace_on_reload` purge.
  No other source's fact count changed.
- Facts added: 53,083 (federal PBS, all 63 portfolio PDFs, all with
  complete per-document citations).
- Facts deleted: 56,117 (the same source's pre-fix batch, superseded).
- Facts quarantined: unchanged at 15 in `facts_pending_attribution`
  (pre-existing, not from this session's work - see Task 9 report). PBS's
  own extractor-level quarantine (ambiguous year resolution, never loaded
  into facts.db) went from an unmeasured pre-session baseline to a final,
  clean 8,682 out of 108,502 raw rows, all with the single reason
  `header_column_count_mismatch`.
- Two DB backups were taken (Task 2 baseline before any writes, an earlier
  point before the PBS load) at `/home/vibe-server/backups/ausgov-budget-tracker/`,
  outside the repo, using `scripts/ops/backup_facts_db.py` (SQLite backup
  API, not a naive file copy).
- Zero orphan facts, fact_nodes, node_edges, or breakdown_edges. Zero
  dangling `source_retrieval_id` references. All 131 distinct
  `cached_copy_path` values across every fact in the database resolve to
  real files on disk.

## Coverage-status changes

`ingestion_coverage_audit.py`, registry total 367, both snapshots:

| status | before (Task 1 re-run) | after (Task 6) | delta |
|---|---:|---:|---:|
| fully_ingested | 47 | 47 | 0 |
| partially_ingested | 0 | 81 | +81 |
| adapter_missing | 247 | 169 | -78 |
| adapter_broken | 27 | 24 | -3 |
| duplicate_source | 23 | 23 | 0 |
| officially_unavailable | 7 | 7 | 0 |
| not_acquired | 12 | 12 | 0 |
| reference_only | 4 | 4 | 0 |

The +81/-78/-3 shift is Task 6's real fix: wiring `config/lineage/
canonical_datasets.yaml` into the audit so registry sources served by a
shared family adapter (67 individual PBS portfolio PDFs via
`pbs_programs_all`, plus `abs_taxation_revenue_detail` and
`state_borrowing_authorities` once their `fact_source_keys` were populated)
are correctly classified instead of falling through to `adapter_missing`.
Wiring this in also caught and fixed two pre-existing config bugs (an
over-broad `abs_gfs_` prefix that would have incorrectly credited several
genuinely-uningested ABS releases as `fully_ingested`, and a `wa_wutc`
typo) - both fixed before they could inflate the numbers.

`fully_ingested` staying flat at 47 is correct, not a missed opportunity:
the PBS reclassification correctly lands in `partially_ingested` (matching
the pre-existing intended semantics for aggregator-covered sources), not
`fully_ingested`.

## Dashboard-depth changes

- 63 individual federal PBS portfolio documents that previously had zero
  facts now have real, cited, deduplicated program-expense facts (53,083
  total) - but **these are not yet linked into the Statement 6/portfolio
  hierarchy via `node_edges`** (the pack is declared `edge_kind:
  related_breakdown` with no `related_crosswalk_id`), so they exist as a
  standalone, independently-queryable dataset and won't yet appear as added
  drill-down depth in the dashboard tree. Building the full program-to-S6
  crosswalk across all 26 portfolios is the top-ranked next action below.
- `mfs_aggregates.py` extractor is built, tested, and produces a correct
  staging CSV (3,354 rows across 26 fiscal years) but is **not loaded** into
  facts.db - deferred pending a measure-semantics decision (see Task 5
  report) rather than guessed.
- No change to any existing dashboard branch's totals or root aggregates -
  confirmed via the Task 8 API traversal audit (21,609 nodes visited across
  6 required regression paths, zero citation failures) and Task 9's direct
  SQL reconciliation.

## Tests / builds run

- `pytest tests` (api + unit + integration + ingest): **88 passed**, 0
  failed. Includes 9 new registry invariant tests, PBS layout/year-variant
  tests, and MFS extractor tests added this session.
- `npm run build` (frontend): clean, all 9 routes statically generated, no
  TypeScript errors.
- `npm run lint` (frontend): 34 pre-existing problems (21 errors, 13
  warnings), all in 4 components last touched in `77c346a` (before this
  branch) - zero in this session's own new files.
- `node tests/frontend/test_citation_panel.mjs`: pass.
- `node tests/frontend/test_default_view_regression.mjs`: pre-existing
  failure (stale assertion from before this branch - see Task 9 report).
- Playwright UI regression suite (new, 7 tests, `npm run test:e2e` in
  `src/frontend`): all pass, against a real `next build` static export with
  a real backend against `data/facts.db`.
- `revenue_reconciliation.py`: Commonwealth passes (0.12% variance); 8
  states/territories show a pre-existing 100%-variance warning (detailed
  state tax-revenue sources not fully wired into this reconciliation's
  per-jurisdiction query - not caused by this session).
- `debt_reconciliation.py`: 7/7 pass.
- `quarantine_report.py`: 15, unchanged, all pre-existing/deliberate.
- `ingestion_coverage_lineage.py`: 7 canonical datasets, correctly
  reflecting the Task 6 fixes.

## Blocked external dependencies

- **QLD machine-readable packs** (`qld_sds_machine_readable_2025_26`,
  `qld_budget_bp2_machine_readable_2025_26`,
  `qld_budget_measures_bp4_machine_readable_2025_26`): AWS WAF
  empty-challenge (HTTP 202, empty body) on direct download, re-confirmed
  with a single request each (not a retry storm). This environment has no
  display, no Xvfb, and no interactive human session, so the headed-browser
  acquisition path cannot run here. Resource manifests are fully verified
  (via the CKAN metadata API, not a bypass) and staged at
  `ops/manifests/*.json`.

## Exact next commands (for a human with a real display session)

```bash
conda run -n ausgov-budget-tracker python scripts/procure_browser_session.py \
  --source-id qld_sds_machine_readable_2025_26 \
  --urls-file ops/manifests/qld_sds_machine_readable_2025_26.json

conda run -n ausgov-budget-tracker python scripts/procure_browser_session.py \
  --source-id qld_budget_bp2_machine_readable_2025_26 \
  --urls-file ops/manifests/qld_budget_bp2_machine_readable_2025_26.json

conda run -n ausgov-budget-tracker python scripts/procure_browser_session.py \
  --source-id qld_budget_measures_bp4_machine_readable_2025_26 \
  --urls-file ops/manifests/qld_budget_measures_bp4_machine_readable_2025_26.json
```

## Next five engineering actions, ranked by impact

1. **Link the generalized PBS dataset into the Statement 6 hierarchy.**
   53,083 real, cited facts across 63 portfolio documents currently exist
   as a standalone dataset with no `node_edges` into the existing tree -
   this is the single highest-leverage remaining action to turn already-
   correct data into visible dashboard depth.
2. **Resolve `mfs_aggregates` measure-type/compatibility-group semantics
   and load it.** The extractor is done and tested; the blocker is
   confirming the frontend's aggregation logic actually respects
   `period_granularity = 'year_to_date'` before mixing partial-year MFS
   figures into the same compatibility group as full-year GFS actuals.
3. **Work the ranked Task 4 adapter-repair queue's next families**
   (`ops/reports/adapter-repair-plan-20260731T202041Z.csv`) - structured
   state budget packs and structured local-government files rank highest
   for value-per-effort after MFS.
4. **Acquire the 3 QLD packs with a real browser session** (commands
   above), then build their adapters from the real files - schema
   deliberately not guessed in advance.
5. **Investigate the state-level revenue reconciliation gap** (8/9
   jurisdictions at 100% variance in `revenue_reconciliation.py`) - likely
   a jurisdiction-linkage gap in that script's detail-sum query rather than
   genuinely missing data, given `abs_taxation_revenue_key_tables_2024_25_
   state`/`_territory` are already loaded per Task 6.

Lower-priority cleanup noted but not actioned: the pre-existing
`test_default_view_regression.mjs` failure and the 34 pre-existing frontend
lint issues (both predate this branch, documented in the Task 9 report).
