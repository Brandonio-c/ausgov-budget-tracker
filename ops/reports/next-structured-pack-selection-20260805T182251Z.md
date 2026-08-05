# Next structured pack selection (Task 1)

Generated: 2026-08-05T18:22:51Z.

## Ground truth verified before any implementation

- `git status --short`: clean. Branch `main`. `HEAD` and `origin/main`
  both at `df2bfe1` (verified via `git fetch origin` + `git rev-parse`).
- `ops/reports/next-backlog-ranking-20260805T161821Z.{csv,md}`: the
  existing ranked backlog from the prior milestone. Rank 1
  (`vic_annual_financial_statements_2024_25`) is now complete (loaded,
  UI-exposed, tested, deployed - see `ops/reports/vic-afs-*.md` and
  `ops/reports/adapter-repair-followup-*.md`).
- `ops/reports/current-state.md`: general project overview, no
  family-specific detail affecting this selection.
- `config/canonical_datasets.yaml` does not exist at that path - the
  actual file is `config/lineage/canonical_datasets.yaml`, and it only
  tracks already-fully-ingested canonical datasets, not the
  adapter-repair backlog (confirmed in the prior milestone too).
- `config/procurement_sources.yaml`: confirmed `vic_budget_portfolio_
  outcomes_2024_25`'s registry entry (`id`, `priority: P0`, `source_family:
  handoff_actuals_state`, `formats: [xlsx, xlsx]`), including
  `handoff_repo_source_key: vic_dtf_annual_report_bpo` (the same
  underlying acquisition source shared with the AFS pick).

## Re-ranking against actual filesystem state

Rank 2 in the existing backlog, `vic_budget_portfolio_outcomes_2024_25`,
was re-verified directly rather than assumed current:

- **Still on disk**: `data/raw/state/vic_budget_portfolio_outcomes_2024_25/
  snapshots/20260724T190604Z/files/Budget-portfolio-outcomes-2024-25.xlsx`
  (433,376 bytes).
- **Hash verified**: `sha256sum` of the on-disk file matches
  `latest.json`'s recorded hash
  (`a947a1bfe2dc7ec701acd8c03630010d7f55312d214aaf10cf273ca99809547e`)
  exactly - the file has not changed since acquisition.
- **No existing adapter**: `grep -rn` across `scripts/ingest/` and
  `config/measure-semantics/` for this source_id returns nothing - no
  extractor, loader, or semantic config exists yet.
- **Still the best value/effort choice**: re-inspected all 6 sheets
  (`Cover`, `OS`, `BS`, `CFS`, `SOCE`, `Admin`) in full this time (the
  prior milestone had only partially inspected `OS`/`BS`/`Cover` before
  deferring it). Confirmed: `OS`, `BS`, `CFS` share one consistent,
  cleanly-parseable layout (see Task 3's inventory for the full
  structure) - genuinely structured, xlsx-only, single acquired file, no
  PDF/OCR involved, and this milestone's own effort is exactly what the
  prior ranking anticipated ("needs its own measure definitions" -
  confirmed true: the column/header shape genuinely differs from AFS,
  detailed in Task 3).
- Runners-up reconsidered: `vic_output_performance_measures_2024_25`
  (non-financial KPIs, lower fit), `nsw_economic_data_2026_27`/
  `nsw_historical_fiscal_indicators_2026_27` (duplicate-overlap risk,
  one already confirmed a duplicate), `qld_report_on_state_finances_
  actuals`/`tas_treasurer_annual_financial_reports` (188/90-asset mixed
  pdf/xlsx populations needing their own dedicated per-file triage pass
  before any adapter work - still too large an investigation to also
  fold into this milestone's implementation slot). None of these
  displaced `vic_budget_portfolio_outcomes_2024_25` as the top choice.

## Selected family

**`vic_budget_portfolio_outcomes_2024_25`** - VIC Department of
Treasury and Finance's own Budget Portfolio Outcomes statement,
2024-25: an actual-vs-budget variance comparison (not a multi-year
actuals series like AFS), covering the same department as the
already-loaded AFS family but a genuinely different semantic shape and
therefore a genuinely different, valuable lens (how did the department's
actual result compare to what was budgeted, not just year-over-year).

- **Already on disk**: yes, verified above.
- **Existing loader/extractor**: none - needs a new adapter (not a
  repair).
- **Why top-ranked**: highest-scoring un-adapted, genuinely structured
  (xlsx-only) candidate remaining after AFS; same jurisdiction/
  department as the already-integrated AFS family (so the operational
  pattern - GFS/jurisdiction explorer exposure, dedicated small API,
  1:1 compatibility groups - is already established and battle-tested,
  lowering execution risk); real dashboard value (an actual-vs-budget
  comparison many users would want); low acquisition/access risk (single
  file, already downloaded, hash-verified).
- **Why the runners-up were deferred**: documented above and in the
  existing ranking CSV - non-financial KPIs, duplicate-overlap risk, or
  large per-file triage burden not suited to this milestone's scope.

## Next

Task 2: Cloudflare route triage (scoped to whether this family actually
needs repo-side work). Task 3: build the adapter - genuinely different
from AFS's extractor (Actual/Budget/Variance columns for one year, not
two years of actuals; `$ million` not `$ thousand`; footnote-letter
markers inline in row/header labels, no "Notes" column; no "Source:"
footer line - a lowercase-letter-parenthetical footnote block instead).
