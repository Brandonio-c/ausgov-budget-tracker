# PBS semantic quality audit — 20260803T200915Z

Read-only against `data/facts.db` (`federal_pbs_programs_all`); no writes performed. 53083 total facts across every acquired PBS portfolio document.

## Totals by classification

| classification | count | publishable |
|---|---:|---|
| malformed_concatenated_row | 21062 | no |
| program | 17042 | yes |
| table_header | 7479 | no |
| narrative_fragment | 2528 | no |
| financial_statement_line | 2090 | no |
| subtotal | 1840 | no |
| unknown | 559 | no |
| component | 475 | yes |
| outcome | 8 | yes |

**Accepted (program/outcome/component): 17525**

**Rejected/quarantined: 35558**

## Top recurring rejection reasons

| reason | count |
|---|---:|
| three_or_more_embedded_value_tokens | 12645 |
| accounting_heading_no_values | 7479 |
| repeated_accounting_heading | 4300 |
| year_header_glued_to_accounting_line | 2233 |
| known_line_item_vocabulary | 2090 |
| total_or_subtotal_line | 1840 |
| starts_lowercase | 1623 |
| exceeds_justified_max_length | 854 |
| embedded_bare_numeric_run | 636 |
| no_confident_signal | 559 |
| narrative_continuation_lead | 494 |
| truncated_trailing_numeric_token | 394 |
| bare_generic_term_no_supporting_context | 207 |
| bare_legislative_citation | 204 |

## Representative malformed_concatenated_row source pages

- `federal_pbs_2026_27_agriculture` p.66 (Agriculture Fisheries and Forestry): "(DCB) - - - 67,507 67,507 Sub-total transactions with owners - - - 77,604 77,604 Estimated closing balance as at 30 June"
- `federal_pbs_2026_27_agriculture` p.66 (Agriculture Fisheries and Forestry): "(DCB) - - - 67,507 67,507 Sub-total transactions with owners - - - 77,604 77,604 Estimated closing balance as at 30 June"
- `federal_pbs_2026_27_agriculture` p.66 (Agriculture Fisheries and Forestry): "(DCB) - - - 67,507 67,507 Sub-total transactions with owners - - - 77,604 77,604 Estimated closing balance as at 30 June"
- `federal_pbs_2026_27_agriculture` p.66 (Agriculture Fisheries and Forestry): "(DCB) - - - 67,507 67,507 Sub-total transactions with owners - - - 77,604 77,604 Estimated closing balance as at 30 June"
- `federal_pbs_2025_26_agriculture_fisheries_and_forestry` p.70 (Agriculture Fisheries and Forestry): "(excluding other intangibles) (a) - (32,940) (3,711) - (36,651) Total other movements - (41,605) (15,988) (41,475) (99,0"
- `federal_pbs_2025_26_agriculture_fisheries_and_forestry` p.70 (Agriculture Fisheries and Forestry): "(excluding other intangibles) (a) - (32,940) (3,711) - (36,651) Total other movements - (41,605) (15,988) (41,475) (99,0"
- `federal_pbs_2025_26_agriculture_fisheries_and_forestry` p.70 (Agriculture Fisheries and Forestry): "(excluding other intangibles) (a) - (32,940) (3,711) - (36,651) Total other movements - (41,605) (15,988) (41,475) (99,0"
- `federal_pbs_2025_26_agriculture_fisheries_and_forestry` p.70 (Agriculture Fisheries and Forestry): "(excluding other intangibles) (a) - (32,940) (3,711) - (36,651) Total other movements - (41,605) (15,988) (41,475) (99,0"
- `federal_pbs_2025_26_agriculture_fisheries_and_forestry` p.70 (Agriculture Fisheries and Forestry): "(excluding other intangibles) (a) - (32,940) (3,711) - (36,651) Total other movements - (41,605) (15,988) (41,475) (99,0"
- `federal_pbs_2026_27_agriculture` p.73 (Agriculture Fisheries and Forestry): "- Appropriations (950,213) (1,077,055) (1,104,398) (1,299,478) (1,643,451) Total cash to Official Public Account (950,21"
- `federal_pbs_2026_27_agriculture` p.73 (Agriculture Fisheries and Forestry): "- Appropriations (950,213) (1,077,055) (1,104,398) (1,299,478) (1,643,451) Total cash to Official Public Account (950,21"
- `federal_pbs_2026_27_agriculture` p.73 (Agriculture Fisheries and Forestry): "- Appropriations (950,213) (1,077,055) (1,104,398) (1,299,478) (1,643,451) Total cash to Official Public Account (950,21"
- `federal_pbs_2026_27_agriculture` p.73 (Agriculture Fisheries and Forestry): "- Appropriations (950,213) (1,077,055) (1,104,398) (1,299,478) (1,643,451) Total cash to Official Public Account (950,21"
- `federal_pbs_2026_27_agriculture` p.73 (Agriculture Fisheries and Forestry): "- Appropriations (950,213) (1,077,055) (1,104,398) (1,299,478) (1,643,451) Total cash to Official Public Account (950,21"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.123 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Employee benefits"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.123 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Employee benefits"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.123 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Employee benefits"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.123 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Employee benefits"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.123 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Employee benefits"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.130 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Suppliers"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.130 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Suppliers"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.130 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Suppliers"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.130 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Suppliers"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.130 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 EXPENSES Suppliers"
- `federal_pbs_2024_25_agriculture_fisheries_and_forestry` p.93 (Agriculture Fisheries and Forestry): "2025–26 2026–27 2027–28 Revenue from Government Payment from related entities"

