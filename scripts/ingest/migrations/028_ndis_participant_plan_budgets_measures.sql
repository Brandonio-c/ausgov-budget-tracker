-- NDIA "Participant Numbers and Plan Budgets" (participant demographic
-- depth, Federal deep-data mission Priority 2).
--
-- Two distinct, non-additive measures - never a partition of the canonical
-- NDIS expenditure figure ("Social security and welfare / Assistance to
-- people with disabilities / National Disability Insurance Scheme",
-- federal_budget_statement_6_components, $53.778b for FY2025-26):
--   - ndis_participant_count: a headcount (source's own ActvPrtcpnt), not
--     dollars. The source is a confidentialized, small-cell-suppressed
--     statistical cube (NDIA data rules); "ALL"-marginal rows are not the
--     literal sum of their disaggregated rows once suppression is applied.
--   - ndis_average_committed_plan_budget: an AVERAGE dollar figure per
--     participant (Total Annualised Budget / Participant Count, source's
--     own definition) - multiplying by participant count to reconstruct a
--     total would fabricate a figure the source does not itself publish,
--     exactly the "count x dollars = expenditure" error the mission
--     explicitly prohibits.
--
-- additive_across_nodes=0 and root_total_allowed=0 keep both measures
-- structurally invisible to the canonical dashboard tree walk (see
-- src/backend/routers/v2/dashboard.py::_fact_rows), matching the same
-- defensive pattern already used for NDIA's PBS-overlap measure (migration
-- 019). Reachable only via an explicit related_breakdown crosswalk edge.
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('ndis_participant_count', 'NDIS active participant count',
     'NDIA Participant Numbers and Plan Budgets: count of NDIS participants with an active plan at the reporting date, by geography/disability/age/support-class marginal breakdown. A confidentialized, small-cell-suppressed statistical count, never a dollar figure and never additive with expenditure measures.',
     0, 0, NULL, 'ndis_participant_statistics', 'federal_budget_related_evidence', 'participants', 0),
    ('ndis_average_committed_plan_budget', 'NDIS average committed plan budget per participant',
     'NDIA Participant Numbers and Plan Budgets: average annualised committed support budget per participant (source''s own Total Annualised Budget / Participant Count), rounded to the nearest thousand dollars. A per-participant average, not an aggregate expenditure total - never additive across nodes and never multiplied by participant count to reconstruct a total the source does not itself publish.',
     0, 0, 'accrual', 'ndis_participant_statistics', 'federal_budget_related_evidence', 'AUD_per_participant', 0);
