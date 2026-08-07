-- Additional distinct measures needed by the 2002-03 to 2017-18
-- Queensland Report on State Finances summary tables. Each receives its own
-- compatibility group and remains outside all annual additive dashboard trees.
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time,
     additive_across_nodes, default_accounting_basis, compatibility_group,
     view_family, default_unit, root_total_allowed)
VALUES
 ('qld_rsf_cash_surplus', 'QLD RSF cash surplus/(deficit)', 'General Government Sector GFS cash surplus/(deficit).', 0, 0, 'gfs', 'qld_rsf_cash_surplus', NULL, 'AUD', 0),
 ('qld_rsf_gross_fixed_capital_formation', 'QLD RSF gross fixed capital formation', 'General Government Sector gross fixed capital formation.', 0, 1, 'gfs', 'qld_rsf_gross_fixed_capital_formation', NULL, 'AUD', 1),
 ('qld_rsf_net_worth', 'QLD RSF net worth (stock)', 'General Government Sector net worth at 30 June.', 0, 0, 'gfs', 'qld_rsf_net_worth', NULL, 'AUD', 0),
 ('qld_rsf_net_debt', 'QLD RSF net debt (stock)', 'General Government Sector net debt at 30 June.', 0, 0, 'gfs', 'qld_rsf_net_debt', NULL, 'AUD', 0),
 ('qld_rsf_net_borrowing', 'QLD RSF net borrowing', 'General Government Sector net borrowing transaction measure.', 0, 0, 'gfs', 'qld_rsf_net_borrowing', NULL, 'AUD', 0),
 ('qld_rsf_borrowing', 'QLD RSF gross borrowing (stock)', 'General Government Sector gross borrowing at 30 June.', 0, 0, 'gfs', 'qld_rsf_borrowing', NULL, 'AUD', 0);