## Manual portfolio review (required by Task 6)

### Social Services

| classification | count |
|---|---:|
| malformed_concatenated_row | 946 |
| program | 808 |
| component | 434 |
| table_header | 383 |
| financial_statement_line | 116 |
| narrative_fragment | 92 |
| subtotal | 48 |
| unknown | 21 |

Sample rows:

- [narrative_fragment] "- Other" (fy=2023-24, federal_pbs_2024_25_social_services_portfolio p.234)
- [narrative_fragment] "- Other" (fy=2024-25, federal_pbs_2024_25_social_services_portfolio p.234)
- [narrative_fragment] "- Other" (fy=2025-26, federal_pbs_2024_25_social_services_portfolio p.234)
- [narrative_fragment] "- Other" (fy=2026-27, federal_pbs_2024_25_social_services_portfolio p.234)
- [narrative_fragment] "- Other" (fy=2027-28, federal_pbs_2024_25_social_services_portfolio p.234)
- [unknown] "- Special accounts" (fy=2023-24, federal_pbs_2024_25_social_services_portfolio p.234)
- [unknown] "- Special accounts" (fy=2024-25, federal_pbs_2024_25_social_services_portfolio p.234)
- [unknown] "- Special accounts" (fy=2025-26, federal_pbs_2024_25_social_services_portfolio p.234)

### Health Disability and Ageing

| classification | count |
|---|---:|
| malformed_concatenated_row | 2135 |
| program | 1295 |
| table_header | 464 |
| financial_statement_line | 186 |
| unknown | 184 |
| subtotal | 126 |
| narrative_fragment | 118 |
| component | 5 |

Sample rows:

