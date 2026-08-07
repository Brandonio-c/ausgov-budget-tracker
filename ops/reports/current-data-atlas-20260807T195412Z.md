# Current data atlas

Generated: `2026-08-07T19:54:12Z`

Repository snapshot: branch `main`, commit `9652bfb` (equal to `origin/main` when inspected). The working tree was clean before this report was written.

## Purpose and evidence rules

This is a read-only atlas of what the repository currently ingests, what the database contains, and how much of that material the dashboard actually exposes. It does not treat “downloaded”, “registered”, “loaded”, “queryable”, and “visible in a dashboard hierarchy” as synonyms.

The principal evidence is:

- the live local database, `data/facts.db`, inspected on 2026-08-07;
- the latest generated coverage pair, [`ingestion-coverage-20260807T174612Z.md`](ingestion-coverage-20260807T174612Z.md) and [`ingestion-coverage-20260807T174612Z.json`](ingestion-coverage-20260807T174612Z.json);
- the final loop handoff, [`backlog-loop-final-20260807T175751Z.md`](backlog-loop-final-20260807T175751Z.md);
- current registry, lineage, measure-semantics, backend, and frontend code;
- focused implementation and validation reports named in the family sections below;
- fresh local API calls and a direct application of the frontend's ring-depth rules to representative trees.

Where a report and the live database differ, this atlas labels the older number rather than silently merging it with the current state. Counts from coverage rows must not be summed as database facts: source aliases and origin attribution can intentionally repeat a fact count across registry records.

## Executive summary

The local database is substantial but structurally uneven: **289,315 facts**, **222,575 nodes**, **14,167 breakdown edges**, and no populated `node_edges` or `lineage_edges`. Most volume is concentrated in a few flat or specialist families. The annual home dashboard therefore cannot turn raw fact volume into proportional ring depth.

For the requested federal comparison:

| View | FY | Default visible rings | Maximum frontend rings | Raw API depth after Commonwealth root | What actually supplies the depth |
|---|---:|---:|---:|---:|---|
| Federal actual | 2022-23 | 2 | 2 | 2 | ABS GFS functions and, for only three functions, subfunctions |
| Federal actual | 2023-24 | 2 | 2 | 2 | Same shape as 2022-23 |
| Federal actual | 2024-25 | 2 | 4 | 5 | ABS GFS plus explicitly related Statement 6/FBO/PBS, grants and procurement branches; raw navigation folders can collapse out of the ring count |
| Federal budget | 2022-23 | 2 | 2 | 2 | Five top portfolio/function branches and their children |
| Federal budget | 2023-24 | 2 | 2 | 2 | Thirteen top branches and their children |
| Federal budget | 2024-25 | 2 | 3 | 3 | Thirty-four top branches, PBS-derived children, and some related-source detail |

The clearest direct route to deeper federal **actual** rings is to investigate and, if sound, wire the already-loaded 2019-20 to 2023-24 FBO archive facts to their same-year ABS GFS nodes. The archive has 415 facts but no current breakdown edges; the relationship code correctly refuses to borrow 2024-25 detail for earlier years. That is a graph/mapping opportunity, not a request to relax year safety. PBS repair and mapping can deepen budget/related branches, while the structured MFS sibling workbooks and already-loaded Victorian output performance data are stronger candidates for specialist-explorer depth than for additive annual rings.

## 1. Current database state

Database file at inspection: `data/facts.db`, 661,381,120 bytes, modified 2026-08-07 13:38 EDT.

| Object | Current count | Interpretation |
|---|---:|---|
| `facts` | 289,315 | Published/current fact rows in the local build |
| `nodes` | 222,575 | 222,568 category nodes and 7 program nodes |
| `fact_nodes` | 289,315 | Exactly one primary node link per fact |
| `breakdown_edges` | 14,167 | 7,337 `same_group`; 6,830 `related_breakdown` |
| `node_edges` | 0 | Hierarchy is not broadly materialized here |
| `lineage_edges` | 0 | Lineage is retained elsewhere rather than as rows in this table |
| `source_documents` | 133 | Fact-bearing and supporting source-document records |
| `source_retrievals` | 185 | Retrieval records |
| `measure_definitions` | 101 | Measure metadata, including measures that may have no facts |
| `facts_pending_attribution` / quarantine | 36,417 | Rows deliberately not promoted to published facts |

Published fact quality labels are 264,625 `ok`, 24,616 null, 44 `published`, and 30 `validated`. Every current `facts.canonical_dataset_id` is null. Canonical-dataset membership is therefore a registry/config/report attribution, not a populated row-level key in this database.

The latest final handoff records zero current hard integrity failures, zero unresolved duplicate groups, zero orphan facts/nodes, and zero invalid breakdown edges. It retains six reviewed false-positive duplicate groups and three source documents without facts: `nsw_tcorp_weekly_bonds`, `qld_qtc_benchmark_bonds`, and `qld_qtc_weekly_outstandings_2026_07_17`. The 283 failures in `task9-sql-integrity-checks-20260803T221200Z.json` are a stale pre-hygiene baseline, superseded by [`database-hygiene-and-ci-hardening-final-20260804T230948Z.md`](database-hygiene-and-ci-hardening-final-20260804T230948Z.md) and the final loop handoff.

