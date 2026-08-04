"""Regression tests for Task 4 of the semantic-defect milestone: every node
beneath a related_breakdown attach point must self-declare non-additive,
at any depth, and the graph must never let a state/local additive path
silently absorb a federal fact as if it were additive.

Root cause (confirmed against the real API, see
ops/reports/dashboard-semantic-defect-root-cause-*.md): build_related_subtree()
only stamped `breakdown.kind` on nodes that happened to have their own
year fallback, and only at one nesting level - every other related child
(and every same_group descendant nested beneath it) was emitted with
breakdown=None, indistinguishable from a real additive fact once
serialized on its own (each node is independently serialized, including
on a standalone /item/{fact_id}/children drill-down with no parent to
inherit a tag from). This is the exact mechanism behind children reading
>100% of an unrelated parent's amount and federal facts appearing under
a local-government additive path with no non-additive signal at all.

Fixture database mirrors the real shape found in data/facts.db: a local
QLD "Economic affairs" node and a local NSW "Economic affairs" node, each
with their OWN related_breakdown edges to a federal Statement 6 node
("Immigration") that itself has a same_group child two levels deep - plus
a Health->PBS program related_breakdown edge to prove the existing
PBS -> Statement 6 crosswalk still works after the fix.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from schema_migrate import migrate  # noqa: E402

from backend.breakdown_graph import (  # noqa: E402
    attach_related_to_tree,
    build_related_subtree,
    primary_node_id,
)


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "breakdown_graph_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    def add_source_document(source_key: str, level: str, jurisdiction: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
            VALUES (?, 'Test', 'Test', ?, ?, 'test')
            """,
            (source_key, jurisdiction, level),
        )
        return int(cur.lastrowid)

    def add_node(source_document_id: int, name: str, canonical_key: str, level: str, jurisdiction: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
            VALUES (?, 'category', ?, ?, ?, ?, '{}')
            """,
            (canonical_key, name, jurisdiction, level, source_document_id),
        )
        return int(cur.lastrowid)

    def add_fact(
        source_document_id: int,
        node_id: int,
        fy: str,
        amount: float,
        measure_type: str = "gfs_expense",
        estimate_status: str = "actual",
    ) -> int:
        cur = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_granularity, measure_type,
                accounting_basis, estimate_status, amount_aud, source_document_id,
                source_locator_json, retrieved_at
            ) VALUES (?, ?, 'financial_year', ?, 'gfs', ?, ?, ?, '{"locator": "pdf:test.pdf|page:1", "cached_copy_path": "test.pdf"}', '2026-01-01T00:00:00')
            """,
            (f"test|{node_id}|{fy}|{measure_type}", fy, measure_type, estimate_status, amount, source_document_id),
        )
        fact_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
            (fact_id, node_id),
        )
        return fact_id

    def add_related_edge(parent_node_id: int, child_node_id: int, fy: str | None, notes: str, crosswalk_id: str | None = None) -> None:
        conn.execute(
            """
            INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id, financial_year, priority, notes)
            VALUES (?, ?, 'related_breakdown', ?, ?, 0, ?)
            """,
            (parent_node_id, child_node_id, crosswalk_id, fy, notes),
        )

    def add_same_group_edge(parent_node_id: int, child_node_id: int) -> None:
        conn.execute(
            """
            INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id, financial_year, priority, notes)
            VALUES (?, ?, 'same_group', NULL, NULL, 0, NULL)
            """,
            (parent_node_id, child_node_id),
        )

    s6_doc = add_source_document("federal_budget_statement_6_a61", "federal", "Commonwealth")
    local_qld_doc = add_source_document("abs_gfs_local_qld_333", "local", "QLD")
    local_nsw_doc = add_source_document("abs_gfs_local_nsw_331", "local", "NSW")
    pbs_doc = add_source_document("federal_pbs_programs_all", "federal", "Commonwealth")

    # Federal Statement 6 "Immigration" with its own nested same_group child
    # two levels deep (mirrors Statement 6 -> component -> PBS cascade).
    s6_immigration = add_node(s6_doc, "Immigration", "s6|node|Immigration", "federal", "Commonwealth")
    s6_immigration_fact = add_fact(s6_doc, s6_immigration, "2024-25", 3_758_000_000)
    s6_immigration_component = add_node(
        s6_doc, "Immigration / Visa processing", "s6|node|Immigration / Visa processing", "federal", "Commonwealth"
    )
    add_fact(s6_doc, s6_immigration_component, "2024-25", 1_200_000_000)
    add_same_group_edge(s6_immigration, s6_immigration_component)

    # Federal Statement 6 "Health" with a related_breakdown edge directly to
    # a PBS program node, same shape as the real pbs_programs_all_under_s6
    # crosswalk from the prior milestone.
    s6_health = add_node(s6_doc, "Health", "s6|node|Health", "federal", "Commonwealth")
    s6_health_fact = add_fact(s6_doc, s6_health, "2024-25", 200_000_000_000)
    pbs_health_program = add_node(
        pbs_doc, "Health Disability and Ageing / Program 1.1", "pbs|node|Program 1.1", "federal", "Commonwealth"
    )
    add_fact(pbs_doc, pbs_health_program, "2024-25", 5_000_000_000)
    add_related_edge(s6_health, pbs_health_program, None, "Health→Program 1.1|exact", crosswalk_id="pbs_programs_all_under_s6")

    # Local QLD and local NSW each have their OWN "Economic affairs" node
    # with a related_breakdown edge to the SAME federal Immigration node -
    # exactly the real-world shape found in data/facts.db.
    local_qld_econ = add_node(local_qld_doc, "Economic affairs", "local_qld|node|Economic affairs", "local", "QLD")
    local_qld_econ_fact = add_fact(local_qld_doc, local_qld_econ, "2024-25", 906_000_000)
    add_related_edge(local_qld_econ, s6_immigration, None, "Economic affairs→Immigration|approx")

    local_nsw_econ = add_node(local_nsw_doc, "Economic affairs", "local_nsw|node|Economic affairs", "local", "NSW")
    local_nsw_econ_fact = add_fact(local_nsw_doc, local_nsw_econ, "2024-25", 1_050_000_000)
    add_related_edge(local_nsw_econ, s6_immigration, None, "Economic affairs→Immigration|approx")

    # Task 7 regression fixture: a related node with an EXACT match at its
    # own level, whose nested same_group child only has data for an
    # *earlier* year - reproduces the real bug found against production
    # (fact_id 257713 "Defence"): the top node's own fallback_reason must
    # not claim "exact_year_match" for the whole subtree just because ITS
    # OWN fact matched exactly, when a descendant genuinely needed a
    # fallback.
    s6_defence = add_node(s6_doc, "Defence", "s6|node|Defence", "federal", "Commonwealth")
    add_fact(s6_doc, s6_defence, "2024-25", 50_000_000_000)
    defence_component = add_node(
        s6_doc, "Defence / Contracts", "s6|node|Defence Contracts", "federal", "Commonwealth"
    )
    add_fact(s6_doc, defence_component, "2019-20", 30_000_000_000)
    add_same_group_edge(s6_defence, defence_component)
    local_qld_defence = add_node(local_qld_doc, "Defence", "local_qld|node|Defence", "local", "QLD")
    local_qld_defence_fact = add_fact(local_qld_doc, local_qld_defence, "2024-25", 500_000)
    add_related_edge(local_qld_defence, s6_defence, None, "Defence→Defence|exact")

    conn.commit()
    conn.close()

    return {
        "path": db_path,
        "s6_immigration_fact": s6_immigration_fact,
        "s6_health_fact": s6_health_fact,
        "local_qld_econ_fact": local_qld_econ_fact,
        "local_nsw_econ_fact": local_nsw_econ_fact,
        "local_qld_defence_fact": local_qld_defence_fact,
    }


