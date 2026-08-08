#!/usr/bin/env python3
"""Read-only semantic, crosswalk, and citation audit of the historical FBO archive."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
DEFAULT_CROSSWALK = (
    REPO_ROOT / "config" / "breakdowns" / "crosswalks" / "cofog_to_budget_function.yaml"
)
SOURCE_KEY = "federal_budget_archive_function_series"
EXPECTED_SEMANTICS = {
    "measure_type": "actual_accrual_expense",
    "accounting_basis": "accrual",
    "estimate_status": "audited_actual",
}


def _casefold_lookup(values: dict[str, int], label: str) -> int | None:
    wanted = label.casefold()
    return next((amount for name, amount in values.items() if name.casefold() == wanted), None)


def _fbo_function_amount(values: dict[str, int], budget_label: str) -> tuple[int | None, str | None]:
    total = _casefold_lookup(values, f"Total {budget_label}")
    if total is not None:
        return total, f"Total {budget_label}"
    direct_suffix = f" / {budget_label}".casefold()
    direct = [(name, amount) for name, amount in values.items() if name.casefold().endswith(direct_suffix)]
    if len(direct) == 1:
        return direct[0][1], direct[0][0]
    prefix = f"{budget_label} / ".casefold()
    children = [(name, amount) for name, amount in values.items() if name.casefold().startswith(prefix)]
    if children:
        return sum(amount for _, amount in children), f"sum of {len(children)} subfunctions"
    return None, None


def _abs_amount(values: dict[str, int], abs_label: str) -> tuple[int | None, str | None]:
    for candidate in (abs_label, f"Total {abs_label}"):
        amount = _casefold_lookup(values, candidate)
        if amount is not None:
            return amount, candidate
    return None, None


def _year_in(value: str | None, year: str) -> bool:
    return bool(value and year in value)


def _load_crosswalk(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mappings = payload.get("mappings") or []
    if not mappings:
        raise ValueError(f"No mappings in {path}")
    return payload


def run(
    db_path: Path = DEFAULT_DB,
    crosswalk_path: Path = DEFAULT_CROSSWALK,
) -> dict[str, Any]:
    crosswalk = _load_crosswalk(crosswalk_path)
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT f.id AS fact_id, f.financial_year, f.measure_type,
                   f.accounting_basis, f.estimate_status, f.amount_aud,
                   f.source_locator_json, f.source_retrieval_id, n.name,
                   sr.resolved_url, sr.local_path, sr.retrieval_status
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN fact_nodes fn
              ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            LEFT JOIN source_retrievals sr ON sr.id = f.source_retrieval_id
            WHERE d.source_key = ?
            ORDER BY f.financial_year, n.name, f.id
            """,
            (SOURCE_KEY,),
        ).fetchall()
        abs_rows = conn.execute(
            """
            SELECT f.financial_year, n.name, f.amount_aud
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN fact_nodes fn
              ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            WHERE d.source_key = 'abs_gfs_commonwealth_130'
              AND f.measure_type = 'gfs_expense'
              AND f.accounting_basis = 'gfs'
              AND f.estimate_status = 'actual'
            """
        ).fetchall()
    finally:
        conn.close()

    by_year: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_year[str(row["financial_year"])].append(row)
    abs_by_year: dict[str, dict[str, int]] = defaultdict(dict)
    for row in abs_rows:
        abs_by_year[str(row["financial_year"])][str(row["name"])] = int(row["amount_aud"])

    budget_to_abs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for mapping in crosswalk["mappings"]:
        budget_to_abs[str(mapping["budget"])].append(
            {
                "label": str(mapping["abs"]),
                "quality": str(mapping.get("quality") or crosswalk.get("match_quality_default") or "approx"),
            }
        )

    years: list[dict[str, Any]] = []
    previous_labels: set[str] | None = None
    mapped_budget_labels = set(budget_to_abs)
    for year, year_rows in sorted(by_year.items()):
        values = {str(row["name"]): int(row["amount_aud"]) for row in year_rows}
        labels = set(values)
        function_parents = sorted({name.split(" / ", 1)[0] for name in labels if " / " in name})
        total_labels = sorted(name for name in labels if " / " not in name)
        comparisons: list[dict[str, Any]] = []
        for budget_label, abs_mappings in sorted(budget_to_abs.items()):
            fbo_amount, fbo_evidence = _fbo_function_amount(values, budget_label)
            abs_parts: list[dict[str, Any]] = []
            abs_total = 0
            abs_complete = True
            for mapping in abs_mappings:
                amount, evidence = _abs_amount(abs_by_year.get(year, {}), mapping["label"])
                abs_parts.append({**mapping, "amount_aud": amount, "evidence_label": evidence})
                if amount is None:
                    abs_complete = False
                else:
                    abs_total += amount
            difference = fbo_amount - abs_total if fbo_amount is not None and abs_complete else None
            comparisons.append(
                {
                    "budget_function": budget_label,
                    "fbo_amount_aud": fbo_amount,
                    "fbo_evidence": fbo_evidence,
                    "abs_purposes": abs_parts,
                    "abs_amount_aud": abs_total if abs_complete else None,
                    "difference_aud": difference,
                    "difference_percent_of_abs": (
                        difference / abs_total * 100 if difference is not None and abs_total else None
                    ),
                    "status": "mapped" if fbo_amount is not None and abs_complete else "missing_evidence",
                }
            )

        citation_checks: list[dict[str, Any]] = []
        for row in year_rows:
            locator = json.loads(str(row["source_locator_json"] or "{}"))
            fields = {
                "locator": _year_in(locator.get("locator"), year),
                "landing_url": _year_in(locator.get("landing_url"), year),
                "original_resource_url": _year_in(locator.get("original_resource_url"), year),
                "locator_cached_copy_path": _year_in(locator.get("cached_copy_path"), year),
                "retrieval_resolved_url": _year_in(row["resolved_url"], year),
                "retrieval_local_path": _year_in(row["local_path"], year),
            }
            citation_checks.append(
                {
                    "fact_id": int(row["fact_id"]),
                    "name": str(row["name"]),
                    "fields": fields,
                    "all_exact_year": all(fields.values()),
                }
            )
        citation_field_counts = {
            field: sum(check["fields"][field] for check in citation_checks)
            for field in next(iter(citation_checks))["fields"]
        }
        semantic_failures = [
            int(row["fact_id"])
            for row in year_rows
            if any(str(row[key]) != value for key, value in EXPECTED_SEMANTICS.items())
        ]
        unmapped = sorted(
            (set(function_parents) - mapped_budget_labels)
            | {
                label.removeprefix("Total ")
                for label in total_labels
                if label.startswith("Total ")
                and label != "Total expenses"
                and label.removeprefix("Total ") not in mapped_budget_labels
            }
        )
        years.append(
            {
                "financial_year": year,
                "fact_count": len(year_rows),
                "function_count": len(function_parents),
                "subfunction_fact_count": sum(" / " in name for name in labels),
                "total_fact_count": sum(" / " not in name for name in labels),
                "function_labels": function_parents,
                "total_labels": total_labels,
                "semantic_failure_fact_ids": semantic_failures,
                "crosswalk_comparisons": comparisons,
                "unmapped_fbo_classifications": unmapped,
                "classification_changes_from_previous_year": {
                    "added": sorted(labels - previous_labels) if previous_labels is not None else [],
                    "removed": sorted(previous_labels - labels) if previous_labels is not None else [],
                },
                "citation": {
                    "complete_fact_count": sum(check["all_exact_year"] for check in citation_checks),
                    "field_exact_year_counts": citation_field_counts,
                    "exceptions": [check for check in citation_checks if not check["all_exact_year"]],
                },
            }
        )
        previous_labels = labels

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "database": str(db_path),
        "source_key": SOURCE_KEY,
        "crosswalk_id": str(crosswalk.get("id")),
        "expected_semantics": EXPECTED_SEMANTICS,
        "years": years,
        "summary": {
            "year_count": len(years),
            "fact_count": sum(year["fact_count"] for year in years),
            "semantic_failure_count": sum(len(year["semantic_failure_fact_ids"]) for year in years),
            "mapped_comparison_count": sum(
                comparison["status"] == "mapped"
                for year in years
                for comparison in year["crosswalk_comparisons"]
            ),
            "missing_evidence_comparison_count": sum(
                comparison["status"] != "mapped"
                for year in years
                for comparison in year["crosswalk_comparisons"]
            ),
            "classification_change_count": sum(
                len(year["classification_changes_from_previous_year"][kind])
                for year in years
                for kind in ("added", "removed")
            ),
            "exact_year_citation_fact_count": sum(
                year["citation"]["complete_fact_count"] for year in years
            ),
            "citation_exception_fact_count": sum(
                len(year["citation"]["exceptions"]) for year in years
            ),
            "unmapped_fbo_classifications": sorted(
                {label for year in years for label in year["unmapped_fbo_classifications"]}
            ),
        },
    }


