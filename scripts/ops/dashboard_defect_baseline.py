#!/usr/bin/env python3
"""Task 1 (semantic-defect milestone): build a timestamped baseline report
of the production audit's structural findings, walking the real API tree
for each required path and cross-referencing every visited fact against
facts.db directly (source_key, government_level, jurisdiction, financial
year, measure_type, compatibility_group, estimate_status) to classify
suspected defects.

Read-only against both the API and facts.db. Does not modify the database.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "facts.db"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

PATHS: list[dict[str, str]] = [
    {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "year": "2024-25", "jurisdiction": None},
    {"label": "qld_state_actuals_2024_25", "mode": "actuals", "level": "state", "year": "2024-25", "jurisdiction": "QLD"},
    {"label": "local_government_actuals_2024_25", "mode": "actuals", "level": "local", "year": None, "jurisdiction": None},
]

# Crude, first-pass label-quality smell test for the baseline only - the
# real classifier (Task 5) is more thorough; this exists so the baseline
# report doesn't need to wait on it.
HEADER_SMELL = re.compile(
    r"\$['’]?000|\$m\b|\$b\b|EXPENSES|ASSETS|LIABILITIES|REVENUE|CASH FLOW|EQUITY|EMPLOYEE BENEFITS",
    re.I,
)
NUMERIC_SEQUENCE = re.compile(r"(-?\(?\d[\d,]{2,}\)?\s*){3,}")


def _get(base_url: str, path: str, **params) -> Any:
    resp = requests.get(f"{base_url}{path}", params={k: v for k, v in params.items() if v is not None}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fact_row(conn: sqlite3.Connection, fact_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT f.id, f.financial_year, f.estimate_status, f.measure_type, m.compatibility_group,
               d.source_key, d.government_level, d.jurisdiction
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        WHERE f.id = ?
        """,
        (fact_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "fact_id": row[0],
        "financial_year": row[1],
        "estimate_status": row[2],
        "measure_type": row[3],
        "compatibility_group": row[4],
        "source_key": row[5],
        "government_level": row[6],
        "jurisdiction": row[7],
    }


def _label_defect(label: str) -> str | None:
    if HEADER_SMELL.search(label or ""):
        return "label_quality_header_or_financial_statement_line"
    if NUMERIC_SEQUENCE.search(label or ""):
        return "label_quality_concatenated_numeric_row"
    if len(label or "") > 160:
        return "label_quality_excessive_length"
    return None


