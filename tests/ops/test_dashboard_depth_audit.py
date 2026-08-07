from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "ops" / "dashboard_depth_audit.py"
SPEC = importlib.util.spec_from_file_location("dashboard_depth_audit", MODULE_PATH)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def _metadata_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE source_documents (
            id INTEGER PRIMARY KEY,
            source_key TEXT,
            source_family TEXT,
            landing_url TEXT,
            canonical_resource_url TEXT
        );
        CREATE TABLE measure_definitions (
            measure_type TEXT PRIMARY KEY,
            compatibility_group TEXT
        );
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            financial_year TEXT,
            accounting_basis TEXT,
            estimate_status TEXT,
            unit TEXT,
            source_locator_json TEXT,
            source_document_id INTEGER,
            measure_type TEXT
        );
        INSERT INTO source_documents VALUES (1, 'base', 'abs_gfs', 'https://example.test', NULL);
        INSERT INTO source_documents VALUES (2, 'related', 'fbo', 'https://example.test', NULL);
        INSERT INTO measure_definitions VALUES ('expense', 'actual_expense');
        INSERT INTO facts VALUES (1, '2023-24', 'gfs', 'actual', 'AUD', '{"locator":"cell:A1"}', 1, 'expense');
        INSERT INTO facts VALUES (2, '2023-24', 'accrual', 'audited_actual', 'AUD', '{"locator":"page:1"}', 2, 'expense');
        """
    )
    return conn


def test_signature_separates_additive_related_and_navigation_depth() -> None:
    conn = _metadata_db()
    tree = {
        "name": "federal — 2023-24",
        "value": 100.0,
        "unit": "AUD",
        "children": [
            {
                "name": "Commonwealth",
                "value": 100.0,
                "children": [
                    {"name": "Health", "value": 100.0, "id": 1},
                    {
                        "name": "FBO Appendix A — related",
                        "value": 0.0,
                        "breakdown": {"kind": "related_breakdown"},
                        "children": [
                            {
                                "name": "Health",
                                "value": 99.0,
                                "id": 2,
                                "breakdown": {"kind": "related_breakdown"},
                            }
                        ],
                    },
                ],
            }
        ],
    }
    spec = {"label": "fixture", "mode": "actuals", "level": "federal", "year": "2023-24"}
    signature, failures = audit.projection_signature(tree, spec, conn)
    conn.close()

    assert failures == []
    assert signature["max_additive_depth"] == 1
    assert signature["max_related_depth"] == 1
    assert signature["branch_counts"] == {"additive": 1, "related": 2}
    assert signature["citation"] == {"fact_leaves": 2, "complete": 2, "missing": 0}


def test_signature_rejects_future_year_fallback() -> None:
    conn = _metadata_db()
    tree = {
        "name": "root",
        "value": 100,
        "children": [
            {
                "name": "Future child",
                "value": 100,
                "id": 2,
                "breakdown": {
                    "kind": "related_breakdown",
                    "requested_financial_year": "2022-23",
                    "fact_financial_year": "2023-24",
                    "is_year_fallback": True,
                    "fallback_reason": "bad fixture",
                },
            }
        ],
    }
    spec = {"label": "fixture", "mode": "actuals", "level": "federal", "year": "2022-23"}
    _, failures = audit.projection_signature(tree, spec, conn)
    conn.close()
    assert {failure["kind"] for failure in failures} == {"future_year_fallback"}


def test_graph_integrity_is_null_safe_and_detects_cycles() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE breakdown_edges (
            parent_node_id INTEGER,
            child_node_id INTEGER,
            edge_kind TEXT,
            financial_year TEXT,
            crosswalk_id TEXT
        )
        """
    )
    conn.executemany(
        "INSERT INTO breakdown_edges VALUES (?, ?, ?, ?, ?)",
        [
            (1, 2, "same_group", None, None),
            (1, 2, "same_group", None, None),
            (2, 1, "same_group", None, "cycle"),
        ],
    )
    summary, failures = audit.graph_integrity(conn)
    conn.close()
    assert summary["duplicate_semantic_edges"] == 1
    assert summary["cycles"] == 1
    assert {failure["kind"] for failure in failures} == {
        "duplicate_semantic_edge",
        "breakdown_cycle",
    }


@pytest.mark.full_data
def test_current_projection_matches_reviewed_golden_fixture() -> None:
    expected = json.loads(audit.FIXTURE_PATH.read_text(encoding="utf-8"))
    current = audit._fixture_payload(audit.run_audit(audit.DB_PATH))
    assert current == expected
