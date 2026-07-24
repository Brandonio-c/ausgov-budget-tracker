-- GFS operating-statement revenue (ABS Table_1).
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group)
VALUES
    ('gfs_revenue', 'GFS revenue',
     'Government Finance Statistics revenue (ABS GFS operating statement).',
     1, 1, 'gfs', 'gfs_revenue'),
    ('net_debt', 'Net debt',
     'General government net debt stock (Budget Statement 11 definition).',
     0, 1, 'gfs', 'net_debt'),
    ('gross_debt_face_value', 'Gross debt face value',
     'Face value of Commonwealth Government Securities outstanding.',
     0, 1, 'gfs', 'gross_debt'),
    ('aofm_cgs_outstanding', 'AOFM CGS outstanding',
     'Australian Government Securities outstanding by instrument (AOFM).',
     0, 1, 'gfs', 'aofm_cgs'),
    ('tax_revenue', 'Taxation revenue',
     'Taxation revenue by type and jurisdiction (ABS Taxation Revenue).',
     1, 1, 'gfs', 'tax_revenue'),
    ('gdp_current', 'GDP current prices',
     'Gross domestic product / GVA at current prices (National Accounts).',
     0, 1, 'not_applicable', 'gdp');
