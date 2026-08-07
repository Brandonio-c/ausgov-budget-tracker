# Consolidated backlog rankings

Generated: 2026-08-07T16:11:25Z.

Repository state inspected: `main` at `9275d07`. This is a read-only
reconciliation of existing reports and configuration; the only repository
change made for this task is this report.

## Executive answer

The latest human-curated, still-unimplemented data-family recommendation is
**Queensland Mid-Year Fiscal and Economic Review (MYFER) editions** from the
`qld_report_on_state_finances_actuals` population. It is the first remaining
runner-up in the newest QLD ranking after both ranked RSF targets—2018-19 to
2024-25 and 2002-03 to 2017-18, including the optional Net Debt/Borrowing
follow-up—were completed. This is **PDF work**, expected to be born-digital /
text-extractable but requiring a fresh edition and format-drift survey. It is
not structured-workbook work and it is not external-infrastructure work.

There is a separate automated-audit answer: the latest ingestion-coverage
report's top-40 list is a large tie of generalized federal PBS sources with
the action `improve_per_source_lineage`. That is maintenance of already
family-covered PBS sources, not selection of a new ingestion family. It does
not displace MYFER as the next unimplemented family.

Cloudflare is **not in scope for any current ranked data item**. It remains a
separate external infrastructure follow-up for nested hard navigation.

## Method and scope

I searched filenames and report contents for `backlog`, `rank`, `rerank`,
`selection`, `scope`, `priority`, `roadmap`, `next`, and family-selection
language. I read every direct ranking/selection report, its CSV companion,
the upstream adapter plan and current-state material, all 26 timestamped
ingestion-coverage ranking pairs, the lineage report, relevant close-outs,
and the three Cloudflare scope decisions. I then checked the latest coverage
audit and completion reports rather than treating an old `adapter_missing`
label as current.

The inventory below distinguishes:

- **primary**: explicitly ranks, re-ranks, or selects a family;
- **supporting/partial**: provides a prioritized roadmap, ranked next actions,
  source-priority inventory, scope exclusion, or current-state basis;
- **generated ranking series**: automated coverage reports with a top-40
  priority backlog.

## 1. Primary ranking and selection artifacts

