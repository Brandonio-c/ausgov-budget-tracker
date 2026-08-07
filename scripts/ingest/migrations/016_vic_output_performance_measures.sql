INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('vic_output_total_cost', 'VIC DTF output total cost',
     'Victorian Department of Treasury and Finance Output Performance Measures: annual actual or target total output cost for one named departmental output.',
     0, 0, 'accrual', 'vic_output_total_cost', 'vic_output_performance', 'AUD', 0);
