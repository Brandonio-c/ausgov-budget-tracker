#!/usr/bin/env python3
"""Task 9 (semantic-defect milestone) / Task 6 (database-hygiene-and-
CI-hardening milestone): direct SQL integrity checks against data/facts.db,
run in addition to pytest/frontend/e2e/reconciliation. Read-only. Prints a
JSON report and exits non-zero if any check finds a hit outside its
documented, expected baseline.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

from accepted_residuals import validate_config as validate_accepted_residuals  # noqa: E402
from pbs_label_classifier import classify_label  # noqa: E402
from reviewed_duplicates import (  # noqa: E402
    load_reviewed_duplicates,
    match_reviewed_duplicate,
)
from reviewed_duplicates import validate_config as validate_reviewed_duplicates  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"


def duplicate_facts(conn) -> list[dict]:
    """Same node + financial_year + measure_type + estimate_status + amount
    appearing under more than one distinct fact_id - a true duplicate
    candidate, not just two different facts that happen to share a
    fact_key (impossible; fact_key is UNIQUE). Includes node_path and
    source_key (not just the mutable node_id) so a reviewer - or
    scripts/ops/reviewed_duplicates.py's declarative registry - can tell a
    genuine true duplicate apart from two legitimately distinct records
    that a shared, under-specified node made look identical."""
    rows = conn.execute(
        """
        SELECT fn.node_id, n.name AS node_path, sd.source_key,
               f.financial_year, f.measure_type, f.estimate_status,
               f.amount_aud, COUNT(DISTINCT f.id) AS n, GROUP_CONCAT(DISTINCT f.id) AS fact_ids
        FROM facts f
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        JOIN source_documents sd ON sd.id = f.source_document_id
        GROUP BY fn.node_id, f.financial_year, f.measure_type, f.estimate_status, f.amount_aud
        HAVING COUNT(DISTINCT f.id) > 1
        """
    ).fetchall()
    return [
        {
            "node_id": r[0],
            "node_path": r[1],
            "source_key": r[2],
            "financial_year": r[3],
            "measure_type": r[4],
            "estimate_status": r[5],
            "amount_aud": r[6],
            "count": r[7],
            "fact_ids": r[8],
        }
        for r in rows
    ]


def partition_duplicate_facts(
    groups: list[dict], reviewed: list | None = None
) -> tuple[list[dict], list[dict]]:
    """Split duplicate_facts() groups into (unresolved, reviewed) using
    scripts/ops/reviewed_duplicates.py's declarative registry. A group only
    ever moves to "reviewed" by exact (source_key, node_path,
    financial_year, measure_type, estimate_status, amount_aud) identity
    match - a changed year, source, node path, measure type, estimate
    status, or amount always falls through to "unresolved" (a hard
    failure), so a stale or too-broad registry entry can never silently
    swallow a new or different duplicate-look-alike group."""
    if reviewed is None:
        reviewed = load_reviewed_duplicates()
    unresolved: list[dict] = []
    matched: list[dict] = []
    for group in groups:
        entry = match_reviewed_duplicate(
            reviewed,
            source_key=group["source_key"],
            node_path=group["node_path"],
            financial_year=group["financial_year"],
            measure_type=group["measure_type"],
            estimate_status=group["estimate_status"],
            amount_aud=float(group["amount_aud"]),
        )
        if entry is None:
            unresolved.append(group)
        else:
            enriched = dict(group)
            enriched["classification"] = entry.classification
            enriched["reason"] = entry.reason
            enriched["evidence_report"] = entry.evidence_report
            matched.append(enriched)
    return unresolved, matched


def duplicate_breakdown_edges(conn) -> list[dict]:
    """NULL-safe duplicate check: two edge rows with the same
    parent/child/edge_kind, where financial_year and crosswalk_id are
    either both equal or both NULL - the exact case a naive UNIQUE
    constraint (NULL <> NULL) does not catch."""
    rows = conn.execute(
        """
        SELECT parent_node_id, child_node_id, edge_kind,
               financial_year IS NULL AS fy_null, crosswalk_id IS NULL AS cw_null,
               financial_year, crosswalk_id, COUNT(*) AS n
        FROM breakdown_edges
        GROUP BY parent_node_id, child_node_id, edge_kind, fy_null, cw_null, financial_year, crosswalk_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    return [dict(zip(("parent_node_id", "child_node_id", "edge_kind", "fy_null", "cw_null", "financial_year", "crosswalk_id", "count"), r)) for r in rows]


