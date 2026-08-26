"""Tests for the federal_pbs_programs_all -> Statement 6 crosswalk.

Two layers:
  - Pure classification logic (classify_program/parse_portfolio_and_label)
    against the real crosswalk YAML - no database needed, covers the
    representative portfolios named in the milestone plus the ambiguous
    and component-depth cases.
  - Edge-loading behaviour (idempotency, no duplicates, no orphans, no
    cycles, no cross-year edges, no additive PBS-into-GFS edges, ambiguous
    stays unpublished, citation/root-total preservation) against a small
    synthetic fixture database built fresh per test, not the real
    data/facts.db.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from pbs_s6_crosswalk import (  # noqa: E402
    CROSSWALK_ID,
    classify_program,
    live_pbs_nodes,
    load_crosswalk,
    load_edges,
    parse_portfolio_and_label,
)
from schema_migrate import migrate  # noqa: E402


@pytest.fixture(scope="module")
def crosswalk():
    return load_crosswalk()


def test_crosswalk_schema_has_required_top_level_keys(crosswalk):
    assert crosswalk["id"] == "pbs_programs_all_under_s6"
    assert crosswalk["edge_kind"] == "related_breakdown"
    assert isinstance(crosswalk["portfolio_defaults"], list)
    assert isinstance(crosswalk["program_label_overrides"], list)
    assert len(crosswalk["portfolio_defaults"]) > 0


def test_crosswalk_entries_have_required_fields(crosswalk):
    for entry in crosswalk["portfolio_defaults"]:
        assert entry["pbs_portfolio"]
        assert entry["status"] in ("mapped", "ambiguous")
        if entry["status"] == "mapped":
            assert entry.get("statement6_function")
            assert entry.get("confidence") in ("high", "medium", "low")
            assert entry.get("evidence")
        else:
            assert entry.get("reason"), "ambiguous entries must state a reason"
    for entry in crosswalk["program_label_overrides"]:
        assert entry["pbs_portfolio"]
        assert entry["label_contains"]
        assert entry["statement6_function"]
        assert entry["confidence"] in ("high", "medium", "low")


def test_parse_portfolio_and_label():
    assert parse_portfolio_and_label("Social Services / Program 1.2") == (
        "Social Services",
        "Program 1.2",
    )
    assert parse_portfolio_and_label("NoSlash") == ("NoSlash", "")


@pytest.mark.parametrize(
    "portfolio,label,expected_function",
    [
        ("Social Services", "Program 1.6 – Working Age Payments Administered expenses", "Social security and welfare"),
        ("Defence", "Program 1.1 Air Combat Capability Total funded expenditure", "Defence"),
        ("Education", "Program 2.1 Higher Education Loan Program", "Education"),
    ],
)
def test_representative_portfolios_map_to_expected_function(
    crosswalk, portfolio, label, expected_function
):
    decision = classify_program(portfolio, label, crosswalk)
    assert decision["status"] == "mapped"
    assert decision["statement6_function"] == expected_function


def test_health_portfolio_defaults_to_health_function(crosswalk):
    decision = classify_program(
        "Health Disability and Ageing", "Program 1.1 Medical Benefits Schedule", crosswalk
    )
    assert decision["status"] == "mapped"
    assert decision["statement6_function"] == "Health"


def test_ndia_program_overrides_health_portfolio_to_social_security(crosswalk):
    """NDIA is legally inside the Health Disability and Ageing portfolio,
    but Statement 6 classifies it under Social security and welfare - the
    program_label_override must win over the portfolio's Health default."""
    decision = classify_program(
        "Health Disability and Ageing",
        "Program 1.2: National Disability Insurance Agency and General Supports",
        crosswalk,
    )
    assert decision["status"] == "mapped"
    assert decision["match_source"] == "program_label_override"
    assert decision["statement6_function"] == "Social security and welfare"
    assert "National Disability Insurance Scheme" in decision["statement6_component"]


