# Database hygiene and CI hardening — final report

Generated: 2026-08-04T23:09:48Z. git HEAD: `89a501a` (this report's own
commit follows). Baseline: `ops/reports/database-hygiene-baseline-20260804T035826Z.md`
(git `76af563`, 2026-08-04T03:58:26Z).

## Outcome

`scripts/ops/task9_sql_integrity_checks.py` against `data/facts.db`:
**`hard_failures: 0`** (was 283 at baseline), verified locally (Task 8)
and against the live production container + public API (Task 9) — the
same bind-mounted file, so no redeploy was needed.

| metric | baseline | final | delta |
|---|---:|---:|---:|
| facts | 285,574 | 285,547 | −27 |
| nodes | 222,798 | 222,516 | −282 |
| fact_nodes | 285,574 | 285,547 | −27 |
| breakdown_edges | 14,183 | 14,167 | −16 |
| source_documents | 127 | 127 | 0 |
| facts_pending_attribution | 36,391 | 36,417 | +26 |

The −27 facts / +26 pending-attribution reconciles exactly: 26 are the
Defence "Key cost category" facts quarantined by Task 2's root-cause fix
(moved to quarantine, not deleted outright), plus 1 true duplicate fact
deleted by Task 4. The −282 nodes reconciles as 278 orphan nodes (Task 5)
+ 4 bad "Key cost category" node names removed (Task 2).

## Task-by-task summary

**Task 1 — baseline.** Recorded pre-fix counts and `task9` output
(283 hard failures: 5 duplicate_facts, 278 orphan_nodes) before any
change, plus a verified backup of `data/facts.db`.
(`ops/reports/database-hygiene-baseline-20260804T035826Z.md`)

**Task 2 — Defence rounding exception, re-verified and corrected.** The
prior milestone's "verified source-document rounding" characterization of
fact_id 337001 (Defence, 100.52% of parent) was wrong. All 26 facts ever
loaded under 4 mis-labelled "Key cost category" names were individually
traced to their raw source tables — every one came from an unrelated
table (workforce headcount, facilities, Statement of Cash Flows), not the
genuine Key Cost Category table. Root cause:
`pbs_programs_all.py`'s `_clean_defence_program_label()` used a bare,
case-insensitive substring match against 3 generic single words
(`Workforce|Operations|Operating`) across the entire ~180-page document.
Fixed at the root (label-cleaning regex tightened to the 2 verified-safe
multi-word category names; `pbs_label_classifier.py`'s whitelist
tightened; `reload_pbs_programs_all.py` fixed to keep 2-segment context
when classifying), not patched in the database. Result:
`hard_failures: 0, accepted_source_rounding_warnings: 0` — the defect was
removed, not tolerated. The accepted-residual mechanism
(`config/audit/accepted_reconciliation_residuals.yaml` +
`scripts/ops/accepted_residuals.py`) was still built and tested as
specified, and remains at zero entries, ready for a genuine future case.
(`ops/reports/task2-defence-rounding-investigation-20260804T043500Z.md`)

