-- New measures for historical Statement 6 (BP1) and Treasury PBS program
-- expense evidence (plan items 5.2/5.3). These facts overlap in coverage
-- with the existing 'budget_expense' compatibility group (Statement 6 is a
-- function-level view and PBS is a program-level view of the *same*
-- underlying commonwealth expenditure), so they must never share that
-- compatibility group: dashboard mode='budget' selects its base fact set
-- with a bare `WHERE m.compatibility_group = 'budget_expense'` (see
-- src/backend/routers/v2/dashboard.py:_fact_rows), with no per-source
-- de-duplication. Loading either historical family under 'budget_expense'
-- was verified on a disposable database copy to inflate the federal_budget
-- root total for FY2022-23/2023-24 by roughly 2-3x (e.g. $1.63b -> $714b
-- from PBS alone, -> $2.34t from Statement 6 alone) - a direct violation of
-- the "no cross-compatibility-group/incompatible summation" invariant.
--
-- Each family gets its own compatibility_group (matching the established
-- convention for single-purpose measures, e.g. vic_output_total_cost in
-- migration 016), additive_across_nodes=0 and root_total_allowed=0 so
-- neither family can ever anchor or inflate any mode's root total via the
-- raw per-mode fact query. They remain reachable by node id for exact-year
-- related_breakdown edges (breakdown_graph.fact_for_node_year has no
-- compatibility_group WHERE-clause restriction - it only orders by
-- preference), which is how item 5.4's crosswalk exposes them.
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('historical_bp1_statement6_expense', 'Historical BP1 Statement 5/6 expense',
     'Edition-bounded historical Budget Paper No. 1 Statement 5/6 function, subfunction and component expense estimates (March 2022-23, October 2022-23, 2023-24 editions). Related evidence for the canonical ABS GFS federal budget projection, never additive to it.',
     0, 0, 'accrual', 'historical_bp1_statement6_expense', 'federal_budget_related_evidence', 'AUD', 0),
    ('historical_treasury_pbs_program_expense', 'Historical Treasury PBS program expense',
     'Edition-bounded historical Treasury Portfolio Budget Statements entity/outcome/program expense estimates (March 2022-23, October 2022-23, 2023-24 editions). Related evidence for the canonical ABS GFS federal budget projection, never additive to it.',
     0, 0, 'accrual', 'historical_treasury_pbs_program_expense', 'federal_budget_related_evidence', 'AUD', 0);