def _conn(fixture_db):
    conn = sqlite3.connect(str(fixture_db["path"]))
    conn.row_factory = sqlite3.Row
    return conn


def _walk_all(node):
    yield node
    for child in (node.get("children") or {}).values():
        yield from _walk_all(child)


def test_related_child_and_nested_same_group_descendant_are_both_tagged(fixture_db):
    """Regression for the exact bug: a related child with no year fallback
    of its own, and a same_group grandchild nested beneath it, must both
    carry breakdown.kind == 'related_breakdown' and preserve_amount."""
    conn = _conn(fixture_db)
    nid = primary_node_id(conn, fixture_db["local_qld_econ_fact"])
    related_list, breakdown = build_related_subtree(conn, nid, "2024-25")
    conn.close()

    assert breakdown["kind"] == "related_breakdown"
    assert related_list, "expected at least one related child (Immigration)"
    immigration = next(item["node"] for item in related_list if item["name"] == "Immigration")

    assert immigration["breakdown"]["kind"] == "related_breakdown"
    assert immigration["preserve_amount"] is True

    nested = immigration["children"]
    assert nested, "expected the nested same_group component to be present"
    component = next(iter(nested.values()))
    assert component["breakdown"]["kind"] == "related_breakdown"
    assert component["preserve_amount"] is True


def test_local_additive_leaf_never_yields_an_untagged_federal_descendant(fixture_db):
    """Every single node produced by attaching related content to a local
    leaf must be self-tagged non-additive - none may be emitted with
    breakdown=None, which would make it indistinguishable from a real
    additive fact of the local jurisdiction."""
    conn = _conn(fixture_db)
    tree = {
        "children": {
            "Economic affairs": {
                "children": {},
                "amount": 906_000_000.0,
                "fact_id": fixture_db["local_qld_econ_fact"],
            }
        }
    }
    attach_related_to_tree(conn, tree, "2024-25")
    conn.close()

    econ = tree["children"]["Economic affairs"]
    all_nodes = list(_walk_all(econ))
    assert len(all_nodes) > 1, "expected related content to have been attached"
    for node in all_nodes[1:]:  # skip the leaf itself, already asserted elsewhere
        bd = node.get("breakdown")
        assert bd is not None, f"node missing breakdown tag: {node}"
        assert bd["kind"] == "related_breakdown"
        assert node.get("preserve_amount") is True


