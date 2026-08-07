-- Extend the descriptions of measures shared by the original newer RSF
-- cluster and the 2002-03 to 2017-18 backfill. Kept separate from migration
-- 013 because 013 was applied before this metadata refinement.
UPDATE measure_definitions SET description =
 'Queensland General Government Sector Revenue from Report on State Finances summary tables, 2002-03 to 2024-25.'
 WHERE measure_type = 'qld_rsf_revenue';
UPDATE measure_definitions SET description =
 'Queensland General Government Sector Expenses from Report on State Finances summary tables, 2002-03 to 2024-25.'
 WHERE measure_type = 'qld_rsf_expense';
UPDATE measure_definitions SET description =
 'Queensland General Government Sector Net Operating Balance, 2002-03 to 2024-25; a non-additive balance.'
 WHERE measure_type = 'qld_rsf_net_operating_balance';
UPDATE measure_definitions SET description =
 'Queensland General Government Sector Capital Purchases where published, 2004-05 to 2024-25.'
 WHERE measure_type = 'qld_rsf_capital_purchases';
UPDATE measure_definitions SET description =
 'Queensland General Government Sector Fiscal Balance / UPF Net Lending-Borrowing where published, 2002-03 to 2024-25; a non-additive balance.'
 WHERE measure_type = 'qld_rsf_fiscal_balance';