| artifact | timestamp | what and scope it ranks/selects | order or selection | criteria | blockers/exclusions and present status |
|---|---|---|---|---|---|
| `ops/reports/adapter-repair-plan-20260731T202041Z.md` | 2026-07-31T20:20:41Z | 247 `adapter_missing` registry sources, grouped into 70 `(source_family, jurisdiction, level)` families | Raw family order starts: (1) Commonwealth `handoff_gdp_tax_federal`, (2) VIC `handoff_actuals_state`, (3) Australia cross-level actuals, (4) NSW actuals, (5) QLD actuals; directive category order starts MFS, structured state, structured local, debt/super, historical actuals, contextual | `avg(viz_value_rank)*2 - format_effort*10 + min(count,20)`; value, structured format, and adapter reuse | No acquisition blockers then. Raw score and directive disagree about #1. Counts/statuses are stale; the family grouping remains useful. |
| `ops/reports/adapter-repair-plan-20260731T202041Z.csv` | 2026-07-31T20:20:41Z | Row-level source inventory underlying the plan | 247 sources with category, priority, visualization rank, format, action, group score, and exclusion reason | Same formula and category directive | Many PBS rows were subsequently recognized as served by a generalized adapter; many selected state families are now complete. |
| `ops/reports/next-backlog-ranking-20260805T161821Z.md` | 2026-08-05T16:18:21Z | Re-ranks structured state-budget/financial-statement candidates | 1 VIC AFS; 2 VIC BPO; 3 VIC Output Performance; 4 NSW Economic Data; 5 NSW Historical Fiscal Indicators; 6 QLD RSF mixed population; 7 TAS annual reports mixed population; QLD SDS excluded | Structured availability, effort, dashboard value, multi-edition reuse, semantic risk; prefer xlsx/csv over PDF/OCR | AFS and BPO are complete. Output Performance remains unimplemented but is non-dollar KPI work. NSW historical indicators excluded as likely duplicate; QLD/TAS required later triage. |
| `ops/reports/next-backlog-ranking-20260805T161821Z.csv` | 2026-08-05T16:18:21Z | Machine-readable companion to the structured-state ranking | Same 1-7 order plus QLD SDS exclusion | Same five criteria, with explicit status/value/effort/risk columns | Superseded for ranks 1-2 by completion and for QLD/TAS by later focused rankings. |
| `ops/reports/next-structured-pack-selection-20260805T182251Z.md` | 2026-08-05T18:22:51Z | Revalidates the first unfinished structured candidate after VIC AFS | Selects `vic_budget_portfolio_outcomes_2024_25` | On-disk/hash verification, no adapter, clean common sheet shape, value/effort, established VIC pattern | Complete. Deferred Output Performance, duplicate-risk NSW work, and mixed QLD/TAS populations. |
| `ops/reports/vic-soce-admin-scope-20260805T212053Z.md` | 2026-08-05T21:20:53Z | Narrows the two deferred VIC BPO workbook sheets | Selects BPO `SOCE` + `Admin`, not the six differently named AFS deferred sheets | Exact tab names, same workbook/hash, semantic distinctness, duplicate checks, label-collision risk | Complete. AFS's six deferred sheets remain a separate lower-priority structured subfamily. |
| `ops/reports/qld-tas-next-backlog-ranking-20260806T171537Z.md` | 2026-08-06T17:15:37Z | Focused QLD/TAS structured-source triage | 1 TAS GGS key-measures xlsx; 2 QLD RSF PDF population; 3 QLD grant/contracts/payment families | Structured availability, effort, dashboard value, reuse, semantic risk, existing support | TAS xlsx complete. QLD's only xlsx was a blank form, so RSF was deferred to PDF triage. QGIP and contract disclosure are now fully ingested; on-time payments remain missing but off-topic. |
| `ops/reports/qld-tas-next-backlog-ranking-20260806T171537Z.csv` | 2026-08-06T17:15:37Z | Companion seven-row focused ranking | TAS GGS first; QLD RSF actual/alternate keys second/third; QGIP, contracts, on-time payments next; TASCORP excluded as already covered | Same six criteria | Substantially superseded by TAS/QLD completion and current coverage status. |
| `ops/reports/qld-tas-scope-selection-20260806T171537Z.md` | 2026-08-06T17:15:37Z | Selects the exact structured shape | TAS `GGS-Key-Fiscal-Measures-Time-Series.xlsx` | One 24x12 workbook, 16 years, three vintages, zero TAS-native overlap, no access blocker | Complete. Its 76 PDF siblings were intentionally left for PDF triage. |
| `ops/reports/pdf-ocr-next-backlog-ranking-20260806T185946Z.md` | 2026-08-06T18:59:46Z | Re-ranks TAS and QLD PDF-heavy populations | 1 TAS TAFR tabular 2010-11–2012-13; 2 TAS TAFR narrative 2003-04–2009-10; 3 TAS in-year reports; 4 TAS economic briefs; 5 QLD RSF | Parsability, effort, dashboard value, reuse, semantic risk, partial support, workable text extraction | Rank 1 complete. TAS narrative remains a real PDF backlog item. Later QLD inspection reduced QLD risk and advanced it ahead within a QLD-specific mission. |
| `ops/reports/pdf-ocr-next-backlog-ranking-20260806T185946Z.csv` | 2026-08-06T18:59:46Z | Companion five-row PDF ranking | Same 1-5 order | Same seven criteria | Rank 1 superseded by completion; remaining ranks are still useful within TAS/PDF scope. |
| `ops/reports/pdf-ocr-scope-selection-20260806T185946Z.md` | 2026-08-06T18:59:46Z | Selects exact TAS PDF sub-shape | Three text-extractable TAFR editions, 2010-11–2012-13 | Stable repeated tables, exact label matches to existing TAS measures, non-overlapping years, no OCR/access blocker | Complete. Narrative-era TAFR remains deferred because numbers sit in prose/mini-chart layouts. |
| `ops/reports/qld-backlog-rerank-20260807T142208Z.md` | 2026-08-07T14:22:08Z | Full content-based re-rank of the 187-file QLD population | 1 RSF 2018-19–2024-25; 2 RSF 2002-03–2017-18; 3 MYFER; 4 Consolidated Fund reports; 5 non-data policy; 6 CFFR bulletins (the prose recommendation places CFFR before policy, while CSV order numbers policy 5/CFFR 6) | Text extraction, effort, value, adapter coverage, semantic risk, existing support, on-disk availability | RSF ranks 1-2 complete. MYFER is the first remaining ranked data family. Consolidated Fund is cash/Public Account; CFFR is Commonwealth-payments context; policy files excluded. |
| `ops/reports/qld-backlog-rerank-20260807T142208Z.csv` | 2026-08-07T14:22:08Z | Machine-readable six-row QLD order | 1 newer RSF; 2 older RSF; 3 MYFER; 4 Consolidated Fund; 5 policy/handbook; 6 CFFR | Value, effort, risk, coverage, format | First two now complete. Note the minor ordering inconsistency with the MD's prose, which lists CFFR fifth and policy sixth. |
| `ops/reports/qld-family-selection-20260807T142208Z.md` | 2026-08-07T14:22:08Z | Selects the recent internally consistent QLD cluster | RSF Summary of Key UPF Financial Aggregates, 2018-19–2024-25 | Seven verified text tables, stable eight-row core, GGS first pair, new family, no access blocker | Complete. Older RSF was the explicit next family. |
| `ops/reports/qld-rsf-older-family-selection-20260807T150911Z.md` | 2026-08-07T15:09:11Z | Re-selects the deferred older RSF continuation after the recent cluster shipped | RSF 2002-03–2017-18 as top in-repository target | All files acquired, born-digital tables, same publication/sector semantics, bounded label vocabularies, no OCR | Complete. It explicitly leaves MYFER as the first runner-up, followed by Consolidated Fund, CFFR, and non-data policy files. |
| `ops/reports/qld-rsf-net-debt-borrowing-triage-20260807T154501Z.md` | 2026-08-07T15:45:01Z | Partial/final-gap selection within the completed RSF family | Publish optional Net Debt and gross Borrowing where printed; keep Net Borrowing distinct | Full 23-edition row inventory, semantic continuity, component reconciliation, exact edition applicability | Complete. This closes the last stated in-family RSF gap; it does not rank the next family. |