### Quarantine composition

The two dominant sources are `federal_pbs_programs_all` (35,601) and `federal_pbs_programs_s6_bridge` (801). Fourteen unattributed old rows are amount-null Gate 2 material from 2005-06/2006-07, and one row is `synthetic_demo` with no landing URL.

The largest reasons are malformed concatenated rows (13,062), table headers (7,664), repeated accounting headings (4,380), year-header concatenations (2,233), financial-statement lines (2,135), subtotals (1,828), and lower-case narrative fragments (1,631). These exclusions protect the dashboard from false categories, but also explain why acquired PBS pages do not translate one-for-one into visible program nodes. No current standalone `quarantine_report.*` exists; these numbers come from the current database, with semantic context from [`semantic-defect-milestone-final-report-20260803T223000Z.md`](semantic-defect-milestone-final-report-20260803T223000Z.md).

## 2. Registry and ingestion coverage

The latest coverage generator reports **367 registry records**, **126 mapping YAML files**, and this status distribution:

| Registry status | Sources | Local file implication |
|---|---:|---|
| `fully_ingested` | 52 | On disk and represented by a completed ingestion path |
| `partially_ingested` | 59 | On disk, with only a selected semantic/structural slice loaded |
| `adapter_missing` | 174 | Acquired/on disk, but no completed adapter |
| `adapter_broken` | 29 | Acquired/on disk, but the current adapter cannot safely load it |
| `reference_only` | 5 | On disk for terminology/index/reference use |
| `duplicate_source` | 29 | Alias or duplicate identity; do not count as separate data volume |
| `officially_unavailable` | 7 | No acquired local file |
| `not_acquired` | 12 | No acquired local file |

The 12 not-acquired entries include three Queensland machine-readable 2025-26 sources and nine convenience `*_related_view` targets. The seven officially unavailable entries are the AusTender weekly export, WA MyCouncil, WA tenders, SA Councils in Focus, SA tenders/contracts, the NT local grants return, and federal transparency PBS set 16. The five reference-only entries are the 2026-27 PBS index, Commonwealth balance-sheet guide, ABN resource index, ANZSIC, and COFOG.

### Fact-bearing source families

These are direct database counts by current `source_family`; unlike registry coverage totals, they do not deliberately repeat rows across aliases.

| Source family | Facts | Documents | FY span | Current character / visibility |
|---|---:|---:|---|---|
| `state_actuals` | 182,810 | 2 | 2000-01–2099-00 | Dominated by QLD QGIP; loaded but not the preferred state annual-home basis. The 2099-00 outlier needs source-level investigation. |
| `territory_actuals` | 46,714 | 1 | 2005-06–2026-27 | ACT invoice payments; large, flat cash-outflow corpus with no dedicated dashboard explorer |
| `budget` | 18,718 | 8 | 2013-14–2029-30 | PBS and related budget facts; annual budget tree uses a subset/graph projection |
| `procurement_contracts` | 16,255 | 3 | 2019-20–2026-27 | Contract explorer plus selected related branches; explorer is flat and capped per request |
| `local_actuals` | 7,983 | 4 | 2014-15–2024-25 | Annual local tree; identity depth varies by jurisdiction |
| `abs_gfs` | 3,401 | 17 | 2008-09–2024-25 | Core annual actuals/debt/revenue basis |
| `mfs_aggregates` | 3,354 | 1 | 2000-01–2025-26 | Dedicated MFS explorer; 14 fact-bearing measures, monthly July–May |
| `abs_gdp_tax` | 2,577 | 26 | 2015-16–2024-25 | GDP/GSP/GVA/tax ratio modes |
| `grant_awards` | 2,486 | 1 | 2024-25 | Related graph material, no dedicated grants explorer |
| `abs_gfs_operating_statement` | 1,220 | 16 | current series | GFS statement facts, generally presented as flat series |
| `abs_gfs_balance_sheet` | 1,120 | 16 | current series | GFS balance-sheet facts, generally presented as flat series |
| `handoff_actuals_state` | 702 | 6 | 2002-03–2028-29 | Native QLD/TAS/VIC specialist families |
| `final_budget_outcome` | 500 | 2 | 2019-20–2024-25 | 2024-25 graph-connected; 2019-20–2023-24 archive loaded but not graph-connected |
| `federal_actuals` | 381 | 1 | 2005-06–2025-26 | Accrual function actuals; annual UI prefers GFS when available |
| `state_budget` | 281 | 7 | 2024-25–2029-30 | Annual state budget mode |
| `local_government` | 214 | 1 | current series | Local specialist facts |
| `state_borrowing` | 170 | 7 | 2023-24–2026-27 | Debt mode and GFS liabilities; mixed valuation/date safeguards apply |
| `budget_historical_aggregates` | 154 | 3 | 1970-71–2029-30 | Long federal aggregate series |
| `contracts` | 142 | 1 | current series | Additional contract source |
| `recipient_statistics` | 52 | 1 | current series | Related recipient statistics |
| `aofm_cgs` | 50 | 3 | current series | Federal debt securities |
| `budget_paper_1` | 26 | 1 | current series | Budget aggregates |
| `superannuation` | 3 | 1 | current series | Small specialist series |
| `synthetic` | 2 | 1 | test/demo | Not substantive coverage |

