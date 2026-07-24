-- P0: breakdown_edges for same_group vs related_breakdown navigation
CREATE TABLE IF NOT EXISTS breakdown_edges (
    id INTEGER PRIMARY KEY,
    parent_node_id INTEGER NOT NULL REFERENCES nodes(id),
    child_node_id INTEGER NOT NULL REFERENCES nodes(id),
    edge_kind TEXT NOT NULL CHECK (edge_kind IN ('same_group', 'related_breakdown')),
    crosswalk_id TEXT,
    financial_year TEXT,
    priority INTEGER NOT NULL DEFAULT 100,
    source_document_id INTEGER REFERENCES source_documents(id),
    notes TEXT,
    CHECK (parent_node_id <> child_node_id),
    UNIQUE (parent_node_id, child_node_id, edge_kind, financial_year, crosswalk_id)
);

CREATE INDEX IF NOT EXISTS idx_breakdown_edges_parent
    ON breakdown_edges(parent_node_id, edge_kind, financial_year, priority);

CREATE INDEX IF NOT EXISTS idx_breakdown_edges_child
    ON breakdown_edges(child_node_id, edge_kind);
