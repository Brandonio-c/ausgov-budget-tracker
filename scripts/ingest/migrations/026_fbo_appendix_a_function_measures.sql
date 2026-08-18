-- Pre-2019 FBO Appendix A: Expenses by Function and Sub-function measure
-- definitions (026), item 8.1's first slice (FY2010-11/FY2011-12 only -
-- the confirmed-tractable 3-numeric-column sub-generation). Semantics,
-- page-anchor evidence, and the deliberately-excluded scope (FY2012-13
-- onward, sub-function detail, non-"Estimate at Outcome" columns) are
-- documented in config/measure-semantics/fbo_appendix_a_function.yaml and
-- ops/reports/fbo-appendix-a-page-anchor-scoping-20260818T160000Z.md.
--
-- additive_across_time = 0: a full-year figure is never summed with
-- another year's figure. additive_across_nodes = 1 for the 18 function/
-- "Other purposes" line items - they are genuinely additive to
-- fbo_appendix_a_total_expenses (a real, source-stated relationship,
-- verified this pass: the 5 Other purposes items sum exactly to the
-- published Total other purposes for both loaded editions, and the 13
-- functions plus Total other purposes sum to Total expenses to within
-- $2 million / 0.0006% for FY2010-11 - immaterial published rounding -
-- and exactly for FY2011-12). root_total_allowed = 1 for those 18, and 0
-- for fbo_appendix_a_total_other_purposes/fbo_appendix_a_total_expenses
-- (already-derived totals, never themselves an addend).

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('fbo_appendix_a_general_public_services', 'FBO Appendix A: General public services',
     'Final Budget Outcome Appendix A: GGS expenses for the General public services function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_general_public_services', NULL, 'AUD', 1),
    ('fbo_appendix_a_defence', 'FBO Appendix A: Defence',
     'Final Budget Outcome Appendix A: GGS expenses for the Defence function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_defence', NULL, 'AUD', 1),
    ('fbo_appendix_a_public_order_safety', 'FBO Appendix A: Public order and safety',
     'Final Budget Outcome Appendix A: GGS expenses for the Public order and safety function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_public_order_safety', NULL, 'AUD', 1),
    ('fbo_appendix_a_education', 'FBO Appendix A: Education',
     'Final Budget Outcome Appendix A: GGS expenses for the Education function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_education', NULL, 'AUD', 1),
    ('fbo_appendix_a_health', 'FBO Appendix A: Health',
     'Final Budget Outcome Appendix A: GGS expenses for the Health function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_health', NULL, 'AUD', 1),
    ('fbo_appendix_a_social_security_welfare', 'FBO Appendix A: Social security and welfare',
     'Final Budget Outcome Appendix A: GGS expenses for the Social security and welfare function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_social_security_welfare', NULL, 'AUD', 1),
    ('fbo_appendix_a_housing_community_amenities', 'FBO Appendix A: Housing and community amenities',
     'Final Budget Outcome Appendix A: GGS expenses for the Housing and community amenities function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_housing_community_amenities', NULL, 'AUD', 1),
    ('fbo_appendix_a_recreation_culture', 'FBO Appendix A: Recreation and culture',
     'Final Budget Outcome Appendix A: GGS expenses for the Recreation and culture function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_recreation_culture', NULL, 'AUD', 1),
    ('fbo_appendix_a_fuel_energy', 'FBO Appendix A: Fuel and energy',
     'Final Budget Outcome Appendix A: GGS expenses for the Fuel and energy function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_fuel_energy', NULL, 'AUD', 1),
    ('fbo_appendix_a_agriculture_forestry_fishing', 'FBO Appendix A: Agriculture, forestry and fishing',
     'Final Budget Outcome Appendix A: GGS expenses for the Agriculture, forestry and fishing function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_agriculture_forestry_fishing', NULL, 'AUD', 1),
    ('fbo_appendix_a_mining_manufacturing_construction', 'FBO Appendix A: Mining, manufacturing and construction',
     'Final Budget Outcome Appendix A: GGS expenses for the Mining, manufacturing and construction function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_mining_manufacturing_construction', NULL, 'AUD', 1),
    ('fbo_appendix_a_transport_communication', 'FBO Appendix A: Transport and communication',
     'Final Budget Outcome Appendix A: GGS expenses for the Transport and communication function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_transport_communication', NULL, 'AUD', 1),
    ('fbo_appendix_a_other_economic_affairs', 'FBO Appendix A: Other economic affairs',
     'Final Budget Outcome Appendix A: GGS expenses for the Other economic affairs function (actual/Estimate at Outcome).',
     0, 1, 'accrual', 'fbo_appendix_a_other_economic_affairs', NULL, 'AUD', 1),
    ('fbo_appendix_a_public_debt_interest', 'FBO Appendix A: Public debt interest',
     'Final Budget Outcome Appendix A: GGS expenses for Public debt interest (Other purposes), actual/Estimate at Outcome.',
     0, 1, 'accrual', 'fbo_appendix_a_public_debt_interest', NULL, 'AUD', 1),
    ('fbo_appendix_a_nominal_superannuation_interest', 'FBO Appendix A: Nominal superannuation interest',
     'Final Budget Outcome Appendix A: GGS expenses for Nominal superannuation interest (Other purposes), actual/Estimate at Outcome.',
     0, 1, 'accrual', 'fbo_appendix_a_nominal_superannuation_interest', NULL, 'AUD', 1),
    ('fbo_appendix_a_general_purpose_intergovt_transactions', 'FBO Appendix A: General purpose inter-government transactions',
     'Final Budget Outcome Appendix A: GGS expenses for General purpose inter-government transactions (Other purposes), actual/Estimate at Outcome.',
     0, 1, 'accrual', 'fbo_appendix_a_general_purpose_intergovt_transactions', NULL, 'AUD', 1),
    ('fbo_appendix_a_natural_disaster_relief', 'FBO Appendix A: Natural disaster relief',
     'Final Budget Outcome Appendix A: GGS expenses for Natural disaster relief (Other purposes), actual/Estimate at Outcome.',
     0, 1, 'accrual', 'fbo_appendix_a_natural_disaster_relief', NULL, 'AUD', 1),
    ('fbo_appendix_a_contingency_reserve', 'FBO Appendix A: Contingency reserve',
     'Final Budget Outcome Appendix A: GGS expenses for the Contingency reserve (Other purposes), actual/Estimate at Outcome.',
     0, 1, 'accrual', 'fbo_appendix_a_contingency_reserve', NULL, 'AUD', 1),
    ('fbo_appendix_a_total_other_purposes', 'FBO Appendix A: Total other purposes',
     'Final Budget Outcome Appendix A: the published Total other purposes subtotal - directly cited from the source''s own stated row, never computed here.',
     0, 0, 'accrual', 'fbo_appendix_a_total_other_purposes', NULL, 'AUD', 0),
    ('fbo_appendix_a_total_expenses', 'FBO Appendix A: Total expenses',
     'Final Budget Outcome Appendix A: the published Total expenses bottom line - directly cited from the source''s own stated row, never computed here.',
     0, 0, 'accrual', 'fbo_appendix_a_total_expenses', NULL, 'AUD', 0);
