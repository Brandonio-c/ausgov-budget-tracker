-- TAS GGS Key Fiscal Measures Time Series: measure definitions (011).
-- Each measure_type has its own dedicated compatibility_group (1:1) -
-- the same isolation guarantee used for every other family in this
-- repo: no tas_ggs_* fact can ever share a compatibility_group with
-- any annual GFS/PBS actual or budget measure, any other jurisdiction's
-- family, or - critically - with the ABS's own independently-compiled
-- abs_gfs_state_tas_236/abs_state_accounts_tas_* series for the same
-- jurisdiction (a different publisher and methodology; never
-- conflated despite similar-sounding names, e.g. tas_ggs_gfs_net_debt
-- vs abs_gfs_state_tas_236's own net debt figure). Semantics,
-- evidence, and rationale for every field:
-- config/measure-semantics/tas_ggs_key_fiscal_measures.yaml and
-- ops/reports/qld-tas-*.md.

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('tas_ggs_revenue', 'TAS GGS revenue from transactions',
     'Tasmanian General Government Sector Revenue from Transactions, accrual basis, 2013-14 to 2028-29 (actual/revised budget/forward estimate).',
     0, 1, 'accrual', 'tas_ggs_revenue', NULL, 'AUD', 1),
    ('tas_ggs_expense', 'TAS GGS expenses from transactions',
     'Tasmanian General Government Sector Expenses from Transactions, accrual basis, 2013-14 to 2028-29.',
     0, 1, 'accrual', 'tas_ggs_expense', NULL, 'AUD', 1),
    ('tas_ggs_net_operating_balance', 'TAS GGS net operating balance',
     'Tasmanian General Government Sector Net Operating Balance (Revenue from transactions less Expenses from transactions), accrual basis, 2013-14 to 2028-29. A derived balance.',
     0, 1, 'accrual', 'tas_ggs_net_operating_balance', NULL, 'AUD', 0),
    ('tas_ggs_fiscal_balance', 'TAS GGS fiscal balance',
     'Tasmanian General Government Sector Fiscal Balance (Net Operating Balance less net addition to non-financial assets), accrual basis, 2013-14 to 2028-29. A derived balance.',
     0, 1, 'accrual', 'tas_ggs_fiscal_balance', NULL, 'AUD', 0),
    ('tas_ggs_infrastructure_investment', 'TAS GGS infrastructure investment',
     'Tasmanian General Government Sector Infrastructure Investment, accrual basis, 2013-14 to 2028-29.',
     0, 1, 'accrual', 'tas_ggs_infrastructure_investment', NULL, 'AUD', 1),
    ('tas_ggs_net_debt', 'TAS GGS net debt (stock)',
     'Tasmanian General Government Sector Net Debt at 30 June (Treasury''s own presentation-framework figure, distinct from the ABS-GFS-consistent variant), 2013-14 to 2028-29.',
     0, 1, 'accrual', 'tas_ggs_net_debt', NULL, 'AUD', 1),
    ('tas_ggs_gfs_net_debt', 'TAS GGS net debt, GFS-consistent variant (stock)',
     'Tasmanian General Government Sector GFS Net Debt at 30 June (Treasury''s own ABS-GFS-consistent calculation - NOT the ABS''s own independently-compiled series), 2013-14 to 2028-29.',
     0, 1, 'gfs', 'tas_ggs_gfs_net_debt', NULL, 'AUD', 1),
    ('tas_ggs_net_worth', 'TAS GGS net worth (stock)',
     'Tasmanian General Government Sector Net Worth (Total assets less Total liabilities) at 30 June, 2013-14 to 2028-29. A derived stock balance.',
     0, 1, 'accrual', 'tas_ggs_net_worth', NULL, 'AUD', 0),
    ('tas_ggs_net_financial_liabilities', 'TAS GGS net financial liabilities (stock)',
     'Tasmanian General Government Sector Net Financial Liabilities (Total liabilities less Financial assets, excluding PNFC/PFC equity investment) at 30 June, 2013-14 to 2028-29.',
     0, 1, 'accrual', 'tas_ggs_net_financial_liabilities', NULL, 'AUD', 1),
    ('tas_ggs_cash_surplus_deficit', 'TAS GGS cash surplus/deficit',
     'Tasmanian General Government Sector Cash Surplus/Deficit (net cash flows from operating activities plus net cash flows from investments in non-financial assets), cash basis, 2013-14 to 2028-29.',
     0, 1, 'cash', 'tas_ggs_cash_surplus_deficit', NULL, 'AUD', 1);
