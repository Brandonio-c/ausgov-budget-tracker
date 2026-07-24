#!/usr/bin/env python3
"""Write handoff download + ingest status report for all 281 sources."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
HANDOFF = REPO / "data/new/ausgov_additional_data_handoff.yaml"
FACTS = REPO / "data/facts.db"
OUT = REPO / "ops/reports/handoff-download-status.md"
OUT_FULL = REPO / f"ops/reports/handoff-full-acquire-ingest-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"


def has_latest(source_id: str) -> bool:
    for m in (REPO / "data/raw").rglob(source_id):
        if m.is_dir() and (m / "latest.json").exists():
            return True
    return False


def main() -> int:
    doc = yaml.safe_load(HANDOFF.read_text(encoding="utf-8"))
    conn = sqlite3.connect(str(FACTS)) if FACTS.exists() else None
    rows = []
    counts = {
        "downloaded": 0,
        "on_disk": 0,
        "ingested": 0,
        "missing": 0,
        "blocked": 0,
        "reference": 0,
    }
    for src in doc["sources"]:
        sid = src["proposed_source_id"]
        action = src.get("recommended_action") or ""
        on_disk_flag = bool(src.get("already_on_disk"))
        present = has_latest(sid) or (on_disk_flag and src.get("repo_source_key") and has_latest(str(src["repo_source_key"])))
        # also check repo_source_key path
        if not present and src.get("repo_source_key"):
            present = has_latest(str(src["repo_source_key"]))
        ingested = 0
        if conn is not None:
            # match by source_key containing proposed id or repo key
            keys = [sid]
            if src.get("repo_source_key"):
                keys.append(str(src["repo_source_key"]))
            placeholders = ",".join("?" for _ in keys)
            # source_documents.source_key exact or facts via LIKE
            q = f"SELECT COUNT(*) FROM facts f JOIN source_documents d ON d.id=f.source_document_id WHERE d.source_key IN ({placeholders})"
            ingested = conn.execute(q, keys).fetchone()[0]
            if ingested == 0:
                like = "%" + sid.replace("_facts", "") + "%"
                ingested = conn.execute(
                    "SELECT COUNT(*) FROM facts f JOIN source_documents d ON d.id=f.source_document_id WHERE d.source_key LIKE ?",
                    (like,),
                ).fetchone()[0]

        if action == "REFERENCE_ONLY" and not present:
            status = "reference_only"
            counts["reference"] += 1
        elif present:
            status = "downloaded" if not on_disk_flag else "already_on_disk"
            counts["downloaded" if status == "downloaded" else "on_disk"] += 1
        elif "MANUAL" in action or "BLOCKED" in action:
            status = "blocked_or_manual"
            counts["blocked"] += 1
        else:
            status = "missing"
            counts["missing"] += 1
        if ingested:
            counts["ingested"] += 1
        rows.append(
            {
                "id": sid,
                "action": action,
                "priority": src.get("priority"),
                "status": status,
                "facts": ingested,
                "title": (src.get("title") or "")[:80],
            }
        )

    if conn:
        measure_counts = conn.execute(
            """
            SELECT f.measure_type, COALESCE(m.compatibility_group, ''), COUNT(*)
            FROM facts f
            LEFT JOIN measure_definitions m ON m.measure_type = f.measure_type
            GROUP BY 1, 2
            ORDER BY 3 DESC
            """
        ).fetchall()
        conn.close()
    else:
        measure_counts = []

    def render(path: Path, title: str) -> None:
        lines = [
            f"# {title}",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Totals",
            "",
            f"- Handoff rows: **{len(rows)}**",
            f"- Already on disk (confirmed present): **{counts['on_disk']}**",
            f"- Newly downloaded / imported: **{counts['downloaded']}**",
            f"- Missing (no latest.json): **{counts['missing']}**",
            f"- Blocked/manual unresolved: **{counts['blocked']}**",
            f"- Reference-only (no file expected): **{counts['reference']}**",
            f"- Rows with ≥1 facts keyed to source: **{counts['ingested']}**",
            "",
            "## Measure family counts in facts.db",
            "",
            "| measure_type | compatibility_group | facts |",
            "|---|---|---:|",
        ]
        for mt, cg, n in measure_counts:
            lines.append(f"| {mt} | {cg} | {n} |")
        lines += ["", "## Per-source status", "", "| id | action | priority | status | facts | title |", "|---|---|---|---|---:|---|"]
        for r in rows:
            lines.append(
                f"| `{r['id']}` | {r['action']} | {r['priority']} | {r['status']} | {r['facts']} | {r['title'].replace('|','/')} |"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {path}")

    render(OUT, "Handoff download status")
    render(OUT_FULL, "Handoff full acquire + ingest coverage")
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
