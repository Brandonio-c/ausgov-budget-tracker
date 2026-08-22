"""Regression test for a P0 defect: resolve_related_parent_node_id() used
its own narrow, 4-entry hardcoded alias dict instead of consulting the
already-correct declarative crosswalk
(config/breakdowns/crosswalks/cofog_to_budget_function.yaml), so budget
functions requiring an APPROXIMATE COFOG mapping - Social security and
welfare, Recreation and culture, Other economic affairs, Transport and
communication - never inherited their Statement 6/PBS related_breakdown
data, while functions with an EXACT (identically-named) mapping did.
Confirmed live against the running production backend before the fix:
these 4 functions returned 0 related children while Health/Education/
Defence/General public services returned real depth.

The fix replaces the hardcoded dict with `_budget_to_abs_purpose()`, a
cached reverse-index built from the real crosswalk YAML."""

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
    _budget_to_abs_purpose,
    resolve_related_parent_node_id,
)


def test_crosswalk_resolves_every_previously_broken_budget_function():
    """Direct proof against the real config file, not a mock - the exact
    class of regression that hardcoding a narrow alias list caused."""
    mapping = _budget_to_abs_purpose()
    assert mapping["social security and welfare"] == "Social protection"
    assert mapping["recreation and culture"] == "Recreation, culture and religion"
    assert mapping["other economic affairs"] == "Economic affairs"
    assert mapping["transport and communication"] == "Transport"


def test_crosswalk_still_resolves_the_originally_working_exact_matches():
    mapping = _budget_to_abs_purpose()
    assert mapping["health"] == "Health"
    assert mapping["education"] == "Education"
    assert mapping["defence"] == "Defence"
    assert mapping["general public services"] == "General public services"


def test_exact_quality_wins_over_a_competing_approx_mapping():
    """"Environmental protection" maps approximately onto "Housing and
    community amenities", which also has its own exact self-mapping - the
    exact one must win, or the resolver would attach the wrong ABS
    purpose's related data under the Housing budget function."""
    mapping = _budget_to_abs_purpose()
    assert mapping["housing and community amenities"] == "Housing and community amenities"


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "cofog_crosswalk_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    doc_id = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('abs_gfs_commonwealth_130', 'Test', 'Test', 'Commonwealth', 'federal', 'test')
        """
    ).lastrowid

    def add_purpose_node(name: str) -> int:
        return conn.execute(
            """
            INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
            VALUES (?, 'category', ?, 'Commonwealth', 'federal', ?)
            """,
            (f"abs_gfs|node|{name}", name, doc_id),
        ).lastrowid

    def add_related_child(parent_id: int, name: str) -> None:
        child_id = conn.execute(
            """
            INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
            VALUES (?, 'category', ?, 'Commonwealth', 'federal', ?)
            """,
            (f"related|node|{parent_id}|{name}", name, doc_id),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id, financial_year, priority, notes)
            VALUES (?, ?, 'related_breakdown', 'cofog_to_budget_function', '2025-26', 0, 'test|approx')
            """,
            (parent_id, child_id),
        )

    social_protection = add_purpose_node("Social protection")
    add_related_child(social_protection, "Statement 6: Social Services")

    conn.commit()
    return conn


def test_social_security_and_welfare_now_resolves_to_social_protection_related_data(fixture_db):
    """The exact P0 scenario: a budget-function node named "Social security
    and welfare" must resolve to the "Social protection" node's
    related_breakdown children, not return None."""
    nid = resolve_related_parent_node_id(fixture_db, "Social security and welfare", None)
    assert nid is not None
    row = fixture_db.execute("SELECT name FROM nodes WHERE id = ?", (nid,)).fetchone()
    assert row["name"] == "Social protection"


def test_unmapped_name_falls_through_unchanged(fixture_db):
    """A name with no crosswalk entry must not be silently coerced into
    matching an unrelated purpose."""
    nid = resolve_related_parent_node_id(fixture_db, "Some Unrelated Function", None)
    assert nid is None
