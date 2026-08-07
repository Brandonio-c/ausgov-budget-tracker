-- QLD Report on State Finances "Key UPF Financial Aggregates" table:
-- measure definitions (012). Each measure_type has its own dedicated
-- compatibility_group (1:1) - the same isolation guarantee used for
-- every other family in this repo: no qld_rsf_* fact can ever share a
-- compatibility_group with any annual GFS/PBS actual or budget
-- measure, any other jurisdiction's family, or the ABS's own
-- independently-compiled abs_gfs_state_qld_233/abs_state_accounts_
-- qld_* series for the same jurisdiction (a different publisher and
-- methodology). Semantics, evidence, and rationale for every field:
-- config/measure-semantics/qld_report_on_state_finances.yaml and
-- ops/reports/qld-*.md.
--
-- Covers General Government Sector only (the Public Non-financial
-- Corporations Sector and Non-financial Public Sector's own parallel
-- columns in the same table are out of scope - never conflated).
-- Financial years 2018-19 to 2024-25 (7 editions confirmed identical
-- 8-row shape); "Net Debt" and "Borrowings" summary rows are excluded
-- since not present in every target edition.

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('qld_rsf_revenue', 'QLD RSF general government revenue',
     'Queensland General Government Sector Revenue, from the Report on State Finances "Key UPF Financial Aggregates" table, 2018-19 to 2024-25 (estimated actual/actual).',
     0, 1, 'gfs', 'qld_rsf_revenue', NULL, 'AUD', 1),
    ('qld_rsf_expense', 'QLD RSF general government expenses',
     'Queensland General Government Sector Expenses, from the Report on State Finances "Key UPF Financial Aggregates" table, 2018-19 to 2024-25.',
     0, 1, 'gfs', 'qld_rsf_expense', NULL, 'AUD', 1),
    ('qld_rsf_net_operating_balance', 'QLD RSF net operating balance',
     'Queensland General Government Sector Net Operating Balance (Revenue less Expenses), 2018-19 to 2024-25. A derived balance.',
     0, 1, 'gfs', 'qld_rsf_net_operating_balance', NULL, 'AUD', 0),
    ('qld_rsf_capital_purchases', 'QLD RSF capital purchases',
     'Queensland General Government Sector Capital Purchases, 2018-19 to 2024-25.',
     0, 1, 'gfs', 'qld_rsf_capital_purchases', NULL, 'AUD', 1),
    ('qld_rsf_fiscal_balance', 'QLD RSF fiscal balance',
     'Queensland General Government Sector Fiscal Balance (Net Operating Balance less net acquisition of non-financial assets), 2018-19 to 2024-25. A derived balance.',
     0, 1, 'gfs', 'qld_rsf_fiscal_balance', NULL, 'AUD', 0),
    ('qld_rsf_borrowing_qtc', 'QLD RSF borrowing with QTC (stock)',
     'Queensland General Government Sector Borrowing with the Queensland Treasury Corporation, 2018-19 to 2024-25. A debt-instrument component.',
     0, 1, 'gfs', 'qld_rsf_borrowing_qtc', NULL, 'AUD', 1),
    ('qld_rsf_leases', 'QLD RSF leases and similar arrangements (stock)',
     'Queensland General Government Sector lease and similar-arrangement liabilities, 2018-19 to 2024-25. A debt-instrument component.',
     0, 1, 'gfs', 'qld_rsf_leases', NULL, 'AUD', 1),
    ('qld_rsf_securities_derivatives', 'QLD RSF securities and derivatives (stock)',
     'Queensland General Government Sector securities and derivative liabilities, 2018-19 to 2024-25. A debt-instrument component.',
     0, 1, 'gfs', 'qld_rsf_securities_derivatives', NULL, 'AUD', 1);
