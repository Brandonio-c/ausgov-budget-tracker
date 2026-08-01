#!/usr/bin/env python3
"""Link federal_pbs_programs_all facts into the Statement 6 hierarchy as
non-additive related_breakdown navigation.

Design (see config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml for
the full evidence-tiered mapping and its rationale):

1. Ensure each PBS portfolio has its own folder node (e.g. "Health Disability
   and Ageing") and that every individual PBS program node hangs off it via
   a same_group edge - internal PBS-family navigation, not touching any GFS
   total. Reuses the existing, already-tested
   breakdown_pack.link_same_group_from_paths().
2. For each PBS portfolio with a mapped default in the crosswalk, add ONE
   related_breakdown edge: Statement 6 (function[, subfunction]) node ->
   PBS portfolio folder node. This is the single non-additive "boundary
   crossing"; everything under the portfolio folder is already same_group
   nested from step 1, so it drills further without re-crossing measure
   families.
3. For each program_label_override match (an exact, case-insensitive
   substring in program_label, corroborated by portfolio), add a MORE
   SPECIFIC related_breakdown edge: Statement 6 (subfunction[, component])
   node -> that specific PBS program node directly (bypassing the
   portfolio-level default, since these are the known exceptions that
   belong under a different Statement 6 destination than the rest of their
   portfolio - e.g. NDIA/NDIS programs administered within the Health
   portfolio but classified under Social security and welfare).
4. Portfolios with crosswalk status "ambiguous", or with no crosswalk entry
   at all, get no related_breakdown edge and are reported as unmapped/
   ambiguous with the documented reason - never guessed.

All edges use edge_kind='related_breakdown' (portfolio-boundary-crossing) or
'same_group' (internal PBS-family nesting only, never crossing into GFS/S6
totals), financial_year=NULL (edges are year-agnostic; per-year fact
resolution and FY-mismatch banners are handled by the existing
build_related_subtree()/build_same_group_subtree() at render time), and
crosswalk_id='pbs_programs_all_under_s6' for full traceability. Idempotent:
INSERT OR IGNORE against breakdown_edges' existing UNIQUE constraint.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from breakdown_pack import link_same_group_from_paths  # noqa: E402

CROSSWALK_PATH = REPO_ROOT / "config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml"
PBS_SOURCE_KEY = "federal_pbs_programs_all"
S6_SOURCE_KEY_PREFIX = "federal_budget_statement_6"
CROSSWALK_ID = "pbs_programs_all_under_s6"
REPORTS_DIR = REPO_ROOT / "ops" / "reports"


def load_crosswalk(path: Path = CROSSWALK_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_portfolio_and_label(node_name: str) -> tuple[str, str]:
    if " / " not in node_name:
        return node_name, ""
    portfolio, label = node_name.split(" / ", 1)
    return portfolio, label


def classify_program(
    portfolio: str, program_label: str, crosswalk: dict[str, Any]
) -> dict[str, Any]:
    """Return the crosswalk decision for one PBS program, checking
    program_label_overrides (evidence tier 4) before portfolio_defaults
    (evidence tier 2), per the documented evidence order."""
    label_lower = (program_label or "").lower()
    for override in crosswalk.get("program_label_overrides") or []:
        if override.get("pbs_portfolio") != portfolio:
            continue
        needle = str(override.get("label_contains") or "").lower()
        if needle and needle in label_lower:
            return {
                "status": "mapped",
                "statement6_function": override.get("statement6_function"),
                "statement6_subfunction": override.get("statement6_subfunction"),
                "statement6_component": override.get("statement6_component"),
                "confidence": override.get("confidence"),
                "evidence": override.get("evidence"),
                "reason": None,
                "match_source": "program_label_override",
            }

    for default in crosswalk.get("portfolio_defaults") or []:
        if default.get("pbs_portfolio") != portfolio:
            continue
        if default.get("status") == "ambiguous":
            return {
                "status": "ambiguous",
                "statement6_function": None,
                "statement6_subfunction": None,
                "statement6_component": None,
                "confidence": default.get("confidence"),
                "evidence": default.get("evidence"),
                "reason": default.get("reason"),
                "match_source": "portfolio_default",
            }
        return {
            "status": "mapped",
            "statement6_function": default.get("statement6_function"),
            "statement6_subfunction": default.get("statement6_subfunction"),
            "statement6_component": default.get("statement6_component"),
            "confidence": default.get("confidence"),
            "evidence": default.get("evidence"),
            "reason": None,
            "match_source": "portfolio_default",
        }

    return {
        "status": "unmapped",
        "statement6_function": None,
        "statement6_subfunction": None,
        "statement6_component": None,
        "confidence": None,
        "evidence": None,
        "reason": "portfolio_not_in_crosswalk",
        "match_source": None,
    }


_s6_node_id_cache: dict[str, list[int]] = {}


def resolve_s6_node_ids(conn: sqlite3.Connection, exact_name: str) -> list[int]:
    """All node ids across every Statement 6 edition with this exact name -
    the rendered tree may resolve to any one of the editions depending on
    year, so the edge must exist from all of them for the related_breakdown
    to be reachable regardless of which edition's fact wins that render.
    Memoized: the crosswalk only names ~15 distinct S6 targets, looked up
    once each rather than once per PBS node (thousands of calls)."""
    if exact_name in _s6_node_id_cache:
        return _s6_node_id_cache[exact_name]
    rows = conn.execute(
        """
        SELECT n.id FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key LIKE ? AND n.name = ?
        """,
        (f"{S6_SOURCE_KEY_PREFIX}%", exact_name),
    ).fetchall()
    result = [int(r[0]) for r in rows]
    _s6_node_id_cache[exact_name] = result
    return result


def live_pbs_nodes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every federal_pbs_programs_all node that has at least one live fact
    (excludes orphaned nodes left behind by an earlier replace_on_reload).
    Single aggregated join, not a per-row correlated subquery, since this
    runs against ~9,800 nodes multiple times in one milestone (report, load,
    reload-to-prove-idempotency)."""
    rows = conn.execute(
        """
        SELECT n.id, n.name,
               COUNT(*) AS fact_count,
               MIN(f.amount_aud) AS min_amount,
               MAX(f.amount_aud) AS max_amount,
               GROUP_CONCAT(DISTINCT f.financial_year) AS financial_years,
               GROUP_CONCAT(DISTINCT f.estimate_status) AS estimate_statuses
        FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        JOIN fact_nodes fn ON fn.node_id = n.id AND fn.dimension_role = 'primary'
        JOIN facts f ON f.id = fn.fact_id
        WHERE d.source_key = ?
        GROUP BY n.id, n.name
        """,
        (PBS_SOURCE_KEY,),
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "node_id": int(r[0]),
                "name": r[1],
                "fact_count": int(r[2] or 0),
                "min_amount": r[3],
                "max_amount": r[4],
                "financial_years": (r[5] or "").split(",") if r[5] else [],
                "estimate_statuses": (r[6] or "").split(",") if r[6] else [],
            }
        )
    return out