The ten largest individual documents reinforce the concentration: QLD QGIP has 180,917 facts, ACT invoices 46,714, the combined PBS source 17,482, NSW procurement 7,853, QLD contracts 6,908, MFS aggregates 3,354, NSW local 2,794, TAS local 2,600, GrantConnect 2,486, and SA GFS 1,893.

## 3. Canonical and compatibility controls

`config/lineage/canonical_datasets.yaml` declares seven canonical/target datasets, not an exhaustive inventory:

| Declared dataset | Declared state | Reported current facts | Important qualification |
|---|---|---:|---|
| ABS GFS Table 4 expenses | full | 230 | Canonical federal annual expense basis |
| ABS GFS Table 1 revenue | partial | 230 | Config points at the same source key as expenses, while the database's federal revenue source is `abs_gfs_commonwealth_130_revenue`; attribution needs correction/clarification |
| ABS taxation revenue detail | partial | 2,530 | Ratio/revenue detail rather than annual spending hierarchy |
| Federal PBS programs | partial | 18,029 | 17,482 combined source plus 472 bridge, 60 DSS, and 15 Health facts |
| Federal Statement 6 | partial | 657 | Crosswalk/related detail, not a complete additive extension |
| Federal FBO Appendix A | full | 85 | This “full” label applies to the configured 2024-25 target, not the entire historical FBO corpus |
| State borrowing authorities | partial | 170 | Seven loaded authorities, with other acquired sources still missing or broken |

[`ingestion-coverage-lineage.md`](ingestion-coverage-lineage.md) observes 129 source keys but predates or omits several later dedicated products (MFS, VIC, TAS and QLD). Its canonical status is declarative, not a comprehensive current-data truth table. The database's null `canonical_dataset_id` values further mean that consumers must not infer row-level canonical membership from that column.

`config/compatibility/view_families.yaml` governs the annual home modes: actuals, budget, debt, revenue, and GDP/GSP/GVA/ratio families. It intentionally does not fold MFS, QLD RSF/MYFER, TAS GGS, or VIC AFS/BPO series into an annual additive tree simply because the numbers share a jurisdiction and year.

## 4. Family atlas: acquired, loaded, and visible

### Federal PBS, Statement 6, and FBO

- **Acquired/loaded:** 18,029 PBS-attributed facts across the combined set and bridge/dedicated sources. The generalized PBS extractor and reload path exist. The current registry has 59 per-source PBS records plus an older alias; historical reports refer to 60 retained origin IDs and 63 original documents.
- **Partial/broken:** `federal_pbs_2026_27_ndia` is an acquired PDF with a broken adapter and zero facts. Six records are duplicate aliases. The HTML index is reference-only. The 36,402 PBS/bridge quarantine rows are primarily headings, statements, fragments, and malformed concatenations.
- **Graph semantics:** after semantic cleanup, the live database has 5,119 related PBS/Statement 6 crosswalk edges. Earlier crosswalk reports with much larger counts are pre-cleanup and should not be read as current. Historical ambiguity reports identify the Attorney-General's/Infrastructure mega-portfolio (1,376 nodes) and Parliamentary (657) as substantial unmapped areas; those counts describe the pre-cleanup audit, not a current live-node recount.
- **Visible:** PBS is directly visible in the federal budget tree and can appear as non-additive related detail below 2024-25 federal actual functions. There is no dedicated PBS explorer. Related branches are explicitly kept out of additive sibling totals.
- **Evidence:** [`pbs-per-source-lineage-implementation-20260807T174640Z.md`](pbs-per-source-lineage-implementation-20260807T174640Z.md), [`pbs-statement6-crosswalk-final-report-20260801T071500Z.md`](pbs-statement6-crosswalk-final-report-20260801T071500Z.md), and current database queries.

FBO has 500 facts: 415 archive facts for 2019-20 through 2023-24 and 85 for 2024-25. Only the 2024-25 source currently participates in graph edges. The archive is present but not wired into the annual graph, and the annual actual selector prefers GFS over standalone accrual/FBO sources. Twenty-one pre-2019 PDFs are acquired/readable but remain adapter-unsafe; 1985–1987 material remains external.

### Federal MFS

- **Loaded:** 3,354 aggregate facts across 26 fiscal years (2000-01–2025-26), 14 fact-bearing measures, actual series, July–May only. The API exposes 15 definitions; `mfs_stock_cash_and_deposits` is a reserved definition with no facts.
- **Visible:** dedicated `/v2/mfs` API and MFS explorer. It is not an annual-home ring source.
- **Remaining structured corpus:** five acquired XLSX siblings—monthly profiles, Note 3 function, balance sheet, operating statement, and tax Notes 1/2—have no completed adapters. “MFS full” therefore means full for the selected aggregates workbook/slice, not full coverage of the MFS publication family.
- **Evidence:** [`mfs-full-validation-20260805T042424Z.md`](mfs-full-validation-20260805T042424Z.md), [`mfs-corpus-inventory-20260804T234455Z.md`](mfs-corpus-inventory-20260804T234455Z.md).