## 2. Supporting and partial prioritization artifacts

| artifact | timestamp | role, order, and scope | criteria / blockers | currency |
|---|---|---|---|---|
| `ops/reports/current-state.md` | 2026-07-24T22:05:33Z | Requested current-state basis: architecture, coverage references, tests, and known limitations; no family ranking | Flags PBS reprocess, revenue warnings, lint debt, thin debt depth | Architecturally useful but numerical state (`~331k`) and limitations are stale. |
| `ops/reports/missing-data-exhaustive-20260723.md` | 2026-07-23 | Broad prioritized roadmap: P0 DSS PBS components then Health aged-care; P1 FBO, state budgets, recipient/NDIS data and history; P2 Defence/Education/AusTender/DVA | Dollar impact, dashboard drill depth, on-disk availability; warns against inventing additive dollars | Superseded for PBS/FBO and several ingestion claims; historical/archive and related recipient/payment work remain useful. |
| `ops/reports/data-expansion-20260723.md` | 2026-07-23 | Remaining engineering order: pre-2019 FBO OCR/layout, Trove 1985-87, Part B on-disk extraction, redeploy | Historical gap, acquisition feasibility, accounting-basis separation | Partially current: older FBO/Trove work remains; PBS/state-family items evolved substantially. |
| `ops/reports/hardening-final-20260724T220533Z.md` | 2026-07-24T22:05:33Z | Partial five-item next-actions list: PBS reprocess; attach ABS tax detail; clear lint; commit ordered PRs; restart API | Correctness risks remaining after semantic/API hardening | PBS reprocessing and later crosswalk work are complete; operational/code-maintenance items are outside the data-family backlog. |
| `ops/reports/handoff-on-disk-inventory.md` | derived from 2026-07-24 handoff | Availability inventory, not a value ranking: 132 confirmed rows and three download orphans | Physical presence/assets/bytes | Supporting evidence only; later acquisitions and adapters supersede statuses. |
| `ops/reports/handoff-download-status.md` | 2026-07-24T17:19:33Z | Per-source P0/P1/P2 acquisition/status list for 281 handoff rows | Registry priority, download status, fact presence | Priority metadata source, not a normalized engineering ranking; stale. |
| `ops/reports/handoff-full-acquire-ingest-20260724.md` | 2026-07-24T17:19:33Z | Same 281-row priority/status corpus plus ingestion acceptance and blockers | Registry priority, acquisition, fact counts | Partial ranking artifact; old WAF/network blockers and zero-fact states have often changed. |
| `ops/reports/ingest-maximise-handoff-20260724T200528Z.md` | 2026-07-24T20:05:28Z | Short remaining-gap list: Defence PBS, QLD SDS, QAO local PDFs | Extraction reliability and availability of structured alternatives | Superseded by generalized PBS work and later coverage; QLD SDS caution remains relevant. |
| `ops/reports/ingest-maximise-handoff-20260724T200621Z.md` | 2026-07-24T20:06:21Z | Corrected short gap list, adding NSW grants ZIP/OLG canonical note | Same | Supersedes the 20:05:28 version. |
| `ops/reports/task10-final-handoff-20260801T005500Z.md` | 2026-08-01T00:55:00Z | Ranked five actions: (1) link PBS to Statement 6; (2) resolve/load MFS; (3) adapter queue; (4) acquire three QLD packs; (5) revenue reconciliation | Impact, readiness, semantic safety, external blockers | PBS crosswalk and MFS are complete; structured state queue was worked through VIC/TAS/QLD; QLD browser acquisition and revenue reconciliation remain separate items. |
| `ops/reports/adapter-repair-batch1-mfs-aggregates-20260731T202800Z.md` | 2026-07-31T20:28:00Z | Narrows top directive family to MFS flat aggregates and defers hierarchical MFS files | Safe unit/header semantics and no partial-year mixing | MFS subsequently completed; useful only as selection history. |
| `ops/reports/pbs-reprocessing-20260731T193413Z.md` | 2026-07-31T19:34:13Z, extended 19:50Z | Partial PBS follow-up selection: recommends the full program-to-Statement-6 crosswalk as a high-impact next step; also flags newest-edition preference as a later backlog issue | Dashboard drill depth, citation integrity, overlapping-edition semantics | The crosswalk recommendation is complete and superseded by its coverage report/task handoff; explicit newest-edition precedence remains a PBS maintenance caveat, not a ranked new family. |
| `ops/reports/cloudflare-route-triage-20260805T160938Z.md` | 2026-08-05T16:09:38Z | Infrastructure scope/priority decision; recommends dashboard purge, reverify, then Cache Rules investigation | Reproducible hard-navigation impact and repo-vs-edge cause | Partially superseded: repo fixes shipped but symptom persisted; external follow-up remains. |
| `ops/reports/cloudflare-route-triage-20260805T182428Z.md` | 2026-08-05T18:24:28Z | Decides Cloudflare does not block VIC BPO | Existing route/client navigation; repo fixes exhausted | Current conclusion: external, not a data-family blocker. |
| `ops/reports/cloudflare-triage-vic-soce-admin-20260805T212214Z.md` | 2026-08-05T21:22:14Z | Reconfirms the same exclusion for SOCE/Admin | Same existing route and client-navigation reasoning | Latest dedicated Cloudflare scope refinement; external follow-up unchanged. |

