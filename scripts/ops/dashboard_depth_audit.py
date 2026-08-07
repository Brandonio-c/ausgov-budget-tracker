#!/usr/bin/env python3
"""Deterministic dashboard projection signatures and semantic-depth audit.

The audit is read-only.  It drives the in-process FastAPI application against
``data/facts.db`` so it does not depend on a separately managed web server.  A
small normalized signature is retained for each required projection; full API
trees are deliberately not stored as fixtures.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "facts.db"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "dashboard_projection" / "baseline.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

PROJECTIONS: tuple[dict[str, str | None], ...] = (
    {"label": "federal_actuals_2022_23", "mode": "actuals", "level": "federal", "year": "2022-23"},
    {"label": "federal_actuals_2023_24", "mode": "actuals", "level": "federal", "year": "2023-24"},
    {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "year": "2024-25"},
    {"label": "federal_budget_2022_23", "mode": "budget", "level": "federal", "year": "2022-23"},
    {"label": "federal_budget_2023_24", "mode": "budget", "level": "federal", "year": "2023-24"},
    {"label": "federal_budget_2024_25", "mode": "budget", "level": "federal", "year": "2024-25"},
    {"label": "federal_budget_latest", "mode": "budget", "level": "federal", "year": None},
    {"label": "state_debt_latest", "mode": "debt", "level": "state", "year": None},
    {"label": "local_actuals_latest", "mode": "actuals", "level": "local", "year": None},
    {"label": "federal_ratios_latest", "mode": "ratios", "level": "federal", "year": None},
)

NAVIGATION_PREFIXES = ("Statement 6", "FBO Appendix A", "Related ")


def _fy_start(financial_year: str | None) -> int:
    try:
        return int(str(financial_year).split("-", 1)[0])
    except (TypeError, ValueError):
        return -1


def _relationship(node: dict[str, Any], inherited_related: bool = False) -> dict[str, Any]:
    """Read the v2 contract when present, otherwise the compatibility alias."""
    explicit = node.get("relationship") or node.get("breakdown") or {}
    edge_kind = explicit.get("edge_kind") or explicit.get("kind") or "same_group"
    branch_kind = explicit.get("branch_kind") or (
        "related" if inherited_related or edge_kind == "related_breakdown" else "additive"
    )
    role = explicit.get("presentation_role")
    if not role:
        role = (
            "navigation"
            if node.get("children")
            and (
                float(node.get("value") or 0) == 0
                or str(node.get("name") or "").startswith(NAVIGATION_PREFIXES)
            )
            else "data"
        )
    return {**explicit, "edge_kind": edge_kind, "branch_kind": branch_kind, "presentation_role": role}


def _collapse_same_name(node: dict[str, Any]) -> dict[str, Any]:
    current = node
    while True:
        children = current.get("children") or []
        if len(children) != 1 or children[0].get("name") != current.get("name"):
            return current
        if float(children[0].get("value") or 0) <= 0:
            return current
        inner = children[0]
        current = {
            **current,
            "id": inner.get("id") or current.get("id"),
            "breakdown": inner.get("breakdown") or current.get("breakdown"),
            "relationship": inner.get("relationship") or current.get("relationship"),
            "children": inner.get("children"),
        }


def _related_folder_children(nodes: Iterable[dict[str, Any]], prefix: str) -> list[dict[str, Any]] | None:
    folder = next(
        (
            node
            for node in nodes
            if str(node.get("name") or "").startswith(prefix) and node.get("children")
        ),
        None,
    )
    if not folder:
        return None
    positive = [child for child in folder.get("children") or [] if float(child.get("value") or 0) > 0]
    return positive or None


def _additive_children(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for node in nodes:
        if float(node.get("value") or 0) <= 0:
            continue
        rel = _relationship(node)
        name = str(node.get("name") or "")
        if rel["branch_kind"] == "related" and name.startswith(("Statement 6", "FBO Appendix A")):
            continue
        result.append(node)
    return result


def _unwrap_same_name(parent_name: str, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current = [_collapse_same_name(node) for node in nodes]
    while len(current) == 1 and current[0].get("name") == parent_name and current[0].get("children"):
        next_nodes = _additive_children(current[0].get("children") or [])
        if not next_nodes:
            break
        current = [_collapse_same_name(node) for node in next_nodes]
    return current


def _ring_root_children(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statement_6 = _related_folder_children(nodes, "Statement 6")
    selected = statement_6 if statement_6 else _additive_children(nodes)
    return [_collapse_same_name(node) for node in selected]


def _nestable_children(parent: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    children = parent.get("children") or []
    statement_6 = _related_folder_children(children, "Statement 6")
    if statement_6:
        return _unwrap_same_name(str(parent.get("name") or ""), statement_6), 0

    candidates = _unwrap_same_name(
        str(parent.get("name") or ""), _additive_children(children)
    )
    if not candidates:
        fbo = _related_folder_children(children, "FBO Appendix A")
        return (
            _unwrap_same_name(str(parent.get("name") or ""), fbo) if fbo else [],
            0,
        )

    parent_value = float(parent.get("value") or 0)
    if parent_value <= 0:
        return candidates, 0
    total = sum(float(child.get("value") or 0) for child in candidates)
    if total <= parent_value * 1.25:
        return candidates, 0
    dominant = [child for child in candidates if float(child.get("value") or 0) > parent_value * 1.25]
    if not dominant:
        return candidates, 0
    partition = [child for child in candidates if float(child.get("value") or 0) <= parent_value * 1.01]
    if partition:
        return partition, len(candidates) - len(partition)
    fbo = _related_folder_children(children, "FBO Appendix A")
    return (
        _unwrap_same_name(str(parent.get("name") or ""), fbo) if fbo else [],
        len(candidates),
    )


def _frontend_depth_metrics(children: list[dict[str, Any]]) -> dict[str, int]:
    hidden_by_folding = 0
    rejected_by_partition = 0

    def visit(nodes: list[dict[str, Any]], depth: int) -> int:
        nonlocal hidden_by_folding, rejected_by_partition
        if not nodes:
            return depth - 1
        if len(nodes) > 8:
            hidden_by_folding += len(nodes) - 7
        deepest = depth
        for raw in nodes:
            node = _collapse_same_name(raw)
            nest, rejected = _nestable_children(node)
            rejected_by_partition += rejected
            if nest:
                deepest = max(deepest, visit(nest, depth + 1))
        return deepest

    roots = _ring_root_children(children)
    return {
        "max_visible_depth": visit(roots, 1) if roots else 0,
        "nodes_hidden_by_folding": hidden_by_folding,
        "nodes_rejected_by_partition": rejected_by_partition,
    }


def _fact_metadata(conn: sqlite3.Connection, fact_ids: set[int]) -> dict[int, dict[str, Any]]:
    if not fact_ids:
        return {}
    placeholders = ",".join("?" for _ in fact_ids)
    rows = conn.execute(
        f"""
        SELECT f.id, f.financial_year, f.accounting_basis, f.estimate_status,
               f.unit, f.source_locator_json, d.source_key, d.source_family,
               d.landing_url, d.canonical_resource_url, m.compatibility_group
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        WHERE f.id IN ({placeholders})
        """,
        tuple(sorted(fact_ids)),
    ).fetchall()
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        try:
            locator = json.loads(row[5] or "{}")
        except (TypeError, json.JSONDecodeError):
            locator = {}
        result[int(row[0])] = {
            "financial_year": row[1],
            "accounting_basis": row[2],
            "estimate_status": row[3],
            "unit": row[4],
            "has_locator": bool(locator.get("locator") or locator.get("cell") or locator.get("page")),
            "source_key": row[6],
            "source_family": row[7],
            "has_source_url": bool(
                row[8]
                or row[9]
                or locator.get("landing_url")
                or locator.get("original_resource_url")
                or locator.get("cached_copy_path")
            ),
            "compatibility_group": row[10],
        }
    return result


def projection_signature(
    tree: dict[str, Any], spec: dict[str, str | None], conn: sqlite3.Connection
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return a compact deterministic signature and semantic hard failures."""
    fact_ids: set[int] = set()

    def collect_ids(node: dict[str, Any]) -> None:
        if isinstance(node.get("id"), int):
            fact_ids.add(int(node["id"]))
        for child in node.get("children") or []:
            collect_ids(child)

    collect_ids(tree)
    metadata = _fact_metadata(conn, fact_ids)
    counts: Counter[int] = Counter()
    branch_counts: Counter[str] = Counter()
    source_families: Counter[str] = Counter()
    units: Counter[str] = Counter()
    origin_counts: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    deepest_paths: list[tuple[int, str]] = []
    fact_leaf_count = 0
    cited_fact_leaf_count = 0
    fallback_count = 0
    exact_year_count = 0
    related_parent_paths: set[str] = set()
    max_additive_depth = 0
    max_related_depth = 0
    max_tree_depth = 0

    def walk(
        node: dict[str, Any],
        depth: int,
        semantic_depth: int,
        path: list[str],
        inherited_related: bool,
        parent_meta: dict[str, Any] | None,
    ) -> None:
        nonlocal fact_leaf_count, cited_fact_leaf_count, fallback_count
        nonlocal exact_year_count, max_additive_depth, max_related_depth, max_tree_depth
        name = str(node.get("name") or "")
        current_path = [*path, name]
        rel = _relationship(node, inherited_related)
        is_related = inherited_related or rel["branch_kind"] == "related"
        counts[depth] += 1
        branch_counts["related" if is_related else "additive"] += 1
        origin_counts[
            "edge_only" if rel.get("edge_set_id") else "path_only"
        ] += 1
        max_tree_depth = max(max_tree_depth, depth)
        current_semantic_depth = semantic_depth + (
            0 if rel["presentation_role"] == "navigation" else 1
        )
        if rel["presentation_role"] != "navigation":
            if is_related:
                max_related_depth = max(max_related_depth, current_semantic_depth)
            else:
                max_additive_depth = max(max_additive_depth, current_semantic_depth)

        fact_id = node.get("id")
        meta = metadata.get(int(fact_id)) if isinstance(fact_id, int) else None
        if meta:
            source_families[str(meta["source_family"])] += 1
            units[str(meta["unit"])] += 1
            if parent_meta and not is_related:
                if meta["compatibility_group"] != parent_meta["compatibility_group"]:
                    failures.append(
                        {
                            "kind": "cross_compatibility_additive_node",
                            "path": " / ".join(current_path),
                            "parent": parent_meta["compatibility_group"],
                            "child": meta["compatibility_group"],
                        }
                    )
                if meta["unit"] != parent_meta["unit"]:
                    failures.append(
                        {
                            "kind": "cross_unit_additive_node",
                            "path": " / ".join(current_path),
                            "parent": parent_meta["unit"],
                            "child": meta["unit"],
                        }
                    )

        is_fallback = bool(rel.get("is_year_fallback"))
        fact_year = rel.get("fact_financial_year") or (meta or {}).get("financial_year")
        requested_year = rel.get("requested_financial_year") or spec.get("year")
        if is_fallback:
            fallback_count += 1
            if not rel.get("fact_financial_year") or not rel.get("fallback_reason"):
                failures.append(
                    {"kind": "fallback_metadata_missing", "path": " / ".join(current_path)}
                )
            if _fy_start(fact_year) > _fy_start(requested_year):
                failures.append(
                    {
                        "kind": "future_year_fallback",
                        "path": " / ".join(current_path),
                        "requested_year": requested_year,
                        "fact_year": fact_year,
                    }
                )
        elif meta and fact_year == requested_year:
            exact_year_count += 1

        if inherited_related and rel["branch_kind"] != "related":
            failures.append(
                {"kind": "related_status_not_inherited", "path": " / ".join(current_path)}
            )
        children = node.get("children") or []
        if (
            children
            and not is_related
            and any(
                _relationship(child).get("branch_kind") == "related"
                for child in children
            )
        ):
            related_parent_paths.add(" / ".join(current_path))
        if not children:
            deepest_paths.append((depth, " / ".join(current_path)))
            if meta:
                fact_leaf_count += 1
                if meta["has_locator"] and meta["has_source_url"]:
                    cited_fact_leaf_count += 1
                else:
                    failures.append(
                        {"kind": "citation_incomplete", "path": " / ".join(current_path), "fact_id": fact_id}
                    )
        for child in children:
            walk(
                child,
                depth + 1,
                current_semantic_depth,
                current_path,
                is_related,
                meta or parent_meta,
            )

    projection_children = list(tree.get("children") or [])
    # The annual UI auto-enters the sole Commonwealth jurisdiction wrapper;
    # ring depth is measured from the first semantic function/portfolio ring.
    if spec.get("level") == "federal" and len(projection_children) == 1:
        sole_children = projection_children[0].get("children") or []
        if sole_children:
            projection_children = list(sole_children)

    for child in projection_children:
        walk(child, 1, 0, [], False, None)

    frontend = _frontend_depth_metrics(projection_children)
    first_level_names = sorted(str(child.get("name") or "") for child in projection_children)
    selected_child_sets: dict[str, list[str]] = {}

    def capture(node: dict[str, Any], path: list[str]) -> None:
        name = str(node.get("name") or "")
        current = [*path, name]
        if name in {"Health", "Defence", "Social protection", "Commonwealth"} and node.get("children"):
            selected_child_sets[" / ".join(current)] = sorted(
                str(child.get("name") or "") for child in node.get("children") or []
            )
        for child in node.get("children") or []:
            capture(child, current)

    for child in projection_children:
        capture(child, [])
    signature = {
        "label": spec["label"],
        "mode": spec["mode"],
        "level": spec["level"],
        "financial_year": spec["year"],
        "selected_basis": sorted(
            {meta["accounting_basis"] for meta in metadata.values() if meta.get("accounting_basis")}
        ),
        "root_total": round(float(tree.get("value") or 0), 6),
        "root_unit": tree.get("unit"),
        "node_count_by_depth": {str(depth): counts[depth] for depth in sorted(counts)},
        "max_tree_depth": max_tree_depth,
        "max_additive_depth": max_additive_depth,
        "max_related_depth": max_related_depth,
        **frontend,
        "branch_counts": dict(sorted(branch_counts.items())),
        "projection_origin_counts": {
            "path_only": origin_counts["path_only"],
            "edge_only": origin_counts["edge_only"],
            "path_plus_edge": 0,
        },
        "canonical_nodes_with_related_children": len(related_parent_paths),
        "exact_year_fact_nodes": exact_year_count,
        "fallback_fact_nodes": fallback_count,
        "source_families": dict(sorted(source_families.items())),
        "units": dict(sorted(units.items())),
        "first_level_names": first_level_names,
        "selected_child_name_sets": dict(sorted(selected_child_sets.items())),
        "deepest_path_samples": [path for _, path in sorted(deepest_paths, key=lambda item: (-item[0], item[1]))[:8]],
        "citation": {
            "fact_leaves": fact_leaf_count,
            "complete": cited_fact_leaf_count,
            "missing": fact_leaf_count - cited_fact_leaf_count,
        },
        "hard_failure_count": len(failures),
    }
    return signature, failures