### Tasmania

- **Loaded:** 232 TAFR/GGS facts, ten measures, 2007-08–2028-29, with actual, budget, revised and forward observations. The path combines structured GGS data, tabular PDF backfill for 2010-11/2011-12, and narrative transition extraction for 2007-08–2009-10.
- **Acquired:** approximately 90 assets, including PDFs and one XLSX. A plural registry alias remains marked `adapter_missing` although the singular canonical identity is fully ingested; this is registry identity noise, not an unrepresented second family.
- **Excluded:** 2003-04–2006-07 is deferred because the pre-AASB 1049 presentation is semantically incompatible, not because OCR is unavailable.
- **Visible:** dedicated TAS GGS selection in the GFS explorer, as flat series rather than nested rings. Current UI copy says 2013-14–2028-29, but the API returns 2007-08 onward.
- **Evidence:** [`tas-tafr-narrative-implementation-20260807T173331Z.md`](tas-tafr-narrative-implementation-20260807T173331Z.md), [`tas-ggs-production-verification-20260806T174153Z.md`](tas-ggs-production-verification-20260806T174153Z.md).

### Victoria

| Product | Loaded | Scope | Visibility | Remaining/excluded |
|---|---:|---|---|---|
| AFS | 22 facts, 11 measures | 2023-24 and 2024-25 XLSX | Dedicated VIC AFS GFS toggle | 88 loader-specific rows deferred/quarantined outside the global DB quarantine; six structured sheets (equity, outputs, appropriations and administered statements) require separate semantics |
| BPO | 40 facts, 20 measures | 2024-25 actual/budget; base plus SOCE/admin | Dedicated VIC BPO toggle | Selected budget statement product, not all workbook content |
| Output performance | 14 facts, one measure, seven output nodes with actual/budget | 2024-25 output appropriations | Generic `/v2/tree` can return all seven nodes and $459.3m | No frontend toggle/route; 70 non-dollar KPI rows intentionally deferred |

Evidence: [`vic-afs-deferred-sheets-inventory-20260807T175300Z.md`](vic-afs-deferred-sheets-inventory-20260807T175300Z.md), [`vic-bpo-full-validation-20260805T193510Z.md`](vic-bpo-full-validation-20260805T193510Z.md), and [`vic-output-performance-implementation-20260807T173750Z.md`](vic-output-performance-implementation-20260807T173750Z.md).

### Queensland

| Product | Acquired / loaded state | Scope | Visibility and limits |
|---|---|---|---|
| RSF | Full selected-series load: 364 facts, 14 measures, 23 years (2002-03–2024-25), actual and estimated actual | Large PDF/XLSX corpus (188 registry assets) | Dedicated QLD RSF GFS toggle; UI copy says 2018-19 onward although API coverage starts 2002-03 |
| MYFER | Partial selected-edition load: 30 facts, five measures, six years (2015-16–2018-19 and 2025-26) | Six text-extractable editions | Dedicated QLD MYFER GFS toggle; other editions have format drift, 2002-03 needs OCR, and debt was out of selected scope |
| Consolidated Fund / CFFR | 46 PDFs: 15 annual and 31 quarterly; all text-extractable; CFFR is the same 25-asset subset, not a separate family | Gross cash/Public Account, period and vintage semantics | No adapter, semantics, DB facts, API or UI; needs a new product model rather than reuse of accrual/GFS rings |
| On-time payment | 42 CSVs, 2020-21–2025-26 | Compliance/payment timeliness | No adapter or UI; suitable for a separate structured product |
| QGIP | 180,917 facts | Deep program/project corpus | Loaded under accrual actuals, but hidden from annual state home when the preferred GFS basis exists; no dedicated QGIP explorer. Known amount-column and missing-subprogram defects require caution |

Evidence: [`qld-rsf-production-verification-20260807T145510Z.md`](qld-rsf-production-verification-20260807T145510Z.md), [`qld-myfer-validation-20260807T171548Z.md`](qld-myfer-validation-20260807T171548Z.md), [`qld-consolidated-fund-inventory-20260807T174900Z.md`](qld-consolidated-fund-inventory-20260807T174900Z.md), [`qld-cffr-identity-triage-20260807T175500Z.md`](qld-cffr-identity-triage-20260807T175500Z.md), and [`qld-on-time-payment-inventory-20260807T175100Z.md`](qld-on-time-payment-inventory-20260807T175100Z.md).

### State borrowing

Seven loaded authority sources contribute 170 facts: NSW TCorp bonds (36), QLD QTC AUD (38), SA SAFA (18), VIC TCV (32), WA WATC (21), TAS TASCORP (8), and NT strategy (17). Three acquired records are broken/zero-fact—the two TCorp/QTC sources named in the integrity section plus QTC weekly outstandings—and other acquired borrowing sources remain adapter-missing.

The loaded data appears in state Debt mode (measured maximum ring depth 5 for the latest available tree) and generic GFS liabilities. Valuation basis and observation-date rules intentionally prevent naïve aggregation across issuers.

### Other large loaded families