## 3. Generated ingestion-coverage ranking series

Every timestamped coverage report contains a `Priority backlog (top 40)`
ranked by `viz_value_rank`, status, fact count, and `next_ingestion_action`.
Each timestamp has an MD summary and JSON detail; both physical artifacts are
listed below. The reports share the same scope/criteria, so the distinguishing
facts are timestamp and status evolution.

| artifacts | timestamp | status snapshot and currency |
|---|---|---|
| `ingestion-coverage-20260724T194315Z.{md,json}` | 2026-07-24T19:43:15Z | 40 fully / 269 missing / 11 broken; superseded |
| `ingestion-coverage-20260724T200621Z.{md,json}` | 2026-07-24T20:06:21Z | 46 / 247 / 27; supersedes prior same-day audit |
| `ingestion-coverage-20260731T153150Z.{md,json}` | 2026-07-31T15:31:50Z | 46 / 247 / 27; superseded |
| `ingestion-coverage-20260731T160320Z.{md,json}` | 2026-07-31T16:03:20Z | 47 / 247 / 27; superseded |
| `ingestion-coverage-20260731T160657Z.{md,json}` | 2026-07-31T16:06:57Z | Registry expands to 367; 47 / 247 / 27; superseded |
| `ingestion-coverage-20260731T161145Z.{md,json}` | 2026-07-31T16:11:45Z | Same counts; superseded |
| `ingestion-coverage-20260731T201730Z.{md,json}` | 2026-07-31T20:17:30Z | Source audit for adapter-repair plan; 47 / 247 / 27; superseded as status, retained as ranking provenance |
| `ingestion-coverage-20260801T002019Z.{md,json}` | 2026-08-01T00:20:19Z | Adds partial status: 47 fully / 81 partial / 169 missing / 24 broken; superseded |
| `ingestion-coverage-20260801T070827Z.{md,json}` | 2026-08-01T07:08:27Z | Same status counts; superseded |
| `ingestion-coverage-20260803T220142Z.{md,json}` | 2026-08-03T22:01:42Z | Same status counts; superseded |
| `ingestion-coverage-20260804T230420Z.{md,json}` | 2026-08-04T23:04:20Z | Same status counts; superseded |
| `ingestion-coverage-20260805T041343Z.{md,json}` | 2026-08-05T04:13:43Z | Same statuses, 126 mapping files; superseded |
| `ingestion-coverage-20260805T164418Z.{md,json}` | 2026-08-05T16:44:18Z | 48 fully / 168 missing after VIC AFS; superseded |
| `ingestion-coverage-20260805T172245Z.{md,json}` | 2026-08-05T17:22:45Z | Same counts; superseded |
| `ingestion-coverage-20260805T191059Z.{md,json}` | 2026-08-05T19:10:59Z | 49 fully / 167 missing after VIC BPO; superseded |
| `ingestion-coverage-20260805T192721Z.{md,json}` | 2026-08-05T19:27:21Z | Same counts; superseded |
| `ingestion-coverage-20260805T193257Z.{md,json}` | 2026-08-05T19:32:57Z | Same counts; superseded |
| `ingestion-coverage-20260805T213349Z.{md,json}` | 2026-08-05T21:33:49Z | Same source-level counts after SOCE/Admin (same parent source); superseded |
| `ingestion-coverage-20260806T172906Z.{md,json}` | 2026-08-06T17:29:06Z | 50 fully / 166 missing after TAS GGS; superseded |
| `ingestion-coverage-20260806T173740Z.{md,json}` | 2026-08-06T17:37:40Z | Same counts; superseded |
| `ingestion-coverage-20260806T191638Z.{md,json}` | 2026-08-06T19:16:38Z | Same source status after TAS TAFR extension; superseded |
| `ingestion-coverage-20260807T000456Z.{md,json}` | 2026-08-07T00:04:56Z | Same statuses; superseded |
| `ingestion-coverage-20260807T144003Z.{md,json}` | 2026-08-07T14:40:03Z | 51 fully / 165 missing after recent QLD RSF; superseded |
| `ingestion-coverage-20260807T144956Z.{md,json}` | 2026-08-07T14:49:56Z | Same counts; superseded |
| `ingestion-coverage-20260807T151118Z.{md,json}` | 2026-08-07T15:11:18Z | Same statuses after older RSF; superseded |
| `ingestion-coverage-20260807T154951Z.{md,json}` | 2026-08-07T15:49:51Z | **Current generated ranking**: 51 fully / 81 partial / 165 missing / 24 broken; 289,241 facts. Top 40 are tied PBS lineage-maintenance items. |

