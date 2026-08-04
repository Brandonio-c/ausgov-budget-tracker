# MFS-aggregates milestone — baseline (Task 1)

Generated: 2026-08-04T23:36:25Z. Starting point: `main` at `d7bad6d`
(local matched `origin/main` exactly; working tree clean).

## CI status found on `d7bad6d`: failing

`gh run watch` on the push that produced `d7bad6d` showed the `python`
job failing at the `Unit tests` step (`frontend` and `e2e` both passed).
Root cause: `tests/unit/test_registry_invariants.py` had three tests that
manually wrote `conn = sqlite3.connect(...) if FACTS_DB.exists() else
None` instead of using the file's own `facts_conn` fixture (which skips
cleanly when `data/facts.db` is absent). In CI, where the real database
never exists, this silently treated every facts.db-only reference as
nonexistent instead of skipping - a false-positive guaranteed to fail on
every push. This was invisible locally because `data/facts.db` is always
present here.

**Fixed** in commit `e5e93cd`, by switching all three tests to depend on
`facts_conn` directly. Verified two ways: (1) normally, against the real
database - still 9/9 passing; (2) with `data/facts.db` temporarily moved
aside to faithfully reproduce CI's actual environment - the three tests
now skip cleanly instead of failing, then the file was restored.
Per this milestone's explicit "do not push until every acceptance
criterion passes" instruction, this fix has **not** been pushed yet - its
effect on the real CI run will be confirmed at the end, in the single
final push.

## Urgent finding: live production contamination, already present

While recording baseline measure definitions (as this task requires),
288 facts turned up under `measure_type='monthly_actuals'`,
`compatibility_group='actual_expense'` - **the same additive
compatibility group as annual GFS/PBS actual expense data** - from
`source_key='federal_monthly_financial_statements'`. This directly
contradicts the mission's own framing ("the extractor was deliberately
not loaded"); some of it clearly was, incompletely, at some earlier
point (`extractor_run_id` and `canonical_dataset_id` both NULL on every
row - not a normal pipeline run).

**Confirmed live, not just theoretical.** For every financial year except
2025-26, `_preferred_basis()` in
`src/backend/routers/v2/dashboard.py` resolves to `'gfs'` for federal
actuals (both `gfs` and `accrual` bases exist), and its `accounting_basis
= ?` filter happens to exclude these `accrual`-basis MFS rows entirely -
accidental protection, not by design. **FY2025-26 has no GFS-basis data
yet**, so `_preferred_basis()` falls back to `'accrual'`, which *does*
match these rows. A direct query against the live, running production
container (`ausgov-budget-tracker-backend-1`, bind-mounted to this same
`data/facts.db`) confirmed 12 `"<label> | July"` nodes - a single month's
figures - summed straight into the federal actuals root total for
FY2025-26, with `root_total_allowed: true` and no warning. This is
exactly the class of defect this milestone's non-negotiable constraints
exist to prevent, and it was already live in production before this
milestone's own load work began.

### Remediation

1. Backed up `data/facts.db` first
   (`scripts/ops/backup_facts_db.py` → `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260804T233110Z.db`).
2. Verified the stray load was fully isolated before touching anything:
   exactly one `source_document` (id 26, title literally "Federal GGS
   monthly operating statement (July expenses)" - an artifact of a
   partial run), all 288 facts under it share the single
   `monthly_actuals` measure type (no other measure types mixed in), and
   zero `breakdown_edges` reference any of its 22 nodes.
3. `scripts/ops/cleanup_stray_mfs_preload.py` (dry-run then `--apply`)
   removed all 288 facts, their `fact_nodes` rows, the 22 nodes, and the
   source_document. A second `--apply` run reports `already_clean` -
   idempotent.
4. Re-queried the live production API: FY2025-26 federal actuals root
   value dropped from `795,072,121,000` to `724,901,922,000` (exactly the
   removed July contribution), no `"| July"` nodes remain.
5. `task9_sql_integrity_checks.py`: `hard_failures: 0` both before and
   after the cleanup.

### Critical note for Task 3 (semantic model)

`measure_definitions` already has a row `monthly_actuals →
actual_expense`. **This existing mapping must not be reused for the
MFS reload** - it is precisely the unsafe grouping this milestone exists
to fix. New MFS measure types need their own, separate compatibility
group(s), distinct from `actual_expense`/`budget_expense`.

## Baseline validation

`python -m pytest tests -q`: **261 passed**, 1 warning (pre-existing
`httpx`/`starlette` deprecation notice, unrelated).

`task9_sql_integrity_checks.py`: **`hard_failures: 0`** (both before and
after the stray-MFS cleanup - the cleanup touched only the isolated
stray dataset, nothing any existing check or test depends on).

## Database counts

| metric | before stray-MFS cleanup | after stray-MFS cleanup | delta |
|---|---:|---:|---:|
| facts | 285,547 | 285,259 | −288 |
| nodes | 222,516 | 222,494 | −22 |
| fact_nodes | 285,547 | 285,259 | −288 |
| breakdown_edges | 14,167 | 14,167 | 0 |
| source_documents | 127 | 126 | −1 |
| measure_definitions | 25 | 25 | 0 |
| facts_pending_attribution | 36,417 | 36,417 | 0 |

## Existing measure_definitions (pre-MFS-milestone)

| measure_type | compatibility_group |
|---|---|
| actual_accrual_expense | actual_expense |
| gfs_expense | actual_expense |
| monthly_actuals | actual_expense |
| appropriation_authority | authority |
| budget_estimate | budget_expense |
| revised_estimate | budget_expense |
| cash_payment | cash_outflow |
| invoice_paid | cash_outflow |
| participant_payment | cash_outflow |
| payment_timing_disclosure | cash_outflow |
| contract_value | commitment |
| grant_award | commitment |
| recipient_count | count |
| gdp_chain_volume | gdp |
| gdp_current | gdp |
| gsp_current | gdp |
| tax_to_gdp_ratio | gdp |
| aofm_cgs_outstanding | gfs_liability |
| borrowing_authority_debt_outstanding | gfs_liability |
| gfs_liability | gfs_liability |
| gross_debt_face_value | gfs_liability |
| net_debt | gfs_liability |
| superannuation_liability | gfs_liability |
| gfs_revenue | gfs_revenue |
| tax_revenue | gfs_revenue |

## Relevant existing schema

`facts` already has `period_start`, `period_end`, `period_granularity`,
`accounting_basis`, `estimate_status`, `observation_date`,
`publication_date`, `valuation_basis`, `amount_granularity`, `scale`,
`price_basis`, `source_budget_year`, `quality_status`,
`quality_flags_json`, `view_family` - the schema already anticipates
period-endpoint and stock/flow-adjacent metadata; `period_start`/
`period_end` are **not currently populated by anything** (0 non-null rows
repo-wide before this milestone). `period_granularity` already has both
`financial_year` and `month` as distinct values in use.

## Next

Task 2: inventory the real MFS corpus (all acquired workbook/table
shapes), before defining the formal semantic model in Task 3.
