"""Regression: /item/{id}/children must trust a node's own published fact
amount, never silently recompute it as sum(children).

Found live: /item/{id}/children on "Recreation and culture / Arts and
cultural heritage" (federal_budget_statement_6_a61, FY2025-26, published
$2,329,000,000) returned $1,199,606,000 instead - the sum of its 13 nested
pbs_dss_bridge same_group children, which do not exhaustively partition it.
build_same_group_subtree() (breakdown_graph.py) never set preserve_amount,
so _to_tree_node()'s default ("no preserve_amount + has children -> sum
children") silently overrode the real fact amount. The main /tree endpoint
already gets this right via _build_tree_dict()'s own preserve_amount
marking (Loop 3); this is the same fix for this second, independent
tree-building path used only by /item/{id}/children.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

DB = REPO_ROOT / "data" / "facts.db"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FACTS_DB_PATH", str(DB))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = DB
    from backend.main import app

    return TestClient(app)


def _a61_fact_id(node_name: str, year: str) -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            SELECT f.id
            FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = 'federal_budget_statement_6_a61'
              AND n.name = ?
              AND f.financial_year = ?
            """,
            (node_name, year),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, f"no federal_budget_statement_6_a61 fact for {node_name}/{year}"
    return int(row[0])


@pytest.mark.full_data
def test_nested_same_group_child_reports_its_own_published_amount(
    client: TestClient,
) -> None:
    """"Recreation and culture" -> "Arts and cultural heritage" is a
    two-level same_group chain: querying the OUTER node's children must
    show the INNER node's own published $2.329B fact (federal_budget_
    statement_6_a61), never the sum of ITS OWN nested pbs_dss_bridge
    children ($1.1996B - a known-partial, non-exhaustive subset)."""
    inner_fact_id = _a61_fact_id(
        "Recreation and culture / Arts and cultural heritage", "2025-26"
    )
    outer_fact_id = _a61_fact_id("Recreation and culture", "2025-26")

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        published = conn.execute(
            "SELECT amount_aud FROM facts WHERE id = ?", (inner_fact_id,)
        ).fetchone()[0]
    finally:
        conn.close()

    r = client.get(f"/v2/dashboard/item/{outer_fact_id}/children", params={"year": "2025-26"})
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "same_group"

    inner = next(c for c in data["children"] if c["name"] == "Arts and cultural heritage")
    assert inner["value"] == pytest.approx(float(published))

    # Confirm this genuinely exercises the non-exhaustive-partition case the
    # bug depended on, not a fixture where children now happen to sum exactly.
    r2 = client.get(f"/v2/dashboard/item/{inner_fact_id}/children", params={"year": "2025-26"})
    assert r2.status_code == 200
    nested = r2.json()["children"]
    assert nested, "expected nested pbs_dss_bridge same_group children"
    assert sum(c["value"] for c in nested) != pytest.approx(float(published)), (
        "fixture drift: nested children now exactly sum to the parent - this "
        "test's premise (a partial partition) no longer demonstrates the bug"
    )
