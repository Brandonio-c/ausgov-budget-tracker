-- VIC DTF Budget Portfolio Outcomes measure definitions (009).
-- Each measure_type has its own dedicated compatibility_group (1:1) - the
-- same isolation guarantee used for MFS (007) and VIC AFS (008): no
-- vic_bpo_* fact can ever share a compatibility_group with any annual
-- GFS/PBS actual or budget measure, nor with the vic_afs_* family
-- (same department, different statement shape - never conflated).
-- Semantics, evidence, and rationale for every field:
-- config/measure-semantics/vic_bpo.yaml and
-- ops/reports/vic-bpo-*.md.
--
-- Unlike vic_afs_* (multi-year actuals, one estimate_status='actual' per
-- financial_year), every vic_bpo_* measure carries TWO facts for the
-- SAME financial_year (2024-25): estimate_status='actual' and
-- estimate_status='budget' - the source's own Actual-vs-Budget
-- comparison for one year, not a multi-year series. The "Variance"
-- column is never loaded (derivable as actual minus budget).
--
-- additive_across_time = 0 for all: each fact is a full-financial-year
-- total or a point-in-time balance, never a partial period.
-- root_total_allowed = 0 for the already-derived balances
-- (net_operating_balance, net_result, net_assets) - never summed again
-- with their own components.

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('vic_bpo_revenue', 'VIC BPO total revenue',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total revenue and income from transactions, accrual basis, for the financial year - actual vs budget.',
     0, 1, 'accrual', 'vic_bpo_revenue', NULL, 'AUD', 1),
    ('vic_bpo_expense', 'VIC BPO total expense',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total expenses from transactions, accrual basis, for the financial year - actual vs budget.',
     0, 1, 'accrual', 'vic_bpo_expense', NULL, 'AUD', 1),
    ('vic_bpo_net_operating_balance', 'VIC BPO net operating balance',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: net result from transactions (net operating balance), actual vs budget. A derived balance.',
     0, 1, 'accrual', 'vic_bpo_net_operating_balance', NULL, 'AUD', 0),
    ('vic_bpo_net_result', 'VIC BPO net result',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: comprehensive net result for the financial year, actual vs budget. A derived balance.',
     0, 1, 'accrual', 'vic_bpo_net_result', NULL, 'AUD', 0),
    ('vic_bpo_total_assets', 'VIC BPO total assets (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total assets, as at 30 June - actual vs budget.',
     0, 1, 'accrual', 'vic_bpo_total_assets', NULL, 'AUD', 1),
    ('vic_bpo_total_liabilities', 'VIC BPO total liabilities (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total liabilities, as at 30 June - actual vs budget.',
     0, 1, 'accrual', 'vic_bpo_total_liabilities', NULL, 'AUD', 1),
    ('vic_bpo_net_assets', 'VIC BPO net assets (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total assets minus total liabilities, as at 30 June, actual vs budget. A derived stock balance. The source restates this identical figure a second time as "Total equity" - only "Net assets" is loaded.',
     0, 1, 'accrual', 'vic_bpo_net_assets', NULL, 'AUD', 0),
    ('vic_bpo_net_cash_operating', 'VIC BPO net cash from operating activities',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: net cash flows from/(used in) operating activities, cash basis, for the financial year - actual vs budget.',
     0, 1, 'cash', 'vic_bpo_net_cash_operating', NULL, 'AUD', 1),
    ('vic_bpo_net_cash_investing', 'VIC BPO net cash from investing activities',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: net cash flows from/(used in) investing activities, cash basis, for the financial year - actual vs budget.',
     0, 1, 'cash', 'vic_bpo_net_cash_investing', NULL, 'AUD', 1),
    ('vic_bpo_net_cash_financing', 'VIC BPO net cash from financing activities',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: net cash flows from/(used in) financing activities, cash basis, for the financial year - actual vs budget.',
     0, 1, 'cash', 'vic_bpo_net_cash_financing', NULL, 'AUD', 1),
    ('vic_bpo_cash_end_of_year', 'VIC BPO cash at end of year (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: cash and cash equivalents at the end of the financial year, as at 30 June - actual vs budget.',
     0, 1, 'cash', 'vic_bpo_cash_end_of_year', NULL, 'AUD', 1);
