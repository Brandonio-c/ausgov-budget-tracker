-- MFS (Monthly Financial Statements) Aggregates measure definitions (007).
-- Each measure_type has its own dedicated compatibility_group (1:1) - the
-- strongest available guarantee that no MFS fact can ever share a
-- compatibility_group with an annual GFS/PBS actual or budget measure,
-- which was the exact mechanism of the contamination bug found and fixed
-- in Task 1 of the MFS-aggregates milestone. Semantics, evidence, and
-- rationale for every field: config/measure-semantics/mfs.yaml and
-- ops/reports/mfs-measure-semantics-*.md.
--
-- additive_across_time = 0 for all: a YTD-through-August figure must never
-- be summed with a YTD-through-July figure for the same measure (that
-- would double-count), and stocks are point-in-time by definition.
-- root_total_allowed = 0 for the six already-derived balance/stock_balance
-- measures (net_operating_balance, fiscal_balance, underlying/headline
-- cash balance, net_worth, net_debt) - they must never be "rooted"/summed
-- further. view_family is intentionally NULL: MFS is exposed only through
-- its own dedicated API (src/backend/routers/v2/mfs.py), never through
-- the existing view_family/mode_to_family dashboard machinery.

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('mfs_ytd_revenue', 'MFS YTD revenue',
     'Monthly Financial Statements: total GGS revenue, accrual basis, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_ytd_revenue', NULL, 'AUD', 1),
    ('mfs_ytd_expense', 'MFS YTD expense',
     'Monthly Financial Statements: total GGS expenses, accrual basis, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_ytd_expense', NULL, 'AUD', 1),
    ('mfs_ytd_net_operating_balance', 'MFS YTD net operating balance',
     'Monthly Financial Statements: revenue minus expenses, YTD through the reporting month. A derived balance - never summed with revenue/expense.',
     0, 1, 'accrual', 'mfs_ytd_net_operating_balance', NULL, 'AUD', 0),
    ('mfs_ytd_net_capital_investment', 'MFS YTD net capital investment',
     'Monthly Financial Statements: net capital investment, YTD through the reporting month. Not published before FY2007-08.',
     0, 1, 'accrual', 'mfs_ytd_net_capital_investment', NULL, 'AUD', 1),
    ('mfs_ytd_fiscal_balance', 'MFS YTD fiscal balance',
     'Monthly Financial Statements: net operating balance minus net capital investment, YTD through the reporting month. A derived balance.',
     0, 1, 'accrual', 'mfs_ytd_fiscal_balance', NULL, 'AUD', 0),
    ('mfs_ytd_receipts', 'MFS YTD cash receipts',
     'Monthly Financial Statements: cash-basis receipts, YTD through the reporting month. Not published before FY2011-12.',
     0, 1, 'cash', 'mfs_ytd_receipts', NULL, 'AUD', 1),
    ('mfs_ytd_payments', 'MFS YTD cash payments',
     'Monthly Financial Statements: cash-basis payments, YTD through the reporting month. Not published before FY2011-12.',
     0, 1, 'cash', 'mfs_ytd_payments', NULL, 'AUD', 1),
    ('mfs_ytd_net_future_fund_earnings', 'MFS YTD net Future Fund earnings',
     'Monthly Financial Statements: net Future Fund earnings adjustment, YTD through the reporting month. Only disclosed FY2013-14..2019-20.',
     0, 1, 'cash', 'mfs_ytd_net_future_fund_earnings', NULL, 'AUD', 1),
    ('mfs_ytd_underlying_cash_balance', 'MFS YTD underlying cash balance',
     'Monthly Financial Statements: published underlying cash balance bottom line, YTD through the reporting month. A derived balance.',
     0, 1, 'cash', 'mfs_ytd_underlying_cash_balance', NULL, 'AUD', 0),
    ('mfs_ytd_headline_cash_balance', 'MFS YTD headline cash balance',
     'Monthly Financial Statements: published headline cash balance bottom line, YTD through the reporting month. A derived balance.',
     0, 1, 'cash', 'mfs_ytd_headline_cash_balance', NULL, 'AUD', 0),
    ('mfs_stock_total_assets', 'MFS total assets (stock)',
     'Monthly Financial Statements: total GGS assets, as at the last day of the reporting month.',
     0, 1, 'accrual', 'mfs_stock_total_assets', NULL, 'AUD', 1),
    ('mfs_stock_total_liabilities', 'MFS total liabilities (stock)',
     'Monthly Financial Statements: total GGS liabilities, as at the last day of the reporting month.',
     0, 1, 'accrual', 'mfs_stock_total_liabilities', NULL, 'AUD', 1),
    ('mfs_stock_net_worth', 'MFS net worth (stock)',
     'Monthly Financial Statements: total assets minus total liabilities, as at the last day of the reporting month. A derived stock balance.',
     0, 1, 'accrual', 'mfs_stock_net_worth', NULL, 'AUD', 0),
    ('mfs_stock_net_debt', 'MFS net debt (stock)',
     'Monthly Financial Statements: net debt, as at the last day of the reporting month. Not published before FY2010-11. A derived stock balance.',
     0, 1, 'accrual', 'mfs_stock_net_debt', NULL, 'AUD', 0),
    ('mfs_stock_cash_and_deposits', 'MFS cash and deposits (stock, reserved)',
     'Monthly Financial Statements: cash and deposits held, as at the last day of the reporting month. Reserved - only in the Balance Sheet workbook, which has no extractor; zero facts until a future milestone.',
     0, 1, 'accrual', 'mfs_stock_cash_and_deposits', NULL, 'AUD', 1);
