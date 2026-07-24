-- Observation / valuation semantics + new measure definitions (005).
-- Columns are additive and nullable so existing facts remain valid.

ALTER TABLE facts ADD COLUMN observation_date TEXT;
ALTER TABLE facts ADD COLUMN publication_date TEXT;
ALTER TABLE facts ADD COLUMN valuation_basis TEXT;
ALTER TABLE facts ADD COLUMN amount_granularity TEXT;

CREATE INDEX IF NOT EXISTS idx_facts_observation_date
    ON facts(observation_date);
CREATE INDEX IF NOT EXISTS idx_facts_valuation_basis
    ON facts(valuation_basis);

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group)
VALUES
    ('borrowing_authority_debt_outstanding', 'Borrowing authority debt outstanding',
     'State/territory borrowing-authority securities outstanding (face, fair, or unspecified).',
     0, 1, 'gfs', 'gfs_liability'),
    ('superannuation_liability', 'Defined-benefit superannuation liability',
     'Commonwealth defined-benefit scheme liabilities (CSS/PSS/military/other).',
     0, 1, 'aasb', 'gfs_liability'),
    ('gdp_chain_volume', 'GDP chain volume',
     'Chain-volume / real GDP or GVA from ABS National Accounts.',
     0, 1, 'not_applicable', 'gdp'),
    ('gsp_current', 'GSP current prices',
     'Gross state product at current prices (ABS State Accounts).',
     0, 1, 'not_applicable', 'gdp'),
    ('tax_to_gdp_ratio', 'Tax revenue to GDP ratio',
     'Derived tax revenue as a share of GDP for a matched financial year.',
     0, 0, 'not_applicable', 'gdp');