def graph_integrity(conn: sqlite3.Connection) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = conn.execute(
        "SELECT parent_node_id, child_node_id, edge_kind, financial_year, crosswalk_id FROM breakdown_edges"
    ).fetchall()
    duplicate_counter = Counter((row[0], row[1], row[2], row[3] or "", row[4] or "") for row in rows)
    duplicates = [key for key, count in duplicate_counter.items() if count > 1]

    adjacency: dict[int, set[int]] = defaultdict(set)
    for parent, child, *_ in rows:
        adjacency[int(parent)].add(int(child))
    cycles: set[tuple[int, ...]] = set()
    visiting: set[int] = set()
    visited: set[int] = set()

    def dfs(node: int, stack: list[int]) -> None:
        if node in visiting:
            start = stack.index(node)
            cycles.add(tuple(stack[start:] + [node]))
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for child in adjacency.get(node, set()):
            dfs(child, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(adjacency):
        dfs(node, [])

    failures = [
        {"kind": "duplicate_semantic_edge", "identity": list(key)} for key in duplicates
    ] + [{"kind": "breakdown_cycle", "node_ids": list(cycle)} for cycle in sorted(cycles)]
    return (
        {
            "edge_count": len(rows),
            "duplicate_semantic_edges": len(duplicates),
            "cycles": len(cycles),
        },
        failures,
    )


def _resolve_year(client: TestClient, spec: dict[str, str | None]) -> str:
    if spec.get("year"):
        return str(spec["year"])
    response = client.get(
        "/v2/dashboard/years", params={"mode": spec["mode"], "level": spec["level"]}
    )
    response.raise_for_status()
    years = response.json()
    if not years:
        raise RuntimeError(f"no years for {spec['label']}")
    return str(years[-1])


def run_audit(db_path: Path = DB_PATH) -> dict[str, Any]:
    os.environ["FACTS_DB_PATH"] = str(db_path)
    import backend.facts_db as facts_db

    facts_db.FACTS_DB_FILE = db_path
    from backend.main import app

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    signatures = []
    failures: list[dict[str, Any]] = []
    with TestClient(app) as client:
        for raw_spec in PROJECTIONS:
            spec = dict(raw_spec)
            spec["year"] = _resolve_year(client, spec)
            response = client.get(
                "/v2/dashboard/tree",
                params={"mode": spec["mode"], "level": spec["level"], "year": spec["year"]},
            )
            response.raise_for_status()
            signature, projection_failures = projection_signature(response.json(), spec, conn)
            signatures.append(signature)
            failures.extend({"projection": spec["label"], **failure} for failure in projection_failures)
    graph, graph_failures = graph_integrity(conn)
    conn.close()
    failures.extend(graph_failures)
    return {
        "schema_version": 1,
        "database": str(db_path.relative_to(REPO_ROOT) if db_path.is_relative_to(REPO_ROOT) else db_path),
        "projections": signatures,
        "graph": graph,
        "hard_failures": failures,
        "hard_failure_count": len(failures),
    }


def _fixture_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload["schema_version"],
        "database": payload["database"],
        "projections": payload["projections"],
        "graph": payload["graph"],
    }


