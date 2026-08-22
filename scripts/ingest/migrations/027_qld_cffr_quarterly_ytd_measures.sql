-- Queensland Consolidated Fund Financial Report (CFFR) quarterly
-- Year-to-Date measure definitions (027), item 7.4's quarterly slice.
-- Semantics, table-structure evidence, and the deliberately-excluded
-- scope (Operating/Investment Account split, quarter-only 3-month flow
-- tables, receipt sub-line-items with genuine multi-generation
-- composition ambiguity, the pre-2017 era pending further audit) are
-- documented in config/measure-semantics/qld_cffr_quarterly.yaml and
-- ops/reports/qld-cffr-quarterly-scoping-20260819T194500Z.md.
--
-- Genuinely distinct measure_types from the already-loaded annual
-- qld_cffr_* family (025) - a quarterly cumulative Year-to-Date figure
-- is a different vintage from a full financial-year figure and must
-- never be blended with it, per this program's standing
-- never-sum-incompatible-vintages rule. additive_across_time = 0: a
-- Year-to-Date figure is never summed with another quarter's figure
-- (each quarter's YTD is already cumulative from 1 July).
-- additive_across_nodes = 0 throughout (same reasoning as the annual
-- measures - the receipts do sum to a published subtotal, not itself
-- loaded this pass). root_total_allowed = 1 throughout (informational).

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('qld_cffr_quarterly_ytd_opening_balance', 'QLD CFFR Quarterly: Consolidated Fund balance as at 1 July',
     'Queensland Consolidated Fund total balance (Operating + Investment Account) as at the start of the financial year, cash basis, as restated in a quarterly Year-to-Date statement.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_opening_balance', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_closing_balance', 'QLD CFFR Quarterly: Consolidated Fund balance as at quarter end',
     'Queensland Consolidated Fund total balance as at the end of the reporting quarter, cash basis, cumulative Year-to-Date.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_closing_balance', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_collections_from_departments', 'QLD CFFR Quarterly: Collections received from Departments (YTD)',
     'Cash collections received from Queensland Government departments into the Consolidated Fund, cumulative from 1 July to the reporting quarter end.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_collections_from_departments', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_investment_interest', 'QLD CFFR Quarterly: Investment interest (YTD)',
     'Cash investment interest received into the Consolidated Fund, cumulative from 1 July to the reporting quarter end.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_investment_interest', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_dividends_income_tax_equivalents', 'QLD CFFR Quarterly: Dividends and income tax equivalents (YTD)',
     'Cash dividends and income tax equivalents received into the Consolidated Fund, cumulative from 1 July to the reporting quarter end.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_dividends_income_tax_equivalents', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_non_appropriated_equity_adjustments', 'QLD CFFR Quarterly: Non-appropriated equity adjustments (YTD)',
     'Non-appropriated equity adjustments recorded against the Consolidated Fund, cumulative from 1 July to the reporting quarter end.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_non_appropriated_equity_adjustments', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_superannuation_lsl_qgif_alcs_contributions', 'QLD CFFR Quarterly: Superannuation, LSL, QGIF and ALCS contributions (YTD)',
     'Cash superannuation, long service leave, Queensland Government Insurance Fund and ALCS contributions received into the Consolidated Fund, cumulative from 1 July to the reporting quarter end.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_superannuation_lsl_qgif_alcs_contributions', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_other_receipts', 'QLD CFFR Quarterly: Other receipts (YTD)',
     'Other cash receipts into the Consolidated Fund not separately itemised, cumulative from 1 July to the reporting quarter end.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_other_receipts', NULL, 'AUD', 1),
    ('qld_cffr_quarterly_ytd_appropriations_provided_to_departments', 'QLD CFFR Quarterly: Appropriations provided to Departments (YTD)',
     'Cash appropriations paid from the Consolidated Fund to Queensland Government departments, cumulative from 1 July to the reporting quarter end - the Consolidated Fund''s entire Payments section.',
     0, 0, 'cash', 'qld_cffr_quarterly_ytd_appropriations_provided_to_departments', NULL, 'AUD', 1);