**Task 3 — the five duplicate-fact candidates, investigated individually
against raw source files.** Only 1 of 5 is a true duplicate (QLD QGIP
"Goondiwindi Regional Council / Black Spot", same real funding record
re-published in two overlapping cumulative export files, differing only
by a trailing space). The other 4 are query false positives — genuinely
different real records that a shared, under-specified node made look
identical:
- VIC local government: 425 facts share 1 node per line-item with zero
  per-council dimension (both councils' own real, distinct figures).
- QLD "various individuals": two different funding programs, both also
  showing $0 due to a separate amount-column auto-selection defect.
- QLD Murray Darling: two different real annual expenditures within a
  multi-year grant, both showing the same wrong (whole-of-agreement)
  total due to the same column-selection defect.
- QLD Palm Island: two different sub-programs collapsed by a missing
  sub-program dimension; retained on ambiguity, not deleted speculatively.

Two further upstream defects (missing per-council/per-sub-program node
granularity; column-order-dependent amount-column selection) were found
and documented as deliberately out of scope — fixing them would mean
redesigning two extractors' column semantics, well beyond "resolve 5
duplicates."
(`ops/reports/duplicate-fact-investigation-20260804T044328Z.md`)

**Task 4 — fixed duplicate creation upstream, then cleaned the one real
duplicate.** Root cause: no whitespace normalization on `category`/
`agency` before building `node_name`/`fact_key` in
`scripts/ingest/m7_qld_procurement.py`'s `export_qgip()`. Fixed at the
root. `scripts/ops/cleanup_duplicate_facts.py` (dry-run + apply mode,
idempotent — a second apply pass found nothing left to do) deleted
fact_id 217525, retaining 81987 by an explicit precedence rule.
(`ops/reports/duplicate-cleanup-apply-20260804T123243Z.md`,
`duplicate-cleanup-second-run-20260804T123249Z.md`)

**Task 5 — investigated and cleaned all 278 orphan nodes.** Two distinct
causes, both traced to code: (1) 226 nodes from 7 still-active
borrowing-authority sources, orphaned by naming-scheme drift (authority
name added to node text; an instrument-reclassification fix) combined
with `m_borrowing_authorities.py` deleting facts/fact_nodes on every
reload but never touching the `nodes` table itself — this whole source
family is flat leaf nodes with no folder/edge structure at all, live or
orphaned, so "genuinely unreachable" was safe to delete; (2) 52 nodes
from 3 fully-retired legacy `source_id`s no longer in the pipeline at
all. `scripts/ops/cleanup_orphan_nodes.py` (dry-run + apply, idempotent —
second pass found 0) deleted all 278; `m_borrowing_authorities.py` fixed
to prevent recurrence on future reloads.
(`ops/reports/orphan-node-investigation-20260804T180700Z.md`,
`orphan-node-cleanup-apply-20260804T180845Z.md`)

**Task 6 — strengthened the integrity checker.**
`duplicate_facts()` now returns `node_path`/`source_key` provenance (not
just a mutable `node_id`) so a reviewer can tell a true duplicate from
legitimate independent agreement. New `partition_duplicate_facts()`
splits results into unresolved (hard failure) vs reviewed (informational)
using `scripts/ops/reviewed_duplicates.py`'s declarative registry,
matched by exact identity — any changed field falls through to
unresolved. `main()` also validates both the accepted-residuals and
reviewed-duplicates config files structurally; either being invalid is
itself a hard failure. 28 new fixture-backed tests
(`tests/ops/test_task9_sql_integrity_checks.py`) cover every check.

**Task 7 — promoted every safeguard into CI.** Ruff's checked scope
widened to include `tests/ops`/`tests/ingest`, and the blanket `|| true`
removed (fixed 11 pre-existing unused-variable issues and reviewed ~30
mechanical import-sort fixes diff-by-diff). New CI step runs
`tests/ops`+`tests/ingest` (SQL integrity checker, semantic
dashboard-audit, cleanup scripts, registries) — none of it needs the
production database, since every test builds its own
`schema_migrate()` fixture; the few tests that do need the real database
are marked `@pytest.mark.full_data` (an existing, previously-unused
`pyproject.toml` marker) and excluded via `-m "not full_data"`, not an
ad-hoc file-ignore list. Frontend `npm run lint || true` replaced with a
baseline-gated `lint:ci` (fails only on regression past the committed
25-error/13-warning baseline, all pre-existing React-hooks issues
unrelated to this milestone). New `e2e` CI job builds a purpose-built
fixture database (`scripts/ingest/build_e2e_fixture_db.py`) and runs
`dashboard.spec.ts` (the one existing Playwright spec that deep-links
purely by mode/level/year, with no hardcoded real IDs) against a real
built static export + real backend — verified locally (7/7) before
wiring into CI. The other two Playwright specs hardcode real
production fact_ids and remain local-only checks.

**Task 8 — full local validation.** Full pytest suite (261 tests)
against the real database; `task9` — 0 hard failures; every
reconciliation/coverage script re-run for regression evidence
(quarantine, revenue, debt, lineage, repo-wide coverage) — no new issues,
all deltas explained by this milestone's own fixes; frontend
lint/tsc/build clean; full 16-test Playwright suite (all 3 specs) passes
against the real backend + real data.
(`ops/reports/debt-reconciliation-20260804T230347Z.md`,
`ingestion-coverage-20260804T230420Z.md`, updated
`ingestion-coverage-lineage.md`)

**Task 9 — verified production behavior.** `data/facts.db` and `config/`
are bind-mounted directly from this host into the running
`ausgov-budget-tracker-backend-1` container (port 8010) — no redeploy was
needed for Tasks 2–6's fixes to take effect. Confirmed via the public API
(`https://ausgov-budget-api.vibefactory.app/api/health` → `200 ok`; the
Defence node value matches the locally-verified figure exactly,
$50,175,000,000) and the public frontend
(`https://vibefactory.app/ausgov-budget-tracker/` → `200`, fetches data
client-side so it reflects the fix automatically). Container logs show no
errors. No backend/frontend application code changed functionally this
milestone (only data, config, and CI/test infrastructure), so nothing
else required deployment.

## Deliberately out of scope (found, documented, not fixed here)

- Missing per-council node dimension across `vic_local_govt_financial`
  (425 facts share 1 node for one line item).
- Missing per-sub-program node dimension in `qld_qgip_expenditure`.
- Column-order-dependent amount-column auto-selection defect in
  `m7_qld_procurement.py`'s QGIP export (affects Groups 3/4's reported
  $0 / wrong-total values, independent of the duplicate-fact question).
- Broad procurement-registry coverage gaps
  (`ingestion_coverage_audit.py`: 169 adapter_missing, 24 adapter_broken,
  etc.) — pre-existing, unrelated to duplicate facts/orphan nodes/CI.
- State-level revenue detail coverage gap (`revenue_reconciliation.py`:
  detail_sum=0 for every jurisdiction except Commonwealth) — pre-existing.

Each would require redesigning an extractor's column/node-identity
scheme or ingesting a new dataset family — genuinely new ingestion work,
which this milestone's brief explicitly excluded.

## Commits (this milestone)

```
ac9b3b2 docs(ops): record database hygiene baseline (Task 1)
794ecde fix(audit): scope the Defence source-rounding exception (Task 2)
8e8364f docs(ops): classify duplicate fact candidates (Task 3)
2ae08a6 fix(ingest): prevent duplicate local and QGIP facts (Task 4)
d0469b0 fix(ingest): prevent orphan borrowing-authority nodes (Task 5)
31145a0 feat(ops): strengthen the SQL integrity checker (Task 6)
7a683ba ci: enforce semantic and database integrity gates (Task 7)
89a501a test(audit): full local validation pass (Task 8)
```
