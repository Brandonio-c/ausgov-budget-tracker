#!/usr/bin/env python3
"""Preview, delete, or transactionally rebuild registered breakdown edge sets."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from breakdown_pack import (  # noqa: E402
    link_a61_to_components,
    link_austender_under_s6,
    link_dss_under_pbs,
    link_grants_under_pbs,
    link_historical_fbo_related,
    link_ndis_participant_statistics,
    link_pbs_to_components,
    link_related_crosswalk,
    link_same_group_from_paths,
)
from pbs_s6_crosswalk import (  # noqa: E402
    load_crosswalk as load_pbs_crosswalk,
)
from pbs_s6_crosswalk import (  # noqa: E402
    load_edges as load_pbs_edges,
)
from schema_migrate import migrate  # noqa: E402

from backend.edge_set_policy import EdgeSetPolicy, load_edge_set_registry  # noqa: E402

DEFAULT_DB = REPO_ROOT / "data" / "facts.db"


def policies_for_selector(
    *, edge_set_id: str | None, crosswalk_id: str | None
) -> tuple[EdgeSetPolicy, ...]:
    registry = load_edge_set_registry()
    if edge_set_id:
        try:
            return (registry.policy_by_id(edge_set_id),)
        except KeyError as exc:
            raise ValueError(f"Unknown edge-set ID: {edge_set_id}") from exc
    assert crosswalk_id
    policies = tuple(
        policy
        for policy in registry.policies
        if policy.crosswalk_id == crosswalk_id
    )
    return policies


def _scope_sql(policy: EdgeSetPolicy) -> tuple[str, list[Any]]:
    clauses = ["e.edge_kind = ?", "e.crosswalk_id IS ?"]
    params: list[Any] = [policy.edge_kind, policy.crosswalk_id]
    source_clauses: list[str] = []
    for source_key in policy.source_key_allowlist:
        source_clauses.append("d.source_key = ?")
        params.append(source_key)
    for prefix in policy.source_key_prefixes:
        source_clauses.append("substr(d.source_key, 1, length(?)) = ?")
        params.extend((prefix, prefix))
    if source_clauses:
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM nodes n "
            "JOIN source_documents d ON d.id = n.source_document_id "
            "WHERE n.id = e.child_node_id AND ("
            + " OR ".join(source_clauses)
            + "))"
        )
    return " AND ".join(clauses), params


def count_edge_set(conn: sqlite3.Connection, policy: EdgeSetPolicy) -> int:
    where, params = _scope_sql(policy)
    row = conn.execute(
        f"SELECT COUNT(*) FROM breakdown_edges e WHERE {where}", params
    ).fetchone()
    return int(row[0])


def delete_edge_set(conn: sqlite3.Connection, policy: EdgeSetPolicy) -> int:
    where, params = _scope_sql(policy)
    conn.execute(f"DELETE FROM breakdown_edges AS e WHERE {where}", params)
    return int(conn.execute("SELECT changes()").fetchone()[0])


def _matching_source_keys(
    conn: sqlite3.Connection, policy: EdgeSetPolicy
) -> tuple[str, ...]:
    keys = {
        str(row[0])
        for row in conn.execute(
            "SELECT DISTINCT source_key FROM source_documents WHERE source_key IS NOT NULL"
        )
        if row[0]
    }
    return tuple(
        sorted(
            key
            for key in keys
            if (
                (not policy.source_key_allowlist or key in policy.source_key_allowlist)
                and (
                    not policy.source_key_prefixes
                    or any(key.startswith(prefix) for prefix in policy.source_key_prefixes)
                )
            )
        )
    )


def rebuild_edge_set(conn: sqlite3.Connection, policy: EdgeSetPolicy) -> Any:
    source_keys = _matching_source_keys(conn, policy)
    if policy.id.endswith("_source_native"):
        inserted = 0
        for source_key in source_keys:
            for _ in range(10):
                round_inserted = link_same_group_from_paths(conn, source_key, {})
                inserted += round_inserted
                if round_inserted == 0:
                    break
        return {"inserted": inserted, "source_keys": list(source_keys)}
    if policy.id == "fbo_archive_under_abs":
        return {
            "inserted": link_historical_fbo_related(conn),
            "source_keys": list(source_keys),
        }
    if policy.id in {"statement_6_under_abs", "fbo_2024_25_under_abs"}:
        inserted = sum(
            link_related_crosswalk(conn, str(policy.crosswalk_id), source_key)
            for source_key in source_keys
        )
        return {"inserted": inserted, "source_keys": list(source_keys)}

    rebuilders = {
        "statement_6_components": link_a61_to_components,
        "pbs_dss_bridge": link_pbs_to_components,
        "pbs_under_component": link_pbs_to_components,
        "contracts_under_statement_6": link_austender_under_s6,
        "grants_under_pbs": link_grants_under_pbs,
        "recipients_under_pbs": link_dss_under_pbs,
        "ndis_participants_under_statement6": link_ndis_participant_statistics,
        "ndis_average_budget_under_statement6": link_ndis_participant_statistics,
    }
    if policy.id == "pbs_programs_all_under_s6":
        return load_pbs_edges(conn, load_pbs_crosswalk())
    rebuilder = rebuilders.get(policy.id)
    if rebuilder is None:
        raise ValueError(f"No registered rebuilder for edge set {policy.id}")
    return {"inserted": int(rebuilder(conn))}


def run(
    *,
    db_path: Path,
    operation: str,
    edge_set_id: str | None,
    crosswalk_id: str | None,
    apply: bool,
) -> dict[str, Any]:
    policies = policies_for_selector(
        edge_set_id=edge_set_id, crosswalk_id=crosswalk_id
    )
    if operation == "rebuild" and not policies:
        raise ValueError(f"No registered edge sets use crosswalk {crosswalk_id!r}")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        before = {policy.id: count_edge_set(conn, policy) for policy in policies}
    finally:
        conn.close()
    result: dict[str, Any] = {
        "operation": operation,
        "applied": apply,
        "selector": edge_set_id or crosswalk_id,
        "edge_sets": list(before),
        "before": before,
    }
    if not apply:
        return result

    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        deleted = {policy.id: delete_edge_set(conn, policy) for policy in policies}
        rebuilt: dict[str, Any] = {}
        if operation == "rebuild":
            for policy in policies:
                rebuilt[policy.id] = rebuild_edge_set(conn, policy)
        after = {policy.id: count_edge_set(conn, policy) for policy in policies}
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    result.update({"deleted": deleted, "rebuilt": rebuilt, "after": after})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--delete", action="store_true")
    operation.add_argument("--rebuild", action="store_true")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--edge-set")
    selector.add_argument("--crosswalk-id")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the requested mutation; without this flag only preview counts are shown",
    )
    args = parser.parse_args(argv)
    result = run(
        db_path=args.db,
        operation="delete" if args.delete else "rebuild",
        edge_set_id=args.edge_set,
        crosswalk_id=args.crosswalk_id,
        apply=args.apply,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
