# Dashboard API traversal audit — 20260803T205517Z

Base URL: `http://127.0.0.1:8000` (real backend against `data/facts.db`)

**Total hard failures across all paths: 449**

| path | visited_nodes | scope | jurisdiction | edge_kind | additive>100% | cross_year | label_quality | citation | transport |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| federal_actuals_2024_25 | 328 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| federal_budget_latest | 1647 | 0 | 0 | 248 | 0 | 0 | 201 | 0 | 0 |
| qld_state_actuals_2024_25 | 229 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| local_government_actuals_2024_25 | 1834 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| federal_debt_latest | 49 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| federal_gdp_ratios_latest | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## scope_failures

None.

## jurisdiction_failures

None.

## edge_kind_failures

- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337604, "name": "Cash used Grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337719, "name": "Cash used Lease liability \u2013 principal payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337280, "name": "Departmental payment OC1,OC2 -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337294, "name": "Forestry Growth Fund - industry growth grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337654, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337634, "name": "Other Grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337740, "name": "Payment from related entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337444, "name": "Payment to CSIRO \u2013 contribution to the operating costs of the Australian Centre for Disease Preparedness", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337574, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337399, "name": "Payments to corporate entities (Draw-down)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337334, "name": "Payments to corporate entities (Draw-down) (a) Australian Pesticides and Veterinary Medicines Authority", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337359, "name": "Payments to corporate entities (Draw-down) (a) Regional Investment Corporation", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337339, "name": "Payments to corporate entities total", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337609, "name": "Repayments of advances and loans", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337379, "name": "Special appropriation Farm Household Support Act 2014, s.105 \u2013 payments for Farm Household Allowance", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337284, "name": "Supporting Trade and Tourism (b) Administered payment 1.10 - 220 80 - - Departmental payment OC1 -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351934, "name": "Cash used Grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351916, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352066, "name": "Extension (c) 1.1 Departmental payment - - - - (1,269) Total payment measures Departmental -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351913, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351993, "name": "Labour Hire, and Other Non-Wage Expenses \u2014 One-Year Extension (b) 1.1 Departmental payment - - - - (61) Total -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351974, "name": "Payment from related entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351943, "name": "Payment measures Addressing Systems Abuse in the Child Support Scheme (a) 1.1 - -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351883, "name": "Payments for Grants to Australian organisations", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351858, "name": "Payments for grants to Australian organisations", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351861, "name": "Payments for membership to international bodies", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351892, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351870, "name": "Payments to corporate entities Australian Human Rights Commission", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352062, "name": "Program Payment measures Boosting Productivity \u2013 Digital ID (a) 1.1 - Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350547, "name": "2029\u00ad30 Payment measures Boosting Consumer Energy Resources and Delivering Bill Savings 1.1 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350337, "name": "Administered payment \u2013 286 \u2013 \u2013 \u2013 Departmental payment \u2013 19,593 \u2013 \u2013 \u2013 Total \u2013 19,879 \u2013 \u2013 \u2013 Water Reform \u2013 continuing funding 4.1 Administered payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350325, "name": "Boosting Productivity \u2013 Accelerating Approvals (b) 2.1 Administered payment \u2013 \u2013 \u2013 \u2013 \u2013 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350950, "name": "Cash received Contributed equity \u2013 \u2013 \u2013 \u2013 1,331 Total cash received \u2013 \u2013 \u2013 \u2013 1,331 Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350534, "name": "Cash used Grant and subsidies paid", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350636, "name": "Cash used Lease liability \u2013 principal payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350492, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350341, "name": "Departmental payment \u2013 1,520 \u2013 \u2013 \u2013 Total \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350333, "name": "Energy Sovereignty \u2013 Establishing a Domestic Gas Reservation 1.1 Administered payment \u2013 \u2013 \u2013 \u2013 \u2013 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350387, "name": "Fuel Security Act 2021 (a) nfp nfp nfp nfp nfp Total special appropriations nfp nfp nfp nfp nfp Payments to corporate entities Australian Renewable Energy Agenc", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350626, "name": "GST on Supplier Payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350920, "name": "Grants (a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350930, "name": "Grants (b)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350945, "name": "Grants cash received", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350827, "name": "Grants received from Government and Industry Partners", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350541, "name": "INVESTING ACTIVITIES Cash received Repayments of loans and advances \u2013 22,000 \u2013 \u2013 \u2013 Other (a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350857, "name": "Interest payment on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350490, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350631, "name": "Lease liability \u2013 interest payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350719, "name": "Other investing cash payments for policy purposes", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350910, "name": "Payment from related entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350862, "name": "Payment to Queensland Government for Field Management Program", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350822, "name": "Payments to Queensland Government for Field Management Program", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350508, "name": "Payments to corporate Commonwealth entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350536, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350405, "name": "Payments to corporate entities (a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350368, "name": "Payments to corporate entities (b)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350442, "name": "Payments to corporate entities Australian Institute of Marine Science", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350329, "name": "Program Energy Sovereignty \u2013 Fuel Security and Resilience (b) 1.1 Administered payment \u2013 \u2013 \u2013 \u2013 \u2013 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350351, "name": "Special accounts \u2013 1,317 \u2013 \u2013 \u2013 Special appropriations (a) nfp nfp nfp nfp nfp Payments to corporate entities (b)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 346947, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 346850, "name": "Claims payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 346900, "name": "GST payment to suppliers", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 346835, "name": "Grants received from portfolio department", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 346910, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347024, "name": "Net GST paid 793 Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340662, "name": "2029\u00ad30 Payment measures (continued) Securing the National Disability Insurance Scheme for Future Generations (h) 1.1 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340616, "name": "2029\u00ad30 Payment measures Indigenous Electoral Participation Program (a) 1.1 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340801, "name": "Addressing Systems Abuse in the Child Support Scheme 1.1, 1.2, 1.3 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340562, "name": "Cash used Grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340477, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340769, "name": "Department of Finance Boosting Productivity \u2013 Digital ID 1.1, 1.2, 1.3 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340777, "name": "Department of Health, Disability and Ageing Better Care for Older Australians 1.1, 1.2 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340773, "name": "Employment Services and Support \u2013 additional funding 1.1, 1.2, 1.3 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340189, "name": "Grant in Aid - Chifley Research Centre", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340194, "name": "Grant in Aid - Green Institute", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340199, "name": "Grant in Aid - Menzies Research Centre", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340204, "name": "Grant in Aid - Page Research Centre", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340214, "name": "Grant in Aid - RSPCA Australia Inc", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340209, "name": "Grant in Aid - Royal Humane Society of Australasia", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340789, "name": "Improving Access and Uptake of Medicines and Vaccines 1.1, 1.2, 1.3 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340797, "name": "Improving Access to Home Care 1.1, 1.2, 1.3 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340457, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340742, "name": "Non-wage Expenses \u2013 one year extension (b) 1.1 Departmental payment - - - - (262) Total payment measures Departmental -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340577, "name": "Repayments of advances and loans", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340658, "name": "Research, Development and Innovation (c) 1.1 Departmental payment - 30 35 - - Boosting Productivity \u2013 Accelerating Approvals (d) 1.1 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340781, "name": "Securing the National Disability Insurance Scheme for Future Generations 1.1, 1.2 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340264, "name": "Special accounts Coordinated Procurement Contracting Special Account", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340785, "name": "Strengthening Medicare 1.1, 1.2, 1.3 Departmental payment (4)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340572, "name": "Superannuation payments (f)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340793, "name": "Thriving Kids 1.1, 1.2, 1.3 Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340369, "name": "Transfers to portfolio special accounts for project payments Disaster Ready Fund special account - expense (200,000) - - - - Closing balance", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351167, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350988, "name": "Common Security (the Jakarta Treaty 2026) (e) 1.1, 1.2, 1.6 Administered payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350984, "name": "Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350981, "name": "Departmental payment - nfp nfp nfp nfp Total - nfp nfp nfp nfp Boosting Australia's Partnership w ith India (b) 1.1 Administered payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351250, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350992, "name": "Maintaining Support for an Effective Foreign Service (f) (g) 1.1, 2.1 Administered payment (3,721)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351187, "name": "Other grants and contributions", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351301, "name": "Payment from portfolio department (a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351221, "name": "Payments to corporate commonw ealth entities \u2013 Tourism Australia", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351014, "name": "Program 1.4: Payments to International Organisations Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351115, "name": "Public Diplomacy and Other International Grants Programs", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350996, "name": "Supporting Trade and Tourism (k) 1.1 Administered payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351164, "name": "Transfer to the OPA - 12,000 73,542 - - Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343251, "name": "2029\u201330 Health Protection (c) Department of Health, Disability and Ageing Administered capital payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343256, "name": "Administered payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343370, "name": "Aged Care (Accommodation Payment Security) Act 2006 - - - - - Total for Program", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343275, "name": "Australian Digital Health Agency Departmental payments 1.1 - 12,175 6,907 - - Department of the Treasury Administered payments -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343491, "name": "Cash used Grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343455, "name": "Cash used Lease principal repayments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343242, "name": "Commission Departme ntal payments 1.1 - 156,837 - - - T otal payments -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343264, "name": "Departmental capital payments 1.1 - 150 - - - Departme nt of the Treasury Administered payments -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343260, "name": "Departmental capital payments 3 - 27,895 2,392 - - Total payments -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343271, "name": "Departmental capital payments 3 - 4,978 1,477 - - Department of the Treasury Administered payments - -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343621, "name": "GST Payments to Suppliers", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343635, "name": "Grant Payments -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343536, "name": "Grants from the Portfolio Department", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343527, "name": "Grants received", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343245, "name": "Health, Agencies, Systems and Data (a) Department of Health, Disability and Ageing Administered payments 1.1 500 -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343510, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343364, "name": "National Health Act 1953 - continence aids payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343499, "name": "Other operating payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337112, "name": "Payment from related entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343278, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343390, "name": "Payments to corporate entities Payments to Corporate Entity - NDIA Agency costs", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343326, "name": "Special appropriations Private Health Insurance Act 2007 - incentive payments and rebate", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343268, "name": "T otal payments -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336238, "name": "2028\u201329 2029\u201330 Supporting Trade and Tourism (g) 3.1 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336226, "name": "Australian Trusted Trader Program \u2013 expansion 3.1 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336366, "name": "Cash used Grant", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336321, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336230, "name": "Departmental payment 183 565 \u2013 \u2013 \u2013 Total 183 565 \u2013 \u2013 \u2013 Streamlining AusCheck's Background Checking Services 1.2 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336569, "name": "Grant payables", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336316, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336433, "name": "Securing the National Disability Insurance Scheme for Future Generations (d) 1.1 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336400, "name": "Securing the National Disability Insurance Scheme for Future Generations (e) 1.1 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336545, "name": "Supplier prepayments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336234, "name": "Supporting Aviation Priorities (f) 3.2 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335442, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335324, "name": "Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335437, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335471, "name": "Payments to corporate Commonwealth entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335349, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339641, "name": "Cash used Grant", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339763, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339098, "name": "Community Infrastructure 3.1, 3.5 Administered payment (99,971)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339381, "name": "Consumer Representation Grants Program", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339094, "name": "Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339599, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339813, "name": "Net GST paid 483 - - - 906 Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339789, "name": "Payment from related entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339090, "name": "Payment measures Building a Better Future through Considered Infrastructure Investment 1.1 Administered payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339218, "name": "Payment scheme for Airservices Australia's en route charges(a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339520, "name": "Payment to corporate entities(b)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339618, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339108, "name": "Payments to corporate entities(a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339466, "name": "Payments to corporate entities(a) Australian Film, Television and Radio School", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339271, "name": "Payments to corporate entities(a) Northern Australia Infrastructure Facility", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339143, "name": "Payments to corporate entities(b)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339198, "name": "Payments to corporate entities(b) Australian Maritime Safety Authority", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339545, "name": "Payments to corporate entities(b) Australian Sports Commission", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339228, "name": "Payments to corporate entities(b) Civil Aviation Safety Authority", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339243, "name": "Payments to corporate entities(c)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339401, "name": "Payments to corporate entities(f) Australian Broadcasting Corporation", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339118, "name": "Table 2.1.2: Program components of Outcome 1 Components for Program 1.1: Infrastructure Investment Administered expenses Infrastructure Investment Program(a): G", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337853, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338038, "name": "Cash used Repayments of borrow ings 100 Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337770, "name": "Departmental payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338215, "name": "Grants payable", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338235, "name": "Grants payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337848, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338018, "name": "Net GST paid - Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338023, "name": "Other - loans repayments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337898, "name": "Payment from related entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338180, "name": "Payments associated w ith Land", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338240, "name": "Payments associated w ith Land Councils", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338190, "name": "Payments to Aboriginal Investment Northern Territory (b)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338245, "name": "Payments to Indigenous Land and Sea Corporation", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338185, "name": "Payments to Indigenous Land and Sea Corporation (a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338250, "name": "Payments to Northern Territory Aboriginal Investment", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337805, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338230, "name": "Subsidy payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339912, "name": "1.1.4 \u2013 Component 4 (Stillborn Baby Payment) Special appropriations A New Tax System (Family Assistance) (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339930, "name": "1.4.2 \u2013 Component 2 (Essential Medical Equipment Payment) Special appropriations Social Security (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339937, "name": "1.5.1 \u2013 Component 1 (Carer Payment) Special appropriations Social Security (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339945, "name": "1.5.5 \u2013 Component 5 (Child Disability Assistance Payment) Special appropriations Social Security (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339947, "name": "1.5.6 \u2013 Component 6 (Carer Adjustment Payment) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339953, "name": "1.6.3 \u2013 Component 3 (Parenting Payment Single) Special appropriations Social Security (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339955, "name": "1.6.4 \u2013 Component 4 (Parenting Payment Partnered) Special appropriations Social Security (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339972, "name": "1.6.8 \u2013 Component 8 (Payments under Special Circumstances) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339877, "name": "Addressing Systems Abuse in the Child Support Scheme Outcome 1 Administered payment \u2013 \u2013 \u2013 \u2013 \u2013 Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340088, "name": "Cash used Grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340072, "name": "Cash used Principal payments of lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339867, "name": "Departmental payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339873, "name": "Departmental payment \u2013 \u2013 \u2013 \u2013 \u2013 Total \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339949, "name": "Estimated Budget Forward Forward Forward 1.6.1 \u2013 Component 1 (JobSeeker Payment) Special appropriations Social Security (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339895, "name": "Estimated Budget Forward Forward Forward Program 1.6 \u2013 Working Age Payments Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340070, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340105, "name": "Interest payments on lease liability 25 11 \u2013 \u2013 \u2013 Other 1 \u2013 \u2013 \u2013 \u2013 Total cash used", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339865, "name": "Payment measures (continued) Addressing Online Gambling Harms (f) 2.1 Administered payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339897, "name": "Program 1.7 \u2013 Student Payments Administered expenses Special appropriations Social Security (Administration) Act 1999", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340050, "name": "Psychological Support payment) Special appropriations National Redress Scheme for Institutional Child Sexual Abuse Act 2018", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339871, "name": "Supporting Individuals and Families Impacted by Intercountry Adoptions 2.1 Administered payment \u2013", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 258278, "name": "National Partnership Payments \u2013 Assistance to people with disabilities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 258248, "name": "National Partnership Payments \u2013 Assistance to the aged", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 258413, "name": "Working Age Payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 258418, "name": "Student Payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347330, "name": "Cash used Grant", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347263, "name": "Cash used Grants paid", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347336, "name": "Cash used Net repayment of borrowings", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347313, "name": "Cash used Payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347226, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347199, "name": "Electric Car Discount \u2013 more sustainable fringe benefits tax treatment of electric cars Administered payments 1.4 - -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347225, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347266, "name": "Other operating payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347423, "name": "Payment from Treasury", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347211, "name": "Payment to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347208, "name": "Payment to corporate entities Housing Australia", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347235, "name": "Payments to corporate entities (a)", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347265, "name": "Payments to corporate entities within the Portfolio", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347258, "name": "Provisions Grants provisions", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347433, "name": "Repayments of advances and loans", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347346, "name": "Risk equalisation levy payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345493, "name": "Advocacy Grants and Support", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345556, "name": "Australian Participants in British Nuclear Tests and British Commonwealth Occupation Force (Treatment) Act 2006 Nuclear test health care payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345589, "name": "Cash used Lease liability - principal payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345497, "name": "Compensation payments for British Commonwealth and Allied veterans", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345492, "name": "Discretionary Payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345604, "name": "Grant payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345596, "name": "Health care payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345603, "name": "Health payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345511, "name": "Incapacity payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345516, "name": "Income maintenance payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345586, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345509, "name": "Ordinary annual services (Appropriation Bill No. 1) Other income support and compensation-related payments - DRCA", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345513, "name": "Other income support and compensation-related payments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345510, "name": "Other income support and compensation-related payments - MRCA", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345465, "name": "Outlook (MYEFO) (continued) Program Payment measures (continued) Strengthening Medicare (a) 2.1 Administered payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345456, "name": "Outlook (MYEFO) Program Payment measures Better Care for Older Australians (a) 2.4 Administered payment -", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345606, "name": "Payments to corporate entities", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345605, "name": "Payments to employees", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345461, "name": "Pharmaceutical Benefits Scheme New and Amended Listings (a) (d) 2.1, 2.3 Administered payment", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345538, "name": "Program 2.4: Veterans\u2019 Community Care and Support Annual Administered Expenses: Ordinary annual services (Appropriation Bill No. 1) Grants-In-Aid", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345545, "name": "Public Governance, Performance and Accountability Act 2013 Section 77 Repayments", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345539, "name": "Veteran Wellbeing Grants", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352818, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 342780, "name": "Cash used Principal payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 342775, "name": "Interest payments on lease liability", "reason": "name_suggests_non_additive_relationship_but_edge_kind_is_additive"}

## additive_reconciliation_failures

None.

## cross_year_failures

None.

## label_quality_failures

- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337519, "name": "Adjusted opening balance (1,458,801)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337696, "name": "Contributions by owners Departmental Capital Budget (DCB) - - 504 504 Sub-total transactions with owners - - 504 504 Estimated closing balance as at 30 June 202", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352006, "name": "1.1.1 - Component 1 Federal Court of Australia Annual administered expenses: Special appropriations: Public Governance Performance and Accountability Act 2013", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352009, "name": "1.1.2 - Component 2: National Native Title Tribunal Annual departmental expenses: Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352053, "name": "Accumulated depreciation/ amortisation and Impairment \u2013 ROU assets - - (636) - - (636) Closing net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352047, "name": "Accumulated depreciation/ amortisation and impairment \u2013 ROU assets - - (561) - - (561) Opening net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352030, "name": "Budget May 2026 Opening balance/cash reserves at 1 July 12,859 12,659 Funds from Government Annual appropriations - ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352075, "name": "Contributions by owners Departmental Capital Budget (DCB) - - 880 880 Sub-total transactions with owners - - 880 880 Estimated closing balance as at 30 June 202", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351993, "name": "Labour Hire, and Other Non-Wage Expenses \u2014 One-Year Extension (b) 1.1 Departmental payment - - - - (61) Total -", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352003, "name": "Program 1.1: Federal Court of Australia Administered expenses Special appropriations Public Governance Performance and Accountability Act 2013", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351841, "name": "Program 1.4: Justice Services Administered expenses Ordinary annual services (Appropriation Bill No. 1) Community Legal Services Program", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351873, "name": "Program 1.5: Family Relationships Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351878, "name": "Program 1.6: Criminal Justice Administered expenses Ordinary annual services (Appropriation Bill No. 1) Justice Reinvestment (c)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352012, "name": "Program 2.1: Federal Circuit and Family Court of Australia (Division 1) Administered expenses Special appropriations Public Governance Performance and Accountab", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352018, "name": "Program 4.2: Commonwealth Courts Registry Services Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350595, "name": "2026\u00ad27 Opening balance/cash reserves at 1 July 923,819 541,104 Funds from Government Annual appropriations - ordinary annual services (a) (b) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350671, "name": "Add Fair Value Loss on Financial Assets 83,697 \u2013 \u2013 \u2013 \u2013 Less Fair Value Gain on Investments (72,340) \u2013 \u2013 \u2013 \u2013 Net adjustments to investment carrying values", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350621, "name": "Adjusted opening balance (1,510,385)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350699, "name": "Adjusted opening balance (1,713,960)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350954, "name": "By purchase - ROU assets 16,728 \u2013 \u2013 16,728 Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350651, "name": "By purchase \u2013 ROU 571 15,632 329 - 16,532 Total additions", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350950, "name": "Cash received Contributed equity \u2013 \u2013 \u2013 \u2013 1,331 Total cash received \u2013 \u2013 \u2013 \u2013 1,331 Cash used Principal payments on lease liability", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350745, "name": "Departmental Capital Budget (DCB) \u2013 \u2013 558 558 Sub-total transactions with owners \u2013 \u2013 947 947 Estimated closing balance as at 30 June 2027 (84,573)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350309, "name": "Estimated Estimate Administered Annual appropriations - ordinary annual services (a) Prior year appropriations available (b) 953,803 527,795 Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350900, "name": "Estimated Estimate Opening balance/cash reserves at 1 July 197,185 174,853 Funds from Government Annual appropriations \u2013 ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350789, "name": "Estimated Estimate Opening balance/cash reserves at 1 July 303,829 281,611 Funds from Government Annual appropriations \u2013 ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350401, "name": "Powering the Regions Fund - Critical Inputs to Clean Energy Industries 24,216 154,700 625 \u2013 \u2013 Powering the Regions Fund - Safeguard Transformation Stream", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350729, "name": "Program 1.1: Clean Energy Regulator Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350583, "name": "Program 1.1: Marine Research Revenue from Government Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1)) (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350905, "name": "Program 1.1: Murray\u2013Darling Basin Authority Revenue from Government Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1)) (a) (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350794, "name": "Program 1.1: Parks and Reserves Revenue from Government Ordinary annual services (Appropriation Bill (No.1) and Supply Bill (No. 1)) (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350346, "name": "Program 1.1: Support reliable, secure and affordable energy Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350356, "name": "Program 1.2: Reduce Australia's greenhouse gas emissions Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350410, "name": "Program 2.2: Protect Australia's cultural, historic and First Nations heritage Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Su", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350456, "name": "Program 4.1: Protect, restore and sustainably manage Australia's water resources Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and ", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350373, "name": "Special accounts 10,632 \u2013 \u2013 \u2013 \u2013 Expenses not requiring appropriation in the Budget year (c)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350394, "name": "Supply Bill (No. 1))) Accelerating EV Charging Program \u2013 \u2013 9,500 23,687 \u2013 Australia Pacific Partnership for Energy Transition", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350604, "name": "Surplus/(deficit) attributable to the Australian Government (374,275) (308,229)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350807, "name": "development of the Marine Park. Estimated Budget Forward Forward Forward Program 1.1: Great Barrier Reef Marine Park Authority Departmental expenses Departmenta", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 350779, "name": "insights from research. Estimated Budget Forward Forward Forward Program 1.1: Reviewing Climate Change Policies Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 346974, "name": "By purchase - appropriation ordinary annual services - ROU assets 29,140 - - 29,140 Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 346924, "name": "By purchase - other - ROU assets 23,051 600 - 23,651 Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340442, "name": "Adjusted opening balance (1,461,182)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340636, "name": "By purchase - appropriation ordinary annual services - ROU assets 16,712 - - 16,712 Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340654, "name": "By purchase - other - ROU assets 14,236 - - 14,236 Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340742, "name": "Non-wage Expenses \u2013 one year extension (b) 1.1 Departmental payment - - - - (262) Total payment measures Departmental -", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340806, "name": "Program 1.2 \u2013 Customer Service Delivery Administered expenses Ordinary annual services (Appropriation Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340757, "name": "Program 1.2: Independent Parliamentary Standards Commission Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340688, "name": "Program 1.2: Management of the Investment of the Australian Government Investment Funds Departmental expenses Special accounts Future Fund Special Account", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340816, "name": "Program 1.3 \u2013 Technology and Transformation Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340244, "name": "Program 2.2: Data Scheme Departmental expenses Departmental appropriation (a) Office of the National Data Commissioner", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340249, "name": "Program 2.3: Property and Construction Departmental expenses Special accounts Property Special Account", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340254, "name": "Program 2.4: Insurance and Risk Management Departmental expenses Special accounts Comcover Special Account", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340259, "name": "Program 2.5: Procurement Departmental expenses Departmental appropriation (a) Procurement Framework", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340269, "name": "Program 2.7: Service Delivery Office Departmental expenses Departmental appropriation (a) Shared Services Transformation Program Office", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340279, "name": "Program 2.8: Public Sector Superannuation Administered expenses Ordinary annual services (Appropriation Bill (No. 1)) Act of Grace", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340299, "name": "Program 2.9: Australian Government Investment Funds Administered expenses Special accounts DisabilityCare Australia Fund Special Account (c)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351316, "name": "1.1.2 - Component 2: Industry Development Annual departmental expenses: Program support", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351328, "name": "By purchase - appropriation ordinary annual services - ROU assets (161) - - (161) Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351311, "name": "Forw ard Forw ard 1.1.1 - Component 1: Grow Demand Annual departmental expenses: Program support", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351282, "name": "Forw ard Forw ard Program 1.1: Secret intelligence Departmental expenses Departmental appropriation (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351244, "name": "Forw ard Forw ard Program 2.1: Consular Services Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351135, "name": "Forw ard Forw ard Program 3.1: Foreign Affairs and Trade Security and IT Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351001, "name": "Forw ard Program 1.1: Foreign Affairs and Trade Operations Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351262, "name": "Forw ard Program 1.1: International Agricultural Research and Development Administered expenses Ordinary annual services (Appropriation Bill (No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351298, "name": "Forw ard Program 1.1: Supporting Outcome 1 Revenue from Government Ordinary annual services (Appropriation Bill (No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351125, "name": "Forw ard Program 2.1: Consular Services Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351009, "name": "Program 1.2: Official Development Assistance Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351287, "name": "Program 1.2: Other services Departmental expenses Departmental appropriation (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351014, "name": "Program 1.4: Payments to International Organisations Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351019, "name": "Program 1.5: New Colombo Plan - Transforming Regional Relationships Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351024, "name": "Program 1.6: Public Information Services and Public Diplomacy Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351029, "name": "Program 1.7: Programs to Promote Australia's International Tourism Interests Administered expenses Corporate Commonw ealth Entity - Tourism Australia", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351130, "name": "Program 2.2: Passport Services Administered expenses Special appropriations Special appropriation PGPA Act 2013 s77", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 351164, "name": "Transfer to the OPA - 12,000 73,542 - - Interest payments on lease liability", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343553, "name": "2026\u201327 Opening balance/cash reserves at 1 July 126,769 124,943 Funds from Government annual appropriations Ordinary annual services(a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343275, "name": "Australian Digital Health Agency Departmental payments 1.1 - 12,175 6,907 - - Department of the Treasury Administered payments -", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343504, "name": "Cash used Advances made - 1,471 1,471 - - Equity injections to corporate Commonwealth entities", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337097, "name": "DEPARTMENTAL Prior year appropriation available 2,528,959 3,101,490 Annual appropriations Annual appropriations - ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343260, "name": "Departmental capital payments 3 - 27,895 2,392 - - Total payments -", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343543, "name": "Estimated expenditure on new or replacement assets By purchase - internal resources 200 - 71 271 By purchase - RoU - 10,022 - 10,022 Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343521, "name": "Expenses not requiring appropriation in the Budget year(c) 523 1,047 1,047 697 - Operating deficit (surplus) Total for Program", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343281, "name": "Program 1.2: Mental Health and Suicide Prevention (a) Administered expenses Ordinary annual services (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337107, "name": "Program 1.2: National Disability Insurance Agency and General Supports Revenue from Government Ordinary annual services", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343284, "name": "Program 1.3: First Nations Health (a) Administered expenses Ordinary annual services (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343287, "name": "Program 1.5: Preventive Health and Chronic Disease Support (a) Administered expenses Ordinary annual services (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343290, "name": "Program 1.6: Primary Health Care Quality and Coordination (a) Administered expenses Ordinary annual services (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343293, "name": "Program 1.7: Primary Care Practice Incentives and Medical Indemnity Administered expenses Ordinary annual services (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343299, "name": "Program 1.9: Immunisation (a) Administered expenses Ordinary annual services (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343314, "name": "Program 2.2: Hearing Services Administered expenses Ordinary annual services (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343317, "name": "Program 2.3: Pharmaceutical Benefits Administered expenses Ordinary annual services (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343323, "name": "Program 2.4: Private Health Insurance Administered expenses Ordinary annual services (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343329, "name": "Program 2.5: Dental Services (b) Administered expenses Special appropriations Dental Benefits Act 2008", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343332, "name": "Program 2.7: Assistance through Aids and Appliances Administered expenses Ordinary annual services (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343346, "name": "Program 3.2: Aged Care Services(b) (c) Administered expenses Ordinary annual services (a)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343380, "name": "Program 4.1: Disability and Carers 4.1.1 \u2013 Component 1 (Disability and Carers) Annual administered expenses: Ordinary annual services Disability and Carer Suppo", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 343375, "name": "Program 4.2: National Disability Insurance Scheme (a) Administered expenses Ordinary annual services (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336424, "name": "ASSETS Funded by capital appropriations (a) 24,374 32,511 \u2013 \u2013 \u2013 Funded by capital appropriation \u2013 DCB (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336512, "name": "ASSETS Funded by capital appropriations (a) 33,177 10,926 996 \u2013 \u2013 Funded by capital appropriation \u2013 DCB (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336516, "name": "Accumulated depreciation/ amortisation and impairment \u2013 ROU assets (25,550) \u2013 \u2013 (25,550) Opening net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336520, "name": "Accumulated depreciation/ amortisation and impairment \u2013 ROU assets (30,915) \u2013 \u2013 (30,915) Closing net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336301, "name": "Adjusted opening balance (4,405,125)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336419, "name": "Equity injections \u2013 Bill 2 24,267 32,511 \u2013 \u2013 \u2013 Total new capital appropriations", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336507, "name": "Equity injections \u2013 Bill 2 35,177 8,926 996 \u2013 \u2013 Total new capital appropriations", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336248, "name": "Program 1.3: Cyber Security Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336253, "name": "Program 1.5: Regional Cooperation Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336258, "name": "Program 2.2: Visas Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336263, "name": "Program 2.4: UMA Offshore Management Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336268, "name": "Program 3.2: Border Management Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336273, "name": "Program 3.4: Border Enforcement Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336564, "name": "Rendering of Services \u2013 \u2013 14,479 14,162 \u2013 Total non-taxation revenue", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336574, "name": "Sale of goods and rendering of services \u2013 \u2013 14,479 14,162 \u2013 Other", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336243, "name": "Special accounts 22,182 9,132 \u2013 \u2013 \u2013 Expenses not requiring appropriation in the Budget year (b)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 336525, "name": "Supply Bill (No. 1)) 10,960 2,000 \u2013 \u2013 \u2013 Special appropriations Social Security (Administration) Act 1999", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335631, "name": "2026\u00ad27 Opening balance/cash reserves at 1 July 1,415,937 885,659 Funds from Government Annual appropriations - ordinary annual services (a) (b) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335566, "name": "2026\u00ad27 Opening balance/cash reserves at 1 July 671,023 594,291 Funds from Government Annual appropriations - ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335618, "name": "2026\u00ad27 Opening balance/cash reserves at 1 July 77,838 67,861 Funds from Government Annual appropriations - ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335534, "name": "Budget May 2026 Opening balance/cash reserves at 1 July 67,343 69,361 Funds from Government Annual appropriations - ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335466, "name": "By purchase - other - ROU assets - 2,605 - - 2,605 Total additions -", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335320, "name": "Estimated Estimate Administered Annual appropriations - ordinary annual services (a)(b) Prior year appropriations available 406,589 142,511 Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335610, "name": "Program 1.2: Education and Awareness Departmental expenses Special accounts", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335329, "name": "Program 1.2: Investing in science and technology Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1)) (c)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335615, "name": "Program 1.3: Advice to Government and International Engagement Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 335539, "name": "Program 1: Science and Technology Solutions Revenue from Government Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339686, "name": "Accumulated depreciation/amortisation and impairment - ROU assets - - (718) - - (718) Closing net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339680, "name": "Accumulated depreciation/amortisation and impairment - ROU assets - - (718) - - (718) Opening net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339840, "name": "Contributions by owners Departmental Capital Budget (DCB) - - 742 742 Sub-total transactions with owners - - 742 742 Estimated closing balance as at 30 June 202", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339855, "name": "Contributions by owners Equity injection - Appropriation - - 911 911 Sub-total transactions with owners - - 911 911 Estimated closing balance as at 30 June 2027", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339691, "name": "Includes impact of applying leases under AASB 16 Leases Program 1.1: ABC General Operational Activities Revenue from government Ordinary annual services Appropr", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339858, "name": "May 2026 Opening balance/cash reserves at 1 July 12,218 11,091 Funds from government Annual appropriations - ordinary annual services(a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339849, "name": "May 2026 Opening balance/cash reserves at 1 July 22,630 13,813 Funds from government Annual appropriations - ordinary annual services(a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339784, "name": "May 2026 Opening balance/cash reserves at 1 July 36,766 25,779 Funds from government Annual appropriations - ordinary annual services(a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339846, "name": "May 2026 Opening balance/cash reserves at 1 July 45,980 47,280 Funds from government Annual appropriations - ordinary annual services(a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339701, "name": "Program 1.2: ABC Transmission and Distribution Services Revenue from government Ordinary annual services Appropriation Bill (No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339735, "name": "Program 1.2: Consumer safeguards, education and information Administered expenses Special appropriations Telecommunications Act 1997(c)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339113, "name": "Program 1.2: Program Support for Outcome 1 Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339158, "name": "Program 2.4: Program Support for Outcome 2 Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339233, "name": "Program 3.2: Local Government Administered expenses Other services Appropriation Bill (No. 2)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339286, "name": "Program 4.2: Program Support for Outcome 4 Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339356, "name": "Program 5.2: Program Support for Outcome 5 Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339416, "name": "Program 6.2: Program Support for Outcome 6 Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339525, "name": "Program 7.2: Program Support for Outcome 7 Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339861, "name": "Surplus/(deficit) attributable to the Australian Government (15,900) (8,900)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339118, "name": "Table 2.1.2: Program components of Outcome 1 Components for Program 1.1: Infrastructure Investment Administered expenses Infrastructure Investment Program(a): G", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339168, "name": "Table 2.2.2: Program components of Outcome 2 Components for Program 2.1: Surface Transport Administered expenses Bass Strait Passenger Vehicle Equalisation Sche", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339300, "name": "Table 2.4.2: Program components of Outcome 4 Components for Program 4.1: Services to Territories Administered expenses ACT Government - national capital functio", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339613, "name": "Write-down and impairment of assets (15,834)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339208, "name": "| Portfolio Budget Statements Table 2.2.2: Program components of Outcome 2 (continued) Components for Program 2.3: Air Transport Administered expenses Airport L", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338320, "name": "Departmental Capital Budget (DCB) - - 352 352 Sub-total transactions with owners - - 352 352 Estimated closing balance as at 30 June 2027 (12,567)", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338275, "name": "Forw ard Forw ard Program 1.1: Assessments and Reports Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337962, "name": "Forw ard Forw ard Program 1.1: Australian Public Service Commission Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338132, "name": "Forw ard Forw ard Program 1.7: Program Support Departmental expenses Departmental appropriation", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337893, "name": "Program 1.1: Company Operated Hostels Revenue from Government Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338067, "name": "Program 1.1: Jobs, Land and the Economy Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338288, "name": "Program 1.1: Support for the Governor-General and Offical Activities Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill ", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338097, "name": "Program 1.2: Children and Schooling Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338280, "name": "Program 1.2: Coordination and Evaluation Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 337967, "name": "Program 1.2: Judicial Office Holders' Remuneration and Entitlements Administered expenses Special appropriations Remuneration Tribunal Act 1973", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338107, "name": "Program 1.3: Safety and Wellbeing Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338112, "name": "Program 1.4: Culture and Capability Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338122, "name": "Program 1.5: Remote Australia Strategies Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 338127, "name": "Program 1.6: Evaluation and Research Administered expenses Ordinary annual services (Appropriation Bill (No. 1))", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339947, "name": "1.5.6 \u2013 Component 6 (Carer Adjustment Payment) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339972, "name": "1.6.8 \u2013 Component 8 (Payments under Special Circumstances) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340028, "name": "2.1.2 \u2013 Component 2 (Family Safety) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340033, "name": "2.1.3 \u2013 Component 3 (Protecting Australia's Children) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340038, "name": "2.1.4 \u2013 Component 4 (Sector Representation) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340043, "name": "2.1.5 \u2013 Component 5 (Financial Wellbeing and Capability) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340048, "name": "2.1.6 \u2013 Component 6 (Volunteering and Community Connectedness) Annual administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340003, "name": "Estimated Budget Forward Forward Forward 1.8.1 \u2013 Component 1 (Disability Employment Services) Annual administered expenses Ordinary annual services (Appropriati", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340023, "name": "Estimated Budget Forward Forward Forward 2.1.1 \u2013 Component 1 (Families and Children) Annual administered expenses Ordinary annual services (Appropriation Bill N", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339895, "name": "Estimated Budget Forward Forward Forward Program 1.6 \u2013 Working Age Payments Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 340008, "name": "Estimated Budget Forward Forward Forward Program 2.1 \u2013 Families and Communities Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339879, "name": "Program 1.2 \u2013 Paid Parental Leave Administered expenses Special appropriations Paid Parental Leave Act 2010", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339884, "name": "Program 1.3 \u2013 Support for Seniors Administered expenses Special appropriations Social Security (Administration) Act 1999", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339889, "name": "Program 1.4 \u2013 Financial Support for People with Disability Administered expenses Special appropriations Social Security (Administration) Act 1999", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339891, "name": "Program 1.5 \u2013 Financial Support for Carers Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339897, "name": "Program 1.7 \u2013 Student Payments Administered expenses Special appropriations Social Security (Administration) Act 1999", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 339902, "name": "Program 1.8 \u2013 Disability Employment Services Administered expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347354, "name": "2026\u201327 Administered Annual appropriations - ordinary annual services (a) Prior year appropriations available (b) 12,115 12,090 Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347422, "name": "2026\u201327 Opening balance/cash reserves at 1 July 1,192,896 1,599,951 Funds from Government Annual appropriations - ordinary annual services (a) Outcome", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347252, "name": "2028\u201329 2029\u201330 Gains Foreign exchange gains 903,186 255,986 - - 172 Other gains", "reason": "concatenated_numeric_row"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347204, "name": "Administered expenses Ordinary annual services (Appropriation Bill (No. 1) and Supply Bill (No. 1)) 3,766 - - - - Special accounts Medicare Guarantee Fund Speci", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347245, "name": "Foreign exchange losses 819,475 406,617 - - 172 Other expenses", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347315, "name": "Program 1.1: Commonwealth Debt Management Administered expenses Special appropriations Commonwealth Inscribed Stock Act 1911", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347287, "name": "Program 1.1: Personal Insolvency and Trustees Services Administered expenses Special appropriations Public Governance, Performance and Accountability Act 2013 s", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347205, "name": "Program 1.2: International Financial Relations Administered expenses Special appropriations International Monetary Agreements Act 1947", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 347206, "name": "Program 1.4: Commonwealth-State Financial Relations Administered expenses Special appropriations Federal Financial Relations Act 2009", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345595, "name": "By purchase - ROU assets 6,805 - - 6,805 Total additions", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345473, "name": "Program 1.3: Assistance to Defence Widow/ers and Dependants Administered Expenses Special Appropriations", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345518, "name": "Program 2.2: Veterans' Hospital Services Administered Expenses Special Appropriations", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345519, "name": "Program 2.3: Veterans' Pharmaceuticals Benefits Administered Expenses Special Appropriations", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345538, "name": "Program 2.4: Veterans\u2019 Community Care and Support Annual Administered Expenses: Ordinary annual services (Appropriation Bill No. 1) Grants-In-Aid", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345566, "name": "Program 3.1: War Graves Administered Expenses Ordinary annual services (Appropriation Bill No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 345572, "name": "Program 3.1: War Graves Annual Administered Expenses: Ordinary annual services (Appropriation Bill No. 1) War graves care & maintenance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352832, "name": "Accumulated depreciation/amortisation and impairment - ROU assets (60) - - (60) Opening net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352836, "name": "Accumulated depreciation/amortisation and impairment - ROU assets (97) - - (97) Closing net book balance", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352788, "name": "Program 2: Administered 2.1 - Schools hospitality Annual administered expenses: Appropriation (Parliamentary Departments) Bill (No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352778, "name": "Program 2: Schools Hospitality Administered expenses Appropriation (Parliamentary Departments) Bill (No. 1)", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 352783, "name": "Table 2.1.2: Program components of Outcome 1 Program 1: Other Departmental DHR 1.1 - Chamber and Federation Chamber Annual departmental expenses: Departmental i", "reason": "header_or_financial_statement_line"}
- `federal_budget_latest`: {"path": "federal_budget_latest", "fact_id": 342740, "name": "Program 1.1: Parliamentary Services Administered expenses Ordinary annual services (Appropriation (Parliamentary Departments) Bill (No. 1))", "reason": "header_or_financial_statement_line"}

## citation_failures

None.

## transport_errors

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

