"""Tests for the semantic dashboard/API traversal audit
(scripts/ops/dashboard_api_audit.py, Task 3 of the semantic-defect
milestone).

Exercises `_walk` directly against synthetic API-shaped node dicts and a
small fixture database (never the real data/facts.db), one test per
required failure bucket, plus a couple of "must NOT fire" checks proving
related_breakdown children are excluded from additive-only invariants.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import dashboard_api_audit as audit  # noqa: E402
from schema_migrate import migrate  # noqa: E402


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "audit_fixture.db"
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

    local_doc = add_source_document("local_government_actuals_2024_25", "local", "QLD")
    federal_doc = add_source_document("abs_gfs_commonwealth_2024_25", "federal", "Commonwealth")
    state_qld_doc = add_source_document("qld_state_actuals_2024_25", "state", "QLD")
    state_nsw_doc = add_source_document("nsw_state_actuals_2024_25", "state", "NSW")
    pbs_doc = add_source_document("federal_pbs_programs_all", "federal", "Commonwealth")

    local_parent_node = add_node(local_doc, "Economic affairs", "local|node|Economic affairs", "local", "QLD")
    local_parent_fact = add_fact(local_doc, local_parent_node, "2024-25", 10_000_000)

    federal_child_node = add_node(federal_doc, "Immigration", "federal|node|Immigration", "federal", "Commonwealth")
    federal_child_fact = add_fact(federal_doc, federal_child_node, "2024-25", 3_758_000_000)

    qld_parent_node = add_node(state_qld_doc, "Health", "qld|node|Health", "state", "QLD")
    qld_parent_fact = add_fact(state_qld_doc, qld_parent_node, "2024-25", 20_000_000)

    nsw_child_node = add_node(state_nsw_doc, "Hospitals", "nsw|node|Hospitals", "state", "NSW")
    nsw_child_fact = add_fact(state_nsw_doc, nsw_child_node, "2024-25", 5_000_000)

    federal_parent_node = add_node(federal_doc, "Defence", "federal|node|Defence", "federal", "Commonwealth")
    federal_parent_fact = add_fact(federal_doc, federal_parent_node, "2024-25", 100_000_000, measure_type="gfs_expense")

    over_100_child_node = add_node(federal_doc, "Capability", "federal|node|Capability", "federal", "Commonwealth")
    over_100_child_fact = add_fact(federal_doc, over_100_child_node, "2024-25", 150_000_000)

    grant_child_node = add_node(federal_doc, "Grant awards", "federal|node|Grant awards", "federal", "Commonwealth")
    grant_child_fact = add_fact(federal_doc, grant_child_node, "2024-25", 1_000_000, measure_type="grant_award")

    future_year_node = add_node(federal_doc, "Future thing", "federal|node|Future thing", "federal", "Commonwealth")
    future_year_fact = add_fact(federal_doc, future_year_node, "2025-26", 2_000_000)

    past_year_node = add_node(federal_doc, "Past thing", "federal|node|Past thing", "federal", "Commonwealth")
    past_year_fact = add_fact(federal_doc, past_year_node, "2023-24", 2_000_000)

    header_label_node = add_node(
        pbs_doc, "000 2028‑29 000 EXPENSES Employee benefits",
        "pbs|node|header", "federal", "Commonwealth",
    )
    header_label_fact = add_fact(pbs_doc, header_label_node, "2024-25", 1_000_000)

    related_federal_node = add_node(federal_doc, "Immigration (related)", "federal|node|Immigration related", "federal", "Commonwealth")
    related_federal_fact = add_fact(federal_doc, related_federal_node, "2024-25", 3_758_000_000)

    conn.commit()
    conn.close()

    return {
        "path": db_path,
        "local_parent_fact": local_parent_fact,
        "federal_child_fact": federal_child_fact,
        "qld_parent_fact": qld_parent_fact,
        "nsw_child_fact": nsw_child_fact,
        "federal_parent_fact": federal_parent_fact,
        "over_100_child_fact": over_100_child_fact,
        "grant_child_fact": grant_child_fact,
        "future_year_fact": future_year_fact,
        "past_year_fact": past_year_fact,
        "header_label_fact": header_label_fact,
        "related_federal_fact": related_federal_fact,
    }


def _node(fact_id, name, value, children=None, breakdown=None):
    return {"id": fact_id, "name": name, "value": value, "children": children or [], "breakdown": breakdown or {}}


def _no_evidence(monkeypatch):
    monkeypatch.setattr(audit, "_get", lambda base_url, path, **params: {"has_source_file": False, "locator": None})


def test_local_path_flags_federal_fact_as_scope_failure(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "local_government_actuals_2024_25", "mode": "actuals", "level": "local", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="local", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["local_parent_fact"], "Economic affairs", 10_000_000,
        children=[_node(fixture_db["federal_child_fact"], "Immigration", 3_758_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.scope_failures) == 1
    assert result.scope_failures[0]["fact_government_level"] == "federal"


def test_related_breakdown_edge_is_exempt_from_scope_check(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "local_government_actuals_2024_25", "mode": "actuals", "level": "local", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="local", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["local_parent_fact"], "Economic affairs", 10_000_000,
        children=[_node(
            fixture_db["federal_child_fact"], "Immigration", 3_758_000_000,
            breakdown={"kind": "related_breakdown", "banner": "Related breakdown - must not be summed into the parent pie slice"},
        )],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert result.scope_failures == []
    assert result.additive_reconciliation_failures == []
    assert result.cross_year_failures == []


def test_state_path_flags_wrong_jurisdiction(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "qld_state_actuals_2024_25", "mode": "actuals", "level": "state", "jurisdiction": "QLD"}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="state", requested_jurisdiction="QLD", requested_year="2024-25")
    tree = _node(
        fixture_db["qld_parent_fact"], "Health", 20_000_000,
        children=[_node(fixture_db["nsw_child_fact"], "Hospitals", 5_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.jurisdiction_failures) == 1
    assert result.jurisdiction_failures[0]["fact_jurisdiction"] == "NSW"


def test_additive_child_over_100_percent_of_parent_flagged(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(fixture_db["over_100_child_fact"], "Capability", 150_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.additive_reconciliation_failures) == 1
    assert result.additive_reconciliation_failures[0]["percent_of_parent"] > 1.0


def test_related_child_over_100_percent_is_not_flagged(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(
            fixture_db["over_100_child_fact"], "Capability", 150_000_000,
            breakdown={"kind": "related_breakdown"},
        )],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert result.additive_reconciliation_failures == []


def _matching_residual_entry(**overrides):
    from accepted_residuals import ResidualEntry

    kwargs = dict(
        source_key="abs_gfs_commonwealth_2024_25",
        node_path="Capability",
        financial_year="2024-25",
        measure_type="gfs_expense",
        estimate_status="actual",
        expected_max_variance_pct=0.5,
        actual_verified_variance_pct=0.5,
        reason="Test fixture: verified source-document rounding.",
        source_locator="pdf:test.pdf|page:1",
        review_date="2026-08-04",
    )
    kwargs.update(overrides)
    return ResidualEntry(**kwargs)


def test_additive_over_100_percent_matching_accepted_residual_is_downgraded(fixture_db, monkeypatch):
    """Task 2 (database-hygiene milestone): a >100%-of-parent additive
    child that exactly matches a declarative accepted-residual entry
    (same source_key, node path, financial_year, measure_type,
    estimate_status, and within the entry's own declared variance) is
    downgraded to an accepted_source_rounding_warning, not a hard
    failure."""
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(fixture_db["over_100_child_fact"], "Capability", 150_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
        residuals=[_matching_residual_entry()],
    )
    conn.close()
    assert result.additive_reconciliation_failures == []
    assert len(result.accepted_source_rounding_warnings) == 1
    assert result.accepted_source_rounding_warnings[0]["fact_id"] == fixture_db["over_100_child_fact"]
    # accepted_source_rounding_warnings is deliberately excluded from
    # hard_failure_count() - it must never contribute to the audit's
    # nonzero-exit-code condition (the unrelated citation_failure this
    # fixture's shared _no_evidence() monkeypatch always produces for a
    # material leaf is a separate, real hard failure this test isn't
    # about; asserting the exact additive/accepted split above is the
    # actual claim under test).


def test_additive_over_100_percent_residual_with_different_year_still_fails(fixture_db, monkeypatch):
    """A residual entry for a different financial_year must not match -
    the exception never silently widens to cover a different year."""
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(fixture_db["over_100_child_fact"], "Capability", 150_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
        residuals=[_matching_residual_entry(financial_year="2023-24")],
    )
    conn.close()
    assert len(result.additive_reconciliation_failures) == 1
    assert result.accepted_source_rounding_warnings == []


def test_additive_over_100_percent_exceeding_declared_variance_still_fails(fixture_db, monkeypatch):
    """A residual entry whose identity matches exactly but whose declared
    expected_max_variance_pct is smaller than the live variance must not
    match - the exception is scoped to the exact variance it was
    verified against, not a blank cheque for a materially larger one."""
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(fixture_db["over_100_child_fact"], "Capability", 150_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
        residuals=[_matching_residual_entry(expected_max_variance_pct=0.01, actual_verified_variance_pct=0.01)],
    )
    conn.close()
    assert len(result.additive_reconciliation_failures) == 1
    assert result.accepted_source_rounding_warnings == []


def test_non_additive_measure_type_as_additive_child_flags_edge_kind_failure(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(fixture_db["grant_child_fact"], "Grant awards", 1_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.edge_kind_failures) == 1
    assert result.edge_kind_failures[0]["child_compatibility_group"] == "commitment"


def test_future_year_additive_child_flagged_as_future_fallback(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(fixture_db["future_year_fact"], "Future thing", 2_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.cross_year_failures) == 1
    assert result.cross_year_failures[0]["is_future_year_fallback"] is True
    assert result.cross_year_failures[0]["child_financial_year"] == "2025-26"


def test_past_year_additive_child_flagged_but_not_as_future_fallback(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["federal_parent_fact"], "Defence", 100_000_000,
        children=[_node(fixture_db["past_year_fact"], "Past thing", 2_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.cross_year_failures) == 1
    assert result.cross_year_failures[0]["is_future_year_fallback"] is False


def test_pbs_header_label_flagged_as_label_quality_failure(fixture_db, monkeypatch):
    _no_evidence(monkeypatch)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(fixture_db["header_label_fact"], "000 2028‑29 000 EXPENSES Employee benefits", 1_000_000)
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.label_quality_failures) == 1


def test_citation_failure_when_evidence_missing(fixture_db, monkeypatch):
    monkeypatch.setattr(audit, "_get", lambda base_url, path, **params: {"has_source_file": False, "locator": None})
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(fixture_db["federal_parent_fact"], "Defence", 100_000_000)
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert result.citation_checks == 1
    assert len(result.citation_failures) == 1


def test_citation_passes_when_evidence_present(fixture_db, monkeypatch):
    monkeypatch.setattr(audit, "_get", lambda base_url, path, **params: {"has_source_file": True, "locator": "pdf:test.pdf|page:1"})
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(fixture_db["federal_parent_fact"], "Defence", 100_000_000)
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert result.citation_checks == 1
    assert result.citation_failures == []


def test_transport_error_recorded_when_evidence_fetch_raises(fixture_db, monkeypatch):
    def _raise(base_url, path, **params):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(audit, "_get", _raise)
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(fixture_db["federal_parent_fact"], "Defence", 100_000_000)
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.transport_errors) == 1
    assert "connection refused" in result.transport_errors[0]


def test_citation_presence_alone_does_not_suppress_other_failures(fixture_db, monkeypatch):
    """A cited node with a real citation must still be flagged for scope
    leakage - presence of a citation is one check among several, never a
    substitute proving the row is semantically valid overall."""
    monkeypatch.setattr(audit, "_get", lambda base_url, path, **params: {"has_source_file": True, "locator": "pdf:test.pdf|page:1"})
    conn = sqlite3.connect(str(fixture_db["path"]))
    spec = {"label": "local_government_actuals_2024_25", "mode": "actuals", "level": "local", "jurisdiction": None}
    result = audit.AuditResult(path_label=spec["label"], requested_mode="actuals", requested_level="local", requested_jurisdiction=None, requested_year="2024-25")
    tree = _node(
        fixture_db["local_parent_fact"], "Economic affairs", 10_000_000,
        children=[_node(fixture_db["federal_child_fact"], "Immigration", 3_758_000_000)],
    )
    audit._walk(
        "http://unused", conn, tree, spec=spec, parent_fact=None, parent_amount=None,
        parent_edge_kind="additive", result=result, depth=0, max_depth=6,
    )
    conn.close()
    assert len(result.scope_failures) == 1
    assert result.citation_failures == []


def test_hard_failure_count_and_exit_code_semantics():
    clean = audit.AuditResult(path_label="clean", requested_mode="actuals", requested_level="federal", requested_jurisdiction=None, requested_year="2024-25")
    assert clean.hard_failure_count() == 0

    dirty = audit.AuditResult(path_label="dirty", requested_mode="actuals", requested_level="local", requested_jurisdiction=None, requested_year="2024-25")
    dirty.scope_failures.append({"fact_id": 1})
    assert dirty.hard_failure_count() == 1