def test_two_jurisdictions_each_resolve_their_own_related_edges_not_each_others(fixture_db):
    """QLD's and NSW's local 'Economic affairs' nodes each have their own
    related_breakdown edge rows pointing at the same federal Immigration
    node. Resolution must go through each fact's own primary_node_id, so
    QLD's related content is never resolved via NSW's edge row or vice
    versa - both must independently reach the same federal reference
    figure without any risk of cross-jurisdiction node aliasing."""
    conn = _conn(fixture_db)
    qld_nid = primary_node_id(conn, fixture_db["local_qld_econ_fact"])
    nsw_nid = primary_node_id(conn, fixture_db["local_nsw_econ_fact"])
    assert qld_nid != nsw_nid

    qld_related, _ = build_related_subtree(conn, qld_nid, "2024-25")
    nsw_related, _ = build_related_subtree(conn, nsw_nid, "2024-25")
    conn.close()

    assert {item["name"] for item in qld_related} == {"Immigration"}
    assert {item["name"] for item in nsw_related} == {"Immigration"}
    # Both correctly reach the same federal reference fact (by design - a
    # national figure has no state/local breakdown) but via their own
    # edge, not by falling through to an unscoped global search.
    assert qld_related[0]["node"]["fact_id"] == fixture_db["s6_immigration_fact"]
    assert nsw_related[0]["node"]["fact_id"] == fixture_db["s6_immigration_fact"]


def test_related_pbs_program_under_statement6_still_reachable_and_preserves_amount(fixture_db):
    """Regression for the existing PBS -> Statement 6 crosswalk (prior
    milestone): a related_breakdown edge attached directly to a PBS
    program node from a Statement 6 parent must remain reachable after
    this fix, stay tagged non-additive, and the Statement 6 parent's own
    amount must be preserved (not re-summed from the PBS child)."""
    conn = _conn(fixture_db)
    nid = primary_node_id(conn, fixture_db["s6_health_fact"])
    related_list, breakdown = build_related_subtree(conn, nid, "2024-25")
    conn.close()

    assert breakdown["kind"] == "related_breakdown"
    assert len(related_list) == 1
    pbs_node = related_list[0]["node"]
    assert pbs_node["fact_id"] is not None
    assert pbs_node["preserve_amount"] is True
    assert pbs_node["breakdown"]["kind"] == "related_breakdown"


def test_related_nodes_are_excluded_from_a_naive_additive_reconciliation(fixture_db):
    """A caller reconciling a parent's additive children (summing only
    nodes NOT tagged related_breakdown) must exclude every node in this
    subtree - proving the tagging fix is sufficient for a consumer to
    correctly separate additive from non-additive content without any
    other signal."""
    conn = _conn(fixture_db)
    nid = primary_node_id(conn, fixture_db["local_qld_econ_fact"])
    related_list, _ = build_related_subtree(conn, nid, "2024-25")
    conn.close()

    for item in related_list:
        for node in _walk_all(item["node"]):
            bd = node.get("breakdown") or {}
            assert bd.get("kind") == "related_breakdown"

    additive_children = [
        item["node"]
        for item in related_list
        if (item["node"].get("breakdown") or {}).get("kind") != "related_breakdown"
    ]
    assert additive_children == []


def test_exact_match_parent_reports_nested_mismatch_not_its_own_reason(fixture_db):
    """Regression for a real bug found while implementing Task 7: a related
    node whose OWN fact matches the requested year exactly must not report
    fallback_reason="exact_year_match" for the whole subtree when a nested
    same_group descendant needed a genuine earlier-year fallback - that
    would misrepresent where the mismatch actually lives. The top node
    reports "nested_child_year_mismatch"; the descendant itself reports its
    own real fallback reason."""
    conn = _conn(fixture_db)
    nid = primary_node_id(conn, fixture_db["local_qld_defence_fact"])
    related_list, _ = build_related_subtree(conn, nid, "2024-25")
    conn.close()

    defence_node = next(item["node"] for item in related_list if item["name"] == "Defence")
    bd = defence_node["breakdown"]
    assert bd["fallback_reason"] == "nested_child_year_mismatch"
    assert bd["is_year_fallback"] is True
    assert bd["fact_financial_year"] == "2019-20"

    nested = next(iter(defence_node["children"].values()))
    nested_bd = nested["breakdown"]
    assert nested_bd["fallback_reason"] in (
        "nearest_earlier_year_same_edition",
        "nearest_earlier_year_other_edition",
    )
    assert nested_bd["fact_financial_year"] == "2019-20"