def _write_markdown(path: Path, payload: dict[str, Any], fixture_matches: bool | None) -> None:
    lines = [
        "# Dashboard depth and projection audit",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        f"Hard semantic failures: **{payload['hard_failure_count']}**",
        "",
        f"Golden fixture match: **{fixture_matches}**",
        "",
        "| projection | year | root total | additive depth | related depth | visible depth | fallback nodes | citations missing |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in payload["projections"]:
        lines.append(
            f"| {item['label']} | {item['financial_year']} | {item['root_total']} | "
            f"{item['max_additive_depth']} | {item['max_related_depth']} | "
            f"{item['max_visible_depth']} | {item['fallback_fact_nodes']} | "
            f"{item['citation']['missing']} |"
        )
    lines.extend(
        [
            "",
            "## Graph integrity",
            "",
            f"```json\n{json.dumps(payload['graph'], indent=2)}\n```",
            "",
            "## Hard failures",
            "",
            f"```json\n{json.dumps(payload['hard_failures'], indent=2)}\n```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--write-fixture", action="store_true")
    parser.add_argument("--check-fixture", action="store_true")
    parser.add_argument("--output-prefix", type=Path)
    args = parser.parse_args()

    payload = run_audit(args.db.resolve())
    fixture = _fixture_payload(payload)
    fixture_matches: bool | None = None
    if args.write_fixture:
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
        fixture_matches = True
    if args.check_fixture:
        expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        fixture_matches = expected == fixture

    now = datetime.now(timezone.utc)
    payload["generated_at"] = now.isoformat()
    payload["fixture_matches"] = fixture_matches
    prefix = args.output_prefix
    if prefix is None:
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        prefix = REPO_ROOT / "ops" / "reports" / f"dashboard-depth-audit-{stamp}"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, payload, fixture_matches)
    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(md_path),
                "fixture_matches": fixture_matches,
                "hard_failure_count": payload["hard_failure_count"],
            }
        )
    )
    if payload["hard_failure_count"]:
        return 1
    if args.check_fixture and not fixture_matches:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
