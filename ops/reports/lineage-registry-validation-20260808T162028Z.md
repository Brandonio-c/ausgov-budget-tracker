# Lineage and source registry validation

Generated: `2026-08-08T16:20:28Z`

## Scope

Plan item 3.6: correct canonical source identities, separate current and historical FBO coverage, populate row-level canonical lineage, enforce single-valued ownership, normalize TAS/QLD aliases and derive explorer availability copy from API results.

## Canonical registry corrections

- ABS Table 1 revenue now owns `abs_gfs_commonwealth_130_revenue` (80 facts), not the Table 4 expense source `abs_gfs_commonwealth_130` (230 facts).
- The former broad `federal_fbo_appendix_a` declaration is split into:
  - `federal_fbo_appendix_a_2024_25`: 85 facts, `fully_ingested`, exact current-edition raw/source identities;
  - `federal_fbo_historical_archive`: 415 facts, `partially_ingested`, exact archive source identity.
- Exact canonical source declarations now take precedence over the generic “facts plus mapping” coverage heuristic. The historical archive therefore cannot be promoted silently to full coverage.

## Row-level canonical lineage

The validated lineage registry maps each configured fact source key to exactly one canonical dataset. Duplicate dataset IDs or assigning one source key to two canonical datasets raise an error before ingestion/backfill.

The shared fact upsert path writes `canonical_dataset_id` on insert and update. The preview-by-default backfill assigned existing rows transactionally:

| canonical dataset | facts |
| --- | ---: |
| `abs_gfs_table1_revenue` | 80 |
| `abs_gfs_table4_expenses` | 230 |
| `abs_taxation_revenue_detail` | 2,530 |
| `federal_fbo_appendix_a_2024_25` | 85 |
| `federal_fbo_historical_archive` | 415 |
| `federal_pbs_programs` | 18,029 |
| `federal_statement_6` | 657 |
| `state_borrowing_authorities` | 170 |
| **Assigned canonical facts** | **22,196** |
| **Non-canonical specialist facts left null** | **267,119** |

Postflight mismatches: **0**. Non-canonical rows carrying an ID: **0**. A second applied backfill changed **0** rows.

## Source identity and coverage dispositions

- `tas_treasurers_annual_financial_reports` is now a generated `duplicate_source` alias of the ingested `tas_treasurer_annual_financial_reports` key (232 facts).
- `qld_report_on_state_finances` is now a generated `duplicate_source` alias of the ingested `qld_report_on_state_finances_actuals` key (364 facts).
- Their handoff registry entries now point at those live canonical repository keys.
- [`ingestion-coverage-20260808T161257Z.md`](ingestion-coverage-20260808T161257Z.md) and its JSON companion contain the corrected repository-wide dispositions.
- [`ingestion-coverage-lineage.md`](ingestion-coverage-lineage.md) and its JSON companion now report eight distinct canonical datasets and the corrected fact counts.

## API-derived UI availability

The GFS specialist explorer no longer embeds VIC/TAS/QLD year ranges or static vintage coverage. It derives the ordered minimum/maximum financial years and distinct estimate statuses from the selected series API response. A frontend unit assertion covers sorting, range generation, status formatting and deduplication.

Final hard-coded range scan under frontend app/components/lib: **0 displayed coverage ranges**. Backend/API historical comments remain documentation, not UI availability claims.

## Validation

- Canonical/registry focused suite: 15 passed.
- Shared loader and specialist API suite: 48 passed.
- Full backend suite: 586 passed, one dependency deprecation warning.
- Frontend semantic/availability unit tests: passed.
- TypeScript: passed.
- Frontend lint baseline: unchanged at 25 errors / 13 warnings.
- Production build: passed, 12 static pages.
- Ruff and `git diff --check`: passed.
- Live `PRAGMA integrity_check`: `ok`.

## Data impact

The ignored live `data/facts.db` was updated only in `facts.canonical_dataset_id`: 22,196 configured canonical facts were assigned; 267,119 non-canonical facts remain null. No fact, node, edge, amount, citation or source document was inserted or deleted.
