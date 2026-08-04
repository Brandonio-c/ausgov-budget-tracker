#!/usr/bin/env python3
"""Generic, transaction-safe orphan-node cleanup (Task 5 of the
database-hygiene-and-CI-hardening milestone).

An "orphan node" here uses the exact same definition as
scripts/ops/task9_sql_integrity_checks.py's orphan_nodes() check: a node
with zero fact_nodes rows, zero breakdown_edges rows (as either parent or
child), and zero node_edges rows (as either parent or child) - genuinely
unreachable from anywhere, never a legitimate fact-less navigation folder
(which still has at least one breakdown_edge or node_edge to a child).

Root cause investigated for the 278 orphans found by this milestone (all
in the state/territory borrowing-authority debt-instrument sources - see
ops/reports/orphan-node-investigation-*.md): scripts/ingest/
m_borrowing_authorities.py deletes facts + fact_nodes for a source before
every reload ("path/valuation upgrades do not double-count") but never
touches the nodes table, and this whole source family's node identity
(scripts/ingest/load_facts.py's ensure_node()) is a flat one-node-per-
distinct-category-string scheme with no breakdown_edges/node_edges ever
created. Two historical upstream changes (adding the authority name into
the category path; reclassifying some "Other funding instruments" rows
into "Fixed-rate bonds") each left a full generation of now-unreferenced
nodes behind under the old naming - a permanent "replace-on-reload
deletes facts but not unused nodes" leak. m_borrowing_authorities.py now
calls delete_orphan_nodes() itself, scoped to its own source, on every
reload, so this cannot recur; this module is also usable standalone for
one-off hygiene against any other source.

Usage:
    python3 scripts/ops/cleanup_orphan_nodes.py --dry-run   (default)
    python3 scripts/ops/cleanup_orphan_nodes.py --apply
    python3 scripts/ops/cleanup_orphan_nodes.py --apply --source nsw_tcorp_bonds_on_issue
    python3 scripts/ops/cleanup_orphan_nodes.py --apply --report path.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "facts.db"

_ORPHAN_WHERE = """
    NOT EXISTS (SELECT 1 FROM fact_nodes fn WHERE fn.node_id = n.id)
    AND NOT EXISTS (SELECT 1 FROM breakdown_edges e WHERE e.parent_node_id = n.id OR e.child_node_id = n.id)
    AND NOT EXISTS (SELECT 1 FROM node_edges ne WHERE ne.parent_node_id = n.id OR ne.child_node_id = n.id)
"""


def orphan_nodes(
    conn: sqlite3.Connection, source_keys: list[str] | None = None
) -> list[dict[str, Any]]:
    """Return full detail for every currently-orphaned node, optionally
    restricted to the given source_keys (matched via nodes.source_document_id
    -> source_documents.source_key, since a node's own jurisdiction/name
    fields are not a reliable source filter)."""
    query = f"""
        SELECT n.id, n.canonical_key, n.name, n.jurisdiction, n.government_level,
               sd.source_key
        FROM nodes n
        LEFT JOIN source_documents sd ON sd.id = n.source_document_id
        WHERE {_ORPHAN_WHERE}
    """
    params: tuple = ()
    if source_keys:
        placeholders = ",".join("?" for _ in source_keys)
        query += f" AND sd.source_key IN ({placeholders})"
        params = tuple(source_keys)
    query += " ORDER BY sd.source_key, n.id"
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": r[0],
            "canonical_key": r[1],
            "name": r[2],
            "jurisdiction": r[3],
            "government_level": r[4],
            "source_key": r[5],
        }
        for r in rows
    ]


def orphan_node_ids_for_source_document(
    conn: sqlite3.Connection, source_document_id: int
) -> list[int]:
    """Orphan node IDs scoped to one source_document_id - used by ingest
    scripts (e.g. scripts/ingest/m_borrowing_authorities.py) to clean up
    their own now-unused nodes immediately after a reload, rather than
    waiting for a separate ops pass."""
    rows = conn.execute(
        f"""
        SELECT n.id FROM nodes n
        WHERE n.source_document_id = ? AND {_ORPHAN_WHERE}
        """,
        (source_document_id,),
    ).fetchall()
    return [r[0] for r in rows]


def delete_orphan_nodes(conn: sqlite3.Connection, node_ids: list[int]) -> int:
    """Delete the given node IDs, re-verifying each is still a genuine
    orphan at delete time (defence against a race with concurrent writes
    in the same process). Caller is responsible for commit/rollback."""
    deleted = 0
    for node_id in node_ids:
        still_orphan = conn.execute(
            f"SELECT 1 FROM nodes n WHERE n.id = ? AND {_ORPHAN_WHERE}",
            (node_id,),
        ).fetchone()
        if still_orphan is None:
            continue
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        deleted += 1
    return deleted


def _write_reports(results: list[dict[str, Any]], report_path: Path, apply_mode: bool) -> None:
    json_path = report_path.with_suffix(".json")
    md_path = report_path.with_suffix(".md")
    by_source: dict[str, int] = {}
    for r in results:
        by_source[r["source_key"] or "(none)"] = by_source.get(r["source_key"] or "(none)", 0) + 1
    payload = {
        "mode": "apply" if apply_mode else "dry_run",
        "total": len(results),
        "by_source_key": by_source,
        "nodes": results,
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Orphan-node cleanup report",
        "",
        f"Mode: **{'apply' if apply_mode else 'dry-run'}**",
        f"Total orphan nodes: **{len(results)}**",
        "",
        "| source_key | count |",
        "|---|---:|",
    ]
    for sk, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {sk} | {n} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="default: plan only, no writes")
    mode.add_argument("--apply", action="store_true", help="delete the found orphan nodes")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        default=None,
        help="restrict to this source_key (repeatable); default: all sources",
    )
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args(argv)

    apply_mode = bool(args.apply)

    conn = sqlite3.connect(str(args.db))
    conn.execute("PRAGMA foreign_keys = ON")
    found = orphan_nodes(conn, args.sources)

    if apply_mode:
        deleted = delete_orphan_nodes(conn, [n["id"] for n in found])
        conn.commit()
        remaining = orphan_nodes(conn, args.sources)
        if remaining:
            print(
                f"WARNING: {len(remaining)} orphan node(s) remain after cleanup "
                "(new orphans created concurrently, or a re-check race)",
                file=sys.stderr,
            )
        summary = {"mode": "apply", "found": len(found), "deleted": deleted, "remaining": len(remaining)}
    else:
        summary = {"mode": "dry_run", "found": len(found)}

    if args.report:
        _write_reports(found, args.report, apply_mode)

    conn.close()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
