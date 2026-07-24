#!/usr/bin/env python3
"""Emit visualization-depth + ingest-maximise handoff reports."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "facts.db"
OPS = REPO / "ops" / "reports"


def fact_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0])


def by_measure(conn: sqlite3.Connection) -> list[tuple]:
    return conn.execute(
        """
        SELECT measure_type, COUNT(*) AS n
        FROM facts
        GROUP BY 1
        ORDER BY n DESC
        LIMIT 40
        """
    ).fetchall()


def by_source(conn: sqlite3.Connection) -> list[tuple]:
    return conn.execute(
        """
        SELECT d.source_key, COUNT(*) AS n
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        GROUP BY 1
        ORDER BY n DESC
        LIMIT 40
        """
    ).fetchall()


def ring_depth_proxy(conn: sqlite3.Connection, group: str) -> dict:
    """Approximate ring depth as max path segments in node names for a mode group."""
    rows = conn.execute(
        """
        SELECT n.name
        FROM facts f
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        WHERE m.compatibility_group = ?
        """,
        (group,),
    ).fetchall()
    depths = [len([p for p in (r[0] or "").split(" / ") if p.strip()]) for r in rows]
    if not depths:
        return {"facts": 0, "max_segments": 0, "avg_segments": 0.0}
    return {
        "facts": len(depths),
        "max_segments": max(depths),
        "avg_segments": round(sum(depths) / len(depths), 2),
    }


def main() -> int:
    OPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    conn = sqlite3.connect(str(DB))
    before_note = "Baseline at plan start was ~270,937 facts / 92 source docs"
    total = fact_count(conn)
    sources = int(conn.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0])
    modes = {
        "actual_expense": ring_depth_proxy(conn, "actual_expense"),
        "budget_expense": ring_depth_proxy(conn, "budget_expense"),
        "gfs_liability": ring_depth_proxy(conn, "gfs_liability"),
        "gfs_revenue": ring_depth_proxy(conn, "gfs_revenue"),
        "gdp": ring_depth_proxy(conn, "gdp"),
    }
    measures = by_measure(conn)
    top_sources = by_source(conn)
    specials = {
        "pbs_programs_all": conn.execute(
            "SELECT COUNT(*) FROM facts f JOIN source_documents d ON d.id=f.source_document_id "
            "WHERE d.source_key='federal_pbs_programs_all'"
        ).fetchone()[0],
        "borrowing_authority": conn.execute(
            "SELECT COUNT(*) FROM facts WHERE measure_type='borrowing_authority_debt_outstanding'"
        ).fetchone()[0],
        "superannuation_liability": conn.execute(
            "SELECT COUNT(*) FROM facts WHERE measure_type='superannuation_liability'"
        ).fetchone()[0],
        "gsp_current": conn.execute(
            "SELECT COUNT(*) FROM facts WHERE measure_type='gsp_current'"
        ).fetchone()[0],
        "gdp_chain_volume": conn.execute(
            "SELECT COUNT(*) FROM facts WHERE measure_type='gdp_chain_volume'"
        ).fetchone()[0],
        "with_observation_date": conn.execute(
            "SELECT COUNT(*) FROM facts WHERE observation_date IS NOT NULL"
        ).fetchone()[0],
        "with_valuation_basis": conn.execute(
            "SELECT COUNT(*) FROM facts WHERE valuation_basis IS NOT NULL"
        ).fetchone()[0],
    }
    conn.close()

    depth_path = OPS / f"visualization-depth-{stamp}.md"
    depth_path.write_text(
        "# Visualization depth (post maximise ingest)\n\n"
        f"- Generated: `{stamp}`\n"
        f"- {before_note}\n"
        f"- Current facts: **{total:,}**; source_documents: **{sources}**\n\n"
        "## Ring-depth proxy by compatibility group\n\n"
        "| Mode group | Facts | Max path segments | Avg segments |\n"
        "|---|---:|---:|---:|\n"
        + "".join(
            f"| `{k}` | {v['facts']:,} | {v['max_segments']} | {v['avg_segments']} |\n"
            for k, v in modes.items()
        )
        + "\n## Special series\n\n"
        + "\n".join(f"- `{k}`: {v:,}" for k, v in specials.items())
        + "\n",
        encoding="utf-8",
    )

    handoff = {
        "generated_at": stamp,
        "baseline_note": before_note,
        "facts_total": total,
        "source_documents": sources,
        "modes": modes,
        "specials": specials,
        "top_measures": [{"measure_type": m, "n": n} for m, n in measures],
        "top_sources": [{"source_key": s, "n": n} for s, n in top_sources],
        "remaining_gaps": [
            "Defence PBS PDFs still yield 0 program rows (layout/OCR).",
            "Most QLD SDS PDFs marked extraction_unreliable pending stable table patterns.",
            "QAO local PDFs: no_useful_fiscal_data — use structured VLGGC/OLG/CDC returns.",
            "Do not commit facts.db or raw downloads.",
        ],
    }
    (OPS / f"ingest-maximise-handoff-{stamp}.json").write_text(
        json.dumps(handoff, indent=2), encoding="utf-8"
    )
    (OPS / f"ingest-maximise-handoff-{stamp}.md").write_text(
        "# Ingest maximise handoff\n\n"
        f"- Generated: `{stamp}`\n"
        f"- Facts: **{total:,}** (baseline ~270,937)\n"
        f"- Source documents: **{sources}**\n\n"
        "## Highlights\n\n"
        + "\n".join(f"- `{k}`: {v:,}" for k, v in specials.items())
        + "\n\n## Remaining gaps\n\n"
        + "\n".join(f"- {g}" for g in handoff["remaining_gaps"])
        + "\n\nSee also `visualization-depth-*.md`, `debt-reconciliation-*.md`, "
        "`ingestion-coverage-*.md`, `qld-sds-extraction-*.md`, `local-qao-limits-*.md`.\n",
        encoding="utf-8",
    )
    print(json.dumps({"depth": str(depth_path), "handoff_stamp": stamp, "facts": total}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
