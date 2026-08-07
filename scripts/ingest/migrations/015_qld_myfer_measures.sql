-- Queensland MYFER current-year revised estimates. These are deliberately
-- isolated from audited QLD RSF facts and independently compiled ABS GFS.
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time,
     additive_across_nodes, default_accounting_basis, compatibility_group,
     view_family, default_unit, root_total_allowed)
VALUES
 ('qld_myfer_revenue', 'QLD MYFER general government revenue',
  'Queensland General Government Sector revenue: current-year revised estimate published in MYFER.',
  0, 1, 'gfs', 'qld_myfer_revenue', 'qld_myfer', 'AUD', 1),
 ('qld_myfer_expense', 'QLD MYFER general government expenses',
  'Queensland General Government Sector expenses: current-year revised estimate published in MYFER.',
  0, 1, 'gfs', 'qld_myfer_expense', 'qld_myfer', 'AUD', 1),
 ('qld_myfer_net_operating_balance', 'QLD MYFER net operating balance',
  'Queensland General Government Sector net operating balance: current-year revised estimate published in MYFER; non-additive balance.',
  0, 0, 'gfs', 'qld_myfer_net_operating_balance', 'qld_myfer', 'AUD', 0),
 ('qld_myfer_capital_purchases', 'QLD MYFER purchases of non-financial assets',
  'Queensland General Government Sector purchases of non-financial assets: current-year revised estimate published in MYFER.',
  0, 1, 'gfs', 'qld_myfer_capital_purchases', 'qld_myfer', 'AUD', 1),
 ('qld_myfer_fiscal_balance', 'QLD MYFER fiscal balance',
  'Queensland General Government Sector fiscal balance: current-year revised estimate published in MYFER; non-additive balance.',
  0, 0, 'gfs', 'qld_myfer_fiscal_balance', 'qld_myfer', 'AUD', 0);
