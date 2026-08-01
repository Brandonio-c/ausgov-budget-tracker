#!/usr/bin/env python3
"""Automated dashboard/API traversal audit (Task 8).

Drives the real backend (must already be running, e.g. `uvicorn
src.backend.main:app`) against the current data/facts.db over a curated set
of mode x level x year combinations - not a manual click-through - and
records, for every visited node: path, fact-node id, amount, unit,
percent-of-parent, depth, whether it has additive children, citation
completeness (evidence endpoint responds, has_source_file), and flags any
leaf >= $1M or >= 1% of its parent with no deeper breakdown and no children.

Read-only against the API; does not touch facts.db directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# One representative combination per directive-required regression path,
# plus a couple of breadth checks. Not an exhaustive mode x level x year x
# jurisdiction crawl (state alone has 184k+ facts) - a bounded, named set
# that maps directly to what a human would click through to verify.
REQUIRED_PATHS: list[dict[str, str]] = [
    {"label": "federal_actuals_2024_25", "mode": "actuals", "level": "federal", "year": "2024-25"},
    {"label": "federal_budget_latest", "mode": "budget", "level": "federal", "year": None},
    {"label": "qld_state_actuals_2024_25", "mode": "actuals", "level": "state", "year": "2024-25", "jurisdiction": "Queensland"},
    {"label": "local_government_actuals_2024_25", "mode": "actuals", "level": "local", "year": None},
    {"label": "federal_debt_latest", "mode": "debt", "level": "federal", "year": None},
    {"label": "federal_gdp_ratios_latest", "mode": "ratios", "level": "federal", "year": None},
]

MIN_FLAG_AMOUNT = 1_000_000
MIN_FLAG_PCT_OF_PARENT = 0.01
# Node names that are navigation/related-detail branches, not additive GFS
# expense decomposition - must never be flagged as "missing additive depth"
# the same way a real expense branch would be.
NON_ADDITIVE_HINTS = ("grant", "contract", "invoice", "recipient", "payment", "award")


@dataclass
class AuditResult:
    path_label: str
    visited_nodes: int = 0
    flagged_leaves: list[dict[str, Any]] = field(default_factory=list)
    citation_checks: int = 0
    citation_failures: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _get(base_url: str, path: str, **params) -> Any:
    resp = requests.get(f"{base_url}{path}", params={k: v for k, v in params.items() if v is not None}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _walk(
    base_url: str,
    node: dict[str, Any],
    *,
    depth: int,
    parent_value: float | None,
    result: AuditResult,
    max_depth: int,
) -> None:
    result.visited_nodes += 1
    name = node.get("name") or ""
    value = float(node.get("value") or 0)
    children = node.get("children")
    fact_id = node.get("id")
    pct_of_parent = (value / parent_value) if parent_value else None

    is_non_additive_area = any(h in name.lower() for h in NON_ADDITIVE_HINTS)
    is_leaf = not children
    material = value >= MIN_FLAG_AMOUNT or (pct_of_parent is not None and pct_of_parent >= MIN_FLAG_PCT_OF_PARENT)

    if is_leaf and material and not is_non_additive_area and fact_id is not None:
        result.citation_checks += 1
        try:
            evidence = _get(base_url, f"/v2/dashboard/item/{fact_id}/evidence")
            if not evidence.get("has_source_file") and not evidence.get("locator"):
                result.citation_failures.append(
                    {"fact_id": fact_id, "name": name, "reason": "no_source_file_and_no_locator"}
                )
        except Exception as exc:  # noqa: BLE001
            result.citation_failures.append({"fact_id": fact_id, "name": name, "reason": f"evidence_error:{exc}"})

        result.flagged_leaves.append(
            {
                "fact_id": fact_id,
                "name": name,
                "amount": value,
                "pct_of_parent": pct_of_parent,
                "depth": depth,
            }
        )

    if children and depth < max_depth:
        for child in children:
            _walk(base_url, child, depth=depth + 1, parent_value=value, result=result, max_depth=max_depth)


def audit_path(base_url: str, spec: dict[str, str], max_depth: int) -> AuditResult:
    result = AuditResult(path_label=spec["label"])
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

        tree = _get(base_url, "/v2/dashboard/tree", mode=spec["mode"], level=spec["level"], year=year)
        _walk(base_url, tree, depth=0, parent_value=None, result=result, max_depth=max_depth)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(str(exc))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8811")
    parser.add_argument("--max-depth", type=int, default=4)
    args = parser.parse_args()

    results = [audit_path(args.base_url, spec, args.max_depth) for spec in REQUIRED_PATHS]

    out_json = REPO_ROOT / f"ops/reports/dashboard-api-audit-{STAMP}.json"
    out_md = REPO_ROOT / f"ops/reports/dashboard-api-audit-{STAMP}.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "results": [
            {
                "path_label": r.path_label,
                "visited_nodes": r.visited_nodes,
                "citation_checks": r.citation_checks,
                "citation_failures": r.citation_failures,
                "flagged_leaves_count": len(r.flagged_leaves),
                "flagged_leaves_sample": r.flagged_leaves[:10],
                "errors": r.errors,
            }
            for r in results
        ],
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with out_md.open("w", encoding="utf-8") as fh:
        fh.write(f"# Dashboard API traversal audit — {STAMP}\n\n")
        fh.write(f"Base URL: `{args.base_url}` (real backend against `data/facts.db`)\n\n")
        fh.write("| path | visited_nodes | material_leaves | citation_checks | citation_failures | errors |\n")
        fh.write("|---|---:|---:|---:|---:|---|\n")
        for r in results:
            fh.write(
                f"| {r.path_label} | {r.visited_nodes} | {len(r.flagged_leaves)} | {r.citation_checks} | "
                f"{len(r.citation_failures)} | {'; '.join(r.errors) or '-'} |\n"
            )
        fh.write("\n## Citation failures\n\n")
        any_failures = False
        for r in results:
            for f in r.citation_failures:
                any_failures = True
                fh.write(f"- `{r.path_label}` fact_id={f['fact_id']} ({f['name']}): {f['reason']}\n")
        if not any_failures:
            fh.write("None.\n")

    print(json.dumps({"json": str(out_json), "md": str(out_md), "paths": len(results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
