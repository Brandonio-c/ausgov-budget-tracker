-- QLD On-Time Payment (small business) compliance measure definitions (022,
-- item 7.5). Each measure_type has its own dedicated compatibility_group
-- (1:1), matching this repo's established discipline, and none shares a
-- group with any expenditure/procurement measure - "Keep compliance metrics
-- separate from expenditure and procurement commitments" per the plan.
-- Semantics, per-file evidence, and rationale:
-- config/measure-semantics/qld_on_time_payments.yaml and
-- ops/reports/qld-on-time-payments-*.md.
--
-- additive_across_time = 0: one quarter's count/percentage/day/payment-value
-- figure is never summed across quarters into an annual figure (the source
-- never publishes one). additive_across_nodes = 1: summing the same measure
-- across different agencies (nodes) for the same quarter is a real,
-- meaningful whole-of-government total (e.g. total penalty interest paid
-- across all agencies) - a legitimate aggregation the source's own
-- structure supports, unlike percentages/day-averages, whose
-- root_total_allowed is 0 (a percentage or a mean is never meaningfully
-- summed across agencies).

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('qld_otp_eligible_claims', 'QLD on-time payment: eligible claims for penalty interest',
     'Count of eligible claims for penalty interest lodged against this agency by small business suppliers, for the quarter.',
     0, 1, 'count', 'qld_otp_eligible_claims', NULL, 'count', 1),
    ('qld_otp_penalty_interest_paid', 'QLD on-time payment: penalty interest paid',
     'Penalty interest actually paid by this agency to small business suppliers for late payment, for the quarter.',
     0, 1, 'cash', 'qld_otp_penalty_interest_paid', NULL, 'AUD', 1),
    ('qld_otp_total_eligible_invoices', 'QLD on-time payment: total eligible invoices',
     'Count of eligible and undisputed small business invoices received by this agency, for the quarter.',
     0, 1, 'count', 'qld_otp_total_eligible_invoices', NULL, 'count', 1),
    ('qld_otp_invoices_paid_late', 'QLD on-time payment: invoices paid late',
     'Count of eligible and undisputed small business invoices this agency paid late, for the quarter.',
     0, 1, 'count', 'qld_otp_invoices_paid_late', NULL, 'count', 1),
    ('qld_otp_value_paid_late', 'QLD on-time payment: value paid late',
     'Dollar value of eligible and undisputed small business invoices this agency paid late, for the quarter.',
     0, 1, 'cash', 'qld_otp_value_paid_late', NULL, 'AUD', 1),
    ('qld_otp_mean_days_paid_late', 'QLD on-time payment: mean days paid late',
     'Mean number of days late for eligible and undisputed small business invoices this agency paid late, for the quarter. A per-agency mean - never meaningfully summed across agencies.',
     0, 1, 'not_applicable', 'qld_otp_mean_days_paid_late', NULL, 'days', 0),
    ('qld_otp_pct_late_smallbus', 'QLD on-time payment: % late payments to small business',
     'Percentage of this agency''s late payments owed to small business suppliers, for the quarter. A percentage - never meaningfully summed across agencies.',
     0, 1, 'not_applicable', 'qld_otp_pct_late_smallbus', NULL, 'percent', 0),
    ('qld_otp_pct_late_others', 'QLD on-time payment: % late payments to others',
     'Percentage of this agency''s late payments owed to non-small-business suppliers, for the quarter. A percentage - never meaningfully summed across agencies.',
     0, 1, 'not_applicable', 'qld_otp_pct_late_others', NULL, 'percent', 0);