- **ABS GFS:** 5,741 facts across expense, revenue and liability documents when the related GFS source families are combined. This is the canonical annual home basis and is structurally shallow: functions/subfunctions or flat statement lines.
- **ACT invoices:** 46,714 loaded cash-outflow facts with no dashboard mode or dedicated explorer.
- **Procurement:** 16,397 facts across the two contract families. The Contracts explorer returns a flat list and limits a year request to 200 records; selected federal procurement categories/suppliers can also appear as related 2024-25 actual branches.
- **GrantConnect:** 2,486 FY2024-25 facts, available as related graph material but without a grants explorer.
- **Local actuals:** 7,983 facts in the annual local tree; hierarchy quality and entity identity differ by source.
- **Federal accrual actuals:** 381 facts span 2005-06–2025-26, but the home years endpoint globally prefers GFS, so its normal federal actual dropdown offers 2008-09–2024-25. The 2005-06–2007-08 facts are directly queryable but not offered through that selector.

### Named-family implementation matrix

This matrix makes the source identity and pipeline distinctions explicit. “Adapter/loader/semantics” describes repository capability, not merely a registry label. A source count is a registry/source-document count; an asset count is the number of acquired files or captured assets reported by the family inventory.

| Family | Source identities and counts | Format / on-disk state | Adapter, loader and semantics | Current status | Next-step class |
|---|---|---|---|---|---|
| Federal PBS | 59 current per-source registry records using `federal_pbs_<year>_<portfolio>` plus `federal_pbs_programs_all`, `federal_pbs_programs_s6_bridge`, `federal_dss_pbs_2026_27`, and `federal_health_disability_ageing_pbs_2026_27`; six duplicate aliases and one index reference | PDFs on disk; HTML index/reference | Reusable generalized extractor/reloader; program semantics and related Statement 6 crosswalk exist | Partial; 18,029 attributed facts; NDIA 2026-27 broken; large semantic quarantine | Internal adapter repair plus graph/semantic mapping |
| Federal FBO | Loaded `federal_budget_archive_function_series` (six PDFs) and `federal_fbo_2024_25_function_subfunction` (one PDF), plus duplicate alias `federal_fbo_appendix_a_2024_25` | PDFs; 21 pre-2019 files plus loaded later archive/current material | Current 2024-25 mapping/loader and graph semantics exist; historical parser/graph coverage is incomplete | Full only for configured 2024-25 Appendix A target; historical family partial | Graph/model repair for 2019-24; internal adapter work for pre-2019 |
| Federal MFS | Six XLSX identities: `federal_mfs_aggregates`, `federal_mfs_monthly_profiles`, `federal_mfs_note3_function`, `federal_mfs_balance_sheet`, `federal_mfs_operating_statement`, `federal_mfs_tax_notes_1_2` | Six acquired XLSX workbooks | Reusable aggregate extractor/loader, revision semantics, dedicated API/UI for aggregates; no adapters for five siblings | Aggregates full; publication family partial | Internal structured-data adapters and specialist UI expansion |
| TAS TAFR/GGS | Canonical `tas_treasurer_annual_financial_reports` (90 PDF/XLSX assets); duplicate plural `tas_treasurers_annual_financial_reports` (89 PDFs) | On disk | Reusable structured GGS, tabular PDF and narrative-transition extractors; loader, semantics, API/UI exist | Canonical family full for selected compatible 2007-08 onward series; alias status misleading; pre-2007 deliberately deferred | Registry hygiene; deliberate semantic deferral |
| VIC AFS | DB source `vic_annual_financial_statements_2024_25`; registry also has PDF `vic_financial_report_2024_25` as a distinct adapter-missing source | One selected XLSX loaded; PDF acquired | Workbook-specific reusable extraction/loader and 11-measure semantics; API/UI exist | Selected statement slice full; workbook/publication family partial | Semantic design for six remaining structured sheets |
| VIC BPO | DB source `vic_budget_portfolio_outcomes_2024_25` | One XLSX on disk | Loader and base/SOCE/admin semantics; dedicated API/UI exist | Selected BPO product full | Maintenance or deliberate scope expansion |
| VIC Output Performance | `vic_output_performance_measures_2024_25` (one XLSX) | On disk | Extractor/loader and dollar output semantics exist; generic tree API works | Ingested, but UI-unsurfaced; non-dollar KPIs deferred | UI surfacing; semantic redesign for KPIs |
| QLD RSF | DB source `qld_report_on_state_finances_actuals`; RSF inventory covers 188 PDF/XLSX assets | On disk | Reusable selected-series extractor/loader, 14-measure semantics, dedicated API/UI exist | Full for selected compatible actual/estimated-actual series; broader editions remain outside adapter scope | Internal adapter extension or deliberate deferral |
| QLD MYFER | DB source `qld_myfer`; six selected PDF editions loaded from the larger acquired series | PDFs on disk | Text-table extraction/loader, five-measure semantics, dedicated API/UI exist | Partial by edition and selected measure; 2002-03 OCR and other layout variants deferred | Internal format adapters; OCR only for the identified old edition |
| QLD Consolidated Fund | `qld_consolidated_fund_reports`, 46 PDFs (15 annual, 31 quarterly) | On disk and text-extractable | No adapter, loader, semantic model, API or UI | Acquired, not ingested | Semantic redesign/new product, then internal adapter/UI |
| QLD CFFR | `qld_cffr`/CFFR-labelled inventory references 25 of the same Consolidated Fund assets | On disk; not a separate corpus | None | Duplicate identity, not a separate backlog family | Registry/identity normalization |
| QLD on-time payment | `qld_on_time_payment_reports`, 42 CSVs | On disk | No adapter, loader, semantic model or UI | Acquired, not ingested | Internal structured-data/new-product work |
| QLD QGIP | `qld_qgip_expenditure`, 15 CSV/PDF assets | On disk | Mapping/loader exists; program/project semantics need defect repair; no dedicated UI | Fully ingested by coverage status, but not presentation-ready as a deep specialist surface | Data/semantic repair, then UI surfacing |
| State borrowing | 16 identified handoff state-debt registry sources: seven loaded, six adapter-missing, three adapter-broken | CSV, XLSX, PDF and ZIP assets on disk | Seven mapping/loader paths and borrowing semantics exist; shared debt UI exists | Partial family | Internal adapter repair/extension; preserve valuation/date rules |
| ABS GFS | `abs_gfs_commonwealth_130` plus state/local table identities and revenue/liability derivatives; 17 GFS-actual registry sources are full, one is missing | ZIP/XLSX on disk for loaded sources | Reusable table mappings/loaders, GFS measure semantics, annual modes and GFS explorer | Canonical aggregate baseline substantially ingested; deliberately shallow by publication grain | External/source-grain limit for program depth; internal maintenance |
| Procurement / contracts | Current loaded core includes NSW procurement, QLD contracts and AusTender/OCDS-derived sources; coverage records three full, four missing and three unavailable in `procurement_contracts` | CSV/JSON/XLSX/PDF mix per registry; acquired files exist for missing adapters | Source-specific mappings/loaders and contract semantics; Contracts explorer and related graph paths exist | Partial family | Internal adapters for acquired sources; external acquisition for unavailable sources |

