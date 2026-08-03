# Dashboard API traversal audit — 20260803T191959Z

Base URL: `https://ausgov-budget-api.vibefactory.app` (real backend against `data/facts.db`)

| path | visited_nodes | material_leaves | citation_checks | citation_failures | errors |
|---|---:|---:|---:|---:|---|
| federal_actuals_2024_25 | 1156 | 897 | 897 | 0 | - |
| federal_budget_latest | 4486 | 3311 | 3311 | 0 | - |
| qld_state_actuals_2024_25 | 2582 | 1951 | 1951 | 0 | - |
| local_government_actuals_2024_25 | 8331 | 6391 | 6391 | 0 | - |
| federal_debt_latest | 50 | 44 | 44 | 0 | - |
| federal_gdp_ratios_latest | 4 | 1 | 1 | 0 | - |

## Citation failures

None.

## PBS -> Statement 6 crosswalk reachability

| case | s6_node | status | non_additive_labelled | sample_child | citation_ok | amount_preserved |
|---|---|---|---|---|---|---|
| social_services | Social security and welfare | reachable | True | - Other | True | True |
| health | Health | reachable | True | (loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreciation/amortisation expenses | True | True |
| ndia | Social security and welfare / Assistance to people with disabilities / National Disability Insurance Scheme | reachable | True | National Disability Insurance Agency Departmental payments 1.1 - (2,013,602) (7,431,787) (11,830,241) (16,652,2 05) 1.2 - | True | True |
| defence | Defence | reachable | True | Key cost category / Capability Acquisition Program | True | True |
| education | Education | reachable | True | $’000 2028­29 $’000 EXPENSES Employee benefits | True | True |
| dva_health | Health / Medical services and benefits / Veterans' pharmaceutical benefits | reachable | True | Pharmaceutical Benefits Scheme (PBS) New and Amended Listings (b) 2.1, 2.3 Administered payment | True | True |
| dva_welfare | Social security and welfare / Assistance to veterans and dependants | reachable | True | (Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA | True | True |

### Detail

**social_services** (`Social security and welfare`)

```json
{
  "label": "social_services",
  "s6_node_name": "Social security and welfare",
  "fact_id": 257892,
  "financial_year": "2029-30",
  "estimate_status": "forward_estimate",
  "parent_amount_aud": 334998000000,
  "unit": "AUD",
  "status": "reachable",
  "non_additive_labelled": true,
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2027-28 where 2029-30 is unpublished in those tables.",
  "child_count": 528,
  "sample_child": "- Other",
  "sample_child_amount": 36473000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2024_25_social_services_portfolio | pdf:federal_pbs_2024_25_social_services_portfolio__federal_pbs_2024_25_social_services_portfolio.pdf | page:234 | program:- Other | fy:2027-28 | unit:$000 | infer:table_header/high"
  },
  "parent_amount_preserved": true
}
```

**health** (`Health`)

```json
{
  "label": "health",
  "s6_node_name": "Health",
  "fact_id": 257838,
  "financial_year": "2029-30",
  "estimate_status": "forward_estimate",
  "parent_amount_aud": 148915000000,
  "unit": "AUD",
  "status": "reachable",
  "non_additive_labelled": true,
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2026-27 where 2029-30 is unpublished in those tables.",
  "child_count": 766,
  "sample_child": "(loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreciation/amortisation expenses",
  "sample_child_amount": 649000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2026_27_health_disability_ageing | pdf:budget-2026-27-health-disability-and-ageing-portfolio-budget-statements.pdf | page:362 | program:(loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreciation/amortisation expenses | fy:2029-30 | unit:$000 | infer:source_layout_template/medium"
  },
  "parent_amount_preserved": true
}
```

**ndia** (`Social security and welfare / Assistance to people with disabilities / National Disability Insurance Scheme`)

```json
{
  "label": "ndia",
  "s6_node_name": "Social security and welfare / Assistance to people with disabilities / National Disability Insurance Scheme",
  "fact_id": 258258,
  "financial_year": "2029-30",
  "estimate_status": "forward_estimate",
  "parent_amount_aud": 56239000000,
  "unit": "AUD",
  "status": "reachable",
  "non_additive_labelled": true,
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2027-28 where 2029-30 is unpublished in those tables.",
  "child_count": 15,
  "sample_child": "National Disability Insurance Agency Departmental payments 1.1 - (2,013,602) (7,431,787) (11,830,241) (16,652,2 05) 1.2 -",
  "sample_child_amount": 82740000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2026_27_health_disability_ageing | pdf:budget-2026-27-health-disability-and-ageing-portfolio-budget-statements.pdf | page:44 | program:National Disability Insurance Agency Departmental payments 1.1 - (2,013,602) (7,431,787) (11,830,241) (16,652,2 05) 1.2 - | fy:2029-30 | unit:$000 | infer:source_layout_template/medium"
  },
  "parent_amount_preserved": true
}
```

**defence** (`Defence`)

```json
{
  "label": "defence",
  "s6_node_name": "Defence",
  "fact_id": 257718,
  "financial_year": "2029-30",
  "estimate_status": "forward_estimate",
  "parent_amount_aud": 61860000000,
  "unit": "AUD",
  "status": "reachable",
  "non_additive_labelled": true,
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2028-29 where 2029-30 is unpublished in those tables.",
  "child_count": 30,
  "sample_child": "Key cost category / Capability Acquisition Program",
  "sample_child_amount": 108454100.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2025_26_defence_portfolio | pdf:federal_pbs_2025_26_defence_portfolio__2025-26-Defence-PBS.pdf | page:30 | program:3 Capability Acquisition Program 17,702.7 18, | fy:2028-29 | unit:$000 | infer:table_header/high"
  },
  "parent_amount_preserved": true
}
```

**education** (`Education`)

```json
{
  "label": "education",
  "s6_node_name": "Education",
  "fact_id": 257790,
  "financial_year": "2029-30",
  "estimate_status": "forward_estimate",
  "parent_amount_aud": 63917000000,
  "unit": "AUD",
  "status": "reachable",
  "non_additive_labelled": true,
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2023-24 where 2029-30 is unpublished in those tables.",
  "child_count": 350,
  "sample_child": "$\u2019000 2028\u00ad29 $\u2019000 EXPENSES Employee benefits",
  "sample_child_amount": 16127000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2025_26_education_portfolio | pdf:federal_pbs_2025_26_education_portfolio__2025-26-Education-PBS.pdf | page:199 | program:$\u2019000 2028\u00ad29 $\u2019000 EXPENSES Employee benefits | fy:2028-29 | unit:$000 | infer:source_layout_template/medium"
  },
  "parent_amount_preserved": true
}
```

**dva_health** (`Health / Medical services and benefits / Veterans' pharmaceutical benefits`)

```json
{
  "label": "dva_health",
  "s6_node_name": "Health / Medical services and benefits / Veterans' pharmaceutical benefits",
  "fact_id": 258178,
  "financial_year": "2029-30",
  "estimate_status": "forward_estimate",
  "parent_amount_aud": 377000000,
  "unit": "AUD",
  "status": "reachable",
  "non_additive_labelled": true,
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2027-28 where 2029-30 is unpublished in those tables.",
  "child_count": 5,
  "sample_child": "Pharmaceutical Benefits Scheme (PBS) New and Amended Listings (b) 2.1, 2.3 Administered payment",
  "sample_child_amount": 8914000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2025_26_veterans_affairs | pdf:federal_pbs_2025_26_veterans_affairs__2025-26-Veterans-Affairs-PBS.pdf | page:29 | program:Pharmaceutical Benefits Scheme (PBS) New and Amended Listings (b) 2.1, 2.3 Administered payment | fy:2028-29 | unit:$000 | infer:table_header/high"
  },
  "parent_amount_preserved": true
}
```

**dva_welfare** (`Social security and welfare / Assistance to veterans and dependants`)

```json
{
  "label": "dva_welfare",
  "s6_node_name": "Social security and welfare / Assistance to veterans and dependants",
  "fact_id": 257850,
  "financial_year": "2029-30",
  "estimate_status": "forward_estimate",
  "parent_amount_aud": 14405000000,
  "unit": "AUD",
  "status": "reachable",
  "non_additive_labelled": true,
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2027-28 where 2029-30 is unpublished in those tables.",
  "child_count": 377,
  "sample_child": "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA",
  "sample_child_amount": 1691000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2025_26_veterans_affairs | pdf:federal_pbs_2025_26_veterans_affairs__2025-26-Veterans-Affairs-PBS.pdf | page:38 | program:(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA | fy:2028-29 | unit:$000 | infer:table_header/high"
  },
  "parent_amount_preserved": true
}
```