`ops/reports/ingestion-coverage-lineage.{md,json}` is the untimestamped
canonical-family companion. It covers seven canonical datasets and reports
their fully/partially-ingested state; it does not choose a unique next family.
Older timestamped coverage pairs are superseded by the 15:49:51Z pair for
current status, but retained above because each physically contains a backlog
ranking.

## 4. Configuration and manifest dependencies

### Canonical datasets

`config/canonical_datasets.yaml` does **not exist**. Multiple selection
reports correctly record that the real file is
`config/lineage/canonical_datasets.yaml`. It tracks seven already-served
canonical families and is used to avoid falsely ranking aliases as missing:
ABS GFS expenses/revenue, ABS taxation detail, generalized federal PBS,
Statement 6, FBO Appendix A, and state borrowing authorities. It is not a
family-selection queue.

### Procurement registry

`config/procurement_sources.yaml` is the upstream registry for priority,
family, jurisdiction, access, format hints, on-disk handoff state, and parser
strategy. Important ranking dependencies:

- VIC AFS/BPO/Output Performance are P0 structured handoff sources.
- TAS annual reports are P0 and acquired; focused inspection found the useful
  xlsx and PDF sub-shapes.
- QLD RSF is P1 and acquired; registry `pdf/xlsx` was only a hint—the xlsx was
  a blank form and the useful corpus was PDF.
