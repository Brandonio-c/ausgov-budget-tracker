# AusGov Budget Tracker: source research and ingestion plan

Researched: 2026-07-20

## Executive finding

The missing drill-down is not only a source-coverage problem. The current application schema is structurally unable to hold the depth available in Australian public finance documents. It stores one row with category, optional subcategory and optional department, while a useful public lineage often needs:

`function -> subfunction -> portfolio -> entity -> outcome -> program -> component -> appropriation or special account -> grant/contract/invoice/payment aggregate`

The immediate data wins are:

1. Ingest Budget Paper No. 1 function/subfunction tables and Portfolio Budget Statements for federal drill-down.
2. Ingest the direct ABS Government Finance Statistics XLSX workbooks for all Commonwealth, state and local aggregate coverage.
3. Add state budget/actual documents and council-level raw returns for NSW, Victoria, Tasmania, Western Australia and South Australia.
4. Add transaction-like sources separately: AusTender, GrantConnect, Queensland QGIP payments, ACT notifiable invoices and NT awarded contracts.
5. Replace the fixed three-level model with arbitrary-depth nodes and explicit measure/accounting-basis fields before mixing these datasets.

The accompanying files are:

- `ausgov_budget_candidate_sources.yaml`: a machine-readable registry of official candidate sources, parser approaches and caveats.
- `ausgov_budget_hierarchical_schema.sql`: a SQLite-compatible provenance-first schema draft.

## What is happening in the deployed FY2025-26 federal view

The displayed federal value is a year-to-date actual, not a final annual total. The May 2026 Monthly Financial Statements report social security and welfare at AUD 269.505 billion year-to-date, against a revised full-year estimate of AUD 297.805 billion. Total expenses are AUD 724.902 billion year-to-date versus AUD 812.063 billion for the full-year revised estimate.

