-- MFS Tax Notes 1-2 (Income Tax / Indirect Tax) measure definitions (023).
-- Fourth of the five MFS sibling workbooks (item 7.1), following exactly
-- the same 1:1 measure_type/compatibility_group discipline as 020's Note 3
-- measures - no mfs_tax1_*/mfs_tax2_* measure can ever share a
-- compatibility_group with an annual GFS/PBS actual or budget measure, nor
-- with any mfs_ytd_*/mfs_stock_*/mfs_note3_* measure. Semantics, label-drift
-- evidence, and the two deliberately-excluded ambiguous label families
-- (Note 1's resource rent tax combination/grand total, Note 2's
-- "Other indirect tax") are documented in
-- config/measure-semantics/mfs.yaml and ops/reports/mfs-tax-notes-1-2-*.md.
--
-- additive_across_time = 0 for all: a YTD-through-August figure must never
-- be summed with a YTD-through-July figure for the same measure.
-- additive_across_nodes: 1 only for Note 2's 6 line items, which genuinely
-- and purely sum (no subtraction involved) to mfs_tax2_total_indirect_taxation_revenue
-- - a real, source-stated relationship, matching Note 3's total_expenses
-- pattern exactly. Note 1's items are additive_across_nodes = 0 throughout:
-- "less Refunds" is SUBTRACTED (not added) to derive
-- mfs_tax1_total_individuals_withholding_tax, so this database does not
-- assert an automatic-summation contract for Note 1's subtotal relationships
-- (the underlying figures are still loaded and citable, just without a
-- formal additive claim that a signed-subtraction formula could misrepresent
-- through this system's addition-only additive_across_nodes mechanism).
-- root_total_allowed = 0 for the two subtotals
-- (mfs_tax1_total_individuals_withholding_tax,
-- mfs_tax1_total_income_other_sources) and mfs_tax2_total_indirect_taxation_revenue
-- (already-derived totals, never themselves treated as an addend).

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group, view_family, default_unit, root_total_allowed)
VALUES
    ('mfs_tax1_gross_income_tax_withholding', 'MFS Tax Note 1: Gross income tax withholding',
     'Monthly Financial Statements Tax Note 1: gross PAYG income tax withholding, YTD through the reporting month.',
     0, 0, 'accrual', 'mfs_tax1_gross_income_tax_withholding', NULL, 'AUD', 1),
    ('mfs_tax1_gross_other_individuals', 'MFS Tax Note 1: Gross other individuals',
     'Monthly Financial Statements Tax Note 1: gross income tax from individuals other than PAYG withholding, YTD through the reporting month.',
     0, 0, 'accrual', 'mfs_tax1_gross_other_individuals', NULL, 'AUD', 1),
    ('mfs_tax1_less_refunds', 'MFS Tax Note 1: less Refunds',
     'Monthly Financial Statements Tax Note 1: individual income tax refunds paid, YTD through the reporting month - a positive magnitude subtracted from gross withholding/other-individuals figures by the source.',
     0, 0, 'accrual', 'mfs_tax1_less_refunds', NULL, 'AUD', 1),
    ('mfs_tax1_total_individuals_withholding_tax', 'MFS Tax Note 1: Total individuals and other withholding taxation',
     'Monthly Financial Statements Tax Note 1: the published subtotal (gross withholding + gross other individuals - less refunds), YTD through the reporting month. A derived subtotal, directly cited from the source''s own stated row - never computed here.',
     0, 0, 'accrual', 'mfs_tax1_total_individuals_withholding_tax', NULL, 'AUD', 0),
    ('mfs_tax1_company_tax', 'MFS Tax Note 1: Company tax',
     'Monthly Financial Statements Tax Note 1: company (corporate) income tax collections, YTD through the reporting month.',
     0, 0, 'accrual', 'mfs_tax1_company_tax', NULL, 'AUD', 1),
    ('mfs_tax1_superannuation_fund_taxes', 'MFS Tax Note 1: Superannuation fund taxes',
     'Monthly Financial Statements Tax Note 1: taxes on superannuation fund earnings/contributions, YTD through the reporting month.',
     0, 0, 'accrual', 'mfs_tax1_superannuation_fund_taxes', NULL, 'AUD', 1),
    ('mfs_tax1_fringe_benefits_tax', 'MFS Tax Note 1: Fringe benefits tax',
     'Monthly Financial Statements Tax Note 1: fringe benefits tax collections, YTD through the reporting month - the raw line-item figure only; this database makes no claim about its inclusion in any grand total (not loaded, genuinely ambiguous by generation).',
     0, 0, 'accrual', 'mfs_tax1_fringe_benefits_tax', NULL, 'AUD', 1),
    ('mfs_tax1_petroleum_resource_rent_tax', 'MFS Tax Note 1: Petroleum resource rent tax (FY2005-06..FY2011-12, FY2017-18 onward)',
     'Monthly Financial Statements Tax Note 1: PRRT collections, YTD through the reporting month, loaded only for the years this exact label reports a clean standalone figure (FY2012-13..FY2016-17 use a different combined "Resource rent taxes" label, not loaded; FY2013-14''s occurrence of this exact label is an incomplete child breakdown, also not loaded).',
     0, 0, 'accrual', 'mfs_tax1_petroleum_resource_rent_tax', NULL, 'AUD', 1),
    ('mfs_tax1_total_income_other_sources', 'MFS Tax Note 1: Total income from other sources (FY2005-06 only)',
     'Monthly Financial Statements Tax Note 1: the published subtotal (Company tax + Superannuation funds + Petroleum resource rent tax), disclosed as its own line only in FY2005-06, YTD through the reporting month. A derived subtotal, directly cited from the source''s own stated row - never computed here.',
     0, 0, 'accrual', 'mfs_tax1_total_income_other_sources', NULL, 'AUD', 0),
    ('mfs_tax2_excise_duty', 'MFS Tax Note 2: Excise duty',
     'Monthly Financial Statements Tax Note 2: excise duty collections, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_tax2_excise_duty', NULL, 'AUD', 1),
    ('mfs_tax2_customs_duty', 'MFS Tax Note 2: Customs duty',
     'Monthly Financial Statements Tax Note 2: customs duty collections, YTD through the reporting month.',
     0, 1, 'accrual', 'mfs_tax2_customs_duty', NULL, 'AUD', 1),
    ('mfs_tax2_goods_and_services_tax', 'MFS Tax Note 2: Goods and services tax',
     'Monthly Financial Statements Tax Note 2: GST collections, YTD through the reporting month, disclosed as its own line only from December 2008-09 onward (bundled into "Other indirect tax" before then, not loaded).',
     0, 1, 'accrual', 'mfs_tax2_goods_and_services_tax', NULL, 'AUD', 1),
    ('mfs_tax2_wine_equalisation_tax', 'MFS Tax Note 2: Wine equalisation tax',
     'Monthly Financial Statements Tax Note 2: wine equalisation tax collections, YTD through the reporting month, disclosed as its own line only from FY2009-10 onward.',
     0, 1, 'accrual', 'mfs_tax2_wine_equalisation_tax', NULL, 'AUD', 1),
    ('mfs_tax2_luxury_car_tax', 'MFS Tax Note 2: Luxury car tax',
     'Monthly Financial Statements Tax Note 2: luxury car tax collections, YTD through the reporting month, disclosed as its own line only from FY2009-10 onward.',
     0, 1, 'accrual', 'mfs_tax2_luxury_car_tax', NULL, 'AUD', 1),
    ('mfs_tax2_carbon_pricing_mechanism', 'MFS Tax Note 2: Carbon pricing mechanism (FY2012-13, FY2013-14 only)',
     'Monthly Financial Statements Tax Note 2: carbon pricing mechanism revenue, YTD through the reporting month, disclosed as its own line only FY2012-13 and FY2013-14.',
     0, 1, 'accrual', 'mfs_tax2_carbon_pricing_mechanism', NULL, 'AUD', 1),
    ('mfs_tax2_total_indirect_taxation_revenue', 'MFS Tax Note 2: Total indirect taxation revenue',
     'Monthly Financial Statements Tax Note 2: the published Total indirect taxation revenue bottom line, YTD through the reporting month. A derived total, directly cited from the source''s own stated total row - never computed here.',
     0, 0, 'accrual', 'mfs_tax2_total_indirect_taxation_revenue', NULL, 'AUD', 0);
