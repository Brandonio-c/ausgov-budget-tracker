-- MFS Note 3 (Total expense by function) measure definitions (020).
-- Second of the five MFS sibling workbooks (item 7.1), following exactly
-- the same 1:1 measure_type/compatibility_group discipline as 007's
-- Aggregates measures - no mfs_note3_* measure can ever share a
-- compatibility_group with an annual GFS/PBS actual or budget measure.
-- Semantics, label-drift evidence, and rationale for every field:
-- config/measure-semantics/mfs.yaml and
-- ops/reports/mfs-note3-function-20260813*.md.
--
-- additive_across_time = 0 for all: a YTD-through-August figure must never
-- be summed with a YTD-through-July figure for the same measure.
-- additive_across_nodes = 1 for the 18 function/"Other purposes" line
-- items - they are genuinely additive to mfs_note3_total_expenses (a real,
-- source-published relationship). root_total_allowed = 1 for those 18,
-- and 0 for mfs_note3_total_expenses itself (it is already the derived
-- total). view_family is NULL: exposed only through the dedicated MFS API,
-- never the annual view_family/mode_to_family dashboard machinery.

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('mfs_note3_general_public_services', 'MFS Note 3: General public services',
     'Monthly Financial Statements Note 3: GGS expense for the General public services function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_general_public_services', NULL, 'AUD', 1),
    ('mfs_note3_defence', 'MFS Note 3: Defence',
     'Monthly Financial Statements Note 3: GGS expense for the Defence function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_defence', NULL, 'AUD', 1),
    ('mfs_note3_public_order_safety', 'MFS Note 3: Public order and safety',
     'Monthly Financial Statements Note 3: GGS expense for the Public order and safety function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_public_order_safety', NULL, 'AUD', 1),
    ('mfs_note3_education', 'MFS Note 3: Education',
     'Monthly Financial Statements Note 3: GGS expense for the Education function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_education', NULL, 'AUD', 1),
    ('mfs_note3_health', 'MFS Note 3: Health',
     'Monthly Financial Statements Note 3: GGS expense for the Health function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_health', NULL, 'AUD', 1),
    ('mfs_note3_social_security_welfare', 'MFS Note 3: Social security and welfare',
     'Monthly Financial Statements Note 3: GGS expense for the Social security and welfare function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_social_security_welfare', NULL, 'AUD', 1),
    ('mfs_note3_housing_community_amenities', 'MFS Note 3: Housing and community amenities',
     'Monthly Financial Statements Note 3: GGS expense for the Housing and community amenities function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_housing_community_amenities', NULL, 'AUD', 1),
    ('mfs_note3_recreation_culture', 'MFS Note 3: Recreation and culture',
     'Monthly Financial Statements Note 3: GGS expense for the Recreation and culture function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_recreation_culture', NULL, 'AUD', 1),
    ('mfs_note3_fuel_energy', 'MFS Note 3: Fuel and energy',
     'Monthly Financial Statements Note 3: GGS expense for the Fuel and energy function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_fuel_energy', NULL, 'AUD', 1),
    ('mfs_note3_agriculture_forestry_fishing', 'MFS Note 3: Agriculture, forestry and fishing',
     'Monthly Financial Statements Note 3: GGS expense for the Agriculture, forestry and fishing function, YTD through the reporting month. One continuous measure across a title-case/sentence-case wording change.',
     0, 1, 'accrual', 'mfs_note3_agriculture_forestry_fishing', NULL, 'AUD', 1),
    ('mfs_note3_mining_manufacturing_construction', 'MFS Note 3: Mining, manufacturing and construction',
     'Monthly Financial Statements Note 3: GGS expense for the mining/manufacturing/construction function, YTD through the reporting month. One continuous measure across a genuine FY2008-09/FY2009-10 wording change.',
     0, 1, 'accrual', 'mfs_note3_mining_manufacturing_construction', NULL, 'AUD', 1),
    ('mfs_note3_transport_communication', 'MFS Note 3: Transport and communication',
     'Monthly Financial Statements Note 3: GGS expense for the Transport and communication function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_transport_communication', NULL, 'AUD', 1),
    ('mfs_note3_other_economic_affairs', 'MFS Note 3: Other economic affairs',
     'Monthly Financial Statements Note 3: GGS expense for the Other economic affairs function, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_other_economic_affairs', NULL, 'AUD', 1),
    ('mfs_note3_public_debt_interest', 'MFS Note 3: Public debt interest',
     'Monthly Financial Statements Note 3: GGS expense for Public debt interest (Other purposes), YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_public_debt_interest', NULL, 'AUD', 1),
    ('mfs_note3_nominal_superannuation_interest', 'MFS Note 3: Nominal superannuation interest',
     'Monthly Financial Statements Note 3: GGS expense for Nominal superannuation interest (Other purposes), YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_nominal_superannuation_interest', NULL, 'AUD', 1),
    ('mfs_note3_general_purpose_intergovt_transactions', 'MFS Note 3: General purpose inter-government transactions',
     'Monthly Financial Statements Note 3: GGS expense for General purpose inter-government transactions (Other purposes), YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_general_purpose_intergovt_transactions', NULL, 'AUD', 1),
    ('mfs_note3_natural_disaster_relief', 'MFS Note 3: Natural disaster relief',
     'Monthly Financial Statements Note 3: GGS expense for Natural disaster relief (Other purposes), YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_natural_disaster_relief', NULL, 'AUD', 1),
    ('mfs_note3_contingency_reserve', 'MFS Note 3: Contingency reserve',
     'Monthly Financial Statements Note 3: GGS expense for the Contingency reserve (Other purposes), YTD through the reporting month. From September 2008 includes former Asset Sales expenses per the source''s own footnote.',
     0, 1, 'accrual', 'mfs_note3_contingency_reserve', NULL, 'AUD', 1),
    ('mfs_note3_asset_sales', 'MFS Note 3: Asset Sales (FY2005-06..FY2007-08 only)',
     'Monthly Financial Statements Note 3: GGS expense for Asset Sales (Other purposes), disclosed as its own line only FY2005-06 through FY2007-08, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_note3_asset_sales', NULL, 'AUD', 1),
    ('mfs_note3_total_expenses', 'MFS Note 3: Total expenses',
     'Monthly Financial Statements Note 3: the published Total expenses bottom line of the function breakdown, YTD through the reporting month. A derived total, directly cited from the source''s own stated total row - never computed here.',
     0, 1, 'accrual', 'mfs_note3_total_expenses', NULL, 'AUD', 0);
