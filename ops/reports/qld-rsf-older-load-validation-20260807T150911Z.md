# Older Queensland RSF load and validation

Generated: 2026-08-07.

## Load outcome

Backup before writes: `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260807T151023Z.db`.

The repaired adapter extracted 346 facts across the complete 2002-03 to
2024-25 RSF series. Of these, 112 newer-cluster facts were already present
and 234 older-cluster facts were inserted (117 actual and 117 estimated
actual). Six new measure nodes and six measure definitions were inserted;
no graph edges, source documents, supersessions, amount changes, or semantic
conflicts were created.

Database counts:

| object | before | after | delta |
|---|---:|---:|---:|
| facts | 288,989 | 289,223 | +234 |
| nodes | 222,557 | 222,563 | +6 |
| fact_nodes | 288,989 | 289,223 | +234 |
| source_documents | 131 | 131 | 0 |
| measure_definitions | 89 | 95 | +6 |
| node_edges / lineage_edges | 0 / 0 | 0 / 0 | 0 |

Four older narrative/heading candidates and seven pre-existing newer
heading candidates were quarantined by the extractor; loader quarantine was
zero. Exact table-title locators were normalized in two citation-only passes
(234 older facts, then 170 titles refined to exact Summary/Key wording; no
amounts or identities changed). A repeat apply
reported 346 idempotent skips, zero inserts, zero updates, zero nodes, zero
edges, zero conflicts, and zero semantic changes.

## Validation

- SQL integrity: `hard_failures: 0`; duplicate breakdown edges 0; orphan
  facts/nodes/edges 0; no cross-government or cross-jurisdiction additive
  edges.
- Coverage: source remains `fully_ingested`; aggregate status counts remain
  51 fully ingested / 165 adapter missing / 81 partial.
- Quarantine report: 36,417 established database quarantine rows, unchanged.
- Revenue reconciliation: completed with the established eight warnings.
- Debt reconciliation: all seven controls pass.
- Python: 520 tests pass (one upstream Starlette deprecation warning); final
  focused RSF/API rerun also passes.
- Frontend: production build passes; Playwright 20/20 passes. Raw `npm run
  lint` reports the unchanged repository baseline (25 errors, 13 warnings);
  the baseline-aware CI gate `npm run lint:ci` passes with exactly 25/13.
- Local dashboard audit: 6 paths and 7 PBS crosswalk cases, zero hard
  failures and zero accepted-rounding warnings. Federal/state/territory/
  local/debt/GDP/MFS/PBS paths remain clean.
- Production: backend rebuilt/restarted. Public UI and both QLD RSF endpoints
  return HTTP 200; the API exposes 14 measures, 46 revenue points across 23
  years, oldest year 2002-03, and an exact file/page/table/row citation. The
  full public dashboard audit (`dashboard-api-audit-20260807T152145Z`) also
  passes all 6 paths and 7 crosswalk cases with zero hard failures/warnings.

No frontend code or route changed. The existing GFS explorer consumes the
expanded dynamic QLD RSF measure/year endpoints, so the Cloudflare nested
hard-navigation issue remains external and irrelevant to this family.
