-- AusGov Budget Tracker - proposed hierarchical and provenance-first schema
-- SQLite compatible. Draft researched 2026-07-20.
--
-- Design goals:
--   1. Represent arbitrary depth, not only category/subcategory/department.
--   2. Keep functional, organisational, appropriation, geographic and supplier
--      hierarchies separate but linkable.
--   3. Never silently add estimates, actuals, appropriations, contracts and
--      payments as though they were the same measure.
--   4. Preserve document, page/sheet/cell and file-hash lineage for every fact.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_documents (
    id INTEGER PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    publisher TEXT NOT NULL,
    title TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    government_level TEXT NOT NULL CHECK (
        government_level IN ('national', 'federal', 'state', 'territory', 'local', 'cross_level')
    ),
    source_family TEXT NOT NULL,
    landing_url TEXT,
    canonical_resource_url TEXT,
    licence TEXT,
    publication_date TEXT,
    reference_period_start TEXT,
    reference_period_end TEXT,
    version_label TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS source_retrievals (
    id INTEGER PRIMARY KEY,
    source_document_id INTEGER NOT NULL REFERENCES source_documents(id),
    retrieved_at TEXT NOT NULL,
    resolved_url TEXT NOT NULL,
    http_status INTEGER,
    content_type TEXT,
    byte_size INTEGER,
    sha256 TEXT NOT NULL,
    local_path TEXT NOT NULL,
    etag TEXT,
    last_modified TEXT,
    retrieval_status TEXT NOT NULL CHECK (
        retrieval_status IN ('ok', 'not_modified', 'manual', 'blocked', 'failed')
    ),
    error_message TEXT,
    UNIQUE (source_document_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_source_retrievals_document
    ON source_retrievals(source_document_id, retrieved_at DESC);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    government_level TEXT NOT NULL,
    abn TEXT,
    entity_identifier TEXT,
    valid_from TEXT,
    valid_to TEXT,
    parent_entity_id INTEGER REFERENCES entities(id),
    source_document_id INTEGER REFERENCES source_documents(id),
    UNIQUE (jurisdiction, canonical_name, valid_from)
);

CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY,
    canonical_key TEXT NOT NULL UNIQUE,
    node_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    jurisdiction TEXT NOT NULL,
    government_level TEXT NOT NULL,
    entity_id INTEGER REFERENCES entities(id),
    external_code TEXT,
    valid_from TEXT,
    valid_to TEXT,
    source_document_id INTEGER REFERENCES source_documents(id),
    source_locator_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(source_locator_json))
);