def test_dva_pharmaceutical_program_routes_to_health_not_welfare(crosswalk):
    """One program with real component-level depth: DVA's pharmaceutical
    benefits program is an exception to DVA's own welfare-function
    default, and resolves down to a specific component node."""
    decision = classify_program(
        "Veterans' Affairs", "Program 2.3: Veterans' Pharmaceuticals Benefits Administered", crosswalk
    )
    assert decision["status"] == "mapped"
    assert decision["match_source"] == "program_label_override"
    assert decision["statement6_function"] == "Health"
    assert decision["statement6_component"] == (
        "Health / Pharmaceutical benefits and services / Veterans' pharmaceutical benefits"
    )


def test_dva_non_health_program_falls_back_to_portfolio_default(crosswalk):
    decision = classify_program(
        "Veterans' Affairs", "Program 1.1 Income Support Payments", crosswalk
    )
    assert decision["status"] == "mapped"
    assert decision["match_source"] == "portfolio_default"
    assert decision["statement6_function"] == "Social security and welfare"


def test_ambiguous_cross_function_portfolio_stays_unmapped(crosswalk):
    """Attorney-General's is deliberately declared ambiguous (spans courts,
    emergency management, human rights, integrity/security with no single
    dominant Statement 6 function) - it must never silently default to a
    guessed function."""
    decision = classify_program(
        "Attorney-General's", "Program 1.1 Federal Circuit and Family Court", crosswalk
    )
    assert decision["status"] == "ambiguous"
    assert decision["statement6_function"] is None
    assert decision["reason"]


def test_portfolio_not_in_crosswalk_is_unmapped_not_guessed(crosswalk):
    decision = classify_program("Some Future New Department", "Program X", crosswalk)
    assert decision["status"] == "unmapped"
    assert decision["reason"] == "portfolio_not_in_crosswalk"


