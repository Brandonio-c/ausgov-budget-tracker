# MFS extractor staging audit (Task 4)

Generated: 2026-08-05T00:04:01Z. Full row-level detail:
`ops/reports/mfs-staging-audit-20260805T000401Z.csv` (3,381 rows: 3,354
publishable + 27 quarantined). Produced by `scripts/ops/mfs_staging_audit.py`,
which runs the existing, unmodified
`scripts/ingest/extractors/mfs_aggregates.py` against the full corpus and
classifies every row against Task 3's semantic model
(`config/measure-semantics/mfs.yaml`). **No writes to `data/facts.db`.**

## Headline result: every publishable row now resolves to exactly one measure type

The first audit run found 88 rows misclassified as `unrecognized_label`
(3 raw label strings the extractor legitimately produces but that
Task 3's initial `source_label_variants` lists hadn't enumerated yet -
each is the result of the extractor's `TRAILING_FOOTNOTE_MARK` regex
stripping only the *last* of two footnote markers, or a single-letter
footnote stripping to a bare string):

| raw label found | measure_type | fix |
|---|---|---|
| `Operating Result (a)` | `mfs_ytd_net_operating_balance` | added to variants |
| `Fiscal Balance (b)` | `mfs_ytd_fiscal_balance` | added to variants |
| `less Payments` (bare) | `mfs_ytd_payments` | added to variants |

`config/measure-semantics/mfs.yaml` updated accordingly (amended, not a
new commit - Task 3's decision table gets this correction as part of
verifying it against the real, complete corpus, exactly as Task 4 is
meant to do). Re-running the audit after the fix: **3,354/3,354
publishable rows resolve to exactly one measure_type; zero unrecognized
labels; zero duplicate (financial_year, reporting_month, raw_label)
keys.**

## The 27 quarantined rows: bare-month ambiguity, confirmed in two separate years

All 27 quarantines are `non_ytd_column_not_supported` - a bare (non-YTD-
prefixed) month column, exactly the ambiguity Task 3's
`bare_month_ambiguity_quarantined` rule anticipates. Precise breakdown
(refines Task 2's initial finding, which only manually sampled a few
years and reported "none found for August-May" - Task 4's full run over
every column found two more instances):

| financial_year | bare month | rows affected |
|---|---|---:|
| 2000-01 | August | 9 (one per measure published that year) |
| 2002-03 | September | 9 |
| 2002-03 | March | 9 |

**27 = 9 + 9 + 9.** Both years are genuine source-publication quirks (a
single month's header text missing its "YTD" qualifier in the original
Treasury-published workbook), not a systematic era-wide pattern - every
other column in both of those same sheets is correctly YTD-labelled. The
existing extractor already refuses to guess these (skips them entirely,
neither published nor silently treated as YTD); this audit confirms that
refusal is correct and complete across the whole corpus, not just the
one case Task 2 happened to sample.

## Explicit checks required by Task 4

- **Million-vs-billion conversion**: confirmed correct end-to-end. Units
  transition from `$m` to `$b` starting FY2024-25 (Task 2's finding);
  the extractor's existing `UNIT_SCALE` dict converts both correctly,
  applied per-column (verified: FY2024-25/2025-26 rows in the staged CSV
  carry `source_unit=$b` and an `amount` scaled by 1,000,000,000, while
  every prior year carries `source_unit=$m` scaled by 1,000,000).
- **Negative values and parentheses**: 1,156 of the 3,354 publishable
  rows are negative (e.g. `Operating Result` for several YTD months of
  FY2000-01). Confirmed these are read as correct native negative floats
  by pandas/openpyxl (Excel's accounting-format parentheses are a
  *display* format over a numeric cell, not a string) - no sign-parsing
  defect found.
- **Blank, dash, and nil values**: the extractor's `pd.isna(val):
  continue` (blank/NaN cells) and `try: float(val) ... except
  (TypeError, ValueError): continue` (any non-numeric cell, e.g. a
  literal `"-"` placeholder) both skip silently rather than zero-filling
  - confirmed by construction; no row in the staged output has a
  fabricated zero standing in for a blank source cell.
- **Duplicated reporting months / repeated headers**: zero
  `(financial_year, reporting_month, raw_label)` duplicates found across
  all 3,354 rows (`duplicated_keys=0`).
- **Overwritten historical revisions / multiple files covering the same
  month**: `federal_mfs_aggregates` has exactly one acquired snapshot (no
  revision history to reconcile within this source). The legacy,
  superseded `federal_monthly_financial_statements` bulk acquisition
  (Task 1/Task 2) also contains a `6.-aggregates.xlsx` - confirmed
  **byte-identical** (SHA-256
  `8b74f69be62ff34a04a18ac4455cc0c706034368d22dbcf3126200d3a0c6ca96`) to
  the canonical `federal_mfs_aggregates` copy: a confirmed identical
  republish, not a competing revision. Using only the canonical source
  loses no information.
- **Bare-month ambiguity**: see above - real, found in 2 years, correctly
  quarantined by the existing extractor.
- **Label drift between editions / rows that change economic meaning
  despite similar wording**: exhaustively covered in Task 2/3 (Revenue/
  Income, Operating Result/Net operating balance, Assets/Total assets,
  Net Assets/Net worth, the Receipts/Payments/Net-Future-Fund-earnings
  disclosure changes). This audit's 3-label fix above is a direct,
  concrete instance of this same class of drift (footnote-stripping
  producing a label variant not yet enumerated), caught by running the
  real extractor rather than assumed from manual sampling.

## Conclusion: safe to proceed to Task 5

Every one of the 3,354 publishable rows now has an explicit, non-guessed
measure_type, flow_or_stock classification, period_start/period_end,
compatibility_group, and citation locator (verified in the CSV). Nothing
is loaded by this task - Task 5 implements the actual measure_definitions
rows and loader safeguards before any write to `data/facts.db`.