`config/procurement_sources.yaml` is a source/research manifest, not proof of ingestion. It defines traceability tiers 1–5 and the critical separation rule that estimates, appropriations, accrual expenses, cash payments, contracts, grants, counts and forecasts must not be summed without an explicit bridge. The current coverage report and database—not presence in that YAML—determine the status in the matrix above. Measure semantics used by the loaded specialist families are defined in `config/measure-semantics/*.yaml` and the family reports; merely having a YAML definition does not prove that every workbook sheet or edition is loaded.

### Remaining blocker classification

| Missing-depth area | Dominant blocker | Why |
|---|---|---|
| Federal actual 2019-20–2023-24 below GFS subfunctions | Graph/model repair | Same-year FBO facts exist, but edges and a validated reconciliation do not |
| Federal actual before the GFS window | Compatibility and UI selection | Accrual facts exist, but the annual selector prefers the comparable GFS family |
| PBS program coverage | Internal adapter + semantic mapping | One acquired source is broken; malformed/non-category rows are quarantined; some genuine portfolio links remain unresolved |
| MFS detail beyond aggregates | Internal repo work | Five structured workbooks are acquired, but adapters and product-specific measures are absent |
| TAS before 2007-08 | Deliberate deferral / semantic redesign | Pre-AASB 1049 presentation is not safely comparable |
| VIC AFS remaining sheets | Semantic redesign | Structured rows exist, but equity, appropriation, output and administered measures are not interchangeable |
| VIC Output Performance visibility | UI surfacing | Dollar facts, nodes and generic API output already exist |
| QLD QGIP deep visibility | Data/semantic repair + UI | Loaded corpus has known field/subprogram defects and no tailored explorer |
| QLD Consolidated Fund | Semantic redesign/new product | Cash account, reporting period and publication-vintage semantics do not fit current accrual rings |
| QLD on-time payment | Internal repo work/new product | Structured CSVs are acquired but have no pipeline or surface |
| Missing/broken state borrowing sources | Internal adapter work | Assets are present; valuation and observation-date semantics make generic parsing unsafe |
| Officially unavailable procurement/local sources | External acquisition | No local asset exists and the official source is unavailable |

## 5. Dashboard surface and structural limits

The frontend has annual home, combined, timeline, legacy, search, and explorers for GFS, MFS and contracts. Dedicated backend routers additionally serve QLD MYFER/RSF, TAS GGS and VIC AFS/BPO/SOCE-admin. Victorian output performance is queryable through the generic tree endpoint but lacks a frontend selection.

The annual home initializes at `ringDepth = 2`. It computes a greater maximum where valid additive/related structure exists, with an absolute safety ceiling of 32. More than eight children are presented as seven named children plus “Other”; this preserves navigation but makes some loaded categories less immediately visible. A child hierarchy is admitted only when it approximately partitions the parent, and implausibly dominant children (over roughly 125% of the parent) can be rejected. Related Statement 6/FBO folders are non-additive and excluded from sibling totals.

Related traversal is capped at eight backend levels and may use the nearest earlier fiscal year, never a future one. That policy is decisive for 2022-23 and 2023-24: current FBO/Statement 6 graph targets are 2024-25, and the system correctly will not attach them to earlier selected years.