-- A node may appear in more than one hierarchy. For example, an NDIS program
-- belongs in a functional hierarchy (social security -> disability), an
-- organisational hierarchy (portfolio -> entity -> outcome -> program), and
-- an appropriation hierarchy. A generic edge table supports this DAG.
CREATE TABLE IF NOT EXISTS node_edges (
    id INTEGER PRIMARY KEY,
    hierarchy_type TEXT NOT NULL CHECK (
        hierarchy_type IN (
            'functional', 'organisational', 'appropriation', 'geographic',
            'supplier', 'grant', 'contract', 'local_service', 'custom'
        )
    ),
    parent_node_id INTEGER NOT NULL REFERENCES nodes(id),
    child_node_id INTEGER NOT NULL REFERENCES nodes(id),
    valid_from TEXT,
    valid_to TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    source_document_id INTEGER REFERENCES source_documents(id),
    source_locator_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(source_locator_json)),
    CHECK (parent_node_id <> child_node_id),
    UNIQUE (hierarchy_type, parent_node_id, child_node_id, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_node_edges_parent
    ON node_edges(hierarchy_type, parent_node_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_node_edges_child
    ON node_edges(hierarchy_type, child_node_id);

CREATE TABLE IF NOT EXISTS measure_definitions (
    measure_type TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    additive_across_time INTEGER NOT NULL DEFAULT 0 CHECK (additive_across_time IN (0, 1)),
    additive_across_nodes INTEGER NOT NULL DEFAULT 1 CHECK (additive_across_nodes IN (0, 1)),
    default_accounting_basis TEXT,
    compatibility_group TEXT NOT NULL
);

INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group)
VALUES
    ('budget_estimate', 'Budget estimate', 'Planned amount in a budget or forward estimate.', 0, 1, 'accrual', 'budget_expense'),
    ('revised_estimate', 'Revised estimate', 'Updated estimate such as MYEFO or a state budget update.', 0, 1, 'accrual', 'budget_expense'),
    ('actual_accrual_expense', 'Actual accrual expense', 'Recognised expense for the reporting period.', 1, 1, 'accrual', 'actual_expense'),
    ('cash_payment', 'Cash payment', 'Cash paid during the reporting period.', 1, 1, 'cash', 'cash_outflow'),
    ('appropriation_authority', 'Appropriation authority', 'Legal authority to draw public money; not necessarily expenditure.', 0, 1, 'appropriation', 'authority'),
    ('grant_award', 'Grant award', 'Approved grant agreement or award; may span several years.', 0, 1, 'commitment', 'commitment'),
    ('contract_value', 'Contract value', 'Maximum or reported value of a contract; not necessarily annual cash paid.', 0, 1, 'commitment', 'commitment'),
    ('invoice_paid', 'Invoice paid', 'Published invoice-level cash payment.', 1, 1, 'cash', 'cash_outflow'),
    ('recipient_count', 'Recipient count', 'Number of recipients; not a monetary measure.', 0, 1, 'count', 'count'),
    ('participant_payment', 'Participant payment', 'Published aggregate payment for participant supports.', 1, 1, 'cash', 'cash_outflow');

CREATE TABLE IF NOT EXISTS facts (
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
        estimate_status IN ('budget', 'forward_estimate', 'revised_estimate', 'estimated_actual', 'actual', 'audited_actual', 'award', 'contract', 'invoice')
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
    notes TEXT,
    CHECK (amount_aud IS NOT NULL OR quantity IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_facts_period_measure
    ON facts(financial_year, measure_type, estimate_status);
CREATE INDEX IF NOT EXISTS idx_facts_source
    ON facts(source_document_id, source_retrieval_id);

-- Attach one fact to any number of dimensions. At least one primary node should
-- be present for a spend fact, while additional links may capture function,
-- sub-function, portfolio, entity, program, component, geography, supplier,
-- contract, grant and appropriation.
CREATE TABLE IF NOT EXISTS fact_nodes (
    fact_id INTEGER NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    node_id INTEGER NOT NULL REFERENCES nodes(id),
    dimension_role TEXT NOT NULL CHECK (
        dimension_role IN (
            'primary', 'function', 'subfunction', 'portfolio', 'entity',
            'outcome', 'program', 'component', 'appropriation', 'special_account',
            'geography', 'council', 'local_service', 'supplier', 'grant_program',
            'grant_award', 'contract', 'invoice', 'payment_category', 'other'
        )
    ),
    PRIMARY KEY (fact_id, node_id, dimension_role)
);

CREATE INDEX IF NOT EXISTS idx_fact_nodes_node
    ON fact_nodes(node_id, dimension_role, fact_id);

-- Explicitly record how a published figure is derived from other figures.
-- This is essential for totals, eliminations, basis bridges and revisions.
CREATE TABLE IF NOT EXISTS lineage_edges (
    parent_fact_id INTEGER NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    child_fact_id INTEGER NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK (
        relation_type IN (
            'sum_of', 'component_of', 'maps_to', 'funded_by', 'paid_under',
            'revises', 'supersedes', 'reconciles_to', 'eliminates', 'derived_from'
        )
    ),
    allocation_weight NUMERIC,
    method TEXT,
    notes TEXT,
    source_document_id INTEGER REFERENCES source_documents(id),
    source_locator_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(source_locator_json)),
    PRIMARY KEY (parent_fact_id, child_fact_id, relation_type)
);

CREATE TABLE IF NOT EXISTS reconciliations (
    id INTEGER PRIMARY KEY,
    reconciliation_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    financial_year TEXT NOT NULL,
    left_fact_id INTEGER NOT NULL REFERENCES facts(id),
    right_fact_id INTEGER NOT NULL REFERENCES facts(id),
    bridge_amount_aud NUMERIC,
    difference_amount_aud NUMERIC NOT NULL,
    tolerance_amount_aud NUMERIC NOT NULL DEFAULT 1.00,
    status TEXT NOT NULL CHECK (
        status IN ('balanced', 'within_tolerance', 'explained_difference', 'unresolved')
    ),
    explanation TEXT,
    created_at TEXT NOT NULL
);

-- Optional raw record staging. Keep each parsed source row before normalisation
-- so parser behaviour is inspectable and can be replayed.
CREATE TABLE IF NOT EXISTS raw_records (
    id INTEGER PRIMARY KEY,
    source_retrieval_id INTEGER NOT NULL REFERENCES source_retrievals(id),
    record_number INTEGER NOT NULL,
    record_json TEXT NOT NULL CHECK (json_valid(record_json)),
    source_locator_json TEXT NOT NULL CHECK (json_valid(source_locator_json)),
    record_hash TEXT NOT NULL,
    parse_status TEXT NOT NULL CHECK (
        parse_status IN ('parsed', 'skipped', 'warning', 'error')
    ),
    parse_message TEXT,
    UNIQUE (source_retrieval_id, record_number)
);

-- Compatibility guard: this view makes it easy for API code to reject attempts
-- to add unlike measures. A tree request should filter to exactly one
-- compatibility_group, accounting_basis and estimate_status unless it is an
-- explicitly named reconciliation view.
CREATE VIEW IF NOT EXISTS v_fact_compatibility AS
SELECT
    f.*,
    m.compatibility_group,
    m.additive_across_time,
    m.additive_across_nodes
FROM facts AS f
JOIN measure_definitions AS m ON m.measure_type = f.measure_type;

-- Example recursive query for a selected hierarchy root. Bind :root_id,
-- :hierarchy_type, :financial_year, :measure_type and :estimate_status.
--
-- WITH RECURSIVE tree(node_id, parent_node_id, depth, path) AS (
--   SELECT n.id, NULL, 0, n.name
--   FROM nodes n
--   WHERE n.id = :root_id
--   UNION ALL
--   SELECT c.id, e.parent_node_id, tree.depth + 1,
--          tree.path || ' > ' || c.name
--   FROM tree
--   JOIN node_edges e
--     ON e.parent_node_id = tree.node_id
--    AND e.hierarchy_type = :hierarchy_type
--   JOIN nodes c ON c.id = e.child_node_id
-- )
-- SELECT tree.*, COALESCE(SUM(f.amount_aud), 0) AS direct_amount_aud
-- FROM tree
-- LEFT JOIN fact_nodes fn
--   ON fn.node_id = tree.node_id
--  AND fn.dimension_role = 'primary'
-- LEFT JOIN facts f
--   ON f.id = fn.fact_id
--  AND f.financial_year = :financial_year
--  AND f.measure_type = :measure_type
--  AND f.estimate_status = :estimate_status
-- GROUP BY tree.node_id, tree.parent_node_id, tree.depth, tree.path
-- ORDER BY tree.path;