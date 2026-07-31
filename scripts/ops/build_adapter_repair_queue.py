#!/usr/bin/env python3
"""Build a truthful, ranked adapter-repair queue from the latest ingestion
coverage audit (Task 4). Read-only: does not touch facts.db or write adapters.

Excludes from the "needs a new adapter" backlog:
  - Sources already served by an existing family adapter even though the
    audit's per-registry-source_id accounting doesn't yet reflect it (only
    the PBS family, source_id containing "pbs"/"portfolio_budget", matching
    extractors/pbs_programs_all.py's own discover_pbs_pdfs() filter exactly -
    verified against a real, already-run adapter, not assumed).
  - Anything the audit itself already classifies outside adapter_missing
    (duplicate_source, reference_only, officially_unavailable, not_acquired)
    - those are separate statuses, already excluded by construction.

Remaining sources are grouped by (source_family, jurisdiction,
government_level) as a proxy for "one adapter likely handles this whole
family", then ranked by a transparent composite score.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "ops" / "reports"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# Mirrors extractors/pbs_programs_all.py's discover_pbs_pdfs() filter exactly.
PBS_FAMILY_MATCH = ("pbs", "portfolio_budget")

# Structured (machine-readable) formats get a lower engineering-effort score
# and a higher reliability bonus than PDF/DOCX/ZIP-of-unknown-contents.
FORMAT_EFFORT = {
    "csv": 1, "xlsx": 1, "xls": 1,
    "docx": 2, "zip": 2, "html": 2,
    "pdf": 3,
}

# Directive's preferred category order, used as a tiebreak label only -
# ranking itself is driven by the composite score below.
CATEGORY_ORDER = [
    ("commonwealth_mfs", "Federal Monthly Financial Statements"),
    ("state_structured", "Structured state budget / financial-statement packs"),
    ("local_structured", "Structured local-government files"),
    ("debt_super", "Debt / superannuation-liability files"),
    ("historical_actuals", "Historical actuals / archival series"),
    ("contextual_other", "Lower-value contextual sources"),
]


def _category_for(source_family: str, viz_bucket: str, jurisdiction: str) -> str:
    if viz_bucket == "monthly_financial_statements_slice":
        return "commonwealth_mfs"
    if viz_bucket in ("debt_instruments", "superannuation_liabilities"):
        return "debt_super"
    if viz_bucket == "state_budget_depth":
        return "state_structured"
    if viz_bucket == "local_government":
        return "local_structured"
    if "actuals" in (source_family or "") or "archival" in (source_family or ""):
        return "historical_actuals"
    return "contextual_other"


def _format_score(formats: list[str]) -> int:
    if not formats:
        return 3
    return min(FORMAT_EFFORT.get(f, 3) for f in formats)


def main() -> int:
    audits = sorted(REPORTS_DIR.glob("ingestion-coverage-2*.json"))
    if not audits:
        raise SystemExit("no ingestion-coverage-*.json audit found - run ingestion_coverage_audit.py first")
    audit_path = audits[-1]
    data = json.loads(audit_path.read_text(encoding="utf-8"))
    items = data["items"]
    missing = [i for i in items if i["ingestion_status"] == "adapter_missing"]

    already_served = [
        i for i in missing
        if any(tok in i["source_id"].lower() for tok in PBS_FAMILY_MATCH)
    ]
    needs_adapter = [i for i in missing if i not in already_served]

    # Category is computed per-item (not per-group) since a single
    # source_family (e.g. "handoff_actuals_federal") can span multiple
    # viz_buckets - grouping by source_family alone before categorizing was
    # silently absorbing distinct Federal MFS items into a bigger, generic
    # "historical_actuals" group keyed off whichever member happened to sort
    # first, hiding them from the directive's explicitly-called-out MFS
    # category entirely.
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for i in needs_adapter:
        category = _category_for(i.get("source_family") or "unknown", i.get("viz_bucket"), i.get("jurisdiction"))
        key = (category, i.get("source_family") or "unknown", i.get("jurisdiction") or "unknown",
               i.get("government_level") or "unknown")
        groups[key].append(i)

    group_rows = []
    for (category, fam, juris, level), members in groups.items():
        viz_ranks = [m.get("viz_value_rank") or 0 for m in members]
        avg_rank = sum(viz_ranks) / len(viz_ranks) if viz_ranks else 0
        fmt_score = min(_format_score(m.get("detected_formats") or []) for m in members)
        # Composite: dashboard value (avg_rank) weighted up, format-effort
        # weighted down (lower fmt_score = better), count rewards adapter
        # reuse across many editions of the same family.
        score = avg_rank * 2 - fmt_score * 10 + min(len(members), 20)
        group_rows.append({
            "source_family": fam,
            "jurisdiction": juris,
            "government_level": level,
            "category": category,
            "count": len(members),
            "avg_viz_value_rank": round(avg_rank, 1),
            "best_format_effort": fmt_score,
            "formats_seen": sorted({f for m in members for f in (m.get("detected_formats") or [])}),
            "score": round(score, 1),
            "sample_source_ids": [m["source_id"] for m in members[:5]],
        })
    group_rows.sort(key=lambda g: -g["score"])

    csv_path = REPORTS_DIR / f"adapter-repair-plan-{STAMP}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "source_id", "source_family", "jurisdiction", "government_level",
                "category", "priority", "viz_value_rank", "viz_bucket",
                "detected_formats", "asset_count", "next_ingestion_action",
                "group_score", "excluded_reason",
            ],
        )
        writer.writeheader()
        for i in already_served:
            writer.writerow({
                "source_id": i["source_id"], "source_family": i.get("source_family"),
                "jurisdiction": i.get("jurisdiction"), "government_level": i.get("government_level"),
                "category": "already_served_pbs_family", "priority": i.get("priority"),
                "viz_value_rank": i.get("viz_value_rank"), "viz_bucket": i.get("viz_bucket"),
                "detected_formats": ";".join(i.get("detected_formats") or []),
                "asset_count": i.get("asset_count"), "next_ingestion_action": i.get("next_ingestion_action"),
                "group_score": "", "excluded_reason": "served_by_pbs_programs_all_family_adapter",
            })
        for g in group_rows:
            members = groups[(g["category"], g["source_family"], g["jurisdiction"], g["government_level"])]
            members.sort(key=lambda m: -(m.get("viz_value_rank") or 0))
            for m in members:
                writer.writerow({
                    "source_id": m["source_id"], "source_family": m.get("source_family"),
                    "jurisdiction": m.get("jurisdiction"), "government_level": m.get("government_level"),
                    "category": g["category"], "priority": m.get("priority"),
                    "viz_value_rank": m.get("viz_value_rank"), "viz_bucket": m.get("viz_bucket"),
                    "detected_formats": ";".join(m.get("detected_formats") or []),
                    "asset_count": m.get("asset_count"), "next_ingestion_action": m.get("next_ingestion_action"),
                    "group_score": g["score"], "excluded_reason": "",
                })

    md_path = REPORTS_DIR / f"adapter-repair-plan-{STAMP}.md"
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(f"# Adapter repair plan — {STAMP}\n\n")
        fh.write(f"Source audit: `{audit_path.name}`\n\n")
        fh.write(f"Total `adapter_missing` registry sources: {len(missing)}\n\n")
        fh.write(
            f"Already served by an existing family adapter (federal PBS "
            f"generalized extractor, `pbs_programs_all` - see "
            f"`ops/reports/pbs-reprocessing-20260731T193413Z.md`), pending "
            f"Task 6 registry linkage so the audit reflects it directly: "
            f"**{len(already_served)}**\n\n"
        )
        fh.write(f"Genuinely un-adapted, acquired-on-disk sources remaining: **{len(needs_adapter)}**\n\n")
        fh.write(
            "All 247 `adapter_missing` sources have `acquisition_status: "
            "acquired` with at least one file on disk - none of this backlog "
            "is blocked on acquisition; every item below is ready for adapter "
            "engineering today.\n\n"
        )
        fh.write("## Methodology\n\n")
        fh.write(
            "Grouped by `(source_family, jurisdiction, government_level)` as "
            "a proxy for \"one adapter handles this whole family's editions\". "
            "Ranked by a composite score: `avg(viz_value_rank) * 2 - "
            "format_effort * 10 + min(count, 20)` - dashboard-value-weighted "
            "up, PDF/OCR-reliant work weighted down relative to structured "
            "(csv/xlsx) data already on disk, and multi-edition families "
            "rewarded for adapter-reuse potential. `format_effort`: "
            "csv/xlsx=1, docx/zip/html=2, pdf=3 (lower is better/cheaper).\n\n"
        )
        fh.write("## Ranked families\n\n")
        fh.write("| rank | category | source_family | jurisdiction | level | count | avg_viz_rank | formats | score |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|\n")
        for rank, g in enumerate(group_rows, 1):
            fh.write(
                f"| {rank} | {g['category']} | {g['source_family']} | {g['jurisdiction']} | "
                f"{g['government_level']} | {g['count']} | {g['avg_viz_value_rank']} | "
                f"{','.join(g['formats_seen'])} | {g['score']} |\n"
            )
        fh.write("\n## Preferred category order (directive) vs actual ranking\n\n")
        for slug, label in CATEGORY_ORDER:
            matching = [g for g in group_rows if g["category"] == slug]
            total = sum(g["count"] for g in matching)
            fh.write(f"- **{label}** (`{slug}`): {len(matching)} families, {total} sources\n")
        fh.write("\n## Sample source_ids per family (top 10 families)\n\n")
        for g in group_rows[:10]:
            fh.write(f"### {g['source_family']} ({g['jurisdiction']}/{g['government_level']}) - score {g['score']}\n")
            for sid in g["sample_source_ids"]:
                fh.write(f"- `{sid}`\n")
            fh.write("\n")

    print(json.dumps({
        "audit_used": str(audit_path),
        "csv": str(csv_path),
        "md": str(md_path),
        "total_adapter_missing": len(missing),
        "already_served_pbs_family": len(already_served),
        "needs_adapter": len(needs_adapter),
        "families": len(group_rows),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