- QLD QGIP and contract disclosure are now fully ingested despite early
  rankings calling them missing; QLD on-time payments remains acquired and
  adapter-missing but is off-topic for fiscal aggregates.

### Measure semantics referenced by the ranking chain

- `config/measure-semantics/vic_afs.yaml`, `vic_bpo.yaml`, and
  `vic_bpo_soce_admin.yaml` confirm that the selected VIC work shipped as
  distinct departmental/controlled/administered concepts.
- `tas_ggs_key_fiscal_measures.yaml` and `tas_tafr_pdf_backfill.yaml` confirm
  the structured TAS series and tabular PDF extension shipped without being
  conflated with ABS GFS.
- `qld_report_on_state_finances.yaml` now covers all 23 RSF editions and the
  residual stock rows, proving QLD ranks 1-2 are complete.

These semantic files validate completion/scope; they do not rank MYFER or
other remaining families.

## 5. Merged top remaining work

This merges only items still open after checking later reports/config. It does
not pretend that rankings made for different scopes share one mathematical
score.

| merged order | remaining work | source ranking evidence | type | reason / blocker |
|---:|---|---|---|---|
| 1 | **QLD Mid-Year Fiscal and Economic Review editions** | Latest QLD rank #3; becomes first remaining after completed RSF #1-2; older-RSF selection names it first runner-up | PDF | Same acquired population and fiscal domain, but lower-value in-year vintages and likely format drift require a dedicated survey. |
| 2 | **TAS TAFR narrative sub-shape, 2003-04–2009-10** | PDF ranking #2 after completed tabular #1 | PDF | Valuable backward actuals coverage; higher misattribution risk because measures sit in prose/mini-chart number lists. |
| 3 | **VIC Output Performance Measures 2024-25** | Structured ranking #3 after completed AFS/BPO #1-2 | Structured xlsx | Clean and acquired, but non-dollar KPI/percent/count semantics make it a weaker fit for the financial dashboard. |
| 4 | **Improve generalized PBS per-source lineage** | Latest automated coverage top-40 tie | PDF-family maintenance | Already family-covered; improves registry/audit lineage rather than adding a new family. |
| 5 | **QLD Consolidated Fund Financial Reports** | Latest QLD rank #4 | PDF | Useful cash/Public Account transactions, but a narrower basis, many quarterly editions, and vintage complexity. |
| 6 | **QLD on-time payment reports** | QLD/TAS structured rank #6 and latest coverage `adapter_missing` | Structured CSV | Easy/available but off-topic compliance metrics; belongs in a contextual/procurement milestone. |
| 7 | **AFS deferred sheets** | VIC SOCE/Admin scope explicitly defers six AFS sheets | Structured xlsx | Real structured remainder, but a broader/more varied subfamily than the completed BPO pair. |
| 8 | **QLD CFFR Commonwealth-relations bulletins** | Latest QLD tail ranking | PDF | Different topic—Commonwealth payments to Queensland—not Queensland's own aggregate finances. |
| 9 | **Historical archive work: pre-2019 FBO OCR/layout and 1985-87 Trove hunt** | Missing-data/data-expansion roadmaps | PDF/OCR/acquisition | High historical value; materially harder extraction and external archive discovery. |
| 10 | **Separate external Cloudflare nested-route follow-up** | Three Cloudflare triages | Infrastructure | Requires dashboard Cache/Page/Bot rule inspection or support; does not block any item above. |

Other broad adapter-plan families remain available, but their 2026-07-31
scores should be regenerated before use because 82 sources changed status and
several named top families have shipped.

## 6. Contradictions and scope-driven disagreements

1. **Raw adapter score vs directive:** the adapter plan's formula ranks
   Commonwealth GDP/tax first, while its mandated category order selects MFS
   first. The report states both; this is a real prioritization conflict, not
   silently reconciled here.
2. **Broad P0 PBS roadmap vs later generalized coverage:** the 2026-07-23
   missing-data report places DSS/Health PBS extraction first. Later work
   generalized PBS extraction and built the Statement 6 crosswalk, so the
   current audit asks for per-source lineage rather than a new PBS adapter.