- [malformed_concatenated_row] "(loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreci" (fy=2026-27, federal_pbs_2026_27_health_disability_ageing p.362)
- [malformed_concatenated_row] "(loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreci" (fy=2026-27, federal_pbs_2026_27_health_disability_ageing p.362)
- [malformed_concatenated_row] "(loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreci" (fy=2027-28, federal_pbs_2026_27_health_disability_ageing p.362)
- [malformed_concatenated_row] "(loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreci" (fy=2028-29, federal_pbs_2026_27_health_disability_ageing p.362)
- [malformed_concatenated_row] "(loss) attributable to the Australian Government (1,288) (324) (649) (649) (649) plus: non-appropriated expenses depreci" (fy=2029-30, federal_pbs_2026_27_health_disability_ageing p.362)
- [malformed_concatenated_row] "(loss) attributable to the Australian Government (5,364) (2,863) (2,863) (2,863) (2,863) plus non-appropriated expenses " (fy=2026-27, federal_pbs_2026_27_health_disability_ageing p.270)
- [malformed_concatenated_row] "(loss) attributable to the Australian Government (5,364) (2,863) (2,863) (2,863) (2,863) plus non-appropriated expenses " (fy=2026-27, federal_pbs_2026_27_health_disability_ageing p.270)
- [malformed_concatenated_row] "(loss) attributable to the Australian Government (5,364) (2,863) (2,863) (2,863) (2,863) plus non-appropriated expenses " (fy=2027-28, federal_pbs_2026_27_health_disability_ageing p.270)

### Defence

| classification | count |
|---|---:|
| program | 190 |

Sample rows:

- [program] "Key cost category / Capability Acquisition Program" (fy=2024-25, federal_pbs_2025_26_defence_portfolio p.30)
- [program] "Key cost category / Capability Acquisition Program" (fy=2025-26, federal_pbs_2025_26_defence_portfolio p.30)
- [program] "Key cost category / Capability Acquisition Program" (fy=2026-27, federal_pbs_2025_26_defence_portfolio p.30)
- [program] "Key cost category / Capability Acquisition Program" (fy=2027-28, federal_pbs_2025_26_defence_portfolio p.30)
- [program] "Key cost category / Capability Acquisition Program" (fy=2028-29, federal_pbs_2025_26_defence_portfolio p.30)
- [program] "Key cost category / Capability Sustainment Program" (fy=2024-25, federal_pbs_2025_26_defence_portfolio p.30)
- [program] "Key cost category / Capability Sustainment Program" (fy=2025-26, federal_pbs_2025_26_defence_portfolio p.30)
- [program] "Key cost category / Capability Sustainment Program" (fy=2026-27, federal_pbs_2025_26_defence_portfolio p.30)

### Education

| classification | count |
|---|---:|
| program | 984 |
| malformed_concatenated_row | 578 |
| table_header | 261 |
| financial_statement_line | 114 |
| narrative_fragment | 76 |
| subtotal | 56 |
| unknown | 20 |

Sample rows:

- [malformed_concatenated_row] "$’000 2028­29 $’000 EXPENSES Employee benefits" (fy=2025-26, federal_pbs_2025_26_education_portfolio p.199)
- [malformed_concatenated_row] "$’000 2028­29 $’000 EXPENSES Employee benefits" (fy=2025-26, federal_pbs_2025_26_education_portfolio p.199)
- [malformed_concatenated_row] "$’000 2028­29 $’000 EXPENSES Employee benefits" (fy=2026-27, federal_pbs_2025_26_education_portfolio p.199)
- [malformed_concatenated_row] "$’000 2028­29 $’000 EXPENSES Employee benefits" (fy=2027-28, federal_pbs_2025_26_education_portfolio p.199)
- [malformed_concatenated_row] "$’000 2028­29 $’000 EXPENSES Employee benefits" (fy=2028-29, federal_pbs_2025_26_education_portfolio p.199)
- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Early Learning Support Australian Early Development Census" (fy=2025-26, federal_pbs_2025_26_education_portfolio p.51)
- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Early Learning Support Australian Early Development Census" (fy=2025-26, federal_pbs_2025_26_education_portfolio p.51)
- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Early Learning Support Australian Early Development Census" (fy=2026-27, federal_pbs_2025_26_education_portfolio p.51)

### Veterans' Affairs

| classification | count |
|---|---:|
| program | 931 |
| malformed_concatenated_row | 647 |
| table_header | 347 |
| narrative_fragment | 87 |
| financial_statement_line | 76 |
| subtotal | 49 |
| unknown | 28 |

Sample rows:

- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA" (fy=2024-25, federal_pbs_2025_26_veterans_affairs p.38)
- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA" (fy=2025-26, federal_pbs_2025_26_veterans_affairs p.38)
- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA" (fy=2026-27, federal_pbs_2025_26_veterans_affairs p.38)
- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA" (fy=2027-28, federal_pbs_2025_26_veterans_affairs p.38)
- [unknown] "(Appropriation Bill (No. 1) and Supply Bill (No. 1)) Other income support and compensation-related payments - DRCA" (fy=2028-29, federal_pbs_2025_26_veterans_affairs p.38)
- [table_header] "(for the period ended 30 June) Estimated Budget Forward Forward Forward OPERATING ACTIVITIES Cash received Appropriation" (fy=2024-25, federal_pbs_2025_26_veterans_affairs p.72)
- [table_header] "(for the period ended 30 June) Estimated Budget Forward Forward Forward OPERATING ACTIVITIES Cash received Appropriation" (fy=2025-26, federal_pbs_2025_26_veterans_affairs p.72)
- [table_header] "(for the period ended 30 June) Estimated Budget Forward Forward Forward OPERATING ACTIVITIES Cash received Appropriation" (fy=2026-27, federal_pbs_2025_26_veterans_affairs p.72)

### Attorney-General's

| classification | count |
|---|---:|
| malformed_concatenated_row | 1889 |
| program | 802 |
| table_header | 419 |
| subtotal | 185 |
| narrative_fragment | 179 |
| financial_statement_line | 128 |
| component | 16 |
| unknown | 9 |

Sample rows:

- [malformed_concatenated_row] "(departmental capital budget funding and/or equity injections) (a) 1,483 820 2,194 (716) (734) plus: depreciation/amorti" (fy=2025-26, federal_pbs_2025_26_attorney_general_s_portfolio p.379)
- [malformed_concatenated_row] "(departmental capital budget funding and/or equity injections) (a) 1,483 820 2,194 (716) (734) plus: depreciation/amorti" (fy=2026-27, federal_pbs_2025_26_attorney_general_s_portfolio p.379)
- [malformed_concatenated_row] "(departmental capital budget funding and/or equity injections) (a) 1,483 820 2,194 (716) (734) plus: depreciation/amorti" (fy=2027-28, federal_pbs_2025_26_attorney_general_s_portfolio p.379)
- [malformed_concatenated_row] "(departmental capital budget funding and/or equity injections) (a) 1,483 820 2,194 (716) (734) plus: depreciation/amorti" (fy=2028-29, federal_pbs_2025_26_attorney_general_s_portfolio p.379)
- [unknown] "- - - - (846) Total - - - - (846) Total payment measures Departmental" (fy=2026-27, federal_pbs_2026_27_attorney_general p.186)
- [unknown] "- - - - (846) Total - - - - (846) Total payment measures Departmental" (fy=2027-28, federal_pbs_2026_27_attorney_general p.186)
- [unknown] "- - - - (846) Total - - - - (846) Total payment measures Departmental" (fy=2028-29, federal_pbs_2026_27_attorney_general p.186)
- [unknown] "- - - - (846) Total - - - - (846) Total payment measures Departmental" (fy=2029-30, federal_pbs_2026_27_attorney_general p.186)

### Infrastructure Transport Regional Development Communications Sport and the Arts

| classification | count |
|---|---:|
| program | 1481 |
| malformed_concatenated_row | 1470 |
| table_header | 421 |
| narrative_fragment | 163 |
| financial_statement_line | 128 |
| subtotal | 102 |
| unknown | 47 |

Sample rows:

