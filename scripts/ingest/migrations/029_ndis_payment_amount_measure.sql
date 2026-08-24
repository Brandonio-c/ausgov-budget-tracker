-- NDIA "Payments data" (Federal deep-data mission Priority 2, Loop 10).
--
-- Reports actual aggregate dollars paid (PmtAmt, "Total amount paid to
-- participants in the preceding 12 months"), by support class/category/
-- item - unlike ndis_participant_count/ndis_average_committed_plan_budget
-- (migration 028), this IS a genuine dollar measure, and its
-- support-class -> support-category nesting is a verified, near-exact
-- additive partition within the source (9 categories under "Capacity
-- Building" sum to $9,400,383,000 vs the class total $9,400,381,000 - a
-- $2,000 rounding gap on $9.4B).
--
-- Still additive_across_nodes=0 and root_total_allowed=0: the implied
-- grand total across support classes ($51.45B) is close to but NOT
-- exactly the canonical NDIS expenditure figure ($53.778B, Statement 6
-- components, FY2025-26) - a different accounting basis/period ("preceding
-- 12 months" ending 30 June 2026 is a rolling actual-payments window, not
-- a Statement 6 estimate), so this measure must never be treated as an
-- additive replacement or partition of the canonical GFS/budget total,
-- even though it IS safely additive within its own source hierarchy (via
-- same_group edges scoped to this measure only).
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('ndis_payment_amount', 'NDIS payment amount',
     'NDIA Payments data: total amount paid to participants in the preceding 12 months, by support class/category/item. Support class -> support category is a verified, near-exact additive partition within this source, but the source''s own grand total does not reconcile exactly to the canonical NDIS Statement 6 expenditure figure (different accounting basis/period) - never treat as an additive replacement or partition of that canonical total.',
     0, 0, 'cash', 'ndis_payment_statistics', 'federal_budget_related_evidence', 'AUD', 0);
