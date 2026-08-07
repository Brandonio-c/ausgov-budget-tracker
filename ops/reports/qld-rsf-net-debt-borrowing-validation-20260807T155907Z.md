# QLD RSF Net Debt / Borrowing validation

Generated: 2026-08-07T15:59:07Z.

## Outcome

The residual Net Debt and gross Borrowing/Borrowings rows are publishable.
They are stable GGS point-in-time stock concepts wherever Queensland prints
them, although neither is present in all 16 older editions. Exact edition
applicability is now declarative, and no value is inferred for a missing row.
The economically distinct Net Borrowing transaction flow remains separate.

The triage evidence and complete edition matrix are recorded in
`qld-rsf-net-debt-borrowing-triage-20260807T154501Z.md`.

## Database load

Backup before the first write:
`/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T154842Z.db`.
SQLite integrity check on the backup returned `ok`.

| object | before | after | delta |
|---|---:|---:|---:|
| facts | 289,223 | 289,241 | +18 |
| nodes | 222,563 | 222,563 | 0 |
| fact_nodes | 289,223 | 289,241 | +18 |
| measure definitions | 95 | 95 | 0 |

First apply: 364 rows extracted and validated as publishable; 11 established
narrative/heading candidates quarantined by the extractor; zero loader
quarantine; 346 existing facts skipped; 18 facts inserted; zero updates,
supersessions, conflicts, nodes, edges, or semantic changes. The additions are
10 Net Debt facts (five editions x two vintages) and 8 gross Borrowing facts
(four editions x two vintages).

Second apply: 364 idempotent skips and zero inserts, updates, supersessions,
conflicts, nodes, edges, or semantic changes.

A direct comparison to the pre-write backup found zero changed pre-existing
facts/citations and zero new non-target facts. All new facts have exact file,
page, table, row, year, and vintage locators. No annual root total changed.

## Validation

- Focused QLD extractor/loader tests: 44 passed.
- Full Python suite: 528 passed, with one existing upstream Starlette
  deprecation warning.
- SQL integrity: zero hard failures; zero duplicate breakdown edges; zero
  orphan facts, nodes, or edges; zero cross-government or cross-jurisdiction
  additive edges.
- Coverage: unchanged at 51 fully ingested, 165 adapter missing, 81 partial,
  23 duplicate source, 24 adapter broken, 7 officially unavailable, 12 not
  acquired, and 4 reference only. Lineage generation completed for 7 datasets.
- Database quarantine population: unchanged at 36,417. The adapter's 11
  extractor quarantine records are the established malformed heading/narrative
  candidates, not Net Debt or Borrowing facts.
- Revenue reconciliation: completed with the established eight warnings.
- Debt reconciliation: all seven controls passed.
- Frontend raw lint: unchanged repository baseline of 25 errors and 13
  warnings. Baseline-aware `npm run lint:ci` passed exactly at 25/13.
- Frontend production build: passed. Playwright: 20/20 passed against a real
  static export and real backend/database.
- Local/container dashboard audits: all 6 paths and 7 PBS crosswalk cases,
  zero hard failures and zero accepted-rounding warnings.

## Production verification

The backend was rebuilt/restarted and is healthy. No frontend code changed,
so no frontend deployment was necessary. The existing dynamic QLD RSF API/UI
surface exposes the additional years without a new route or component.

Public API checks:

- 14 QLD RSF measures, unchanged.
- Net Debt: 28 facts across 14 published editions; 2024-25 actual
  $16.727 billion with exact page 9 `Net Debt` citation.
- Gross Borrowing: 30 facts across 15 published editions; 2024-25 actual
  $72.864 billion with exact page 9 `Borrowing` citation.
- Federal FY2024-25 annual root: $745.030 billion, unchanged.
- State FY2024-25 annual root: $553,464,488,764.247, unchanged.
- Public UI root and QLD RSF GFS explorer returned HTTP 200.
- Full public dashboard audit: all 6 paths and 7 PBS crosswalk cases, zero
  hard failures and zero accepted-rounding warnings.

The known Cloudflare nested hard-navigation behavior remains external and was
not changed by this backend/data-only milestone.

## Scope and limitations

Only QLD RSF semantic configuration, its reusable edition filter, tests, and
reports changed. `data/facts.db`, backups, generated quarantine files, raw
sources, WAL/SHM files, and browser profiles are not committed. The only
remaining validation limitation is the pre-existing raw ESLint baseline; its
regression-aware CI gate is clean.