3. **QLD initially excluded, later selected:** structured-only rankings
   excluded QLD RSF because it had no usable workbook. PDF-focused reports
   later selected it after table-page inspection. This is a scope change, not
   evidence that the xlsx assessment was wrong.
4. **TAS narrative ahead of QLD in one report, QLD ahead later:** the
   PDF/OCR ranking puts TAS narrative #2 and QLD #5 based on one QLD sample.
   The later dedicated QLD survey found stable text tables and promoted recent
   and older RSF clusters. New evidence and jurisdiction-specific scope explain
   the changed order.
5. **Older QLD adapter effort changed:** the QLD re-rank warned that older
   RSF might need three adapters or a complex unified parser. The later full
   inventory proved one reusable adapter with bounded declarative vocabularies
   was sufficient. The earlier risk estimate is superseded by direct evidence.
6. **QLD MD/CSV tail order:** the QLD Markdown recommendation lists CFFR
   before policy documents, but the CSV gives policy rank 5 and CFFR rank 6.
   Policy files are explicitly non-data and therefore excluded; the practical
   remaining-data order puts CFFR ahead of them.
7. **Source-level coverage can hide sub-shape gaps:** TAS annual reports and
   QLD RSF now show `fully_ingested`, even though TAS narrative-era PDFs and
   other QLD report categories remain untouched. The focused reports are more
   precise than the registry-level status for those subfamilies.
8. **Counts vary across reports:** QLD/TAS inventories sometimes count files
   across multiple snapshots/alternate keys, while focused selections count
   unique target assets. These are different scopes, not necessarily missing
   files.

## 7. Supersession map

- `current-state.md` and `missing-data-exhaustive-20260723.md` are superseded
  for counts/current coverage by `ingestion-coverage-20260807T154951Z.*` and
  the later family validation reports.
- `ingest-maximise-handoff-20260724T200528Z.md` is directly superseded by the
  corrected `...T200621Z.md`.
- All ingestion-coverage pairs before `20260807T154951Z` are superseded for
  current status by that latest pair.
- `adapter-repair-plan-20260731T202041Z.*` is superseded as a status snapshot,
  but not as the historical source of the family-scoring method.
- `task10-final-handoff-20260801T005500Z.md` ranks PBS linkage and MFS first;
  both are complete, so its next-action order is historical.
- `hardening-final-20260724T220533Z.md` and
  `pbs-reprocessing-20260731T193413Z.md` nominate PBS reprocessing/crosswalk
  work that later completion and coverage reports show as shipped; their
  remaining operational and edition-precedence caveats are not new-family
  rankings.
- `next-backlog-ranking-20260805T161821Z.*` ranks VIC AFS/BPO first; both are
  complete. Later focused QLD/TAS/PDF rankings supersede it for those families.
- `next-structured-pack-selection-20260805T182251Z.md` and
  `vic-soce-admin-scope-20260805T212053Z.md` selected work that is complete.
- `qld-tas-next-backlog-ranking-20260806T171537Z.*` and its scope selection are
  superseded for TAS GGS and QLD RSF by completion/later PDF surveys.
- `pdf-ocr-next-backlog-ranking-20260806T185946Z.*` remains current for the TAS
  narrative runner-up, but its selected tabular rank is complete and its QLD
  risk assessment was superseded by the full QLD survey.
- `qld-backlog-rerank-20260807T142208Z.*`, `qld-family-selection-...`, and
  `qld-rsf-older-family-selection-...` are the newest curated family lineage.
  Their first two ranks are complete; their remaining order starts at MYFER.
- `qld-rsf-net-debt-borrowing-triage-...` is closed by
  `qld-rsf-net-debt-borrowing-validation-20260807T155907Z.md`.

## 8. Latest recommended next task

Run a dedicated, read-only-first corpus survey of **Queensland MYFER annual
editions**, classify stable table generations, and select the largest safe
text-extractable cluster before designing an adapter. This follows the newest
curated QLD order, stays within an already-acquired fiscal family, and avoids
guessing vintage semantics across many editions.

Classification: **PDF work**. No evidence says OCR is definitely required;
the correct first step is text-extractability and layout verification. It is
not structured-data work and does not depend on Cloudflare.

Cloudflare remains relevant only as an independent infrastructure ticket. It
should not be folded into the MYFER milestone unless that work introduces a
new hard-navigation route, which the existing GFS explorer pattern does not
require.
