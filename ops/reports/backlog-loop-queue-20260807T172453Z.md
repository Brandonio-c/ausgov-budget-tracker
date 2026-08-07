# Canonical backlog loop queue

Generated: 2026-08-07T17:24:53Z  
Repository state: clean `main` at `d60b7a6`, six completed MYFER commits
ahead of unchanged `origin/main` (`9275d07`).

## Reconciliation rule

This queue starts from the merged order in
`backlog-rankings-consolidated-20260807T161125Z.md`, then applies all later
completion evidence. QLD RSF (both generations and debt/borrowing) and QLD
MYFER are complete and are not reopened. Old source-level `adapter_missing`
labels do not override later family validation reports. Policy/handbook files
that the QLD ranking identifies as non-data are excluded.

## Primary remaining data-family work

| queue rank | report source | family / subfamily | why still open | type | reusable adapter | blocker |
|---:|---|---|---|---|---|---|
| 1 | `pdf-ocr-next-backlog-ranking-20260806T185946Z.md` rank 2; consolidated merged rank 2 | TAS TAFR narrative-era Executive Summaries, 2003-04 to 2009-10 | The later tabular 2010-11 to 2012-13 cluster shipped, but these seven editions were explicitly deferred because measures occur in prose and chart-adjacent number lists. | PDF | `tas_tafr_pdf_backfill.py` exists for the tabular generation only; it is not proven reusable for narrative layouts. | No acquisition blocker; extraction/attribution risk must be surveyed per edition. |
| 2 | `next-backlog-ranking-20260805T161821Z.*` rank 3 after completed AFS/BPO; consolidated merged rank 3 | VIC Output Performance Measures 2024-25 | Acquired structured workbook remains unimplemented. It contains non-dollar KPI percentages/counts and therefore needs its own semantics rather than financial amount coercion. | structured workbook | VIC workbook adapters provide patterns, but no Output Performance adapter exists. | No acquisition blocker; dashboard fit is deliberately limited. |
| 4 | `qld-backlog-rerank-20260807T142208Z.*` rank 4; consolidated merged rank 5 | QLD Consolidated Fund Financial Reports | Annual and quarterly Public Account cash reports were explicitly deferred after RSF/MYFER. | PDF | No dedicated adapter. | No acquisition blocker; cash basis, quarterly vintages, and annual/quarterly overlap require a bounded cluster decision. |
| 5 | `qld-tas-next-backlog-ranking-20260806T171537Z.*` rank 6; consolidated merged rank 6 | QLD on-time payment reports | Acquired CSV population remains `adapter_missing`. It is contextual agency compliance data, not fiscal totals. | structured CSV | No dedicated adapter; QLD procurement code may provide multi-file patterns only. | Files are present locally; WAF is an update/acquisition risk, not a current parsing blocker. |
| 6 | `vic-soce-admin-scope-20260805T212053Z.md`; consolidated merged rank 7 | VIC AFS deferred six-sheet subfamily | The AFS core shipped, while six materially different sheets were explicitly left out of the later BPO SOCE/Admin scope. | structured workbook | `vic_afs.py` exists, but support for these sheet shapes is unproven. | No acquisition blocker; sheet-level semantic diversity and duplication risk. |
| 7 | `qld-backlog-rerank-20260807T142208Z.*` tail; consolidated merged rank 8 | QLD CFFR Commonwealth-relations bulletins | Acquired bulletins remain untouched and are a different topic from QLD's own aggregate finances. | PDF | No dedicated adapter. | No acquisition blocker; low dashboard fit and Commonwealth-payment vintage semantics. |
| 8a | `data-expansion-20260723.md`; consolidated merged rank 9 | Pre-2019 FBO Appendix A historical layout/OCR work | Current FBO coverage does not close the older layout gap. | PDF/OCR | `fbo_appendix_a.py` exists for supported layouts; older-layout applicability is unproven. | May require OCR/layout-specific rules; must not be guessed. |

## Maintenance on already-covered families

| queue rank | report source | family / subfamily | why still open | type | reusable adapter | blocker |
|---:|---|---|---|---|---|---|
| 3 | latest `ingestion-coverage-20260807T165605Z.*` top-40 tie; consolidated merged rank 4 | Generalized federal PBS per-source lineage | PBS facts and Statement 6 crosswalk are complete, but registry rows still show zero direct facts because facts use the generalized source key. This is lineage/audit maintenance, not extraction of a new family. | maintenance | `pbs_programs_all.py` and its reload/crosswalk tooling already exist. | No acquisition blocker; change must preserve all facts, totals, and crosswalk edges. |

## External, acquisition-blocked, or out of scope

| order | report source | item | classification | decision / blocker |
|---:|---|---|---|---|
| 8b | `data-expansion-20260723.md`; consolidated merged rank 9 | 1985-87 Trove archive hunt | external acquisition | No verified local source asset. Document/defer unless an official usable asset is already present; do not invent or scrape an uncertain substitute. |
| 9 | `cloudflare-route-triage-20260805T160938Z.md`, `...T182428Z.md`, and `cloudflare-triage-vic-soce-admin-20260805T212214Z.md` | Cloudflare nested hard-navigation defect | external infrastructure | Repo-side fixes were exhausted and the symptom remains platform/dashboard-level. Do not spend this loop on it unless a selected family introduces a genuine dependency. |
| excluded | `qld-backlog-rerank-20260807T142208Z.*` | QLD policy/procedure/handbook PDFs | non-data | Explicitly excluded by the ranking as non-data-bearing. |

## Initial selection

The highest-ranked open in-repository item is the **TAS TAFR narrative-era
sub-shape (2003-04 to 2009-10)**. It is PDF work. The first action is a
read-only seven-edition inventory and text/layout survey; the existing tabular
TAFR adapter must not be broadened unless the source evidence proves a shared
rule.
