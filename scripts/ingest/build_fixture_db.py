#!/usr/bin/env python3
"""Build a tiny committed-fixture facts DB for integration tests (no production raw)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ingest"))

from schema_migrate import migrate  # noqa: E402

OUT = REPO / "data" / "test" / "facts_fixture.db"


def main() -> int:
    if OUT.exists():
        OUT.unlink()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    migrate(OUT)
    conn = sqlite3.connect(str(OUT))
    conn.execute(
        """
        INSERT INTO source_documents (
            source_key, publisher, title, jurisdiction, government_level, source_family
        ) VALUES (
            'fixture_gfs', 'Test', 'Fixture GFS', 'Commonwealth', 'federal', 'fixture'
        )
        """
    )
    doc_id = conn.execute("SELECT id FROM source_documents WHERE source_key='fixture_gfs'").fetchone()[0]
    conn.execute(
        """
        INSERT INTO nodes (
            canonical_key, node_type, name, jurisdiction, government_level, source_document_id
        ) VALUES (
            'fixture:defence', 'category', 'Defence', 'Commonwealth', 'federal', ?
        )
        """,
        (doc_id,),
    )
    node_id = conn.execute("SELECT id FROM nodes WHERE canonical_key='fixture:defence'").fetchone()[0]
    conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type, accounting_basis,
            estimate_status, amount_aud, amount_value, unit, currency, source_document_id,
            view_family, price_basis, quality_status, source_locator_json, source_record_hash,
            retrieved_at
        ) VALUES (
            'fixture|defence|2024-25', '2024-25', 'financial_year', 'gfs_expense', 'gfs',
            'actual', 1000, 1000, 'AUD', 'AUD', ?,
            'actual_expense', 'unspecified', 'ok', '{}', 'fixturehash1',
            '2026-01-01T00:00:00Z'
        )
        """,
        (doc_id,),
    )
    fid = conn.execute("SELECT id FROM facts WHERE fact_key='fixture|defence|2024-25'").fetchone()[0]
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
        (fid, node_id),
    )
    conn.execute(
        """
        INSERT INTO nodes (
            canonical_key, node_type, name, jurisdiction, government_level, source_document_id
        ) VALUES (
            'fixture:tax_gdp', 'category', 'Tax to GDP', 'Commonwealth', 'federal', ?
        )
        """,
        (doc_id,),
    )
    nid2 = conn.execute("SELECT id FROM nodes WHERE canonical_key='fixture:tax_gdp'").fetchone()[0]
    conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type, accounting_basis,
            estimate_status, amount_aud, amount_value, quantity, unit, currency, source_document_id,
            view_family, price_basis, quality_status, amount_granularity, source_locator_json,
            source_record_hash, retrieved_at
        ) VALUES (
            'fixture|ratio|2024-25', '2024-25', 'financial_year', 'tax_to_gdp_ratio', 'not_applicable',
            'actual', NULL, 24.5, 24.5, 'percent', 'NA', ?,
            'ratios', 'not_applicable', 'ok', 'ratio', '{}',
            'fixturehash2', '2026-01-01T00:00:00Z'
        )
        """,
        (doc_id,),
    )
    rid = conn.execute("SELECT id FROM facts WHERE fact_key='fixture|ratio|2024-25'").fetchone()[0]
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
        (rid, nid2),
    )
    conn.commit()
    conn.close()
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
