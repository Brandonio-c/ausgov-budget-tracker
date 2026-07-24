-- GFS balance-sheet liability stocks (ABS Table_3).
-- Stocks are additive across liability categories within a year, not across years.
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group)
VALUES
    ('gfs_liability', 'GFS liability',
     'Government Finance Statistics end-of-year liability stock (ABS GFS balance sheet).',
     0, 1, 'gfs', 'gfs_liability');
