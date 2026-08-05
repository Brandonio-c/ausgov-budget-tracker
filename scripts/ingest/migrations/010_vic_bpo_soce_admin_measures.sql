-- VIC DTF Budget Portfolio Outcomes: deferred SOCE/Admin measure
-- definitions (010). Each measure_type has its own dedicated
-- compatibility_group (1:1) - the same isolation guarantee used for
-- every other family in this repo: no vic_bpo_admin_*/vic_bpo_net_
-- assets_opening/vic_bpo_owner_transactions fact can ever share a
-- compatibility_group with any annual GFS/PBS actual or budget measure,
-- any whole-of-government VIC family, or the sibling vic_bpo_*
-- (OS/BS/CFS) / vic_afs_* families. Semantics, evidence, and rationale
-- for every field: config/measure-semantics/vic_bpo_soce_admin.yaml and
-- ops/reports/vic-soce-admin-*.md.
--
-- Admin ("Administered items statement") is a materially different
-- concept from vic_bpo_*'s own controlled-operations measures
-- (payments made ON BEHALF OF THE STATE, at a completely different
-- scale - e.g. $82 billion administered income vs $466 million
-- controlled revenue) - never conflated with vic_bpo_revenue/expense/
-- total_assets/etc despite sharing similar-sounding labels in the
-- source workbook (the source literally reuses "Net result"/"Net
-- assets" as row labels for both concepts).
--
-- SOCE contributes exactly two genuinely new measures not already
-- captured by the loaded OS/BS/CFS sheets: the FY2024-25 OPENING equity
-- position (vic_bpo_net_assets_opening - OS/BS/CFS only cover the
-- closing position) and owner-capital movements
-- (vic_bpo_owner_transactions, a concept distinct from operating
-- result). SOCE's "Balance at 30 June 2025" and "Comprehensive result"
-- rows are NOT loaded as separate measures - they restate
-- vic_bpo_net_assets and vic_bpo_net_result verbatim (verified by
-- direct value comparison), the same duplicate-by-design pattern found
-- throughout this family.

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('vic_bpo_admin_income', 'VIC BPO administered income',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total administered income (payments made on behalf of the State), accrual basis, FY2024-25 - actual vs budget. A materially different concept from the department''s own controlled-operations revenue.',
     0, 1, 'accrual', 'vic_bpo_admin_income', NULL, 'AUD', 1),
    ('vic_bpo_admin_expense', 'VIC BPO administered expense',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total administered expenses, accrual basis, FY2024-25 - actual vs budget.',
     0, 1, 'accrual', 'vic_bpo_admin_expense', NULL, 'AUD', 1),
    ('vic_bpo_admin_net_result', 'VIC BPO administered net result',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: administered net result (income less expenses, plus other economic flows), FY2024-25 - actual vs budget. A derived balance, genuinely distinct from vic_bpo_admin_comprehensive_result (unlike the department''s own OS sheet, these two figures differ here).',
     0, 1, 'accrual', 'vic_bpo_admin_net_result', NULL, 'AUD', 0),
    ('vic_bpo_admin_comprehensive_result', 'VIC BPO administered comprehensive result',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: administered comprehensive result (net result plus other comprehensive income), FY2024-25 - actual vs budget. A derived balance.',
     0, 1, 'accrual', 'vic_bpo_admin_comprehensive_result', NULL, 'AUD', 0),
    ('vic_bpo_admin_total_assets', 'VIC BPO administered total assets (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total administered assets, as at 30 June 2025 - actual vs budget.',
     0, 1, 'accrual', 'vic_bpo_admin_total_assets', NULL, 'AUD', 1),
    ('vic_bpo_admin_total_liabilities', 'VIC BPO administered total liabilities (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total administered liabilities, as at 30 June 2025 - actual vs budget.',
     0, 1, 'accrual', 'vic_bpo_admin_total_liabilities', NULL, 'AUD', 1),
    ('vic_bpo_admin_net_assets', 'VIC BPO administered net assets (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: administered total assets minus administered total liabilities, as at 30 June 2025 - actual vs budget. A derived stock balance.',
     0, 1, 'accrual', 'vic_bpo_admin_net_assets', NULL, 'AUD', 0),
    ('vic_bpo_net_assets_opening', 'VIC BPO net assets, opening balance (stock)',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: total equity as at 1 July 2024 (the opening position for FY2024-25) - actual vs budget. From the Statement of Changes in Equity - not previously captured by the Balance Sheet, which only reports the closing (30 June) position.',
     0, 1, 'accrual', 'vic_bpo_net_assets_opening', NULL, 'AUD', 1),
    ('vic_bpo_owner_transactions', 'VIC BPO transactions with owners',
     'Victorian Department of Treasury and Finance Budget Portfolio Outcomes: transactions with owners in their capacity as owners (capital contributed by or returned to the State), FY2024-25 - actual vs budget. From the Statement of Changes in Equity - a genuinely new concept distinct from operating result.',
     0, 1, 'accrual', 'vic_bpo_owner_transactions', NULL, 'AUD', 1);
