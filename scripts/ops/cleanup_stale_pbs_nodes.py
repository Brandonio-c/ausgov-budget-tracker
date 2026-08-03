#!/usr/bin/env python3
"""Task 8 (semantic-defect milestone): remove PBS graph state left stale by
a federal_pbs_programs_all reload - nodes/edges that pointed at facts the
corrected label-quality classifier no longer accepts.

replace_on_reload only replaces *facts*; a node whose only fact is
quarantined this run keeps existing (nodes are never deleted by a fact
reload) and is otherwise left behind as an orphan, along with any edge
still pointing at it.

Staleness is intentionally NOT "this node currently has zero facts" - the
PBS corpus's own internal same_group cascade legitimately creates
permanent, fact-less *folder* nodes (bare portfolio names like "Defence",
and multi-separator-label intermediate nodes like "Agriculture Fisheries
and Forestry / Retained surplus") as normal structure; a first version of
this script used that as the staleness signal and would have deleted
9,791 same_group edges belonging entirely to legitimate portfolio folders
(confirmed by dry-run against a scratch copy before this was ever run for
real). Instead, staleness is a *transition*: a node that had at least one
live fact before the reload and has zero after it is a genuinely orphaned
former leaf - a folder node, which never had a fact before or after,
never qualifies. Order matters: stale edges are removed first (an edge
referencing an orphaned node is unambiguously stale on its own), then
nodes are removed only once confirmed to have zero facts AND zero edges
of any kind - never force-deleted to make room for node deletion. Never
touches any non-PBS node/edge/fact.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
PBS_SOURCE_KEY = "federal_pbs_programs_all"


def fact_bearing_pbs_node_ids(
    conn: sqlite3.Connection, source_key: str = PBS_SOURCE_KEY
) -> set[int]:
    """Snapshot of every node for the given PBS-family source that is
    currently attached to at least one fact - call this BEFORE a reload
    (or any direct fact deletion) to know which nodes must not be silently
    dropped without investigation afterward. source_key defaults to
    federal_pbs_programs_all but any PBS-family source (e.g. the older
    federal_pbs_programs_s6_bridge dataset) can reuse this same, tested
    staleness logic."""
    rows = conn.execute(
        """
        SELECT DISTINCT n.id
        FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        JOIN fact_nodes fn ON fn.node_id = n.id
        WHERE d.source_key = ?
        """,
        (source_key,),
    ).fetchall()
    return {int(r[0]) for r in rows}


def cleanup(
    conn: sqlite3.Connection,
    before_fact_bearing_node_ids: set[int],
    source_key: str = PBS_SOURCE_KEY,
) -> dict:
    conn.execute("PRAGMA foreign_keys = ON")

    after_fact_bearing = fact_bearing_pbs_node_ids(conn, source_key)
    # A node that had a live fact before the reload and has none now is a
    # genuinely orphaned former leaf. A folder node (never fact-bearing,
    # before or after) is never in this set.
    newly_orphaned = sorted(before_fact_bearing_node_ids - after_fact_bearing)

    stale_edges_removed = 0
    if newly_orphaned:
        placeholders = ",".join("?" for _ in newly_orphaned)
        cur = conn.execute(
            f"""
            DELETE FROM breakdown_edges
            WHERE parent_node_id IN ({placeholders})
               OR child_node_id IN ({placeholders})
            """,
            (*newly_orphaned, *newly_orphaned),
        )
        stale_edges_removed = cur.rowcount

    stale_nodes_removed = 0
    kept_with_remaining_edges = 0
    if newly_orphaned:
        placeholders = ",".join("?" for _ in newly_orphaned)
        deletable = [
            int(r[0])
            for r in conn.execute(
                f"""
                SELECT n.id
                FROM nodes n
                LEFT JOIN fact_nodes fn ON fn.node_id = n.id
                LEFT JOIN breakdown_edges e_out ON e_out.parent_node_id = n.id
                LEFT JOIN breakdown_edges e_in ON e_in.child_node_id = n.id
                WHERE n.id IN ({placeholders})
                GROUP BY n.id
                HAVING COUNT(fn.fact_id) = 0
                   AND COUNT(e_out.id) = 0
                   AND COUNT(e_in.id) = 0
                """,
                newly_orphaned,
            ).fetchall()
        ]
        kept_with_remaining_edges = len(newly_orphaned) - len(deletable)
        if deletable:
            del_placeholders = ",".join("?" for _ in deletable)
            cur = conn.execute(
                f"DELETE FROM nodes WHERE id IN ({del_placeholders})", deletable
            )
            stale_nodes_removed = cur.rowcount

    return {
        "before_fact_bearing_count": len(before_fact_bearing_node_ids),
        "after_fact_bearing_count": len(after_fact_bearing),
        "newly_orphaned_nodes": len(newly_orphaned),
        "stale_edges_removed": stale_edges_removed,
        "stale_nodes_removed": stale_nodes_removed,
        "nodes_kept_with_remaining_edges": kept_with_remaining_edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-key", default=PBS_SOURCE_KEY)
    parser.add_argument(
        "--before-node-ids-file",
        type=Path,
        required=True,
        help="JSON file containing the list of PBS node IDs that had a live fact BEFORE the reload (see fact_bearing_pbs_node_ids()).",
    )
    args = parser.parse_args()
    before_ids = set(json.loads(args.before_node_ids_file.read_text(encoding="utf-8")))
    conn = sqlite3.connect(str(args.db))
    try:
        result = cleanup(conn, before_ids, args.source_key)
        conn.commit()
    finally:
        conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