def orphan_facts(conn) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) FROM facts f
        WHERE NOT EXISTS (SELECT 1 FROM fact_nodes fn WHERE fn.fact_id = f.id)
        """
    ).fetchone()[0]


def orphan_nodes(conn) -> int:
    """A node with zero facts, zero breakdown_edges, AND zero node_edges -
    genuinely unreachable from anywhere, not a legitimate fact-less folder
    (which still has same_group edges to its children)."""
    return conn.execute(
        """
        SELECT COUNT(*) FROM nodes n
        WHERE NOT EXISTS (SELECT 1 FROM fact_nodes fn WHERE fn.node_id = n.id)
          AND NOT EXISTS (SELECT 1 FROM breakdown_edges e WHERE e.parent_node_id = n.id OR e.child_node_id = n.id)
          AND NOT EXISTS (SELECT 1 FROM node_edges ne WHERE ne.parent_node_id = n.id OR ne.child_node_id = n.id)
        """
    ).fetchone()[0]


def orphan_edges(conn) -> int:
    """breakdown_edges referencing a node_id that no longer exists -
    should be structurally impossible (FK), checked directly anyway."""
    return conn.execute(
        """
        SELECT COUNT(*) FROM breakdown_edges e
        WHERE NOT EXISTS (SELECT 1 FROM nodes n WHERE n.id = e.parent_node_id)
           OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.id = e.child_node_id)
        """
    ).fetchone()[0]


def dangling_source_documents(conn) -> list[str]:
    rows = conn.execute(
        """
        SELECT d.source_key FROM source_documents d
        WHERE NOT EXISTS (SELECT 1 FROM facts f WHERE f.source_document_id = d.id)
          AND NOT EXISTS (SELECT 1 FROM nodes n WHERE n.source_document_id = d.id)
        """
    ).fetchall()
    return [r[0] for r in rows]


def cross_government_additive_edges(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.id, pn.government_level, cn.government_level, pn.name, cn.name
        FROM breakdown_edges e
        JOIN nodes pn ON pn.id = e.parent_node_id
        JOIN nodes cn ON cn.id = e.child_node_id
        WHERE e.edge_kind = 'same_group'
          AND pn.government_level != cn.government_level
        """
    ).fetchall()
    return [{"edge_id": r[0], "parent_level": r[1], "child_level": r[2], "parent_name": r[3][:80], "child_name": r[4][:80]} for r in rows]


def cross_jurisdiction_additive_edges(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.id, pn.jurisdiction, cn.jurisdiction, pn.name, cn.name
        FROM breakdown_edges e
        JOIN nodes pn ON pn.id = e.parent_node_id
        JOIN nodes cn ON cn.id = e.child_node_id
        WHERE e.edge_kind = 'same_group'
          AND pn.jurisdiction != cn.jurisdiction
        """
    ).fetchall()
    return [{"edge_id": r[0], "parent_jurisdiction": r[1], "child_jurisdiction": r[2], "parent_name": r[3][:80], "child_name": r[4][:80]} for r in rows]


def pbs_crosswalk_children_with_rejected_labels(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT DISTINCT e.id, cn.id, cn.name
        FROM breakdown_edges e
        JOIN nodes cn ON cn.id = e.child_node_id
        WHERE e.crosswalk_id = 'pbs_programs_all_under_s6'
        """
    ).fetchall()
    bad = []
    for edge_id, node_id, node_name in rows:
        label = node_name.rsplit(" / ", 1)[-1] if " / " in node_name else node_name
        result = classify_label(label)
        if not result.publishable:
            bad.append({"edge_id": edge_id, "node_id": node_id, "name": node_name[:120], "classification": result.classification})
    return bad


