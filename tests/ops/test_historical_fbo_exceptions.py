from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DB = REPO_ROOT / "data" / "facts.db"


@pytest.mark.full_data
def test_unmapped_fbo_functions_are_explicit_and_not_silently_wired() -> None:
    expected = {
        "Agriculture, forestry and fishing",
        "Other purposes",
        "labour and employment affairs",
    }
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    related_children = {
        str(row[0])
        for row in conn.execute(
            """
            SELECT c.name
            FROM breakdown_edges e
            JOIN nodes c ON c.id = e.child_node_id
            JOIN source_documents d ON d.id = c.source_document_id
            WHERE d.source_key = 'federal_budget_archive_function_series'
              AND e.edge_kind = 'related_breakdown'
            """
        )
    }
    conn.close()
    assert expected.isdisjoint(related_children)