- [malformed_concatenated_row] "$’000 Opening balance as at 1 July 2024 Balance carried forward from previous period 3,455 3,455 Adjusted opening balanc" (fy=2024-25, federal_pbs_2024_25_infrastructure_transport_regional_development_communications_sport_and_the_arts p.457)
- [malformed_concatenated_row] "$’000 Opening balance as at 1 July 2024 Balance carried forward from previous period 3,455 3,455 Adjusted opening balanc" (fy=2025-26, federal_pbs_2024_25_infrastructure_transport_regional_development_communications_sport_and_the_arts p.457)
- [malformed_concatenated_row] "$’000 Opening balance as at 1 July 2024 Balance carried forward from previous period 3,455 3,455 Adjusted opening balanc" (fy=2026-27, federal_pbs_2024_25_infrastructure_transport_regional_development_communications_sport_and_the_arts p.457)
- [malformed_concatenated_row] "$’000 Opening balance as at 1 July 2025 Balance carried forward from previous period 5,818 5,818 Adjusted opening balanc" (fy=2025-26, federal_pbs_2025_26_infrastructure_transport_regional_development_communications_sport_and_the_arts p.459)
- [malformed_concatenated_row] "$’000 Opening balance as at 1 July 2025 Balance carried forward from previous period 5,818 5,818 Adjusted opening balanc" (fy=2026-29, federal_pbs_2025_26_infrastructure_transport_regional_development_communications_sport_and_the_arts p.459)
- [malformed_concatenated_row] "(c) Figures displayed as a negative (–) represent a decrease in funds and a positive (+) represent an increase in funds." (fy=2025-26, federal_pbs_2025_26_infrastructure_transport_regional_development_communications_sport_and_the_arts p.47)
- [malformed_concatenated_row] "(c) Figures displayed as a negative (–) represent a decrease in funds and a positive (+) represent an increase in funds." (fy=2025-26, federal_pbs_2025_26_infrastructure_transport_regional_development_communications_sport_and_the_arts p.47)
- [malformed_concatenated_row] "(c) Figures displayed as a negative (–) represent a decrease in funds and a positive (+) represent an increase in funds." (fy=2026-27, federal_pbs_2025_26_infrastructure_transport_regional_development_communications_sport_and_the_arts p.47)

### NDIA (label-matched within Health Disability and Ageing)

- [unknown] "2.1 Departmental payment - - - - (17,872) Securing the National Disability Insurance Scheme for Future Generations (k) 2" (fy=2026-27, federal_pbs_2026_27_finance p.29)
- [unknown] "2.1 Departmental payment - - - - (17,872) Securing the National Disability Insurance Scheme for Future Generations (k) 2" (fy=2027-28, federal_pbs_2026_27_finance p.29)
- [unknown] "2.1 Departmental payment - - - - (17,872) Securing the National Disability Insurance Scheme for Future Generations (k) 2" (fy=2028-29, federal_pbs_2026_27_finance p.29)
- [unknown] "2.1 Departmental payment - - - - (17,872) Securing the National Disability Insurance Scheme for Future Generations (k) 2" (fy=2029-30, federal_pbs_2026_27_finance p.29)
- [program] "2029­30 Payment measures (continued) Securing the National Disability Insurance Scheme for Future Generations (h) 1.1 De" (fy=2026-27, federal_pbs_2026_27_finance p.139)
- [program] "2029­30 Payment measures (continued) Securing the National Disability Insurance Scheme for Future Generations (h) 1.1 De" (fy=2027-28, federal_pbs_2026_27_finance p.139)
- [program] "2029­30 Payment measures (continued) Securing the National Disability Insurance Scheme for Future Generations (h) 1.1 De" (fy=2028-29, federal_pbs_2026_27_finance p.139)
- [program] "2029­30 Payment measures (continued) Securing the National Disability Insurance Scheme for Future Generations (h) 1.1 De" (fy=2029-30, federal_pbs_2026_27_finance p.139)
- [malformed_concatenated_row] "National Disability Insurance Scheme - Getting the NDIS back on track (l) 2.1 Departmental payment - 150 150 100 - Natio" (fy=2024-25, federal_pbs_2024_25_finance_portfolio p.30)
- [malformed_concatenated_row] "National Disability Insurance Scheme - Getting the NDIS back on track (l) 2.1 Departmental payment - 150 150 100 - Natio" (fy=2025-26, federal_pbs_2024_25_finance_portfolio p.30)