def pbs_children_missing_source_year(conn) -> int:
    """Every fact backing a PBS crosswalk child must have a real
    financial_year (schema NOT NULL already guarantees this - checked
    directly as defence in depth, not assumed)."""
    return conn.execute(
        """
        SELECT COUNT(DISTINCT f.id)
        FROM breakdown_edges e
        JOIN nodes cn ON cn.id = e.child_node_id
        JOIN fact_nodes fn ON fn.node_id = cn.id AND fn.dimension_role = 'primary'
        JOIN facts f ON f.id = fn.fact_id
        WHERE e.crosswalk_id = 'pbs_programs_all_under_s6'
          AND (f.financial_year IS NULL OR TRIM(f.financial_year) = '')
        """
    ).fetchone()[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="facts.db to check (default: the live data/facts.db). Previously this "
        "flag was silently accepted-but-ignored by every caller in this repo since "
        "main() never read sys.argv - always checked DB_PATH regardless of any "
        "--db value passed. Fixed here so a --db override actually takes effect.",
    )
    args = parser.parse_args(argv)
    conn = sqlite3.connect(str(args.db))
    all_duplicate_groups = duplicate_facts(conn)
    unresolved_duplicates, reviewed_duplicates = partition_duplicate_facts(all_duplicate_groups)
    results = {
        "unresolved_duplicate_facts": unresolved_duplicates,
        "reviewed_duplicate_facts": reviewed_duplicates,
        "duplicate_breakdown_edges": duplicate_breakdown_edges(conn),
        "orphan_facts": orphan_facts(conn),
        "orphan_nodes": orphan_nodes(conn),
        "orphan_edges": orphan_edges(conn),
        "dangling_source_documents": dangling_source_documents(conn),
        "cross_government_additive_edges": cross_government_additive_edges(conn),
        "cross_jurisdiction_additive_edges": cross_jurisdiction_additive_edges(conn),
        "pbs_crosswalk_children_with_rejected_labels": pbs_crosswalk_children_with_rejected_labels(conn),
        "pbs_children_missing_source_year": pbs_children_missing_source_year(conn),
        "accepted_residual_config": validate_accepted_residuals(),
        "reviewed_duplicate_config": validate_reviewed_duplicates(),
    }
    conn.close()

    hard_failures = 0
    # Confirmed duplicate facts and unresolved duplicate candidates are
    # both hard failures - the only way out of "unresolved" is either a
    # declarative reviewed_duplicate_facts.yaml entry (proven, in this
    # milestone, to be a query false positive / legitimate distinct
    # record - see scripts/ops/reviewed_duplicates.py) or an actual
    # deletion (scripts/ops/cleanup_duplicate_facts.py). A reviewed group
    # is never a hard failure; it is also never silently dropped from the
    # report (see "reviewed_duplicate_facts" above).
    hard_failures += len(results["unresolved_duplicate_facts"])
    hard_failures += len(results["duplicate_breakdown_edges"])
    hard_failures += results["orphan_facts"]
    hard_failures += results["orphan_nodes"]
    hard_failures += results["orphan_edges"]
    hard_failures += len(results["cross_government_additive_edges"])
    hard_failures += len(results["cross_jurisdiction_additive_edges"])
    hard_failures += len(results["pbs_crosswalk_children_with_rejected_labels"])
    hard_failures += results["pbs_children_missing_source_year"]
    if not results["accepted_residual_config"]["valid"]:
        hard_failures += 1
    if not results["reviewed_duplicate_config"]["valid"]:
        hard_failures += 1
    # dangling_source_documents is informational only (unused reference
    # rows, not a graph-integrity hazard) - not counted as a hard failure.

    print(json.dumps({"hard_failures": hard_failures, **results}, indent=2, default=str))
    return 1 if hard_failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
