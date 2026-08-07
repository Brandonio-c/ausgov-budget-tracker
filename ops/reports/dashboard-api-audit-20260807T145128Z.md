# Dashboard API traversal audit — 20260807T145128Z

Base URL: `http://127.0.0.1:8000` (real backend against `data/facts.db`)

**Total hard failures across all paths: 0**

**Total accepted source-rounding warnings: 0**

| path | visited_nodes | scope | jurisdiction | edge_kind | additive>100% | cross_year | label_quality | citation | transport |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| federal_actuals_2024_25 | 298 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| federal_budget_latest | 1638 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| qld_state_actuals_2024_25 | 223 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| local_government_actuals_2024_25 | 1624 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| federal_debt_latest | 49 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| federal_gdp_ratios_latest | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## scope_failures

None.

## jurisdiction_failures

None.

## edge_kind_failures

None.

## additive_reconciliation_failures

None.

## cross_year_failures

None.

## label_quality_failures

None.

## citation_failures

None.

## transport_errors

None.

## accepted_source_rounding_warnings

None.

## PBS -> Statement 6 crosswalk reachability

| case | s6_node | status | non_additive_labelled | sample_child | citation_ok | amount_preserved |
|---|---|---|---|---|---|---|
| social_services | Social security and welfare | reachable | True | 1.1.1 – Component 1 (Family Tax Benefit Part A) Special appropriations A New Tax System (Family Assistance) (Administration) Act 1999 | True | True |
| health | Health | reachable | True | 2024–25 2023–24 Administered Australian Immunisation Register | True | True |
| ndia | Social security and welfare / Assistance to people with disabilities / National Disability Insurance Scheme | reachable | True | National Disability Insurance Scheme Participant Plans | True | True |
| defence | Defence | reachable | True | Key cost category / Capability Acquisition Program | True | True |
| education | Education | reachable | True | 2024­25 2025­26 2026­27 2027­28 Quality Outcomes | True | True |
| dva_health | Health / Medical services and benefits / Veterans' pharmaceutical benefits | reachable | True | Pharmaceutical Benefits Scheme (PBS) New and Amended Listings (b) 2.1, 2.3 Administered payment | True | True |
| dva_welfare | Social security and welfare / Assistance to veterans and dependants | reachable | True | Administered payment - 67 5 - - Total - 67 5 - - Strengthening Medicare - Health Workforce (b) (f) 2.1, 2.4 Administered payment - | True | True |

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
  "child_count": 216,
  "sample_child": "1.1.1 \u2013 Component 1 (Family Tax Benefit Part A) Special appropriations A New Tax System (Family Assistance) (Administration) Act 1999",
  "sample_child_amount": 15009970000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2026_27_social_services | pdf:portfolio-budget-statements-2026-27-social-services.pdf | page:38 | program:1.1.1 \u2013 Component 1 (Family Tax Benefit Part A) Special appropriations A New Tax System (Family Assistance) (Administration) Act 1999 | fy:2029-30 | unit:$000 | infer:table_header/high"
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
  "child_count": 180,
  "sample_child": "2024\u201325 2023\u201324 Administered Australian Immunisation Register",
  "sample_child_amount": 10391000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2024_25_health_disability_and_ageing | pdf:federal_pbs_2024_25_health_disability_and_ageing__2024-25-health-pbs.pdf | page:118 | program:2024\u201325 2023\u201324 Administered Australian Immunisation Register | fy:2027-28 | unit:$000 | infer:source_layout_template/medium"
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
  "child_count": 9,
  "sample_child": "National Disability Insurance Scheme Participant Plans",
  "sample_child_amount": 40353135000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2026_27_health_disability_ageing | pdf:budget-2026-27-health-disability-and-ageing-portfolio-budget-statements.pdf | page:114 | program:National Disability Insurance Scheme Participant Plans | fy:2029-30 | unit:$000 | infer:source_layout_template/medium"
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
  "child_count": 24,
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
  "banner": "Related breakdown from a different measure family \u2014 amounts are shown for navigation and must not be summed into the parent pie slice. Source: federal_pbs_programs_all. Crosswalk match: approx. Deeper component/program rows use FY 2027-28 where 2029-30 is unpublished in those tables.",
  "child_count": 153,
  "sample_child": "2024\u00ad25 2025\u00ad26 2026\u00ad27 2027\u00ad28 Quality Outcomes",
  "sample_child_amount": 36060000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2024_25_education_portfolio | pdf:federal_pbs_2024_25_education_portfolio__federal_pbs_2024_25_education_portfolio.pdf | page:53 | program:2024\u00ad25 2025\u00ad26 2026\u00ad27 2027\u00ad28 Quality Outcomes | fy:2027-28 | unit:$000 | infer:source_layout_template/medium"
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
  "child_count": 144,
  "sample_child": "Administered payment - 67 5 - - Total - 67 5 - - Strengthening Medicare - Health Workforce (b) (f) 2.1, 2.4 Administered payment -",
  "sample_child_amount": 96000.0,
  "citation_ok": true,
  "citation_detail": {
    "has_source_file": true,
    "locator": "source_id:federal_pbs_2025_26_veterans_affairs | pdf:federal_pbs_2025_26_veterans_affairs__2025-26-Veterans-Affairs-PBS.pdf | page:30 | program:Administered payment - 67 5 - - Total - 67 5 - - Strengthening Medicare - Health Workforce (b) (f) 2.1, 2.4 Administered payment - | fy:2028-29 | unit:$000 | infer:table_header/high"
  },
  "parent_amount_preserved": true
}
```