# --- Fixture DB for edge-loading behaviour --------------------------------


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "crosswalk_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    def add_source_document(source_key: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
            VALUES (?, 'Test', 'Test', 'Commonwealth', 'federal', 'test')
            """,
            (source_key,),
        )
        return int(cur.lastrowid)

    def add_node(source_document_id: int, name: str, canonical_key: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
            VALUES (?, 'category', ?, 'Commonwealth', 'federal', ?, '{}')
            """,
            (canonical_key, name, source_document_id),
        )
        return int(cur.lastrowid)

    def add_fact(source_document_id: int, node_id: int, fy: str, amount: float, locator: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_granularity, measure_type,
                accounting_basis, estimate_status, amount_aud, source_document_id,
                source_locator_json, retrieved_at
            ) VALUES (?, ?, 'financial_year', 'budget_estimate', 'appropriation', 'budget', ?, ?, ?, '2026-01-01T00:00:00')
            """,
            (
                f"test|{node_id}|{fy}",
                fy,
                amount,
                source_document_id,
                f'{{"locator": "{locator}", "cached_copy_path": "test.pdf"}}',
            ),
        )
        fact_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
            (fact_id, node_id),
        )
        return fact_id

    s6_doc = add_source_document("federal_budget_statement_6_a61")
    pbs_doc = add_source_document("federal_pbs_programs_all")

    add_node(s6_doc, "Health", "federal_budget_statement_6_a61|node|Health")
    add_node(s6_doc, "Social security and welfare", "federal_budget_statement_6_a61|node|Social security and welfare")

    pbs_health_program = add_node(
        pbs_doc,
        "Health Disability and Ageing / Program 1.1 Medical Benefits Schedule",
        "federal_pbs_programs_all|node|Health Disability and Ageing / Program 1.1 Medical Benefits Schedule",
    )
    add_fact(pbs_doc, pbs_health_program, "2024-25", 1_000_000, "pdf:health.pdf|page:1")
    add_fact(pbs_doc, pbs_health_program, "2025-26", 1_100_000, "pdf:health.pdf|page:1")

    pbs_ambiguous_program = add_node(
        pbs_doc,
        "Attorney-General's / Program 1.1 Federal Circuit and Family Court",
        "federal_pbs_programs_all|node|Attorney-General's / Program 1.1 Federal Circuit and Family Court",
    )
    add_fact(pbs_doc, pbs_ambiguous_program, "2024-25", 500_000, "pdf:ag.pdf|page:1")

    # A label with a literal "/" as ordinary English phrasing, not a real
    # hierarchy separator (real example: "Retained surplus /
    # (accumulated deficit)") - regression case for the
    # link_same_group_from_paths stabilization loop in load_edges().
    pbs_slash_in_label = add_node(
        pbs_doc,
        "Social Services / Net cash from / (used by) investing activities",
        "federal_pbs_programs_all|node|Social Services / Net cash from / (used by) investing activities",
    )
    add_fact(pbs_doc, pbs_slash_in_label, "2024-25", 200_000, "pdf:ss.pdf|page:1")

    conn.commit()
    conn.close()
    return db_path


def test_edge_load_is_idempotent(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()

    first = load_edges(conn, crosswalk)
    conn.commit()
    count_after_first = conn.execute("SELECT COUNT(*) FROM breakdown_edges").fetchone()[0]

    second = load_edges(conn, crosswalk)
    conn.commit()
    count_after_second = conn.execute("SELECT COUNT(*) FROM breakdown_edges").fetchone()[0]

    assert count_after_first > 0
    assert count_after_second == count_after_first
    assert second["related_breakdown_inserted"] == 0
    assert first["related_breakdown_inserted"] > 0
    conn.close()


def test_single_load_call_fully_stabilizes_multi_separator_labels(fixture_db):
    """A single load_edges() call must be idempotent on its own - even for
    a label containing a literal "/" as ordinary phrasing (creating a
    spurious intermediate parent that link_same_group_from_paths only
    fully resolves over multiple internal passes). Regression for a real
    bug found against production data (12 new same_group edges appeared on
    a second load before this fix)."""
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()

    load_edges(conn, crosswalk)
    conn.commit()
    count_after_one_call = conn.execute("SELECT COUNT(*) FROM breakdown_edges").fetchone()[0]

    load_edges(conn, crosswalk)
    conn.commit()
    count_after_two_calls = conn.execute("SELECT COUNT(*) FROM breakdown_edges").fetchone()[0]

    assert count_after_one_call == count_after_two_calls
    conn.close()


def test_no_duplicate_edges(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    load_edges(conn, crosswalk)
    conn.commit()
    dupes = conn.execute(
        """
        SELECT parent_node_id, child_node_id, edge_kind, COUNT(*) c
        FROM breakdown_edges
        GROUP BY parent_node_id, child_node_id, edge_kind, financial_year, crosswalk_id
        HAVING c > 1
        """
    ).fetchall()
    assert dupes == []
    conn.close()


def test_no_orphan_endpoints(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    orphans = conn.execute(
        """
        SELECT COUNT(*) FROM breakdown_edges e
        LEFT JOIN nodes p ON p.id = e.parent_node_id
        LEFT JOIN nodes c ON c.id = e.child_node_id
        WHERE p.id IS NULL OR c.id IS NULL
        """
    ).fetchone()[0]
    assert orphans == 0
    conn.close()


def test_no_two_node_cycles(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    pairs = conn.execute("SELECT parent_node_id, child_node_id FROM breakdown_edges").fetchall()
    edge_set = {(p, c) for p, c in pairs}
    cycles = [(p, c) for (p, c) in edge_set if (c, p) in edge_set]
    assert cycles == []
    conn.close()


def test_all_crosswalk_edges_are_year_agnostic_not_contaminated(fixture_db):
    """financial_year=NULL on every edge this crosswalk creates - per-year
    resolution happens at render time (fact_for_node_year), so the edge
    itself never pins a specific (and potentially wrong) year."""
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    rows = conn.execute(
        "SELECT financial_year FROM breakdown_edges WHERE crosswalk_id = ?", (CROSSWALK_ID,)
    ).fetchall()
    assert rows, "expected at least one crosswalk edge in the fixture"
    assert all(r[0] is None for r in rows)
    conn.close()


def test_no_additive_edge_from_pbs_into_s6(fixture_db):
    """Every edge whose parent is a Statement 6 node and child is a PBS
    node must be related_breakdown, never same_group - same_group is only
    used internally within the PBS family (portfolio folder -> program)."""
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    bad = conn.execute(
        """
        SELECT COUNT(*) FROM breakdown_edges e
        JOIN nodes p ON p.id = e.parent_node_id
        JOIN source_documents pd ON pd.id = p.source_document_id
        JOIN nodes c ON c.id = e.child_node_id
        JOIN source_documents cd ON cd.id = c.source_document_id
        WHERE pd.source_key LIKE 'federal_budget_statement_6%'
          AND cd.source_key = 'federal_pbs_programs_all'
          AND e.edge_kind != 'related_breakdown'
        """
    ).fetchone()[0]
    assert bad == 0
    conn.close()


def test_related_breakdown_child_nodes_have_a_direct_fact(fixture_db):
    """Regression test for a real bug found via the live dashboard API:
    the backend's fact_for_node_year() requires the related_breakdown
    CHILD node to carry a fact directly on itself - a fact-less
    aggregation/folder node as the child is silently invisible at render
    time (build_related_subtree() finds the edge but drops it because
    fact_for_node_year() returns None for that node). Every edge this
    crosswalk creates must attach to a real, fact-bearing PBS program
    node, never a folder."""
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    childless = conn.execute(
        """
        SELECT COUNT(*) FROM breakdown_edges e
        WHERE e.crosswalk_id = ?
          AND NOT EXISTS (
              SELECT 1 FROM fact_nodes fn WHERE fn.node_id = e.child_node_id
          )
        """,
        (CROSSWALK_ID,),
    ).fetchone()[0]
    assert childless == 0
    conn.close()


def test_ambiguous_portfolio_gets_zero_related_edges(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    ag_node = conn.execute(
        "SELECT id FROM nodes WHERE name = ?",
        ("Attorney-General's / Program 1.1 Federal Circuit and Family Court",),
    ).fetchone()
    assert ag_node is not None
    edges_to_ag_program = conn.execute(
        "SELECT COUNT(*) FROM breakdown_edges WHERE child_node_id = ? AND edge_kind = 'related_breakdown'",
        (ag_node[0],),
    ).fetchone()[0]
    assert edges_to_ag_program == 0
    conn.close()


def test_citation_preserved_after_edge_load(fixture_db):
    """Loading edges must never touch the facts table - citations are
    exactly as they were before."""
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    before = conn.execute("SELECT id, source_locator_json FROM facts ORDER BY id").fetchall()
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    after = conn.execute("SELECT id, source_locator_json FROM facts ORDER BY id").fetchall()
    assert before == after
    conn.close()


def test_root_totals_unchanged_after_edge_load(fixture_db):
    """Loading edges must never modify amount_aud on any fact - the
    authoritative totals a dashboard tree sums are untouched."""
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    before_total = conn.execute("SELECT SUM(amount_aud) FROM facts").fetchone()[0]
    crosswalk = load_crosswalk()
    load_edges(conn, crosswalk)
    conn.commit()
    after_total = conn.execute("SELECT SUM(amount_aud) FROM facts").fetchone()[0]
    assert before_total == after_total
    conn.close()


def test_live_pbs_nodes_excludes_orphans(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    conn.execute("PRAGMA foreign_keys = ON")
    # Add an orphaned PBS node (no fact_nodes) to prove it's excluded.
    doc = conn.execute(
        "SELECT id FROM source_documents WHERE source_key = 'federal_pbs_programs_all'"
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
        VALUES ('orphan|node|x', 'category', 'Stale Portfolio / Old Program', 'Commonwealth', 'federal', ?, '{}')
        """,
        (doc,),
    )
    conn.commit()
    nodes = live_pbs_nodes(conn)
    names = {n["name"] for n in nodes}
    assert "Stale Portfolio / Old Program" not in names
    conn.close()