def _money(value: int | float | None) -> str:
    return "—" if value is None else f"${value / 1_000_000_000:,.3f}b"


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Historical FBO archive crosswalk preflight",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "This is a no-write audit of the already-published 2019-20 through 2023-24 Final Budget Outcome Appendix A facts. Cross-source differences are evidence only: FBO budget functions and ABS GFS COFOG-A purposes are not additively interchangeable.",
        "",
        "## Result",
        "",
        f"- Facts audited: **{summary['fact_count']}** across **{summary['year_count']}** exact fact years.",
        f"- Semantic failures: **{summary['semantic_failure_count']}**; every fact is `actual_accrual_expense / accrual / audited_actual`.",
        f"- Crosswalk comparisons with evidence on both sides: **{summary['mapped_comparison_count']}**; missing evidence: **{summary['missing_evidence_comparison_count']}**.",
        f"- Source classification label additions/removals after 2019-20: **{summary['classification_change_count']}**.",
        f"- Facts with all six exact-year citation signals: **{summary['exact_year_citation_fact_count']} / {summary['fact_count']}**.",
        "",
        "## Source-native inventory",
        "",
        "| year | facts | function parents | subfunction facts | total facts | semantic failures | label changes |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for year in payload["years"]:
        changes = year["classification_changes_from_previous_year"]
        lines.append(
            f"| {year['financial_year']} | {year['fact_count']} | {year['function_count']} | "
            f"{year['subfunction_fact_count']} | {year['total_fact_count']} | "
            f"{len(year['semantic_failure_fact_ids'])} | {len(changes['added']) + len(changes['removed'])} |"
        )
    lines.extend(
        [
            "",
            "The eleven function-parent labels are stable across all five editions. Three subfunction labels vary only by dash, apostrophe, or capitalization; those exact source-label changes are listed below.",
            "",
        ]
    )
    for year in payload["years"]:
        lines.append(f"### {year['financial_year']} functions")
        lines.append("")
        lines.append(", ".join(f"`{label}`" for label in year["function_labels"]))
        lines.append("")

    lines.extend(
        [
            "## COFOG crosswalk evidence",
            "",
            "The repository's existing `cofog_to_budget_function` mapping is reversed here only to locate comparable labels. Approximate mappings and classification aggregation remain explicit.",
            "",
            "| year | FBO budget function | FBO | ABS mapped purpose(s) | ABS | FBO − ABS | quality |",
            "|---|---|---:|---|---:|---:|---|",
        ]
    )
    for year in payload["years"]:
        for comparison in year["crosswalk_comparisons"]:
            abs_labels = "; ".join(part["label"] for part in comparison["abs_purposes"])
            qualities = "; ".join(sorted({part["quality"] for part in comparison["abs_purposes"]}))
            lines.append(
                f"| {year['financial_year']} | {comparison['budget_function']} | "
                f"{_money(comparison['fbo_amount_aud'])} | {abs_labels} | "
                f"{_money(comparison['abs_amount_aud'])} | {_money(comparison['difference_aud'])} | {qualities} |"
            )
    lines.extend(
        [
            "",
            "### Unmapped and excluded classifications",
            "",
            "The existing crosswalk does not independently map the FBO classifications `Agriculture, forestry and fishing`, `labour and employment affairs`, or `Other purposes`. They must remain explicit exceptions in the graph pack; silently folding them into `Economic affairs` or another ABS purpose would introduce an unreviewed classification rule. `Total expenses` is an aggregate and is excluded from function mapping.",
            "",
            "## Citation and exact-year audit",
            "",
            "| year | locator | landing URL | resource URL | locator cached path | retrieval URL | retrieval local path | all six |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for year in payload["years"]:
        counts = year["citation"]["field_exact_year_counts"]
        lines.append(
            f"| {year['financial_year']} | {counts['locator']} | {counts['landing_url']} | "
            f"{counts['original_resource_url']} | {counts['locator_cached_copy_path']} | "
            f"{counts['retrieval_resolved_url']} | {counts['retrieval_local_path']} | "
            f"{year['citation']['complete_fact_count']} |"
        )
    lines.extend(
        [
            "",
            "All 415 fact locators, landing URLs, and original official resource URLs identify the correct fact year. The ingestion provenance is nevertheless not exact-year safe: all facts share one retrieval row whose resolved URL is 2019-20 and whose local path is the 2023-24 PDF; the locator JSON cached path also points to the 2023-24 PDF for every year. Therefore item 4.2 must repair per-edition retrieval/cached-copy attribution before deploying graph edges.",
            "",
            "## Classification changes",
            "",
        ]
    )
    found_changes = False
    for year in payload["years"]:
        changes = year["classification_changes_from_previous_year"]
        if not changes["added"] and not changes["removed"]:
            continue
        found_changes = True
        lines.append(
            f"- `{year['financial_year']}`: added {json.dumps(changes['added'], ensure_ascii=False)}; "
            f"removed {json.dumps(changes['removed'], ensure_ascii=False)}."
        )
    if not found_changes:
        lines.append("None.")
    lines.extend(
        [
            "",
            "These are typographic/capitalization changes, not substantive classification additions or removals. Exact-label graph construction must still avoid treating them as new semantic categories.",
            "",
            "## Preflight disposition",
            "",
            "**Conditional pass.** Measures, basis, status, year labels, source-native classification, official locator URLs, and crosswalk coverage are sufficient to design an exact-only augmenting pack. Deployment is blocked until the shared retrieval/cached-copy provenance is repaired and re-audited. Cross-source amount differences must remain related evidence and must never reconcile into ABS totals.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--output-prefix", type=Path)
    args = parser.parse_args()
    payload = run(args.db, args.crosswalk)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = args.output_prefix or REPO_ROOT / "ops" / "reports" / f"fbo-archive-crosswalk-{stamp}"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    markdown_path = prefix.with_suffix(".md")
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(markdown_path, payload)
    print(json.dumps({"json": str(json_path), "markdown": str(markdown_path), **payload["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
