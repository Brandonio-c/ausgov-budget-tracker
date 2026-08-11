#!/usr/bin/env python3
"""Attach historical Treasury PBS program facts beneath the matching
edition's Statement 6 "General public services" function node, as
exact-only related_breakdown evidence.

See config/breakdowns/crosswalks/historical_pbs_treasury_under_statement6.yaml
for the full evidence and edition-locking rationale, and
config/breakdowns/edge_sets.yaml's historical_pbs_treasury_under_statement6
entry for the runtime fallback_policy=exact_only / projection_policy=augment
contract. Each PBS edition pairs only with its own Statement 6 edition -
never a different vintage - even though both publish the same node name.

Idempotent: INSERT OR IGNORE against breakdown_edges' UNIQUE constraint
(migration 017). Attaches to specific PBS program nodes directly (not a
shared folder node), matching the precedent set by pbs_s6_crosswalk.py,
since fact_for_node_year() requires the related_breakdown child to carry a
real fact directly.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CROSSWALK_PATH = (
    REPO_ROOT / "config/breakdowns/crosswalks/historical_pbs_treasury_under_statement6.yaml"
)
CROSSWALK_ID = "historical_pbs_treasury_under_statement6"


def load_crosswalk(path: Path = CROSSWALK_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _statement6_function_node_id(conn: sqlite3.Connection, source_key: str, name: str) -> int | None:
    row = conn.execute(
        """
        SELECT n.id FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = ? AND n.name = ?
        """,
        (source_key, name),
    ).fetchone()
    return int(row[0]) if row else None


def _pbs_program_node_ids(conn: sqlite3.Connection, source_key: str) -> list[dict[str, Any]]:
    """Program-level PBS nodes only, not their component detail.

    scripts/ingest/extractors/historical_treasury_pbs.py::_rows() always
    builds the program-total category as exactly
    "Treasury / {entity} / Outcome {N} / Program {X} - {name}" (three
    " / " separators) and every component category as that base plus a
    scope segment plus a component label (five separators). A literal
    "Administered"/"Departmental" substring match is insufficient: at
    least one entity (National Housing Finance and Investment Corporation)
    publishes components under a scope of "Unscoped" instead - verified
    against the live database, not assumed. Segment count is exact and
    source-format-independent.
    """
    rows = conn.execute(
        """
        SELECT DISTINCT n.id, n.name
        FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = ?
        """,
        (source_key,),
    ).fetchall()
    return [
        {"node_id": int(r[0]), "name": r[1]}
        for r in rows
        if r[1].count(" / ") == 3
    ]


def load_edges(conn: sqlite3.Connection, crosswalk: dict[str, Any]) -> dict[str, Any]:
    inserted = 0
    skipped_no_parent = 0
    pairings_result = []
    for pairing in crosswalk.get("pairings") or []:
        pbs_source = str(pairing["pbs_source_key"])
        s6_source = str(pairing["statement6_source_key"])
        function_name = str(pairing["statement6_function"])

        doc_id_row = conn.execute(
            "SELECT id FROM source_documents WHERE source_key = ?", (pbs_source,)
        ).fetchone()
        doc_id = int(doc_id_row[0]) if doc_id_row else None

        parent_id = _statement6_function_node_id(conn, s6_source, function_name)
        if parent_id is None:
            pairings_result.append(
                {
                    "pbs_source_key": pbs_source,
                    "statement6_source_key": s6_source,
                    "status": "skipped_no_parent_node",
                }
            )
            skipped_no_parent += 1
            continue

        children = _pbs_program_node_ids(conn, pbs_source)
        pairing_inserted = 0
        for child in children:
            if child["node_id"] == parent_id:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO breakdown_edges (
                    parent_node_id, child_node_id, edge_kind, crosswalk_id,
                    financial_year, priority, source_document_id, notes
                ) VALUES (?, ?, 'related_breakdown', ?, NULL, 100, ?, ?)
                """,
                (
                    parent_id,
                    child["node_id"],
                    CROSSWALK_ID,
                    doc_id,
                    f"portfolio_ownership|{pairing.get('confidence')}",
                ),
            )
            pairing_inserted += conn.execute("SELECT changes()").fetchone()[0]
        inserted += pairing_inserted
        pairings_result.append(
            {
                "pbs_source_key": pbs_source,
                "statement6_source_key": s6_source,
                "parent_node_id": parent_id,
                "child_programs": len(children),
                "edges_inserted": pairing_inserted,
                "status": "mapped",
            }
        )

    return {
        "edges_inserted": inserted,
        "skipped_no_parent": skipped_no_parent,
        "pairings": pairings_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=REPO_ROOT / "data" / "facts.db")
    parser.add_argument(
        "--apply", action="store_true", help="commit the edges; default is a dry-run rollback"
    )
    args = parser.parse_args()

    conn = sqlite3.connect(str(args.db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    try:
        result = load_edges(conn, crosswalk)
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        result["applied"] = bool(args.apply)
    finally:
        conn.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
