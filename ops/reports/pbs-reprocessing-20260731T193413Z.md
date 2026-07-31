# PBS reprocessing report — 20260731T193413Z

Sources processed: 63

Total raw rows (pre cross-document dedupe): 108502

Total quarantined rows: 8682

Sources with zero rows and zero quarantine: 0

## facts.db load (Task 3.5) — added 2026-07-31T19:50Z

Ran `scripts/ingest/breakdown_pack.py --pack pbs_programs_all` after this
extraction (extractor + mapping both re-run; `data/staging/breakdowns/
pbs_programs_all.csv` regenerated fresh from the fixed extractor):

- `source_documents.source_key = 'federal_pbs_programs_all'` already existed
  from three prior runs on 2026-07-24 (before every fix documented above:
  header-fragment/nil-row contamination, per-row citation integrity, the
  Act-citation-year fabrication bug, the soft-hyphen year-header bug). That
  pre-existing batch held 56,117 facts, a portion of them provably corrupted
  (fabricated amounts from the Act-year bug; ~44% still citing a single
  hardcoded Treasury PDF regardless of which of the 63 portfolio PDFs the
  fact actually came from).
- Because `fact_key` embeds derived label text, a fact produced by the fixed
  extractor gets a different key than its pre-fix predecessor and would
  never overwrite it — the two would sit side by side forever, double
  counting. Added opt-in `replace_on_reload: true` support to
  `load_facts.py`'s `load_decisions()` (deletes all existing facts for this
  source's `source_document_id`, cascade-cleaning `fact_nodes`/
  `lineage_edges`, before inserting the fresh batch). Every other mapping's
  behaviour (upsert against existing fact_key) is unchanged.
- After adding that flag and rerunning: 93,265 stale/duplicate facts deleted
  (56,117 pre-existing + 37,148 added by an earlier run this session before
  the flag existed), 103,945 rows re-published, collapsing via `fact_key`
  (portfolio + label + fy + estimate_status + measure_type, not amount) to
  **53,083 distinct facts** now under this source.
- **Idempotency verified**: ran the identical load a second time.
  `replaced_existing: 53083`, `published: 103945` — byte-identical to the
  first post-fix run. Fact count under this source stayed at exactly 53,083
  across both runs. Total `facts.db` row count also unchanged between the
  two runs (321,950).
- **Net effect on facts.db**: 324,984 → 321,950 (-3,034), entirely
  attributable to this one source (56,117 → 53,083, -3,034). This is a
  decrease, not an increase, because the fixes remove fabricated rows
  (Act-year bug) and because fact_key collisions between overlapping budget
  editions (e.g. the same program/fy/status reported as a slightly
  different "actual" in both the 2024-25 and 2025-26 PBS editions) collapse
  to one stored value, chosen by processing order rather than an explicit
  "prefer newest edition" rule. This is a known, documented limitation, not
  data corruption — every stored value is a genuine figure from a real PBS
  document, just not always the most-recently-restated one when editions
  disagree. Flagged as a follow-up (see Task 4/5 backlog).
- **Citations verified**: 0 of 53,083 facts still reference the placeholder
  fallback path; every fact's `source_locator_json.cached_copy_path` now
  points at its own real portfolio PDF, confirmed by exact-path check (not
  substring, which produces false positives since several real filenames
  legitimately contain "Treasury-PBS").
- **Hierarchy/S6-bridge linking**: NOT done as part of this load. The pack
  config (`config/breakdowns/pbs_programs_all.yaml`) declares
  `edge_kind: related_breakdown` and sets no `related_crosswalk_id`, so this
  load creates facts and category nodes but zero `node_edges` — the data is
  loaded, correct, and independently queryable/citable, but not yet wired
  into the existing Statement 6 / portfolio hierarchy tree, so it will not
  yet appear as added drill-down depth in the dashboard. The existing,
  narrower `pbs_programs_s6_bridge` pack (Defence/Education/Infrastructure/
  Home Affairs/Industry only) already does real S6 linking for the
  portfolios it covers; building a full program-to-S6-function crosswalk
  across all 26 portfolios in `pbs_programs_all` is a substantial separate
  engineering task, not attempted here given the remaining scope of this
  directive. Recommended as a high-impact next step.

