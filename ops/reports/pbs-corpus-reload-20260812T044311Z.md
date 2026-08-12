# federal_pbs_programs_all corpus reload and a --db validation-tooling bug (item 5.5b)

Generated: 2026-08-12T04:43:11Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan item 5.5b (surfaced while validating item 5.5's classifier precision fix): the live
`federal_pbs_programs_all` facts had not been reloaded since 2026-07-31 and were stale
relative to the current extractor/classifier code.

## A second, independent bug found before deployment: `task9_sql_integrity_checks.py` ignored `--db`

While validating this reload on a disposable copy, `task9_sql_integrity_checks.py --db
<disposable>` reported **254 hard failures** both before and after cleanup attempts on the
disposable copy - identical to the live database's count, and unaffected by any change
made to the disposable copy. Investigation found `main()` never called
`parser.parse_args()` - in fact the script had **no argparse at all**, so every `--db`
flag ever passed to it anywhere in this repository's history was silently accepted by the
shell but completely ignored by the script, which always opened the hardcoded module-level
`DB_PATH` (the live `data/facts.db`) regardless. A disposable-copy pre-flight check with
this script was therefore never actually validating the disposable copy - it was
re-checking the unchanged live database every time.

Fixed by adding a real `--db` argument (defaulting to the existing `DB_PATH` for backward
compatibility) and an `argv: list[str] | None = None` parameter on `main()`, matching this
repository's established CLI pattern (e.g. `scripts/ingest/run.py`). Updated
`tests/ops/test_task9_sql_integrity_checks.py`'s four existing `main()`-calling tests to
pass `main([])` explicitly (they rely on `monkeypatch.setattr(task9, "DB_PATH", ...)`, not
`--db`, and would otherwise pick up pytest's own `sys.argv`). Added a new dedicated
regression test (`test_main_db_flag_overrides_module_default`) that points `DB_PATH` at a
nonexistent file while passing a real database via `--db`, proving the flag is what gets
used.

**Implication for this program's own history:** every milestone this session that ran
`task9_sql_integrity_checks.py --db <disposable copy>` as a *pre-flight* check before a
live deployment was, in each case, unknowingly re-checking the already-known-good live
database rather than the disposable copy under test. The *post-deployment* checks (run
without `--db`, correctly reading the live database by default) remained valid throughout,
since by that point the live database matched what was being validated. No incorrect
deployment resulted from this - live deployments in this session were independently
validated through `dashboard_depth_audit.py --db <copy>` (which has always correctly
respected `--db`), isolated Python-level diffs, and live API/browser checks - but the task9
pre-flight step specifically was a no-op every time it was used with `--db` in this
session, until this fix.

## The reload itself

Ran `scripts/ingest/reload_pbs_programs_all.py` (validated on a disposable copy first,
byte-identical results to the eventual live run) with a backup taken first
(`facts-20260812T041605Z.db`, baseline 289,318 facts).

The published *row* count (33,291, matching item 5.5's own isolated classifier-diff
prediction exactly) is not the same as the resulting *distinct fact* count after
`fact_key`-based deduplication across the corpus's many overlapping-edition documents.
Comparing exact `fact_key` sets between the backup and the post-reload database found:

| | count |
| --- | ---: |
| Facts before (this source only) | 17,482 |
| Facts after (this source only) | 16,800 |
| Removed | 682 |
| **Added** | **0** |
| Unchanged | 16,800 |

**Every fact remaining after the reload already existed before it.** The reload's entire
net effect was removing 682 facts - all of them among the 158 genuinely garbled labels
item 5.5's classifier precision fix now correctly rejects (verified in that milestone
against real page/table evidence) - with zero new fact content introduced. This is a
narrower, safer, more fully-understood change than the "would nearly double published
facts" framing originally used to scope item 5.5b, which conflated the row-level
`published` count with the deduplicated fact count.

## Stale crosswalk edges: `cleanup_stale_pbs_nodes.py`

The already-live `pbs_programs_all_under_s6` related_breakdown crosswalk (built in an
earlier, pre-this-program milestone) held edges pointing at 158 nodes whose only fact was
one of the 682 removed - a genuine, currently-live graph-integrity defect
(`task9_sql_integrity_checks.py`'s `pbs_crosswalk_children_with_rejected_labels` check,
254 hard failures) that in fact predates this reload entirely: it was already present in
the live database the moment item 5.5's classifier code was committed, and would have been
caught immediately had the `--db` bug above not existed to mask it during that milestone's
own validation.

Used the existing, tested `scripts/ops/cleanup_stale_pbs_nodes.py` (built in an earlier
"Task 8" milestone specifically for this exact scenario - "nodes/edges that pointed at
facts the corrected label-quality classifier no longer accepts"). Captured the pre-reload
fact-bearing node set from the live database before reloading, then ran the cleanup after:

```
before_fact_bearing_count: 2957
after_fact_bearing_count: 2799
newly_orphaned_nodes: 158
stale_edges_removed: 412
stale_nodes_removed: 158
nodes_kept_with_remaining_edges: 0
```

158 orphaned nodes exactly matches item 5.5's own count of genuinely garbled labels -
independent cross-validation that that milestone's classification work was correct.

## Validation

- Disposable-copy dry run: reload + cleanup produced results identical to the eventual
  live run at every step (published row counts, cleanup counts, before/after `fact_key`
  deltas).
- `task9_sql_integrity_checks.py` (now correctly `--db`-aware): 254 hard failures before
  cleanup, **0** after, both on the disposable copy and, after live deployment, on the
  live database.
- `dashboard_depth_audit.py`: root totals for `federal_actuals_*` (the canonical GFS
  tree) are **completely unchanged** - this reload only affects `mode='budget'`
  projections, as expected for a `budget_expense`-compatibility-group source. Root totals
  for `federal_budget_2023_24`, `federal_budget_2024_25` and `federal_budget_latest`
  decreased (e.g. FY2023-24: $1,818,520,572,000 -> $1,787,437,333,000, a
  $31,083,239,000 reduction) - a fully explained, reviewed, and now fixture-recorded
  change: removing 158 garbled labels' inflated dollar contributions outweighs the (zero,
  per the fact-key analysis above) new content added. Citation completeness remained
  100% before and after.
- Spot-checked a random sample of remaining `federal_pbs_programs_all` facts directly
  against their locators - all sensible, correctly-labeled program/component figures.
- Reviewed golden fixture (`tests/fixtures/dashboard_projection/baseline.json`) updated
  via `--write-fixture` and re-verified `fixture_matches: true`.
- Two tests with hardcoded pre-reload FY2023-24 root totals
  (`tests/api/test_historical_pbs_s6_crosswalk.py`,
  `tests/api/test_historical_related_evidence_isolation.py`) updated with an inline
  explanation of why the expected value changed - the guarantees those tests exist to
  protect (crosswalk edges and isolated historical-evidence measures cannot move the
  `mode='budget'` root total) still hold; only the correct baseline itself changed.
- New regression test for the `--db` fix (`test_main_db_flag_overrides_module_default`).
- Full backend suite: 643 passed, 0 unexplained regressions (the 2 expected-value updates
  above were the only failures, both resolved as documented).

## Data impact

`data/facts.db`: -682 facts, -158 nodes, -412 edges, all confined to
`federal_pbs_programs_all` and its `pbs_programs_all_under_s6` crosswalk. No other source,
canonical fact, or unrelated edge changed. Backup taken before any write.

## Dashboard impact

Once deployed (see the production-deployment-lag finding recorded elsewhere in this
ledger), the federal "budget" mode for FY2023-24/2024-25/latest stops presenting 158
genuinely garbled label fragments as if they were real PBS program facts, and the
already-live PBS-under-Statement-6 crosswalk no longer exposes those same fragments as
related detail. The canonical `federal_actuals_*` (GFS) tree is entirely unaffected.

## Remaining risks

None identified for this specific reload. The general pattern this milestone establishes -
run `reload_pbs_programs_all.py` then `cleanup_stale_pbs_nodes.py` together whenever the
classifier changes - should be followed for any future classifier precision work on this
source, to avoid recreating the same 254-hard-failure window this milestone found and
closed.