### Fresh representative depth measurements

These figures were measured against the current local API and frontend depth algorithm; they are not copied from an old screenshot audit.

| Branch | Current observation |
|---|---|
| Federal actual 2022-23 | $639.703b; 11 first-ring functions. Only Health (6), Education (3), and General public services (2) expose a second category ring; the rest stop at the function. Maximum two rings. |
| Federal actual 2023-24 | $687.277b; the same two-ring ABS GFS shape. |
| Federal actual 2024-25 | $745.030b; 11 functions; raw node counts by depth after the root are 58, 85, 35 and 108 through depth 5. Frontend maximum is four rings because synthetic/navigation folders are skipped or collapsed. Example deepest paths include Defence → Contracts → UNSPSC category → supplier. |
| Federal budget 2022-23 | $1.629b; five first branches and 82 children; maximum two rings. Some labels resemble financial-statement fragments and warrant semantic caution. |
| Federal budget 2023-24 | $1.818tn; 13 first branches and 722 children; maximum two rings, with similar label-quality concerns. |
| Federal budget 2024-25 | $5.461tn; 34 first branches, 1,949 second-level and 714 third-level nodes; maximum three rings. This is a mixed portfolio/function/related-source graph, not one clean additive hierarchy. |
| State actual, latest | Maximum four frontend rings; raw API depth six. QLD/TAS home branches are ABS GFS, not their native RSF/TAFR series. |
| Local actual, latest | Maximum four frontend rings; raw API depth five. |
| State revenue, latest | Maximum/raw depth four. |
| State debt, latest | Maximum/raw depth five. |
| State budget, latest | Maximum three frontend rings; raw API depth four. |

The latest automated audit, [`dashboard-api-audit-20260807T174624Z.md`](dashboard-api-audit-20260807T174624Z.md), reports zero hard failures over six audited paths and seven PBS cases. The final loop also records 553 passing tests, frontend `lint:ci` passing its accepted 25-error/13-warning baseline, a successful 12-page build, and 21/21 end-to-end tests. This is good operational evidence, but not evidence that every source family has a tailored surface.

## 6. Why dashboard depth is limited: top five causes

1. **The annual UI begins at two rings.** Deeper current branches, including four-ring federal actual 2024-25 and five-ring state debt, require user expansion; loaded depth is not all initially visible.
2. **Historical graph coverage is year-specific and incomplete.** Federal actual 2022-23 and 2023-24 end at ABS GFS function/subfunction nodes. The 415 same-era FBO archive facts are in the database but have no breakdown edges, while safeguards correctly reject future 2024-25 detail.
3. **Compatibility boundaries intentionally separate unlike products.** MFS cash aggregates, RSF/MYFER fiscal statements, TAS/VIC native statements, procurement, grants and invoices cannot safely become additive children of annual expenditure merely because their years or jurisdictions overlap.
4. **Most loaded volume is flat rather than hierarchical.** The database has no populated generic `node_edges`, and only 14,167 explicit breakdown edges against 222,575 nodes. QGIP, invoices, contracts, specialist statements and measure-per-series products therefore create fact depth without automatically creating ring depth.
5. **Adapters and semantic exclusions still remove potential detail.** Five structured MFS siblings lack adapters; PBS has one broken current source and 36,402 quarantined rows; pre-2019 FBO parsing is unsafe; and many acquired state/local/debt sources remain missing or broken. Conservative partition, dominance, valuation and quality rules then suppress unsafe nesting.

The seven-plus-Other fold and the absence of dedicated explorers for some loaded families are additional visibility limits, but they are presentation issues rather than the primary cause of shallow federal 2022-23/2023-24 trees.

## 7. Families most likely to yield more visible depth

Ranked by likely visible gain, while distinguishing annual rings from specialist products:

1. **Historical FBO archive → same-year federal actual graph (annual rings).** The data is already loaded for 2019-20–2023-24. A source/year/function crosswalk audit could determine whether the 415 facts can safely attach under same-year ABS GFS nodes. This is the best evidenced candidate for closing the conspicuous 2022-23/2023-24 versus 2024-25 depth gap.
2. **PBS/Statement 6 mapping and the broken 2026-27 NDIA source (budget and related rings).** Repairing the broken source and resolving genuine portfolio mappings can increase program-level visibility. It must not restore quarantined headings or pretend related values are additive.
3. **MFS structured sibling workbooks (dedicated explorer depth).** Five acquired XLSX products can add functional, statement, balance-sheet and tax-note dimensions to an already mature MFS explorer. This is structured-data work and should remain a specialist product.
4. **Victorian output performance (immediate specialist visibility).** Fourteen facts and seven nodes are already queryable. A frontend route/toggle would surface them with little ingestion work, though it adds breadth rather than additional ring levels. Non-dollar KPIs need a separate measure design.
5. **QLD QGIP repair and dedicated exploration (specialist hierarchy).** Its 180,917 loaded facts represent the largest latent project/program corpus, but known amount-column and missing-subprogram defects make verification a prerequisite. It should not displace GFS in the annual actual tree without an explicit basis decision.
6. **QLD Consolidated Fund and on-time payment families (new products).** Both corpora are acquired and text/CSV-readable, but each needs new period, vintage and measure semantics plus a dedicated surface. They are high-value breadth opportunities, not quick annual-ring additions.