## Per-source detail

| source_id | portfolio | before_fact_count | after_raw_rows | after_quarantine_rows | outcome |
|---|---|---|---|---|---|
| federal_pbs_2025_26_attorney_general_s_portfolio | Attorney-General's | 0 | 4811 | 0 | facts |
| federal_pbs_2024_25_health_disability_and_ageing | Health Disability and Ageing | 0 | 4606 | 0 | facts |
| federal_pbs_2024_25_treasury_portfolio | Treasury | 0 | 4298 | 63 | facts |
| federal_pbs_2025_26_treasury_portfolio | Treasury | 0 | 4273 | 10 | facts |
| federal_pbs_2026_27_treasury | Treasury | 0 | 4266 | 100 | facts |
| federal_pbs_2026_27_pmc | Prime Minister and Cabinet | 0 | 3912 | 0 | facts |
| federal_pbs_2024_25_prime_minister_and_cabinet | Prime Minister and Cabinet | 0 | 3854 | 0 | facts |
| federal_pbs_2026_27_climate_energy_environment_water | Climate Change Energy the Environment and Water | 0 | 3831 | 10 | facts |
| federal_pbs_2025_26_climate_change_energy_the_environment_and_water | Climate Change Energy the Environment and Water | 0 | 3631 | 9 | facts |
| federal_pbs_2026_27_health_disability_ageing | Health Disability and Ageing | 0 | 3372 | 301 | facts |
| federal_pbs_2026_27_attorney_general | Attorney-General's | 0 | 3263 | 0 | facts |
| federal_pbs_2024_25_infrastructure_transport_regional_development_communications_sport_and_the_arts | Infrastructure Transport Regional Development Communications Sport and the Arts | 0 | 3221 | 811 | facts |
| federal_pbs_2026_27_infrastructure_transport_regions | Infrastructure Transport Regional Development Communications Sport and the Arts | 0 | 2945 | 995 | facts |
| federal_pbs_2025_26_prime_minister_and_cabinet | Prime Minister and Cabinet | 0 | 2826 | 221 | facts |
| federal_pbs_2026_27_finance | Finance | 0 | 2605 | 80 | facts |
| federal_pbs_2026_27_industry_science_resources | Industry Science and Resources | 0 | 2483 | 11 | facts |
| federal_pbs_2026_27_home_affairs | Home Affairs | 0 | 2483 | 0 | facts |
| federal_pbs_2025_26_finance_portfolio | Finance | 0 | 2371 | 0 | facts |
| federal_pbs_2024_25_employment_and_workplace_relations | Employment and Workplace Relations | 0 | 2347 | 0 | facts |
| federal_pbs_2024_25_social_services_portfolio | Social Services | 0 | 2342 | 0 | facts |
| federal_pbs_2024_25_industry_science_and_resources | Industry Science and Resources | 0 | 2325 | 13 | facts |
| federal_pbs_2025_26_industry_science_and_resources | Industry Science and Resources | 0 | 2197 | 8 | facts |
| federal_pbs_2025_26_social_services_portfolio | Social Services | 0 | 2180 | 0 | facts |
| federal_pbs_2024_25_finance_portfolio | Finance | 0 | 2126 | 48 | facts |
| federal_pbs_2025_26_health_disability_and_ageing | Health Disability and Ageing | 0 | 2046 | 504 | facts |
| federal_pbs_2026_27_foreign_affairs_trade | Foreign Affairs and Trade | 0 | 1839 | 0 | facts |
| federal_pbs_2024_25_foreign_affairs_and_trade | Foreign Affairs and Trade | 0 | 1762 | 0 | facts |
| federal_pbs_2025_26_foreign_affairs_and_trade | Foreign Affairs and Trade | 0 | 1757 | 0 | facts |
| federal_pbs_2024_25_agriculture_fisheries_and_forestry | Agriculture Fisheries and Forestry | 0 | 1607 | 266 | facts |
| federal_pbs_2026_27_agriculture | Agriculture Fisheries and Forestry | 0 | 1454 | 263 | facts |
| federal_pbs_2024_25_veterans_affairs | Veterans' Affairs | 0 | 1445 | 7 | facts |
| federal_pbs_2025_26_veterans_affairs | Veterans' Affairs | 0 | 1421 | 5 | facts |
| federal_pbs_2025_26_education_portfolio | Education | 0 | 1396 | 0 | facts |
| federal_pbs_2024_25_climate_change_energy_the_environment_and_water | Climate Change Energy the Environment and Water | 0 | 1340 | 498 | facts |
| federal_pbs_2026_27_veterans_affairs | Veterans' Affairs | 0 | 1319 | 5 | facts |
| federal_pbs_2025_26_agriculture_fisheries_and_forestry | Agriculture Fisheries and Forestry | 0 | 1287 | 309 | facts |
| federal_pbs_2026_27_employment_workplace | Employment and Workplace Relations | 0 | 1180 | 238 | facts |
| federal_pbs_2025_26_home_affairs_portfolio | Home Affairs | 0 | 1179 | 0 | facts |
| federal_pbs_2026_27_social_services | Social Services | 0 | 1138 | 0 | facts |
| federal_pbs_2024_25_home_affairs_portfolio | Home Affairs | 0 | 1081 | 82 | facts |
| federal_pbs_2024_25_attorney_general_s_portfolio | Attorney-General's | 0 | 962 | 772 | facts |
| federal_pbs_2025_26_department_of_parliamentary_services | department of parliamentary services 2025 26 Parliamentary Departments | 0 | 882 | 18 | facts |
| federal_pbs_2025_26_department_of_the_senate_pbs | department of the senate pbs | 0 | 882 | 18 | facts |
| federal_education_pbs_2026_27 | Education | 0 | 841 | 133 | facts |
| federal_pbs_2026_27_education | Education | 0 | 841 | 133 | facts |
| federal_pbs_2024_25_education_portfolio | Education | 0 | 667 | 116 | facts |
| federal_pbs_2025_26_employment_and_workplace_relations | Employment and Workplace Relations | 0 | 402 | 405 | facts |
| federal_pbs_2026_27_parliamentary_services | parliamentary services 2026 27 Portfolio Budget Statement | 0 | 400 | 0 | facts |
| federal_pbs_2025_26_infrastructure_transport_regional_development_communications_sport_and_the_arts | Infrastructure Transport Regional Development Communications Sport and the Arts | 0 | 400 | 1424 | facts |
| federal_pbs_2024_25_department_of_parliamentary_services | department of parliamentary services DPS 2024 25 | 0 | 395 | 0 | facts |
| federal_pbs_2025_26_department_of_the_house_of_representatives | department of the house of representatives doc | 0 | 304 | 0 | facts |
| federal_pbs_2026_27_house_representatives | house representatives DHR 2026 27 | 0 | 285 | 0 | facts |
| federal_pbs_2024_25_department_of_the_house_of_representatives | department of the house of representatives doc | 0 | 268 | 0 | facts |
| federal_pbs_2024_25_department_of_the_senate_pbs | department of the senate pbs DoS 2024 25 | 0 | 197 | 0 | facts |
| federal_pbs_2026_27_senate | senate | 0 | 165 | 0 | facts |
| federal_pbs_2025_26_defence_portfolio | Defence | 0 | 161 | 120 | facts |
| federal_pbs_2026_27_defence | Defence | 0 | 136 | 271 | facts |
| federal_defence_pbs_2026_27 | Defence | 0 | 136 | 271 | facts |
| federal_pbs_2024_25_defence_portfolio | Defence | 0 | 135 | 63 | facts |
| federal_pbs_2024_25_parliamentary_budget_office | parliamentary budget office | 0 | 113 | 0 | facts |
| federal_pbs_2026_27_ndia | Health Disability and Ageing | 0 | 86 | 44 | facts |
| federal_pbs_2025_26_parliamentary_budget_office | parliamentary budget office | 0 | 14 | 18 | facts |
| federal_pbs_2026_27_parliamentary_budget_office | parliamentary budget office 2026 27 Portfolio Budget Statement Parliamentary Bud | 0 | 11 | 19 | facts |
