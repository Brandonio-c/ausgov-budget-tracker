-- Queensland Consolidated Fund Financial Report (CFFR) measure
-- definitions (025), item 7.4's first slice. Semantics, label-drift
-- evidence, and the deliberately-excluded scope (Operating/Investment
-- Account split, quarterly interim editions, receipt sub-line-items with
-- genuine multi-generation composition ambiguity) are documented in
-- config/measure-semantics/qld_cffr.yaml and
-- ops/reports/qld-cffr-scoping-20260815T163500Z.md.
--
-- additive_across_time = 0: a full-year figure is never summed with
-- another year's figure. additive_across_nodes = 0 for every measure
-- here: the 6 receipt line items do genuinely sum to a published
-- receipts subtotal, but that subtotal is not itself loaded this pass
-- (see the scoping report), so no automatic-summation contract is
-- declared this pass. root_total_allowed = 1 throughout (informational -
-- none of these measures is itself a total loaded in this database).

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('qld_cffr_opening_balance', 'QLD CFFR: Consolidated Fund balance as at 1 July',
     'Queensland Consolidated Fund total balance (Operating + Investment Account) as at the start of the financial year, cash basis.',
     0, 0, 'cash', 'qld_cffr_opening_balance', NULL, 'AUD', 1),
    ('qld_cffr_closing_balance', 'QLD CFFR: Consolidated Fund balance as at 30 June',
     'Queensland Consolidated Fund total balance as at the end of the financial year, cash basis.',
     0, 0, 'cash', 'qld_cffr_closing_balance', NULL, 'AUD', 1),
    ('qld_cffr_collections_from_departments', 'QLD CFFR: Collections received from Departments',
     'Cash collections received from Queensland Government departments into the Consolidated Fund, full financial year.',
     0, 0, 'cash', 'qld_cffr_collections_from_departments', NULL, 'AUD', 1),
    ('qld_cffr_investment_interest', 'QLD CFFR: Investment interest',
     'Cash investment interest received into the Consolidated Fund, full financial year.',
     0, 0, 'cash', 'qld_cffr_investment_interest', NULL, 'AUD', 1),
    ('qld_cffr_dividends_income_tax_equivalents', 'QLD CFFR: Dividends and income tax equivalents',
     'Cash dividends and income tax equivalents received into the Consolidated Fund, full financial year.',
     0, 0, 'cash', 'qld_cffr_dividends_income_tax_equivalents', NULL, 'AUD', 1),
    ('qld_cffr_non_appropriated_equity_adjustments', 'QLD CFFR: Non-appropriated equity adjustments',
     'Non-appropriated equity adjustments recorded against the Consolidated Fund, full financial year.',
     0, 0, 'cash', 'qld_cffr_non_appropriated_equity_adjustments', NULL, 'AUD', 1),
    ('qld_cffr_superannuation_lsl_qgif_alcs_contributions', 'QLD CFFR: Superannuation, LSL, QGIF and ALCS contributions',
     'Cash superannuation, long service leave, Queensland Government Insurance Fund and ALCS contributions received into the Consolidated Fund, full financial year.',
     0, 0, 'cash', 'qld_cffr_superannuation_lsl_qgif_alcs_contributions', NULL, 'AUD', 1),
    ('qld_cffr_other_receipts', 'QLD CFFR: Other receipts',
     'Other cash receipts into the Consolidated Fund not separately itemised, full financial year.',
     0, 0, 'cash', 'qld_cffr_other_receipts', NULL, 'AUD', 1),
    ('qld_cffr_appropriations_provided_to_departments', 'QLD CFFR: Appropriations provided to Departments',
     'Cash appropriations paid from the Consolidated Fund to Queensland Government departments, full financial year - the Consolidated Fund''s entire Payments section.',
     0, 0, 'cash', 'qld_cffr_appropriations_provided_to_departments', NULL, 'AUD', 1);