## 8. Main ingested categories that do not surface deeply enough

| Loaded category | Evidence of ingestion | Current visibility gap |
|---|---|---|
| QLD QGIP programs/projects | 180,917 facts | Annual state tree prefers GFS; no dedicated QGIP explorer; known semantic defects |
| ACT invoice payments | 46,714 facts | No annual mode or invoice explorer |
| Procurement contracts | 16,397 facts | Flat capped explorer; only selected federal related branches become deep navigation |
| Historical FBO | 415 facts for 2019-20–2023-24 | Present but not graph-wired; does not deepen those actual years |
| GrantConnect awards | 2,486 facts | Related 2024-25 paths only; no dedicated grants explorer |
| Federal accrual actuals | 381 facts, including 2005-06–2007-08 | GFS preference removes early years from normal home selection |
| VIC output performance | 14 facts / seven nodes | API-only; no frontend route/toggle |
| Local actuals | 7,983 facts | Visible, but entity/category identity and hierarchy remain uneven by jurisdiction |

## 9. Recommended research questions

### Immediate, evidence-led

1. Can each 2019-20–2023-24 FBO archive function/subfunction be mapped to an ABS GFS node for the **same fiscal year and compatible accounting basis**, with reconciliation tolerances documented?
2. Are the archive FBO node identifiers merely missing edges, or do their labels/measure definitions first need normalization to avoid false partitions?
3. Which PBS nodes remain unmapped after the current semantic cleanup, by source origin and portfolio—not by stale pre-cleanup aggregate counts?
4. Can `federal_pbs_2026_27_ndia` be repaired with the generalized extractor, and what exact layout divergence caused `adapter_broken`?
5. Which MFS sibling workbook offers the highest user value per semantic risk: Note 3 function, balance sheet, operating statement, tax notes, or monthly profiles?

### Visibility and product design

6. Should Victorian output performance get a small dedicated explorer now, or be combined with a broader non-dollar KPI design?
7. What is the safest dedicated QGIP view after correcting amount-column and missing-subprogram defects, and how should it signal that it is not GFS?
8. Should ACT invoices and GrantConnect receive dedicated searchable explorers rather than being forced into ring metaphors?
9. Can the frontend show “two of four rings” and explain related/non-additive branches so users recognize available depth without confusing it with additive decomposition?
10. Should stale TAS and QLD explorer coverage copy be generated directly from API availability rather than hard-coded?

### Registry and evidence hygiene

11. Should canonical dataset attribution be populated at fact level, or should the null column be removed/explicitly documented as unused?
12. Why does the revenue canonical declaration reference the expense source key, and what is the intended row-level relation to `abs_gfs_commonwealth_130_revenue`?
13. Can duplicate registry identities such as the TAS singular/plural pair be normalized so coverage status does not imply a missing second adapter?
14. Is the 2099-00 fiscal-year value in `state_actuals` a legitimate source forecast, a label conversion defect, or a sentinel?

## 10. Evidence insufficiencies and cautions

- There is no current standalone quarantine report; quarantine counts in this atlas are live database queries, while reasons are interpreted with older semantic reports.
- The latest file named as a SQL integrity check is a stale failure baseline. Current zero-failure evidence is recorded in later narrative/final reports rather than a newly timestamped equivalent JSON artifact.
- The canonical lineage report is not exhaustive and contains at least one apparent revenue/source-key misalignment. It cannot stand alone as the data atlas.
- Registry status can disagree with practical family state because of duplicate aliases and broad versus canonical identities (notably TAS and some QLD families).
- The dashboard audit covers six paths and seven PBS cases, not every jurisdiction/mode/year permutation. This atlas freshly measured the requested federal years and selected latest state/local branches, but did not claim an exhaustive all-combinations crawl.
- Raw file formats and schemas for all 367 registry entries were not individually reopened; acquisition and format statements rely on the current registry and focused family inventories.
- Historical ambiguity counts in PBS reports predate semantic cleanup. They are retained only as historical scope indicators.
- Budget totals and labels reflect the current mixed source graph; they should not be interpreted as a reconciled, exclusively additive economic aggregate without source-specific validation.
- The local database is a workspace artifact and may not be tracked as a reproducible release asset. Counts describe this inspected snapshot.

## 11. Bottom line

The dashboard is not shallow because the repository lacks data. It is shallow because most data is flat, specialist, semantically incompatible with annual expenditure nesting, not yet graph-wired by year, or deliberately quarantined. Federal actual 2024-25 demonstrates that four safe visible rings are already possible. Federal actual 2022-23 and 2023-24 remain at two because their same-year FBO archive facts are not connected and future detail is correctly prohibited.

The recommended next investigation is therefore **same-year FBO archive graph coverage for 2019-20–2023-24**, beginning with a reconciliation/crosswalk audit rather than loading new data. If that audit proves the basis incompatible, the best next structured-data expansion is one of the acquired MFS sibling XLSX products; the quickest already-ingested visibility win is the Victorian output-performance frontend surface.