Source: [Department of Finance monthly statement for May 2026](https://ministers.finance.gov.au/financeminister/media-release/2026/06/26/australian-government-general-government-sector-monthly-financial-statements-may-2026), Note 3.

The current parser chooses the last non-null monthly YTD column and writes it as the row amount. That is valid as a latest-YTD series, but the user interface should label it `actual_accrual_expense / year_to_date / through May`, not simply FY2025-26. It should sit beside, not replace, a full-year budget estimate and a later Final Budget Outcome actual.

## Federal social security: the drill path already exists in official documents

### Functional spine

For 2026-27, Budget Paper No. 1 Statement 6 publishes social security and welfare at AUD 308.737 billion and splits it into: assistance to the aged AUD 115.601 billion; veterans and dependants AUD 11.366 billion; people with disabilities AUD 98.143 billion; families with children AUD 53.863 billion; unemployed and sick AUD 18.304 billion; other welfare AUD 1.853 billion; Indigenous Australians not elsewhere classified AUD 3.540 billion; and general administration AUD 6.067 billion.

Source: [Budget Paper No. 1, Statement 6](https://budget.gov.au/content/bp1/download/bp1_bs-6.pdf), Table 6.9 and Appendix A.

Statement 6 also gives major program expense and cash-payment views. For example, the 2026-27 NDIS line is AUD 56.124 billion as an expense estimate and AUD 55.117 billion as a payment estimate. Those two values must be stored as different measure types, because the source explicitly distinguishes accrual expenses from cash-equivalent payments.

### Portfolio, entity, outcome, program and component spine

The 2026-27 PBS index points to each portfolio. Social security and welfare spans at least Social Services, Health/Disability/Ageing and Veterans Affairs. The Health, Disability and Ageing PBS includes a dedicated NDIA entity section and separate downloadable NDIA PBS. The Social Services PBS contains programs such as Support for Seniors, Financial Support for People with Disability and Financial Support for Carers. DVA PBS supplies veterans programs.

For the exact FY2025-26 drill-down requested in the app, the archived Social Services PBS demonstrates the hierarchy. Its Department of Social Services Program 3.2, National Disability Insurance Scheme, records a 2025-26 total program expense of AUD 39.174472 billion, including Component 3 participant plans of AUD 36.742521 billion and Component 5 NDIA agency costs of AUD 2.428247 billion.

Source: [Social Services PBS 2025-26](https://www.dss.gov.au/system/files/documents/2025-03/2025-26social-servicespbsaccessible.pdf), Table 2.3.2, pages 55-57 of the Department of Social Services section.

That PBS total should not be forced to equal the Budget Paper top-program figure. The documents have different scopes, flows, eliminations, state contributions and accounting presentations. Store each source fact independently and add explicit reconciliation edges. A mismatch is evidence to explain, not a number to overwrite.

### Actuals and payment detail

Use the Final Budget Outcome for final annual function/subfunction actuals, Commonwealth Consolidated Financial Statements and entity annual reports for audited controls, and the Transparency Portal for entity reporting. For NDIS, the public payments CSVs and quarterly reports are the best public bridge below program level because they expose aggregated payments by support category, geography and cohort. DSS/Services Australia recipient datasets add counts and geography, but generally not individual dollar payments.

### Recommended federal lineage

A defensible path for a node in the app is:

`Monthly YTD or FBO actual -> function -> subfunction -> major program -> portfolio -> entity -> outcome -> program -> component -> appropriation/special account -> aggregate payments or award/contract records`

The source locator shown on hover should include document title, release/version, table, page or sheet/cell, column heading, original unit, file SHA-256 and retrieval time.

## What "trace every dollar" can and cannot mean publicly

A public tracker can get much closer to dollar lineage, but it cannot truthfully expose every internal ledger transaction. The practical public ceiling is:

- Budget authority and estimates down to outcomes/programs/components.
- Final or audited expenses at function, entity and financial-statement-note level.
- Published grants and contract awards, clearly marked as commitments rather than cash paid.
- Published payment aggregates such as NDIS support-category payments and Queensland QGIP amounts paid.
- Invoice-level payments where a jurisdiction publishes them, such as the ACT register for invoices at or above its disclosure threshold.

Public sources generally exclude or aggregate individual welfare payments, payroll bank transactions, sensitive/security procurement, commercial-in-confidence items, sub-threshold purchases and internal general-ledger entries. The product should use a visible traceability grade rather than implying unsupported exactness.

## Source stack by jurisdiction

| Jurisdiction | Budget / planned | Actual / audited | Local / council | Contract, grant or payment detail |
|---|---|---|---|---|
| Commonwealth | BP1 Statement 6; BP2; BP4; portfolio PBS | Monthly statements; FBO; CFS; annual reports | Not applicable | AusTender; GrantConnect; NDIS payments; DSS statistics |
| NSW | 2026-27 Budget Papers; open-data XLSX; BP4 agency statements | Report on State Finances | OLG council time-series XLSX | buy.nsw register/export |
| VIC | 2026-27 State Budget; Department Performance Statements | Financial Report; Budget Portfolio Outcomes XLSX | VGC/ABS raw council data packs | Victorian procurement disclosures/search |
| QLD | 2026-27 Budget; Service Delivery Statements | Report on State Finances | QAO local-government report/dashboard plus ABS local workbook | QGIP grants/frontline-service amounts paid |
| WA | 2026-27 Budget Papers | Annual Report on State Finances with XLSX appendices | MyCouncil program expenditure and revenue | Tenders WA awarded contracts |
| SA | 2026-27 Budget Statement; agency volumes; measures | Final Budget Outcome; Consolidated Financial Report | Councils in Focus | SA Tenders and Contracts |
| TAS | 2026-27 Budget Papers | Treasurer's Annual Financial Reports | Consolidated Data Collection for 29 councils | Tasmanian eTendering |
| ACT | 2026-27 budget tables and agency statements | ACT Treasury financial publications | ACT has no separate local-government sector in ABS GFS | Notifiable Invoices Socrata API |
| NT | 2026-27 Budget Papers | Treasury annual reports | ABS local NT workbook; council annual reports; Grants Commission export request | Awarded contracts XLSX |

### The biggest state/local shortcut: direct ABS XLSX files

The current repository describes ABS GFS as manual-export-only, but the latest annual release exposes direct XLSX downloads for Commonwealth Table 130, every state/territory Table 231-238 and every local-government Table 331-337, plus an all-workbooks ZIP. These should be the first cross-jurisdiction baseline because they give consistent aggregates without writing eight unrelated discovery pipelines first.

Source: [ABS Government Finance Statistics, Annual 2024-25](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/latest-release).

ABS is not a substitute for council-level detail. Pair each aggregate workbook with the jurisdiction-specific local source in the table above, then reconcile council sums to the ABS local total where definitions permit.

## Data model and API changes required before broad ingestion

### Replace the fixed hierarchy

The current tree is effectively `jurisdiction -> category -> subcategory -> leaf`, and the backend does not use the stored department field in the tree. Replace this with nodes and typed edges so the same fact can participate in functional, organisational, appropriation, geographic and supplier hierarchies.

Recommended core tables are implemented in the accompanying SQL draft:

- `source_documents` and `source_retrievals` for immutable file lineage.
- `entities`, `nodes` and `node_edges` for arbitrary-depth, versioned hierarchies.
- `facts` and `fact_nodes` for measures and multiple dimensions.
- `lineage_edges` for sum/component/funded-by/paid-under/revision relationships.
- `reconciliations` for documented bridges and unresolved differences.
- `raw_records` so every parser decision remains inspectable and replayable.

### Make measure semantics first-class

At minimum, every amount needs: financial year and exact period; measure type; accounting basis; estimate status; source document/version; source locator; original unit; amount in AUD; and whether the value is consolidated or an elimination.

Required measure types include `budget_estimate`, `revised_estimate`, `appropriation_authority`, `actual_accrual_expense`, `cash_payment`, `grant_award`, `contract_value`, `invoice_paid`, `participant_payment` and `recipient_count`. The API should reject mixed-measure totals unless the endpoint is explicitly a reconciliation.

### Recursive API shape

A revised tree endpoint should accept:

`level`, `jurisdiction`, `financial_year`, `hierarchy_type`, `root_node_id`, `measure_type`, `accounting_basis`, `estimate_status`, and `period_end`

It should return direct amount, rolled-up amount, child count, source count, reconciliation status and traceability grade for every node. Leaf evidence should be a list because one public number can require several documents.

## Prioritised ingestion plan

### P0 - schema and correctness guardrails

1. Migrate to arbitrary-depth nodes/edges and facts with measure semantics.
2. Preserve source file SHA-256, page/sheet/cell/table and release version.
3. Add recursive tree queries and a source-evidence list per fact.
4. Add reconciliation tests and block incompatible sums.

### P1 - federal social-security drill-down and national coverage

1. Parse BP1 Statement 6 and the archived 2025-26 Statement 5 for functions, subfunctions, major programs, expense and payment views.
2. Parse Social Services, Health/Disability/Ageing, NDIA and DVA PBS documents by entity/outcome/program/component/appropriation.
3. Parse FBO actuals and reconcile them to the final monthly YTD run.
4. Ingest NDIS payment CSVs and quarterly report data.
5. Ingest all ABS GFS state and local workbooks as the comparable baseline.
6. Ingest the strongest council raw sources: VIC VGC/ABS packs, TAS CDC, NSW OLG time series, WA MyCouncil and SA Councils in Focus.

### P2 - all state budgets and audited actuals

Add each state/territory budget, agency/service statements and annual whole-of-government actual report. Start with machine-readable XLSX where offered, then PDF tables. Keep budget estimates, revised estimates and actuals as parallel series.

### P3/P4 - transaction-like disclosure

Add AusTender OCDS/CSV and GrantConnect, ACT invoices, Queensland QGIP and NT contract exports. Do not display contract/grant values as cash spending. Label each leaf `commitment`, `award`, `invoice paid` or `aggregate payment` and show its date range.

## Parser and quality-control rules

1. Never use a PDF-extracted number without a page/table locator and a retained copy of the source file.
2. Preserve original units and multiply only in a normalisation layer.
3. Version program/entity names because portfolios and agencies move over time.
4. Store source rows before transformation and hash each raw record.
5. Exclude source aggregate rows only when the component relationship is proven; do not remove every row named total globally.
6. Reconcile child sums to source totals with published rounding tolerance and record unresolved differences.
7. Tag intergovernmental transfers and eliminations so federal, state and local views cannot be naively combined.
8. Distinguish publication status: budget, revised estimate, estimated actual, actual and audited actual.
9. Do not infer payment dollars from recipient counts unless a separate, clearly labelled analytical estimate is requested.
10. Add automated regression fixtures for every workbook sheet/table used.

## Complete candidate-source registry

The YAML registry contains 76 official candidate source entries. It records access method, formats, update frequency, supported hierarchy, parser strategy, caveats and a public traceability tier. It is intentionally broader than the current three-entry `scripts/sources.yaml`.

### Priority counts

- P1: 28 sources
- P2: 42 sources
- P3: 1 sources
- P4: 5 sources

### Official source list

| Priority | Jurisdiction | Level | Source | Access | Trace tier |
|---|---|---|---|---|---:|
| P1 | ACT | territory | [Notifiable Invoices Register](https://www.data.act.gov.au/Government-and-Transparency/Notifiable-Invoices-Register/kzmf-7uhp) | socrata_api | 5 |
| P1 | Australia | cross_level | [Government Finance Statistics, Annual - all workbooks](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/All-workbooks.zip) | direct_file | 1 |
| P1 | Commonwealth | federal | [Table 130. General government - Commonwealth](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO002_202425.xlsx) | direct_file | 1 |
| P1 | Commonwealth | federal | [Budget Paper No. 4: Agency Resourcing 2026-27](https://budget.gov.au/content/bp4/download/bp4_2026_27_consolidated.pdf) | direct_file | 3 |
| P1 | Commonwealth | federal | [Budget Paper No. 1, Statement 6: Expenses and Net Capital Investment 2026-27](https://budget.gov.au/content/bp1/download/bp1_bs-6.pdf) | direct_file | 2 |
| P1 | Commonwealth | federal | [Social Services Portfolio Budget Statements 2026-27](https://www.dss.gov.au/system/files/documents/2026-05/portfolio-budget-statements-2026-27-social-services.pdf) | direct_file | 3 |
| P1 | Commonwealth | federal | [Department of Veterans' Affairs Portfolio Budget Statements 2026-27](https://www.dva.gov.au/sites/default/files/2026-05/dva-pbs-2026-27.pdf) | direct_file | 3 |
| P1 | Commonwealth | federal | [Final Budget Outcome 2024-25, Appendix A: Expenses by function and sub-function](https://archive.budget.gov.au/2024-25/fbo/download/05_appendix_a.pdf) | direct_file | 2 |
| P1 | Commonwealth | federal | [Health, Disability and Ageing Portfolio Budget Statements 2026-27](https://www.health.gov.au/sites/default/files/2026-06/budget-2026-27-health-disability-and-ageing-portfolio-budget-statements.pdf) | direct_file | 3 |
| P1 | Commonwealth | federal | [Australian Government General Government Sector Monthly Financial Statements - tables and data](https://data.gov.au/data/dataset/australian-government-general-government-sector-monthly-financial-statements-tables-and-data) | ckan_api | 2 |
| P1 | Commonwealth | federal | [National Disability Insurance Agency Portfolio Budget Statements 2026-27](https://www.health.gov.au/sites/default/files/2026-06/budget_2026-27_national_disability_insurance_agency_2026-27_health_pbs.pdf) | direct_file | 3 |
| P1 | Commonwealth | federal | [Portfolio Budget Statements index 2026-27](https://budget.gov.au/content/pbs/index.htm) | landing_page_discovery | 3 |
| P1 | Commonwealth | federal | [Social Services Portfolio Budget Statements 2025-26](https://www.dss.gov.au/system/files/documents/2025-03/2025-26social-servicespbsaccessible.pdf) | direct_file | 3 |
| P1 | Commonwealth and states | cross_level | [Budget Paper No. 3: Federal Financial Relations 2026-27](https://budget.gov.au/content/bp3/download/bp3_2026-27.pdf) | direct_file | 3 |
| P1 | NSW | local | [Table 331. General government - local - New South Wales](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO012_202425.xlsx) | direct_file | 1 |
| P1 | NSW | local | [Your council data and reports - time series](https://www.olg.nsw.gov.au/public/your-council-data-and-reports) | landing_page_discovery | 3 |
| P1 | NT | local | [Table 337. General government - local - Northern Territory](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO018_202425.xlsx) | direct_file | 1 |
| P1 | NT | territory | [Awarded government contracts](https://data.nt.gov.au/dataset/awarded-government-contracts) | ckan_api | 4 |
| P1 | QLD | local | [Table 333. General government - local - Queensland](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO014_202425.xlsx) | direct_file | 1 |
| P1 | QLD | state | [Queensland Government Investment Portal expenditure data - consolidated view](https://www.data.qld.gov.au/dataset/queensland-government-investment-portal-expenditure-data-consolidated-view) | ckan_api | 4 |
| P1 | SA | local | [Table 334. General government - local - South Australia](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO015_202425.xlsx) | direct_file | 1 |
| P1 | SA | local | [Councils in Focus](https://dit.sa.gov.au/local-government/councils-in-focus) | landing_page_discovery | 3 |
| P1 | TAS | local | [Table 336. General government - local - Tasmania](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO017_202425.xlsx) | direct_file | 1 |
| P1 | TAS | local | [Council performance and Consolidated Data Collection](https://www.dpac.tas.gov.au/government-information/local-government/council-performance) | landing_page_discovery | 3 |
| P1 | VIC | local | [Table 332. General government - local - Victoria](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO013_202425.xlsx) | direct_file | 1 |
| P1 | VIC | local | [Council raw VGC and ABS data packs](https://www.localgovernment.vic.gov.au/lgv-funding-programs/victoria-grants-commission/consultation-and-operations) | landing_page_discovery | 3 |
| P1 | WA | local | [Table 335. General government - local - Western Australia](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO016_202425.xlsx) | direct_file | 1 |
| P1 | WA | local | [MyCouncil local government information and comparison](https://www.wa.gov.au/service/building-utilities-and-essential-services/integrated-essential-services/local-government-information-and-comparison) | landing_page_discovery | 3 |
| P2 | ACT | territory | [Table 238. General government - state - Australian Capital Territory](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO010_202425.xlsx) | direct_file | 1 |
| P2 | ACT | territory | [ACT Treasury financial publications](https://www.treasury.act.gov.au/publications) | landing_page_discovery | 2 |
| P2 | ACT | territory | [ACT Budget Papers and Statements 2026-27](https://www.treasury.act.gov.au/budget/budget-2026-27/budget-papers-and-statements) | landing_page_discovery | 2 |
| P2 | Commonwealth | federal | [DSS Income Support Recipients - Monthly Time Series](https://data.gov.au/data/dataset/dss-income-support-recipients-monthly-time-series) | ckan_api | 3 |
| P2 | Commonwealth | federal | [DSS JobSeeker Payment and Youth Allowance recipients - monthly profile](https://data.gov.au/data/dataset/jobseeker-payment-and-youth-allowance-recipients-monthly-profile) | ckan_api | 3 |
| P2 | Commonwealth | federal | [DSS Benefit and Payment Recipient Demographics - quarterly data](https://data.gov.au/data/dataset/dss-payment-demographic-data) | ckan_api | 3 |
| P2 | Commonwealth | federal | [DSS Payments by Local Government Area](https://www.data.gov.au/data/dataset/dss-payments-by-local-government-area) | ckan_api | 3 |
| P2 | Commonwealth | federal | [Historical Australian Government Contract Notice Data - OCDS API](https://data.gov.au/data/dataset/historical-australian-government-contract-data/resource/a7f471ad-e085-49b5-bd6b-1b270ea46e99) | ocds_api | 4 |
| P2 | Commonwealth | federal | [AusTender Contract Notice Export](https://data.gov.au/data/dataset/austender-contract-notice-export) | ckan_api | 4 |
| P2 | Commonwealth | federal | [Budget Paper No. 2: Budget Measures 2026-27](https://budget.gov.au/content/bp2/download/bp2_2026-27.pdf) | direct_file | 3 |
| P2 | Commonwealth | federal | [Commonwealth Consolidated Financial Statements 2024-25](https://www.finance.gov.au/publications/commonwealth-consolidated-financial-statements/2024-2025-commonwealth-consolidated-financial-statements) | landing_page_discovery | 1 |
| P2 | Commonwealth | federal | [GrantConnect grant opportunities and awards](https://www.grants.gov.au/) | web_portal | 4 |
| P2 | Commonwealth | federal | [Transparency Portal - Commonwealth annual reports and data](https://www.transparency.gov.au/) | web_portal | 3 |
| P2 | Commonwealth | federal | [NDIS annual financial sustainability reports](https://ndis.gov.au/publications/annual-financial-sustainability-reports) | landing_page_discovery | 3 |
| P2 | Commonwealth | federal | [NDIS participant datasets](https://dataresearch.ndis.gov.au/datasets/participant-datasets) | landing_page_discovery | 3 |
| P2 | Commonwealth | federal | [NDIS payments datasets](https://dataresearch.ndis.gov.au/datasets/payments-datasets) | landing_page_discovery | 4 |
| P2 | Commonwealth | federal | [NDIS quarterly reports](https://ndis.gov.au/publications/quarterly-reports) | landing_page_discovery | 3 |
| P2 | Commonwealth | federal | [Services Australia annual reports](https://www.servicesaustralia.gov.au/annual-reports?context=22) | landing_page_discovery | 3 |
| P2 | NSW | state | [Table 231. General government - state - New South Wales](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO003_202425.xlsx) | direct_file | 1 |
| P2 | NSW | state | [NSW Budget Papers 2026-27](https://www.nsw.gov.au/business-and-economy/nsw-budget/2026-27-budget-papers) | landing_page_discovery | 2 |
| P2 | NSW | state | [NSW Budget 2026-27 Open Data](https://www.nsw.gov.au/business-and-economy/nsw-budget/2026-27-budget-papers/open-data) | landing_page_discovery | 2 |
| P2 | NSW | state | [NSW Report on State Finances](https://www.nsw.gov.au/departments-and-agencies/nsw-treasury/documents-library/report-on-state-finances) | landing_page_discovery | 2 |
| P2 | NT | territory | [Table 237. General government - state - Northern Territory](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO009_202425.xlsx) | direct_file | 1 |
| P2 | NT | territory | [Northern Territory Budget Papers 2026-27](https://budget.nt.gov.au/papers) | landing_page_discovery | 2 |
| P2 | NT | territory | [Northern Territory Treasury annual reports](https://treasury.nt.gov.au/publications/annual-reports) | landing_page_discovery | 2 |
| P2 | QLD | state | [Table 233. General government - state - Queensland](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO005_202425.xlsx) | direct_file | 1 |
| P2 | QLD | state | [Queensland Budget Papers 2026-27](https://budget.qld.gov.au/budget-papers/) | landing_page_discovery | 2 |
| P2 | QLD | local | [Local government 2025 report and dashboard](https://www.qao.qld.gov.au/reports-resources/reports-parliament/local-government-2025) | landing_page_discovery | 3 |
| P2 | QLD | state | [Queensland Report on State Finances](https://www.treasury.qld.gov.au/budget/report-on-state-finances/) | landing_page_discovery | 2 |
| P2 | SA | state | [Table 234. General government - state - South Australia](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO006_202425.xlsx) | direct_file | 1 |
| P2 | SA | state | [South Australia Budget 2026-27](https://treasury.sa.gov.au/budget/current-budget) | landing_page_discovery | 2 |
| P2 | SA | state | [South Australia Final Budget Outcome and Consolidated Financial Report](https://treasury.sa.gov.au/budget/current-budget/budget-papers) | landing_page_discovery | 2 |
| P2 | TAS | state | [Table 236. General government - state - Tasmania](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO008_202425.xlsx) | direct_file | 1 |
| P2 | TAS | state | [Tasmanian Budget 2026-27](https://www.treasury.tas.gov.au/budget-and-financial-management/2026-27-tasmanian-budget) | landing_page_discovery | 2 |
| P2 | TAS | state | [Treasurer's Annual Financial Reports](https://www.treasury.tas.gov.au/budget-and-financial-management/financial-reports/treasurers-annual-financial-reports) | landing_page_discovery | 2 |
| P2 | VIC | state | [Table 232. General government - state - Victoria](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO004_202425.xlsx) | direct_file | 1 |
| P2 | VIC | state | [Victorian State Budget 2026-27](https://www.dtf.vic.gov.au/2026-27-state-budget) | landing_page_discovery | 2 |
| P2 | VIC | state | [DTF Annual Report and Budget Portfolio Outcomes](https://www.dtf.vic.gov.au/2024-25-annual-report) | landing_page_discovery | 2 |
| P2 | VIC | state | [Victoria Financial Report 2024-25](https://www.dtf.vic.gov.au/financial-report-inc-quarterly-financial-report-no-4) | landing_page_discovery | 2 |
| P2 | WA | state | [Table 235. General government - state - Western Australia](https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/2024-25/55120DO007_202425.xlsx) | direct_file | 1 |
| P2 | WA | state | [Western Australia Annual Report on State Finances 2024-25](https://www.wa.gov.au/government/publications/2024-25-annual-report-state-finances) | landing_page_discovery | 2 |
| P2 | WA | state | [Western Australia Budget Papers 2026-27](https://www.ourstatebudget.wa.gov.au/budget-papers.html) | landing_page_discovery | 2 |
| P3 | VIC | local | [Council planning, budget and annual reporting guidance and models](https://www.localgovernment.vic.gov.au/council-innovation-and-performance/sector-guidance-planning-and-reporting) | landing_page_discovery | 3 |
| P4 | NSW | state | [buy.nsw register of notices](https://buy.nsw.gov.au/help/register-of-notices) | landing_page_discovery | 4 |
| P4 | NT | local | [Northern Territory Grants Commission Annual Return](https://gcannualreturn.nt.gov.au/) | landing_page_discovery | 3 |
| P4 | SA | state | [SA Tenders and Contracts](https://www.tenders.sa.gov.au/) | landing_page_discovery | 4 |
| P4 | TAS | state | [Tasmanian purchasing and eTendering](https://www.treasury.tas.gov.au/purchasing-and-property/purchasing-whole-of-government-common-use-contracts-and-etendering) | landing_page_discovery | 4 |
| P4 | WA | state | [Tenders WA awarded contracts](https://www.tenders.wa.gov.au/) | landing_page_discovery | 4 |

## Bottom line

The fastest credible improvement is not to hunt for a single national transaction ledger; none was found. Build a layered evidence graph. Use ABS for comparable totals, budget papers for function/subfunction, PBS and agency statements for programs/components, final outcomes/annual reports for actuals, and payment/contract/invoice datasets only where the government actually publishes them. With the schema change first, the app can drill far deeper while remaining honest about what each dollar figure represents.