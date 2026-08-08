#!/usr/bin/env python3
"""Read-only audit of federal budget path children versus same-group edges."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "facts.db"
sys.path.insert(0, str(REPO_ROOT / "src"))

from backend.breakdown_graph import (  # noqa: E402
    apply_edge_cascade_to_budget_tree,
    build_same_group_subtree,
    primary_node_id,
)
from backend.routers.v2.dashboard import _build_tree_dict, _fact_rows, _to_tree_node  # noqa: E402


def _normal(name: str) -> str:
    return " / ".join(part.strip().casefold() for part in name.split(" / ") if part.strip())


def _root_total(tree: dict[str, Any], year: str) -> float:
    return sum(
        node.value
        for name, raw in (tree.get("children") or {}).items()
        if (
            node := _to_tree_node(
                name,
                raw,
                requested_financial_year=year,
                include_relationship=False,
            )
        )
    )


def _node_at_path(tree: dict[str, Any], path: list[str]) -> dict[str, Any] | None:
    node = tree
    for name in path:
        node = (node.get("children") or {}).get(name)
        if node is None:
            return None
    return node


def audit_year(
    conn: sqlite3.Connection,
    year: str,
    *,
    replacement_baseline_total: float | None = None,
) -> dict[str, Any]:
    rows = _fact_rows(conn, "budget", "federal", year)
    tree = _build_tree_dict(rows, mode="budget")
    before_total = _root_total(tree, year)
    comparisons: list[dict[str, Any]] = []

    def visit(node: dict[str, Any], path: list[str]) -> None:
        children = node.get("children") or {}
        for child_name, child in children.items():
            visit(child, [*path, child_name])

        node_id = node.get("node_id")
        if not node_id and node.get("fact_id"):
            node_id = primary_node_id(conn, int(node["fact_id"]))
        if not node_id:
            return
        edge_list, _ = build_same_group_subtree(
            conn,
            int(node_id),
            year,
            allow_nearest_fy=False,
        )
        if not edge_list:
            return
        path_by_key = {_normal(name): name for name in children}
        edge_by_key = {_normal(item["name"]): item["name"] for item in edge_list}
        path_keys = set(path_by_key)
        edge_keys = set(edge_by_key)
        comparisons.append(
            {
                "path": " / ".join(path),
                "path_parts": path,
                "node_id": int(node_id),
                "path_children": sorted(path_by_key.values()),
                "edge_children": sorted(edge_by_key.values()),
                "path_only": sorted(path_by_key[key] for key in path_keys - edge_keys),
                "edge_only": sorted(edge_by_key[key] for key in edge_keys - path_keys),
                "path_plus_edge": sorted(path_by_key[key] for key in path_keys & edge_keys),
                "would_drop_count": len(path_keys - edge_keys),
            }
        )

    for name, child in (tree.get("children") or {}).items():
        visit(child, [name])

    projected = copy.deepcopy(tree)
    apply_edge_cascade_to_budget_tree(conn, projected, year)
    after_total = _root_total(projected, year)
    missing_after_augment: list[dict[str, Any]] = []
    for item in comparisons:
        projected_parent = _node_at_path(projected, item["path_parts"])
        projected_names = {
            _normal(name) for name in (projected_parent or {}).get("children", {})
        }
        missing = [
            name for name in item["path_only"] if _normal(name) not in projected_names
        ]
        if missing:
            missing_after_augment.append({"path": item["path"], "children": missing})
    return {
        "financial_year": year,
        "fact_rows": len(rows),
        "parents_with_edges": len(comparisons),
        "parents_with_path_only_children": sum(bool(item["path_only"]) for item in comparisons),
        "path_only_children_that_current_replace_would_drop": sum(
            item["would_drop_count"] for item in comparisons
        ),
        "edge_only_children": sum(len(item["edge_only"]) for item in comparisons),
        "path_plus_edge_children": sum(len(item["path_plus_edge"]) for item in comparisons),
        "root_total_before": before_total,
        "root_total_after_projection": after_total,
        "replacement_baseline_root_total": replacement_baseline_total,
        "root_total_delta_vs_replacement_baseline": (
            after_total - replacement_baseline_total
            if replacement_baseline_total is not None
            else None
        ),
        "path_only_missing_after_augment": missing_after_augment,
        "comparisons": comparisons,
    }


def run(
    db_path: Path = DB_PATH, baseline_json: Path | None = None
) -> dict[str, Any]:
    os.environ["FACTS_DB_PATH"] = str(db_path)
    import backend.facts_db as facts_db

    facts_db.FACTS_DB_FILE = db_path
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    years = [
        str(row[0])
        for row in conn.execute(
            """
            SELECT DISTINCT f.financial_year
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            WHERE m.compatibility_group = 'budget_expense'
              AND d.government_level IN ('federal', 'national')
              AND f.estimate_status IN ('budget', 'forward_estimate', 'revised_estimate', 'estimated_actual')
            ORDER BY f.financial_year
            """
        ).fetchall()
    ]
    baseline_totals: dict[str, float] = {}
    if baseline_json:
        baseline = json.loads(baseline_json.read_text(encoding="utf-8"))
        baseline_totals = {
            str(item["financial_year"]): float(item["root_total_after_current_replace"])
            for item in baseline["years"]
        }
    results = [
        audit_year(
            conn,
            year,
            replacement_baseline_total=baseline_totals.get(year),
        )
        for year in years
    ]
    conn.close()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": str(db_path),
        "years": results,
        "summary": {
            "year_count": len(results),
            "parents_with_path_only_children": sum(
                item["parents_with_path_only_children"] for item in results
            ),
            "path_only_children_that_current_replace_would_drop": sum(
                item["path_only_children_that_current_replace_would_drop"] for item in results
            ),
            "path_only_children_missing_after_augment": sum(
                len(missing["children"])
                for item in results
                for missing in item["path_only_missing_after_augment"]
            ),
            "years_with_root_total_delta_vs_replacement_baseline": [
                item["financial_year"]
                for item in results
                if item["root_total_delta_vs_replacement_baseline"] is not None
                and abs(item["root_total_delta_vs_replacement_baseline"]) > 0.5
            ],
        },
    }


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Federal budget path-versus-edge cascade validation",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "This read-only validation checks the augmenting cascade against the captured pre-change replacement totals.",
        "",
        "| year | parents with edges | parents with path-only children | path-only retained | edge-only | collisions | delta vs replacement baseline |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in payload["years"]:
        lines.append(
            f"| {item['financial_year']} | {item['parents_with_edges']} | "
            f"{item['parents_with_path_only_children']} | "
            f"{item['path_only_children_that_current_replace_would_drop'] - sum(len(m['children']) for m in item['path_only_missing_after_augment'])} | "
            f"{item['edge_only_children']} | {item['path_plus_edge_children']} | "
            f"{item['root_total_delta_vs_replacement_baseline']} |"
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"```json\n{json.dumps(payload['summary'], indent=2)}\n```",
            "",
            "## Parents with path-only children",
            "",
        ]
    )
    found = False
    for result in payload["years"]:
        for item in result["comparisons"]:
            if not item["path_only"]:
                continue
            found = True
            lines.append(
                f"- `{result['financial_year']}` `{item['path']}`: "
                f"path-only={json.dumps(item['path_only'])}; "
                f"edge-only={json.dumps(item['edge_only'])}; "
                f"collisions={json.dumps(item['path_plus_edge'])}"
            )
    if not found:
        lines.append("None.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output-prefix", type=Path)
    parser.add_argument("--baseline-json", type=Path)
    args = parser.parse_args()
    payload = run(
        args.db.resolve(),
        args.baseline_json.resolve() if args.baseline_json else None,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = args.output_prefix or REPO_ROOT / "ops" / "reports" / f"budget-edge-cascade-preflight-{stamp}"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, payload)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), **payload["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
