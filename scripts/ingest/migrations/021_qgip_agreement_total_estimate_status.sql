-- Item 7.2 QGIP repair (021): add 'actual_cumulative_agreement_total' to the
-- facts.estimate_status CHECK constraint.
--
-- 2012-13/2013-14 QLD QGIP source files genuinely have no per-year
-- expenditure column at all (verified directly against both real files) -
-- only a whole-of-agreement cumulative total. Loading these under plain
-- 'actual' (the same estimate_status as every genuine single-year figure
-- elsewhere) would let them be silently blended with a different vintage,
-- which this program's non-negotiable rules forbid. A distinct
-- estimate_status keeps them structurally separated by the same
-- mandatory-triple discipline used everywhere else in this schema.
--
-- SQLite has no ALTER TABLE ... ADD CHECK; a CHECK constraint change
-- requires a full table rebuild. Every column, all data, and every index
-- are preserved exactly - only the estimate_status CHECK list gains one
-- new value. See ops/reports/qgip-repair-*.md for full evidence.

PRAGMA foreign_keys=OFF;

-- v_fact_compatibility selects from facts and must be dropped before facts
-- itself can be dropped, then recreated identically afterward.
DROP VIEW IF EXISTS v_fact_compatibility;

CREATE TABLE facts_021_new (
    id INTEGER PRIMARY KEY,
    fact_key TEXT NOT NULL UNIQUE,
    financial_year TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    period_granularity TEXT NOT NULL CHECK (
        period_granularity IN ('point_in_time', 'month', 'quarter', 'year_to_date', 'financial_year', 'multi_year')
    ),
    measure_type TEXT NOT NULL REFERENCES measure_definitions(measure_type),
    accounting_basis TEXT NOT NULL CHECK (
        accounting_basis IN ('cash', 'accrual', 'gfs', 'aasb', 'appropriation', 'commitment', 'count', 'mixed', 'not_applicable')
    ),
    estimate_status TEXT NOT NULL CHECK (
        estimate_status IN ('budget', 'forward_estimate', 'revised_estimate', 'estimated_actual', 'actual', 'audited_actual', 'award', 'contract', 'invoice', 'actual_cumulative_agreement_total')
    ),
    amount_aud NUMERIC,
    quantity NUMERIC,
    unit TEXT NOT NULL DEFAULT 'AUD',
    currency TEXT NOT NULL DEFAULT 'AUD',
    is_consolidated INTEGER NOT NULL DEFAULT 0 CHECK (is_consolidated IN (0, 1)),
    is_elimination INTEGER NOT NULL DEFAULT 0 CHECK (is_elimination IN (0, 1)),
    confidential_or_suppressed INTEGER NOT NULL DEFAULT 0 CHECK (confidential_or_suppressed IN (0, 1)),
    source_document_id INTEGER NOT NULL REFERENCES source_documents(id),
    source_retrieval_id INTEGER REFERENCES source_retrievals(id),
    source_locator_json TEXT NOT NULL CHECK (json_valid(source_locator_json)),
    source_record_hash TEXT,
    published_at TEXT,
    retrieved_at TEXT NOT NULL,
    notes TEXT, observation_date TEXT, publication_date TEXT, valuation_basis TEXT, amount_granularity TEXT, amount_value REAL, scale TEXT, price_basis TEXT, volume_basis TEXT, seasonal_adjustment TEXT, source_budget_year TEXT, column_header_original TEXT, year_inference_method TEXT, year_inference_confidence TEXT, canonical_dataset_id TEXT, extractor_run_id TEXT, quality_status TEXT, quality_flags_json TEXT, view_family TEXT,
    CHECK (amount_aud IS NOT NULL OR quantity IS NOT NULL)
);

INSERT INTO facts_021_new SELECT * FROM facts;

DROP TABLE facts;
ALTER TABLE facts_021_new RENAME TO facts;

CREATE INDEX idx_facts_period_measure ON facts(financial_year, measure_type, estimate_status);
CREATE INDEX idx_facts_source ON facts(source_document_id, source_retrieval_id);
CREATE INDEX idx_facts_observation_date ON facts(observation_date);
CREATE INDEX idx_facts_valuation_basis ON facts(valuation_basis);
CREATE INDEX idx_facts_view_family ON facts(view_family);
CREATE INDEX idx_facts_price_basis ON facts(price_basis);
CREATE INDEX idx_facts_quality_status ON facts(quality_status);
CREATE INDEX idx_facts_canonical_dataset ON facts(canonical_dataset_id);

CREATE VIEW v_fact_compatibility AS
SELECT
    f.*,
    m.compatibility_group,
    m.additive_across_time,
    m.additive_across_nodes
FROM facts AS f
JOIN measure_definitions AS m ON m.measure_type = f.measure_type;

PRAGMA foreign_keys=ON;
