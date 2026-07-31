-- Semantic hardening (006): typed amounts, inference provenance, quality, lineage hooks.
-- Additive / nullable. amount_aud remains AUD-only when unit=AUD.
-- Duplicate-column ALTERs are ignored by schema_migrate.apply_sql (idempotent).

ALTER TABLE facts ADD COLUMN amount_value REAL;
ALTER TABLE facts ADD COLUMN scale TEXT;
ALTER TABLE facts ADD COLUMN price_basis TEXT;
ALTER TABLE facts ADD COLUMN volume_basis TEXT;
ALTER TABLE facts ADD COLUMN seasonal_adjustment TEXT;
ALTER TABLE facts ADD COLUMN source_budget_year TEXT;
ALTER TABLE facts ADD COLUMN column_header_original TEXT;
ALTER TABLE facts ADD COLUMN year_inference_method TEXT;
ALTER TABLE facts ADD COLUMN year_inference_confidence TEXT;
ALTER TABLE facts ADD COLUMN canonical_dataset_id TEXT;
ALTER TABLE facts ADD COLUMN extractor_run_id TEXT;
ALTER TABLE facts ADD COLUMN quality_status TEXT;
ALTER TABLE facts ADD COLUMN quality_flags_json TEXT;
ALTER TABLE facts ADD COLUMN view_family TEXT;

UPDATE facts
SET amount_value = amount_aud
WHERE amount_value IS NULL AND amount_aud IS NOT NULL;

UPDATE facts
SET scale = COALESCE(scale, 'units')
WHERE scale IS NULL;

UPDATE facts
SET price_basis = COALESCE(price_basis, 'unspecified')
WHERE price_basis IS NULL;

UPDATE facts
SET quality_status = COALESCE(quality_status, 'ok')
WHERE quality_status IS NULL;

-- Ratios: keep numeric in quantity + amount_value; clear amount_aud (CHECK allows quantity).
UPDATE facts
SET quantity = COALESCE(quantity, amount_aud),
    amount_value = COALESCE(amount_value, amount_aud, quantity),
    amount_aud = NULL,
    unit = 'percent',
    currency = 'NA',
    amount_granularity = 'ratio',
    price_basis = 'not_applicable',
    view_family = 'ratios'
WHERE measure_type = 'tax_to_gdp_ratio';

UPDATE facts SET view_family = 'gdp_current', price_basis = 'current_prices'
WHERE measure_type = 'gdp_current' AND (view_family IS NULL OR view_family = '');
UPDATE facts SET view_family = 'gdp_chain_volume', price_basis = 'chain_volume'
WHERE measure_type = 'gdp_chain_volume' AND (view_family IS NULL OR view_family = '');
UPDATE facts SET view_family = 'gsp_current', price_basis = 'current_prices'
WHERE measure_type = 'gsp_current' AND (view_family IS NULL OR view_family = '');

CREATE INDEX IF NOT EXISTS idx_facts_view_family ON facts(view_family);
CREATE INDEX IF NOT EXISTS idx_facts_price_basis ON facts(price_basis);
CREATE INDEX IF NOT EXISTS idx_facts_quality_status ON facts(quality_status);
CREATE INDEX IF NOT EXISTS idx_facts_canonical_dataset ON facts(canonical_dataset_id);

ALTER TABLE measure_definitions ADD COLUMN view_family TEXT;
ALTER TABLE measure_definitions ADD COLUMN default_unit TEXT;
ALTER TABLE measure_definitions ADD COLUMN root_total_allowed INTEGER NOT NULL DEFAULT 1;

UPDATE measure_definitions SET view_family = 'gdp_current', default_unit = 'AUD', root_total_allowed = 1
WHERE measure_type = 'gdp_current';
UPDATE measure_definitions SET view_family = 'gdp_chain_volume', default_unit = 'AUD', root_total_allowed = 1
WHERE measure_type = 'gdp_chain_volume';
UPDATE measure_definitions SET view_family = 'gsp_current', default_unit = 'AUD', root_total_allowed = 1
WHERE measure_type = 'gsp_current';
UPDATE measure_definitions SET view_family = 'ratios', default_unit = 'percent', root_total_allowed = 0,
    additive_across_nodes = 0
WHERE measure_type = 'tax_to_gdp_ratio';
UPDATE measure_definitions SET view_family = 'actual_expense', default_unit = 'AUD'
WHERE compatibility_group = 'actual_expense' AND view_family IS NULL;
UPDATE measure_definitions SET view_family = 'budget_expense', default_unit = 'AUD'
WHERE compatibility_group = 'budget_expense' AND view_family IS NULL;
UPDATE measure_definitions SET view_family = 'gfs_revenue', default_unit = 'AUD'
WHERE compatibility_group = 'gfs_revenue' AND view_family IS NULL;
UPDATE measure_definitions SET view_family = 'debt_stock', default_unit = 'AUD', root_total_allowed = 1
WHERE compatibility_group = 'gfs_liability' AND view_family IS NULL;
