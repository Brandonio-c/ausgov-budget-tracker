-- Isolated measure for the 2026-27 NDIA PBS repair (plan item 5.5).
--
-- NDIA's own Table 2.1.1 reports "Payment from related entities" (~$38-40b
-- for FY2025-26/2026-27) as revenue - the same underlying Commonwealth-to-
-- NDIA transfer that the already-loaded federal_pbs_programs_all source
-- reports as the portfolio department's own "Program 3.2 - National
-- Disability Insurance Scheme" administered expense (~$34-38b for the same
-- years; verified directly against the live database, not assumed).
-- Loading NDIA's Program 1.1/1.2 totals under the shared 'budget_expense'
-- compatibility group was verified on a disposable database copy to add
-- NDIA's *entire* $56.5b FY2029-30 outcome total on top of everything
-- already loaded, double-counting the shared transfer - the same class of
-- defect fixed in migration 018 for historical Statement 6/PBS evidence.
--
-- additive_across_nodes=0 and root_total_allowed=0 keep this measure
-- structurally invisible to every existing dashboard mode's raw fact walk
-- (see src/backend/routers/v2/dashboard.py::_fact_rows), while remaining
-- reachable by node id for a future related_breakdown crosswalk edge.
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('federal_pbs_2026_27_ndia_expense', 'NDIA 2026-27 PBS program expense',
     'National Disability Insurance Agency 2026-27 Portfolio Budget Statements Table 2.1.1 program expense estimates. Overlaps with the portfolio department''s own administered "Program 3.2 - National Disability Insurance Scheme" expense already loaded under federal_pbs_programs_all; never additive to it.',
     0, 0, 'accrual', 'federal_pbs_2026_27_ndia_expense', 'federal_budget_related_evidence', 'AUD', 0);
