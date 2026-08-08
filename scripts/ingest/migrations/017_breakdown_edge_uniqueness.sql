-- Enforce breakdown edge identity even when optional key columns are NULL.
-- Keep the oldest row if a pre-migration database contains duplicates.
DELETE FROM breakdown_edges
WHERE id NOT IN (
    SELECT MIN(id)
    FROM breakdown_edges
    GROUP BY
        parent_node_id,
        child_node_id,
        edge_kind,
        COALESCE(financial_year, ''),
        COALESCE(crosswalk_id, '')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_breakdown_edges_identity
    ON breakdown_edges (
        parent_node_id,
        child_node_id,
        edge_kind,
        COALESCE(financial_year, ''),
        COALESCE(crosswalk_id, '')
    );
