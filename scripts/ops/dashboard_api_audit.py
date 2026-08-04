#!/usr/bin/env python3
"""Automated dashboard/API traversal audit — semantic, not just structural.

Drives the real backend (must already be running, e.g. `uvicorn
src.backend.main:app`) against the current data/facts.db over a curated set
of mode x level x year combinations - not a manual click-through - and for
every visited node cross-references facts.db directly (this is the part a
purely-API-level audit cannot do: the TreeNode response does not expose
source_key/government_level/jurisdiction/measure_type at all) to check:

- scope: an additive node's own government_level/jurisdiction must match
  what was requested (a federal/state/local traversal must never silently
  include a fact from a different level or jurisdiction);
- edge kind: a related_breakdown (non-additive) child must never be
  evaluated as if it were part of an additive decomposition (percent-of-
  parent, "missing depth" flags, etc. do not apply to it);
- additive reconciliation: an additive child must not exceed 100% of its
  parent's amount unless it exactly matches a declarative, evidence-backed
  entry in config/audit/accepted_reconciliation_residuals.yaml (source_key
  + node path + financial_year + measure_type + estimate_status, within
  its own declared variance) - anything else is a hard failure;
- cross-year: an additive (same_group) child must not silently carry a
  different financial year than its parent, and in particular must never
  be a *later* year than an earlier-year parent (a real bug found in this
  milestone, not hypothetical);
- citation: presence of a citation is checked, but is never sufficient by
  itself to mark a row as semantically valid - it is one of several
  checks, not a substitute for the others.

Read-only against the API and facts.db; never writes to either.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "facts.db"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
from pbs_label_classifier import classify_label  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
from accepted_residuals import load_accepted_residuals, match_residual  # noqa: E402

# Representative test cases for the PBS -> Statement 6 crosswalk
# (config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml), one per
# portfolio the milestone names explicitly, plus the DVA health/welfare
# split and the ambiguous cross-function case. Each names a real Statement
# 6 node path known (from the coverage report) to carry at least one
# related_breakdown edge from this crosswalk.
PBS_S6_VERIFICATION_TARGETS: list[dict[str, str]] = [
    {"label": "social_services", "s6_node_name": "Social security and welfare"},
    {"label": "health", "s6_node_name": "Health"},
    {"label": "ndia", "s6_node_name": "Social security and welfare / Assistance to people with disabilities / National Disability Insurance Scheme"},
    {"label": "defence", "s6_node_name": "Defence"},
    {"label": "education", "s6_node_name": "Education"},
    {"label": "dva_health", "s6_node_name": "Health / Medical services and benefits / Veterans' pharmaceutical benefits"},
    {"label": "dva_welfare", "s6_node_name": "Social security and welfare / Assistance to veterans and dependants"},
]

# One representative combination per directive-required regression path,
# plus a couple of breadth checks. Not an exhaustive mode x level x year x
# jurisdiction crawl (state alone has 184k+ facts) - a bounded, named set
# that maps directly to what a human would click through to verify.
REQUIRED_PATHS: list[dict[str, str]] = [
    {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "year": "2024-25", "jurisdiction": None},
    {"label": "federal_budget_latest", "mode": "budget", "level": "federal", "year": None, "jurisdiction": None},
    {"label": "qld_state_actuals_2024_25", "mode": "actuals", "level": "state", "year": "2024-25", "jurisdiction": "QLD"},
    {"label": "local_government_actuals_2024_25", "mode": "actuals", "level": "local", "year": None, "jurisdiction": None},
    {"label": "federal_debt_latest", "mode": "debt", "level": "federal", "year": None, "jurisdiction": None},
    {"label": "federal_gdp_ratios_latest", "mode": "ratios", "level": "federal", "year": None, "jurisdiction": None},
]

MIN_FLAG_AMOUNT = 1_000_000
MIN_FLAG_PCT_OF_PARENT = 0.01
# Node names that are navigation/related-detail branches, not additive GFS
# expense decomposition - used only to decide whether a leaf is worth a
# citation check below, never as a hard-failure signal on its own. An
# earlier version also used this as a secondary, name-based edge_kind
# check ("payment"/"grant" appearing anywhere in the name) - dropped after
# it flagged hundreds of legitimate PBS program/administered-item names
# (e.g. "Program 1.4: Payments to International Organisations") against
# the real corpus; the DB-driven compatibility_group check below is the
# only reliable signal for that invariant.
NON_ADDITIVE_HINTS = ("grant", "contract", "invoice", "recipient", "payment", "award")

PBS_SOURCE_KEY_PREFIX = "federal_pbs_"

LEVEL_ALIASES = {"federal": {"federal", "national"}}

FAILURE_BUCKETS = (
    "scope_failures",
    "jurisdiction_failures",
    "edge_kind_failures",
    "additive_reconciliation_failures",
    "cross_year_failures",
    "label_quality_failures",
    "citation_failures",
    "transport_errors",
)


@dataclass
class AuditResult:
    path_label: str
    requested_mode: str
    requested_level: str
    requested_jurisdiction: str | None
    requested_year: str | None
    visited_nodes: int = 0
    flagged_leaves: list[dict[str, Any]] = field(default_factory=list)
    citation_checks: int = 0
    citation_failures: list[dict[str, Any]] = field(default_factory=list)
    scope_failures: list[dict[str, Any]] = field(default_factory=list)
    jurisdiction_failures: list[dict[str, Any]] = field(default_factory=list)
    edge_kind_failures: list[dict[str, Any]] = field(default_factory=list)
    additive_reconciliation_failures: list[dict[str, Any]] = field(default_factory=list)
    accepted_source_rounding_warnings: list[dict[str, Any]] = field(default_factory=list)
    cross_year_failures: list[dict[str, Any]] = field(default_factory=list)
    label_quality_failures: list[dict[str, Any]] = field(default_factory=list)
    transport_errors: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def hard_failure_count(self) -> int:
        return sum(len(getattr(self, b)) for b in FAILURE_BUCKETS)


def _get(base_url: str, path: str, **params) -> Any:
    resp = requests.get(f"{base_url}{path}", params={k: v for k, v in params.items() if v is not None}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fact_row(conn: sqlite3.Connection, fact_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT f.id, f.financial_year, f.estimate_status, f.measure_type, m.compatibility_group,
               d.source_key, d.government_level, d.jurisdiction, n.name AS node_name
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
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
        "node_name": row[8],
    }


def _walk(
    base_url: str,
    conn: sqlite3.Connection,
    node: dict[str, Any],
    *,
    spec: dict[str, Any],
    parent_fact: dict[str, Any] | None,
    parent_amount: float | None,
    parent_edge_kind: str,
    result: AuditResult,
    depth: int,
    max_depth: int,
    residuals: list | None = None,
) -> None:
    if depth > max_depth:
        return
    result.visited_nodes += 1
    name = node.get("name") or ""
    value = float(node.get("value") or 0)
    children = node.get("children")
    fact_id = node.get("id")
    breakdown = node.get("breakdown") or {}
    edge_kind = breakdown.get("kind") or parent_edge_kind
    is_additive_edge = edge_kind not in ("related_breakdown",)
    fact_row = _fact_row(conn, fact_id) if fact_id else None
    pct_of_parent = (value / parent_amount) if parent_amount else None

    requested_level = spec["level"]
    expected_levels = LEVEL_ALIASES.get(requested_level, {requested_level})
    requested_jur = spec.get("jurisdiction")

    if fact_row and is_additive_edge:
        # Invariant 1/3: an additive path must not silently contain a fact
        # from a different government level (federal facts under
        # local/state, or vice versa).
        if fact_row["government_level"] not in expected_levels:
            result.scope_failures.append(
                {
                    "path": spec["label"], "fact_id": fact_id, "name": name[:160],
                    "requested_level": requested_level, "fact_government_level": fact_row["government_level"],
                    "fact_source_key": fact_row["source_key"],
                }
            )
        # Invariant 2: a state/local traversal scoped to one jurisdiction
        # must not contain another jurisdiction's fact.
        if requested_jur and fact_row["jurisdiction"] and requested_jur.lower() not in fact_row["jurisdiction"].lower():
            result.jurisdiction_failures.append(
                {
                    "path": spec["label"], "fact_id": fact_id, "name": name[:160],
                    "requested_jurisdiction": requested_jur, "fact_jurisdiction": fact_row["jurisdiction"],
                }
            )
        # Invariant 4 (DB-driven): additive edges must stay within one
        # compatibility_group. Mixing (e.g. a commitment/count/cash_outflow
        # measure appearing as an additive child of an actual_expense
        # parent) is a real semantic defect, not just a naming smell.
        if parent_fact and fact_row["compatibility_group"] != parent_fact.get("compatibility_group"):
            result.edge_kind_failures.append(
                {
                    "path": spec["label"], "fact_id": fact_id, "name": name[:160],
                    "parent_compatibility_group": parent_fact.get("compatibility_group"),
                    "child_compatibility_group": fact_row["compatibility_group"],
                }
            )
        # Invariant 5: additive child must not exceed 100% of parent unless
        # it exactly matches a declarative, evidence-backed entry in
        # config/audit/accepted_reconciliation_residuals.yaml - a changed
        # year, source, label, amount, or materially larger variance never
        # matches (see scripts/ops/accepted_residuals.py), so this can
        # only narrow what is accepted, never silently widen it.
        if pct_of_parent is not None and pct_of_parent > 1.0 + 1e-9:
            variance_pct = pct_of_parent - 1.0
            matched = (
                match_residual(
                    residuals or [],
                    source_key=fact_row["source_key"],
                    node_path=fact_row["node_name"],
                    financial_year=fact_row["financial_year"],
                    measure_type=fact_row["measure_type"],
                    estimate_status=fact_row["estimate_status"],
                    variance_pct=variance_pct,
                )
                if residuals
                else None
            )
            entry_dict = {
                "path": spec["label"], "fact_id": fact_id, "name": name[:160],
                "percent_of_parent": pct_of_parent, "parent_amount": parent_amount, "child_amount": value,
            }
            if matched:
                entry_dict["accepted_reason"] = matched.reason
                entry_dict["source_locator"] = matched.source_locator
                result.accepted_source_rounding_warnings.append(entry_dict)
            else:
                result.additive_reconciliation_failures.append(entry_dict)
        # Invariant 6 (partial - full explicit fallback metadata is Task 7):
        # an additive child must not silently carry a different year than
        # its parent, and must never be a *later* year than an earlier
        # parent year.
        if parent_fact and fact_row.get("financial_year") != parent_fact.get("financial_year"):
            is_future = _fy_start(fact_row.get("financial_year")) > _fy_start(parent_fact.get("financial_year"))
            result.cross_year_failures.append(
                {
                    "path": spec["label"], "fact_id": fact_id, "name": name[:160],
                    "parent_financial_year": parent_fact.get("financial_year"),
                    "child_financial_year": fact_row.get("financial_year"),
                    "is_future_year_fallback": is_future,
                }
            )

    # Use the same classifier that gates what gets published to the PBS
    # crosswalk (scripts/ingest/pbs_label_classifier.py), not a separate,
    # cruder duplicate regex set - a bare substring match on "EXPENSES" (or
    # similar) previously flagged genuine component descriptions that
    # legitimately mention "administered expenses" as ordinary phrasing
    # (e.g. "1.5.6 - Component 6 (Carer Adjustment Payment) Annual
    # administered expenses"), which the real classifier already knows to
    # accept via its numbering-pattern precedence.
    if fact_row and str(fact_row["source_key"] or "").startswith(PBS_SOURCE_KEY_PREFIX):
        classification = classify_label(name)
        if not classification.publishable:
            result.label_quality_failures.append(
                {
                    "path": spec["label"], "fact_id": fact_id, "name": name[:160],
                    "reason": classification.classification,
                    "rejection_reason": classification.rejection_reason,
                }
            )

    is_leaf = not children
    material = value >= MIN_FLAG_AMOUNT or (pct_of_parent is not None and pct_of_parent >= MIN_FLAG_PCT_OF_PARENT)
    is_non_additive_area = any(h in name.lower() for h in NON_ADDITIVE_HINTS)

    if is_leaf and material and not is_non_additive_area and fact_id is not None:
        result.citation_checks += 1
        try:
            evidence = _get(base_url, f"/v2/dashboard/item/{fact_id}/evidence")
            if not evidence.get("has_source_file") and not evidence.get("locator"):
                result.citation_failures.append(
                    {"path": spec["label"], "fact_id": fact_id, "name": name[:160], "reason": "no_source_file_and_no_locator"}
                )
        except Exception as exc:  # noqa: BLE001
            result.transport_errors.append(f"{spec['label']} evidence fetch fact_id={fact_id}: {exc}")

        result.flagged_leaves.append(
            {"fact_id": fact_id, "name": name, "amount": value, "pct_of_parent": pct_of_parent, "depth": depth}
        )

    if children and depth < max_depth:
        for child in children:
            _walk(
                base_url, conn, child, spec=spec, parent_fact=fact_row or parent_fact,
                parent_amount=value, parent_edge_kind=edge_kind, result=result,
                depth=depth + 1, max_depth=max_depth, residuals=residuals,
            )


def _fy_start(fy: str | None) -> int:
    if not fy:
        return -1
    try:
        return int(str(fy).split("-", 1)[0])
    except (TypeError, ValueError):
        return -1


def audit_path(
    base_url: str,
    spec: dict[str, Any],
    max_depth: int,
    db_path: Path = DB_PATH,
    residuals: list | None = None,
) -> AuditResult:
    result = AuditResult(
        path_label=spec["label"], requested_mode=spec["mode"], requested_level=spec["level"],
        requested_jurisdiction=spec.get("jurisdiction"), requested_year=spec.get("year"),
    )
    if residuals is None:
        residuals = load_accepted_residuals()
    conn = sqlite3.connect(str(db_path))
    try:
        levels = _get(base_url, "/v2/dashboard/levels", mode=spec["mode"])
        level_names = {row["level"] for row in levels}
        if spec["level"] not in level_names:
            result.errors.append(f"level {spec['level']} not present for mode {spec['mode']} ({sorted(level_names)})")
            return result

        year = spec.get("year")
        if not year:
            years = _get(base_url, "/v2/dashboard/years", mode=spec["mode"], level=spec["level"])
            if not years:
                result.errors.append(f"no years available for mode={spec['mode']} level={spec['level']}")
                return result
            year = years[-1]
        result.requested_year = year

        tree = _get(base_url, "/v2/dashboard/tree", mode=spec["mode"], level=spec["level"], year=year)
        # /dashboard/tree for level=state/local returns every jurisdiction
        # as a top-level sibling in one response (by design). Scope the
        # walk to the matching branch only when a jurisdiction was
        # requested, so legitimate sibling jurisdictions are never flagged
        # as if they leaked into the requested one.
        roots = tree.get("children") or [tree]
        req_jur = spec.get("jurisdiction")
        if req_jur:
            roots = [r for r in roots if req_jur.lower() in (r.get("name") or "").lower()] or roots
        for root in roots:
            _walk(
                base_url, conn, root, spec=spec, parent_fact=None, parent_amount=None,
                parent_edge_kind="additive", result=result, depth=0, max_depth=max_depth,
                residuals=residuals,
            )
    except Exception as exc:  # noqa: BLE001
        result.transport_errors.append(str(exc))
    finally:
        conn.close()
    return result


def verify_pbs_s6_crosswalk(base_url: str, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Task 7: for each named representative portfolio/case, find a real
    Statement 6 node this crosswalk attached related_breakdown edges to,
    fetch its children via the real API, and check: the node has a real
    fact (amount/unit/year/estimate_status present), the relationship is
    explicitly labelled non-additive, at least one PBS child is present
    with a complete citation (evidence endpoint), and the parent's own
    amount is preserved (not re-summed from the related children)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    results = []
    for target in PBS_S6_VERIFICATION_TARGETS:
        name = target["s6_node_name"]
        row = conn.execute(
            """
            SELECT fn.fact_id, f.financial_year, f.estimate_status, f.amount_aud, f.unit, n.id AS node_id
            FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            JOIN fact_nodes fn ON fn.node_id = n.id AND fn.dimension_role = 'primary'
            JOIN facts f ON f.id = fn.fact_id
            WHERE n.name = ? AND d.source_key LIKE 'federal_budget_statement_6%'
            AND EXISTS (
                SELECT 1 FROM breakdown_edges be
                WHERE be.parent_node_id = n.id AND be.crosswalk_id = 'pbs_programs_all_under_s6'
            )
            ORDER BY f.financial_year DESC
            LIMIT 1
            """,
            (name,),
        ).fetchone()
        entry: dict[str, Any] = {"label": target["label"], "s6_node_name": name}
        if row is None:
            entry.update({"status": "error", "reason": "no_fact_bearing_crosswalk_node_found"})
            results.append(entry)
            continue
        entry.update(
            {
                "fact_id": row["fact_id"],
                "financial_year": row["financial_year"],
                "estimate_status": row["estimate_status"],
                "parent_amount_aud": row["amount_aud"],
                "unit": row["unit"],
            }
        )
        try:
            resp = requests.get(
                f"{base_url}/v2/dashboard/item/{row['fact_id']}/children",
                params={"year": row["financial_year"]},
                timeout=15,
            )
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            entry.update({"status": "error", "reason": f"api_error:{exc}"})
            results.append(entry)
            continue

        related_block = None
        if data.get("kind") == "related_breakdown":
            related_block = {**data, "value": data.get("parent_amount_aud")}
        else:
            for child in data.get("children") or []:
                bd = child.get("breakdown") or {}
                if "Related PBS" in (child.get("name") or "") or bd.get("kind") == "related_breakdown":
                    related_block = {
                        "children": (child.get("children") or []),
                        "breakdown": bd or child.get("breakdown"),
                        "value": child.get("value"),
                    }
                    break

        if related_block is None:
            entry.update({"status": "not_reachable", "reason": f"kind={data.get('kind')}, no related folder found"})
            results.append(entry)
            continue

        breakdown = related_block.get("breakdown") or {}
        banner = (breakdown.get("banner") or "")
        non_additive_labelled = "not be summed" in banner or "non-additive" in banner.lower()
        children = related_block.get("children") or []
        pbs_child = children[0] if children else None
        citation_ok = False
        citation_detail = None
        if pbs_child and pbs_child.get("id"):
            try:
                ev = requests.get(f"{base_url}/v2/dashboard/item/{pbs_child['id']}/evidence", timeout=15).json()
                citation_ok = bool(ev.get("has_source_file") or ev.get("locator"))
                citation_detail = {"has_source_file": ev.get("has_source_file"), "locator": ev.get("locator")}
            except Exception as exc:  # noqa: BLE001
                citation_detail = {"error": str(exc)}

        parent_value = related_block.get("value")
        amount_preserved = parent_value is None or float(parent_value) == float(row["amount_aud"] or 0)

        entry.update(
            {
                "status": "reachable" if (non_additive_labelled and pbs_child and citation_ok and amount_preserved) else "reachable_with_issues",
                "non_additive_labelled": non_additive_labelled,
                "banner": banner,
                "child_count": len(children),
                "sample_child": pbs_child.get("name") if pbs_child else None,
                "sample_child_amount": pbs_child.get("value") if pbs_child else None,
                "citation_ok": citation_ok,
                "citation_detail": citation_detail,
                "parent_amount_preserved": amount_preserved,
            }
        )
        results.append(entry)
    conn.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8811")
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--skip-traversal", action="store_true", help="only run the PBS->S6 crosswalk verification")
    args = parser.parse_args()

    residuals = load_accepted_residuals()
    results = [] if args.skip_traversal else [
        audit_path(args.base_url, spec, args.max_depth, args.db, residuals=residuals)
        for spec in REQUIRED_PATHS
    ]
    crosswalk_results = verify_pbs_s6_crosswalk(args.base_url, args.db)

    out_json = REPO_ROOT / f"ops/reports/dashboard-api-audit-{STAMP}.json"
    out_md = REPO_ROOT / f"ops/reports/dashboard-api-audit-{STAMP}.md"

    total_hard_failures = sum(r.hard_failure_count() for r in results)
    total_accepted_warnings = sum(len(r.accepted_source_rounding_warnings) for r in results)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "total_hard_failures": total_hard_failures,
        "total_accepted_source_rounding_warnings": total_accepted_warnings,
        "results": [
            {
                "path_label": r.path_label,
                "requested_mode": r.requested_mode,
                "requested_level": r.requested_level,
                "requested_jurisdiction": r.requested_jurisdiction,
                "requested_year": r.requested_year,
                "visited_nodes": r.visited_nodes,
                "citation_checks": r.citation_checks,
                "hard_failure_count": r.hard_failure_count(),
                **{b: getattr(r, b) for b in FAILURE_BUCKETS},
                "accepted_source_rounding_warnings": r.accepted_source_rounding_warnings,
                "flagged_leaves_count": len(r.flagged_leaves),
                "flagged_leaves_sample": r.flagged_leaves[:10],
                "errors": r.errors,
            }
            for r in results
        ],
        "pbs_s6_crosswalk": crosswalk_results,
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with out_md.open("w", encoding="utf-8") as fh:
        fh.write(f"# Dashboard API traversal audit — {STAMP}\n\n")
        fh.write(f"Base URL: `{args.base_url}` (real backend against `data/facts.db`)\n\n")
        fh.write(f"**Total hard failures across all paths: {total_hard_failures}**\n\n")
        fh.write(f"**Total accepted source-rounding warnings: {total_accepted_warnings}**\n\n")
        if results:
            fh.write(
                "| path | visited_nodes | scope | jurisdiction | edge_kind | additive>100% | cross_year | label_quality | citation | transport |\n"
            )
            fh.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
            for r in results:
                fh.write(
                    f"| {r.path_label} | {r.visited_nodes} | {len(r.scope_failures)} | "
                    f"{len(r.jurisdiction_failures)} | {len(r.edge_kind_failures)} | "
                    f"{len(r.additive_reconciliation_failures)} | {len(r.cross_year_failures)} | "
                    f"{len(r.label_quality_failures)} | {len(r.citation_failures)} | {len(r.transport_errors)} |\n"
                )
            for bucket in (*FAILURE_BUCKETS, "accepted_source_rounding_warnings"):
                fh.write(f"\n## {bucket}\n\n")
                any_rows = False
                for r in results:
                    for item in getattr(r, bucket):
                        any_rows = True
                        fh.write(f"- `{r.path_label}`: {json.dumps(item)}\n")
                if not any_rows:
                    fh.write("None.\n")

        fh.write("\n## PBS -> Statement 6 crosswalk reachability\n\n")
        fh.write(
            "| case | s6_node | status | non_additive_labelled | sample_child | citation_ok | amount_preserved |\n"
        )
        fh.write("|---|---|---|---|---|---|---|\n")
        for r in crosswalk_results:
            fh.write(
                f"| {r['label']} | {r['s6_node_name']} | {r.get('status')} | "
                f"{r.get('non_additive_labelled')} | {r.get('sample_child')} | "
                f"{r.get('citation_ok')} | {r.get('parent_amount_preserved')} |\n"
            )
        fh.write("\n### Detail\n\n")
        for r in crosswalk_results:
            fh.write(f"**{r['label']}** (`{r['s6_node_name']}`)\n\n")
            fh.write(f"```json\n{json.dumps(r, indent=2)}\n```\n\n")

    print(json.dumps({"json": str(out_json), "md": str(out_md), "paths": len(results),
                       "crosswalk_cases": len(crosswalk_results), "total_hard_failures": total_hard_failures,
                       "total_accepted_source_rounding_warnings": total_accepted_warnings}))
    return 1 if total_hard_failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
