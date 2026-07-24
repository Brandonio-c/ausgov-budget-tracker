#!/usr/bin/env python3
"""Write breakdown coverage matrix (federal packs + state analogues note)."""

from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
OUT_DIR = REPO_ROOT / "ops" / "reports"
CROSSWALK = (
    REPO_ROOT / "config/breakdowns/crosswalks/cofog_to_budget_function.yaml"
)


def main(db_path: Path = DEFAULT_DB) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_csv = OUT_DIR / f"breakdown-coverage-{stamp}.csv"
    out_md = OUT_DIR / f"breakdown-coverage-{stamp}.md"

    cw = yaml.safe_load(CROSSWALK.read_text(encoding="utf-8")) or {}
    mappings = cw.get("mappings") or []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows_out: list[dict] = []

    for m in mappings:
        abs_name = m["abs"]
        budget_fn = m["budget"]
        quality = m.get("quality", "approx")

        abs_facts = conn.execute(
            """
            SELECT COUNT(*) AS n FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key LIKE 'abs_gfs_commonwealth%'
              AND n.name = ?
              AND f.financial_year = '2024-25'
            """,
            (abs_name,),
        ).fetchone()["n"]

        a61_subs = conn.execute(
            """
            SELECT COUNT(DISTINCT n.name) AS n FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = 'federal_budget_statement_6_a61'
              AND n.name LIKE ? AND n.name LIKE '% / %'
              AND n.name NOT LIKE '% / % / %'
            """,
            (f"{budget_fn} / %",),
        ).fetchone()["n"]

        components = conn.execute(
            """
            SELECT COUNT(DISTINCT n.name) AS n FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = 'federal_budget_statement_6_components'
              AND n.name LIKE ?
            """,
            (f"{budget_fn} / %",),
        ).fetchone()["n"]

        pbs = conn.execute(
            """
            SELECT COUNT(DISTINCT n.name) AS n FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = 'federal_dss_pbs_programs'
              AND n.name LIKE ?
            """,
            (f"{budget_fn} / %",),
        ).fetchone()["n"]

        related = conn.execute(
            """
            SELECT COUNT(DISTINCT e.child_node_id) AS n
            FROM breakdown_edges e
            JOIN nodes pn ON pn.id = e.parent_node_id
            JOIN source_documents d ON d.id = pn.source_document_id
            WHERE e.edge_kind = 'related_breakdown'
              AND d.source_key LIKE 'abs_gfs_commonwealth%'
              AND pn.name = ?
            """,
            (abs_name,),
        ).fetchone()["n"]

        deepest = "abs_only"
        if pbs:
            deepest = "pbs_program"
        elif components:
            deepest = "s6_component"
        elif a61_subs:
            deepest = "s6_subfunction"
        elif related:
            deepest = "related_total"

        rows_out.append(
            {
                "abs_purpose": abs_name,
                "budget_function": budget_fn,
                "crosswalk_quality": quality,
                "abs_commonwealth_2024_25_facts": abs_facts,
                "a61_subfunctions": a61_subs,
                "s6_component_nodes": components,
                "pbs_program_nodes": pbs,
                "related_child_edges": related,
                "deepest_layer": deepest,
                "state_analogue": (
                    "ABS GFS state Table_4 same_group only; "
                    "no Statement 6 / PBS analogues in packs yet"
                ),
            }
        )

    conn.close()

    fields = list(rows_out[0].keys()) if rows_out else []
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)

    lines = [
        "# Breakdown coverage matrix",
        "",
        f"Generated `{stamp}` from `{db_path.relative_to(REPO_ROOT)}`.",
        "",
        "Federal packs: `abs_gfs_table4` → `bp1_s6_a61` → `bp1_s6_components` → `pbs_programs_dss`.",
        "Related edges never roll into parent GFS pie totals.",
        "",
        "| ABS purpose | Budget function | Quality | A.6.1 subs | Components | PBS | Related | Deepest |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for r in rows_out:
        lines.append(
            f"| {r['abs_purpose']} | {r['budget_function']} | {r['crosswalk_quality']} | "
            f"{r['a61_subfunctions']} | {r['s6_component_nodes']} | {r['pbs_program_nodes']} | "
            f"{r['related_child_edges']} | {r['deepest_layer']} |"
        )
    lines.extend(
        [
            "",
            "## State / territory analogues",
            "",
            "- ABS GFS state and territory Table_4 workbooks remain the Actuals same_group source.",
            "- Commonwealth Budget Statement 6 and DSS PBS packs are federal-only.",
            "- Future state analogues: state budget paper function tables + agency PBS equivalents,",
            "  registered as separate packs with their own `compatibility_group` and crosswalks.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print({"csv": str(out_csv), "md": str(out_md), "rows": len(rows_out)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB))
