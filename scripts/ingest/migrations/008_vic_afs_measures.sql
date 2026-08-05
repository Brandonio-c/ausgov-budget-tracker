-- VIC DTF Annual Financial Statements measure definitions (008).
-- Each measure_type has its own dedicated compatibility_group (1:1) - the
-- same isolation guarantee used for MFS (007): no vic_afs_* fact can ever
-- share a compatibility_group with an annual GFS/PBS actual or budget
-- measure. Semantics, evidence, and rationale for every field:
-- config/measure-semantics/vic_afs.yaml and
-- ops/reports/vic-afs-*.md.
--
-- Scope: the Victorian Department of Treasury and Finance's own
-- departmental annual financial statements (2024-25 annual report,
-- Operating Statement/Balance Sheet/Cash Flow Statement sheets only -
-- Statement of Changes in Equity has a different rolling-balance shape
-- and is out of scope this milestone). This is DEPARTMENT-level detail,
-- not whole-of-Victorian-government - a genuinely new granularity not
-- already covered by any existing GFS/state-actuals family.
--
-- additive_across_time = 0 for all: each fact is a full-financial-year
-- total (Operating Statement/Cash Flow Statement) or a point-in-time
-- balance (Balance Sheet) - never a partial period to be summed across
-- years. root_total_allowed = 0 for the four already-derived balances
-- (net_operating_balance, net_result, net_assets, and the three net-cash
-- subtotals are NOT derived-further so remain 1, but net_operating_balance/
-- net_result/net_assets are literally revenue-minus-expense/assets-minus-
-- liabilities and must never be summed again). view_family is
-- intentionally NULL: exposed only through its own dedicated API, never
-- through the existing view_family/mode_to_family dashboard machinery.

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('vic_afs_revenue', 'VIC DTF total revenue',
     'Victorian Department of Treasury and Finance annual financial statements: total income from transactions, accrual basis, for the financial year.',
     0, 1, 'accrual', 'vic_afs_revenue', NULL, 'AUD', 1),
    ('vic_afs_expense', 'VIC DTF total expense',
     'Victorian Department of Treasury and Finance annual financial statements: total expenses from transactions, accrual basis, for the financial year.',
     0, 1, 'accrual', 'vic_afs_expense', NULL, 'AUD', 1),
    ('vic_afs_net_operating_balance', 'VIC DTF net operating balance',
     'Victorian Department of Treasury and Finance annual financial statements: net result from transactions (net operating balance). A derived balance - never summed with revenue/expense.',
     0, 1, 'accrual', 'vic_afs_net_operating_balance', NULL, 'AUD', 0),
    ('vic_afs_net_result', 'VIC DTF net result',
     'Victorian Department of Treasury and Finance annual financial statements: comprehensive net result for the financial year (net operating balance plus other economic flows). A derived balance.',
     0, 1, 'accrual', 'vic_afs_net_result', NULL, 'AUD', 0),
    ('vic_afs_total_assets', 'VIC DTF total assets (stock)',
     'Victorian Department of Treasury and Finance annual financial statements: total assets, as at 30 June.',
     0, 1, 'accrual', 'vic_afs_total_assets', NULL, 'AUD', 1),
    ('vic_afs_total_liabilities', 'VIC DTF total liabilities (stock)',
     'Victorian Department of Treasury and Finance annual financial statements: total liabilities, as at 30 June.',
     0, 1, 'accrual', 'vic_afs_total_liabilities', NULL, 'AUD', 1),
    ('vic_afs_net_assets', 'VIC DTF net assets (stock)',
     'Victorian Department of Treasury and Finance annual financial statements: total assets minus total liabilities, as at 30 June. A derived stock balance. The source workbook restates this identical figure a second time as "Net worth" after the Equity section - only the first occurrence ("Net assets") is loaded to avoid a definitionally-guaranteed duplicate.',
     0, 1, 'accrual', 'vic_afs_net_assets', NULL, 'AUD', 0),
    ('vic_afs_net_cash_operating', 'VIC DTF net cash from operating activities',
     'Victorian Department of Treasury and Finance annual financial statements: net cash flows from/(used in) operating activities, cash basis, for the financial year.',
     0, 1, 'cash', 'vic_afs_net_cash_operating', NULL, 'AUD', 1),
    ('vic_afs_net_cash_investing', 'VIC DTF net cash from investing activities',
     'Victorian Department of Treasury and Finance annual financial statements: net cash flows from/(used in) investing activities, cash basis, for the financial year.',
     0, 1, 'cash', 'vic_afs_net_cash_investing', NULL, 'AUD', 1),
    ('vic_afs_net_cash_financing', 'VIC DTF net cash from financing activities',
     'Victorian Department of Treasury and Finance annual financial statements: net cash flows from/(used in) financing activities, cash basis, for the financial year.',
     0, 1, 'cash', 'vic_afs_net_cash_financing', NULL, 'AUD', 1),
    ('vic_afs_cash_end_of_year', 'VIC DTF cash at end of year (stock)',
     'Victorian Department of Treasury and Finance annual financial statements: cash and cash equivalents at end of financial year, as at 30 June.',
     0, 1, 'cash', 'vic_afs_cash_end_of_year', NULL, 'AUD', 1);