def build_coverage_rows(conn: sqlite3.Connection, crosswalk: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = live_pbs_nodes(conn)
    rows = []
    for node in nodes:
        portfolio, label = parse_portfolio_and_label(node["name"])
        decision = classify_program(portfolio, label, crosswalk)
        target_path = None
        if decision["status"] == "mapped":
            target_path = (
                decision.get("statement6_component")
                or decision.get("statement6_subfunction")
                or decision.get("statement6_function")
            )
            target_ids = resolve_s6_node_ids(conn, target_path) if target_path else []
            if not target_ids:
                decision = {
                    **decision,
                    "status": "unmapped",
                    "reason": f"statement6_target_node_not_found:{target_path}",
                }
        rows.append(
            {
                "portfolio": portfolio,
                "program_label": label[:160],
                "node_id": node["node_id"],
                "fact_count": node["fact_count"],
                "min_amount_aud": node["min_amount"],
                "max_amount_aud": node["max_amount"],
                "financial_years": ";".join(sorted(set(node["financial_years"]))),
                "estimate_statuses": ";".join(sorted(set(node["estimate_statuses"]))),
                "statement6_target": target_path,
                "relationship_type": "related_breakdown" if decision["status"] == "mapped" else None,
                "confidence": decision.get("confidence"),
                "evidence": decision.get("evidence"),
                "match_source": decision.get("match_source"),
                "status": decision["status"],
                "reason": decision.get("reason"),
            }
        )
    return rows


def write_coverage_report(rows: list[dict[str, Any]], stamp: str) -> tuple[Path, Path]:
    csv_path = REPORTS_DIR / f"pbs-statement6-crosswalk-coverage-{stamp}.csv"
    md_path = REPORTS_DIR / f"pbs-statement6-crosswalk-coverage-{stamp}.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    mapped = [r for r in rows if r["status"] == "mapped"]
    ambiguous = [r for r in rows if r["status"] == "ambiguous"]
    unmapped = [r for r in rows if r["status"] == "unmapped"]
    facts_mapped = sum(r["fact_count"] for r in mapped)
    facts_total = sum(r["fact_count"] for r in rows)

    by_portfolio: dict[str, Counter] = {}
    for r in rows:
        c = by_portfolio.setdefault(r["portfolio"], Counter())
        c[r["status"]] += 1

    manual_review = [r for r in mapped if r["confidence"] == "low"]

    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(f"# PBS -> Statement 6 crosswalk coverage — {stamp}\n\n")
        fh.write(f"Total live PBS program nodes: **{total}**\n\n")
        fh.write(f"Mapped: **{len(mapped)}** ({facts_mapped} facts)\n\n")
        fh.write(f"Ambiguous (portfolio-level, deliberately unmapped): **{len(ambiguous)}**\n\n")
        fh.write(f"Unmapped (no crosswalk entry or target not found): **{len(unmapped)}**\n\n")
        fh.write(f"Total facts across all live PBS nodes: {facts_total}\n\n")
        fh.write(f"Mappings at confidence=low (recommended for manual review): **{len(manual_review)}**\n\n")

        fh.write("## By portfolio\n\n")
        fh.write("| portfolio | mapped | ambiguous | unmapped |\n|---|---:|---:|---:|\n")
        for portfolio in sorted(by_portfolio):
            c = by_portfolio[portfolio]
            fh.write(f"| {portfolio} | {c['mapped']} | {c['ambiguous']} | {c['unmapped']} |\n")

        fh.write("\n## Dollar value covered by year and estimate status (mapped only)\n\n")
        fh.write(
            "Not summed here: a PBS node commonly carries facts spanning "
            "several financial years and estimate statuses "
            "(actual/estimated_actual/budget/forward_estimate) at once, and "
            "summing them without separating by year+status would mix "
            "incompatible figures - exactly what this milestone prohibits. "
            "See the CSV's `financial_years`/`estimate_statuses` columns per "
            "node instead; per-year/status dollar totals are available via "
            "the dashboard tree at render time, which already separates them.\n\n"
        )

        fh.write("## Unmapped/ambiguous reasons\n\n")
        reason_counts = Counter((r["status"], r["reason"]) for r in rows if r["status"] != "mapped")
        for (status, reason), count in reason_counts.most_common():
            fh.write(f"- `{status}` ({count}): {reason}\n")

        fh.write("\n## Mappings recommended for manual review (confidence=low)\n\n")
        for r in manual_review[:20]:
            fh.write(f"- `{r['portfolio']}` / {r['program_label']} -> {r['statement6_target']}\n")

    return csv_path, md_path


def load_edges(conn: sqlite3.Connection, crosswalk: dict[str, Any]) -> dict[str, int]:
    """Idempotent load: portfolio folders + internal same_group nesting,
    then related_breakdown boundary-crossing edges per the crosswalk."""
    mapping_meta = {"jurisdiction": "Commonwealth", "government_level": "federal"}
    # A handful of PBS labels contain a literal "/" as ordinary English
    # phrasing (e.g. "Retained surplus / (accumulated deficit)", "Net cash
    # from / (used by) investing activities"), not a real hierarchy
    # separator. link_same_group_from_paths() treats every " / " as one,
    # so it creates a spurious intermediate parent node the first time it
    # sees such a name - but that new node isn't in *this* call's own
    # initial node fetch, so its own parent edge is only created on a
    # second pass. Loop to a fixed point so a single load_edges() call is
    # fully idempotent on its own, rather than needing the caller to know
    # to invoke it twice.
    same_group_inserted = 0
    for _ in range(5):
        round_inserted = link_same_group_from_paths(conn, PBS_SOURCE_KEY, mapping_meta)
        same_group_inserted += round_inserted
        if round_inserted == 0:
            break

    doc_id = conn.execute(
        "SELECT id FROM source_documents WHERE source_key = ?", (PBS_SOURCE_KEY,)
    ).fetchone()
    doc_id = doc_id[0] if doc_id else None

    nodes = live_pbs_nodes(conn)
    related_inserted = 0
    skipped_no_target = 0
    for node in nodes:
        portfolio, label = parse_portfolio_and_label(node["name"])
        decision = classify_program(portfolio, label, crosswalk)
        if decision["status"] != "mapped":
            continue
        target_path = (
            decision.get("statement6_component")
            or decision.get("statement6_subfunction")
            or decision.get("statement6_function")
        )
        target_ids = resolve_s6_node_ids(conn, target_path)
        if not target_ids:
            skipped_no_target += 1
            continue

        # Attach directly to this specific PBS program node, not to a
        # shared portfolio-folder node. A portfolio folder (created by
        # link_same_group_from_paths() above, for browsing all of a
        # portfolio's PBS facts together) has no fact of its own -
        # fact_for_node_year() requires the *related_breakdown child* to
        # carry a real fact directly, so an edge pointing at a fact-less
        # folder is silently invisible at render time (confirmed against
        # the real dashboard API, not assumed). Matches the existing
        # precedent (pbs_dss_bridge, grantconnect_under_pbs) of attaching
        # directly to leaf-level program nodes.
        child_node_id = node["node_id"]

        for parent_id in target_ids:
            if parent_id == child_node_id:
                continue
            try:
                # financial_year is NULL on every edge this crosswalk
                # creates (year-agnostic; resolved per-year at render
                # time). SQL NULLs are never equal to each other even
                # inside a UNIQUE constraint, so INSERT OR IGNORE alone
                # would not dedupe across repeated runs - check first with
                # IS (which treats NULL IS NULL as true).
                exists = conn.execute(
                    """
                    SELECT 1 FROM breakdown_edges
                    WHERE parent_node_id = ? AND child_node_id = ?
                      AND edge_kind = 'related_breakdown' AND crosswalk_id = ?
                      AND financial_year IS NULL
                    """,
                    (parent_id, child_node_id, CROSSWALK_ID),
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    """
                    INSERT INTO breakdown_edges (
                        parent_node_id, child_node_id, edge_kind, crosswalk_id,
                        financial_year, priority, source_document_id, notes
                    ) VALUES (?, ?, 'related_breakdown', ?, NULL, 100, ?, ?)
                    """,
                    (
                        parent_id,
                        child_node_id,
                        CROSSWALK_ID,
                        doc_id,
                        f"{decision['match_source']}|{decision.get('confidence')}",
                    ),
                )
                related_inserted += conn.execute("SELECT changes()").fetchone()[0]
            except sqlite3.IntegrityError:
                continue

    return {
        "same_group_inserted": same_group_inserted,
        "related_breakdown_inserted": related_inserted,
        "skipped_no_target": skipped_no_target,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=REPO_ROOT / "data" / "facts.db")
    parser.add_argument("--report-only", action="store_true", help="write the coverage report, do not modify facts.db")
    args = parser.parse_args()

    conn = sqlite3.connect(str(args.db))
    conn.execute("PRAGMA foreign_keys = ON")
    crosswalk = load_crosswalk()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        rows = build_coverage_rows(conn, crosswalk)
        csv_path, md_path = write_coverage_report(rows, stamp)
        result: dict[str, Any] = {
            "coverage_csv": str(csv_path),
            "coverage_md": str(md_path),
            "total_nodes": len(rows),
            "mapped": sum(1 for r in rows if r["status"] == "mapped"),
            "ambiguous": sum(1 for r in rows if r["status"] == "ambiguous"),
            "unmapped": sum(1 for r in rows if r["status"] == "unmapped"),
        }
        if not args.report_only:
            edge_result = load_edges(conn, crosswalk)
            conn.commit()
            result["edges"] = edge_result
        else:
            conn.rollback()
    finally:
        conn.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