def walk(
    base_url: str,
    conn: sqlite3.Connection,
    node: dict[str, Any],
    *,
    path_spec: dict[str, str],
    parent_fact: dict[str, Any] | None,
    parent_amount: float | None,
    parent_edge_kind: str,
    rows: list[dict[str, Any]],
    depth: int,
    max_depth: int,
) -> None:
    if depth > max_depth:
        return
    fact_id = node.get("id")
    amount = float(node.get("value") or 0)
    breakdown = node.get("breakdown") or {}
    edge_kind = breakdown.get("kind") or parent_edge_kind
    fact_row = _fact_row(conn, fact_id) if fact_id else None

    defects = []
    if fact_row:
        requested_level = path_spec["level"]
        if requested_level == "federal":
            expected_levels = {"federal", "national"}
        else:
            expected_levels = {requested_level}
        if fact_row["government_level"] not in expected_levels and edge_kind != "related_breakdown":
            defects.append(f"cross_government_leak:{fact_row['government_level']}_in_{requested_level}_additive_path")
        req_jur = path_spec.get("jurisdiction")
        if req_jur and fact_row["jurisdiction"] and req_jur.lower() not in fact_row["jurisdiction"].lower() and edge_kind != "related_breakdown":
            defects.append(f"cross_jurisdiction_leak:{fact_row['jurisdiction']}_in_{req_jur}_additive_path")
        if parent_fact and edge_kind != "related_breakdown" and parent_fact.get("financial_year") != fact_row.get("financial_year"):
            defects.append("cross_year_silent_mismatch")

    pct = (amount / parent_amount) if parent_amount else None
    if pct is not None and edge_kind != "related_breakdown" and pct > 1.0:
        defects.append(f"additive_over_100pct:{pct:.2%}")

    label_defect = _label_defect(node.get("name") or "")
    if label_defect:
        defects.append(label_defect)

    if fact_id or defects:
        rows.append(
            {
                "path": path_spec["label"],
                "requested_mode": path_spec["mode"],
                "requested_level": path_spec["level"],
                "requested_jurisdiction": path_spec.get("jurisdiction") or "",
                "fact_id": fact_id,
                "fact_source_key": (fact_row or {}).get("source_key"),
                "fact_government_level": (fact_row or {}).get("government_level"),
                "fact_jurisdiction": (fact_row or {}).get("jurisdiction"),
                "parent_fact_id": (parent_fact or {}).get("fact_id"),
                "edge_kind": edge_kind,
                "parent_amount": parent_amount,
                "child_amount": amount,
                "percent_of_parent": pct,
                "parent_financial_year": (parent_fact or {}).get("financial_year"),
                "child_financial_year": (fact_row or {}).get("financial_year"),
                "label": (node.get("name") or "")[:200],
                "suspected_defect_class": ";".join(defects) if defects else "",
            }
        )

    for child in node.get("children") or []:
        walk(
            base_url,
            conn,
            child,
            path_spec=path_spec,
            parent_fact=fact_row or parent_fact,
            parent_amount=amount,
            parent_edge_kind=edge_kind,
            rows=rows,
            depth=depth + 1,
            max_depth=max_depth,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    conn = sqlite3.connect(str(args.db))
    all_rows: list[dict[str, Any]] = []
    for spec in PATHS:
        try:
            years = [spec["year"]] if spec["year"] else _get(args.base_url, "/v2/dashboard/years", mode=spec["mode"], level=spec["level"])
            year = years[-1] if not spec["year"] else spec["year"]
            tree = _get(args.base_url, "/v2/dashboard/tree", mode=spec["mode"], level=spec["level"], year=year)
        except Exception as exc:  # noqa: BLE001
            all_rows.append({"path": spec["label"], "suspected_defect_class": f"transport_error:{exc}"})
            continue
        # /dashboard/tree for level=state/local returns EVERY jurisdiction
        # as a top-level sibling in one response (by design - it's not a
        # per-jurisdiction endpoint). Walking the whole response and
        # labelling every node with one requested jurisdiction would
        # falsely flag every *other* legitimate sibling jurisdiction as a
        # "leak". Scope the walk to the matching top-level branch only
        # when a specific jurisdiction was requested.
        roots = tree.get("children") or [tree]
        req_jur = spec.get("jurisdiction")
        if req_jur:
            roots = [r for r in roots if req_jur.lower() in (r.get("name") or "").lower()] or roots
        for root in roots:
            walk(
                args.base_url, conn, root, path_spec=spec, parent_fact=None, parent_amount=None,
                parent_edge_kind="additive", rows=all_rows, depth=0, max_depth=args.max_depth,
            )
    conn.close()

    defect_rows = [r for r in all_rows if r.get("suspected_defect_class")]

    csv_path = REPO_ROOT / f"ops/reports/dashboard-defect-baseline-{STAMP}.csv"
    md_path = REPO_ROOT / f"ops/reports/dashboard-defect-baseline-{STAMP}.md"
    fieldnames = [
        "path", "requested_mode", "requested_level", "requested_jurisdiction",
        "fact_id", "fact_source_key", "fact_government_level", "fact_jurisdiction",
        "parent_fact_id", "edge_kind", "parent_amount", "child_amount", "percent_of_parent",
        "parent_financial_year", "child_financial_year", "label", "suspected_defect_class",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    from collections import Counter
    defect_counts = Counter()
    for r in defect_rows:
        for d in r["suspected_defect_class"].split(";"):
            defect_counts[d.split(":")[0]] += 1

    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(f"# Dashboard defect baseline — {STAMP}\n\n")
        fh.write(f"Base URL: `{args.base_url}`\n\n")
        fh.write(f"Total nodes visited across {len(PATHS)} paths: {len(all_rows)}\n\n")
        fh.write(f"Nodes with a suspected defect: **{len(defect_rows)}**\n\n")
        fh.write("## Defect class counts\n\n")
        for cls, count in defect_counts.most_common():
            fh.write(f"- `{cls}`: {count}\n")
        fh.write("\n## Sample defect rows\n\n")
        for r in defect_rows[:40]:
            fh.write(
                f"- `{r['path']}` fact_id={r.get('fact_id')} "
                f"({r.get('fact_government_level')}/{r.get('fact_jurisdiction')}) "
                f"label=\"{r['label']}\" -> {r['suspected_defect_class']}\n"
            )

    print(json.dumps({"csv": str(csv_path), "md": str(md_path), "total_rows": len(all_rows), "defect_rows": len(defect_rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
