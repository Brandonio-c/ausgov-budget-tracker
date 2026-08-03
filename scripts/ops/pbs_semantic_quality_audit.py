#!/usr/bin/env python3
"""Task 6 (semantic-defect milestone): run the Task 5 label-quality
classifier across the entire acquired PBS corpus (federal_pbs_programs_all
in data/facts.db) without modifying the database, and produce a timestamped
CSV/MD semantic-quality audit report.

Read-only against facts.db. Does not write, reload, or quarantine anything -
this is the pre-reload evidence Task 8 requires before touching the graph.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from pbs_label_classifier import classify_label  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
PBS_SOURCE_KEY = "federal_pbs_programs_all"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# Portfolios the mission explicitly requires a manual sample review of.
# NDIA content lives inside the "Health Disability and Ageing" PBS
# portfolio (see config/breakdowns/crosswalks/pbs_programs_all_under_s6.yaml
# program_label_overrides) rather than its own top-level PBS portfolio, so
# it is matched on label content instead of the portfolio column.
REQUIRED_REVIEW_PORTFOLIOS = [
    "Social Services",
    "Health Disability and Ageing",
    "Defence",
    "Education",
    "Veterans' Affairs",
    "Attorney-General's",
    "Infrastructure Transport Regional Development Communications Sport and the Arts",
]
NDIA_LABEL_MARKERS = re.compile(r"National Disability Insurance|\bNDIS\b|\bNDIA\b", re.I)

LOCATOR_FIELD_RE = re.compile(r"source_id:(?P<source_id>[^|]+)\|.*?page:(?P<page>\d+)")


def parse_portfolio_and_label(node_name: str) -> tuple[str, str]:
    if " / " not in node_name:
        return node_name, ""
    portfolio, label = node_name.split(" / ", 1)
    return portfolio, label


def _parse_locator(source_locator_json: str | None) -> tuple[str, str]:
    if not source_locator_json:
        return "", ""
    try:
        data = json.loads(source_locator_json)
    except (TypeError, ValueError):
        return "", ""
    locator = data.get("locator") or ""
    m = LOCATOR_FIELD_RE.search(locator)
    source_id = m.group("source_id").strip() if m else ""
    page = m.group("page") if m else ""
    return source_id, page


def main() -> int:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT f.id AS fact_id, f.financial_year, f.estimate_status, f.amount_aud,
               f.source_locator_json, n.name AS node_name
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        WHERE d.source_key = ?
        ORDER BY n.name, f.financial_year
        """,
        (PBS_SOURCE_KEY,),
    ).fetchall()
    conn.close()

    out_csv = REPO_ROOT / f"ops/reports/pbs-semantic-quality-audit-{STAMP}.csv"
    out_md = REPO_ROOT / f"ops/reports/pbs-semantic-quality-audit-{STAMP}.md"

    class_counts: Counter[str] = Counter()
    rejection_reason_counts: Counter[str] = Counter()
    portfolio_class_counts: dict[str, Counter[str]] = {}
    csv_rows: list[dict[str, Any]] = []
    portfolio_samples: dict[str, list[dict[str, Any]]] = {}
    ndia_samples: list[dict[str, Any]] = []
    malformed_samples: list[dict[str, Any]] = []

    for row in rows:
        portfolio, raw_label = parse_portfolio_and_label(row["node_name"])
        result = classify_label(raw_label)
        source_id, page = _parse_locator(row["source_locator_json"])
        normalized_label = re.sub(r"\s+", " ", raw_label).strip()

        class_counts[result.classification] += 1
        if result.rejection_reason:
            rejection_reason_counts[result.rejection_reason] += 1
        portfolio_class_counts.setdefault(portfolio, Counter())[result.classification] += 1

        record = {
            "source_id": source_id,
            "source_file": "",  # filled below from the locator string
            "page": page,
            "portfolio": portfolio,
            "raw_label": raw_label[:300],
            "normalized_label": normalized_label[:300],
            "classification": result.classification,
            "publishable": result.publishable,
            "rejection_reason": result.rejection_reason or "",
            "financial_year": row["financial_year"],
            "estimate_status": row["estimate_status"],
            "amount": row["amount_aud"],
            "locator": (
                json.loads(row["source_locator_json"]).get("locator", "")
                if row["source_locator_json"]
                else ""
            ),
        }
        # source_file is embedded in the locator string ("pdf:<name>"), not
        # a separate JSON field - pull it out for the CSV's own column.
        m = re.search(r"pdf:([^|]+)\|", record["locator"] + "|")
        record["source_file"] = m.group(1).strip() if m else ""
        csv_rows.append(record)

        if portfolio in REQUIRED_REVIEW_PORTFOLIOS:
            bucket = portfolio_samples.setdefault(portfolio, [])
            if len(bucket) < 15:
                bucket.append(record)
        if NDIA_LABEL_MARKERS.search(raw_label):
            if len(ndia_samples) < 15:
                ndia_samples.append(record)
        if result.classification == "malformed_concatenated_row" and len(malformed_samples) < 25:
            malformed_samples.append(record)

    import csv as csv_mod

    fieldnames = [
        "source_id", "source_file", "page", "portfolio", "raw_label", "normalized_label",
        "classification", "publishable", "rejection_reason", "financial_year",
        "estimate_status", "amount", "locator",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv_mod.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in csv_rows:
            writer.writerow(r)

    total = len(csv_rows)
    accepted = class_counts["program"] + class_counts["outcome"] + class_counts["component"]
    rejected = total - accepted

    with out_md.open("w", encoding="utf-8") as fh:
        fh.write(f"# PBS semantic quality audit — {STAMP}\n\n")
        fh.write(
            f"Read-only against `data/facts.db` (`{PBS_SOURCE_KEY}`); no writes performed. "
            f"{total} total facts across every acquired PBS portfolio document.\n\n"
        )
        fh.write("## Totals by classification\n\n")
        fh.write("| classification | count | publishable |\n|---|---:|---|\n")
        from pbs_label_classifier import PUBLISHABLE_CLASSES

        for cls, count in class_counts.most_common():
            fh.write(f"| {cls} | {count} | {'yes' if cls in PUBLISHABLE_CLASSES else 'no'} |\n")
        fh.write(f"\n**Accepted (program/outcome/component): {accepted}**\n\n")
        fh.write(f"**Rejected/quarantined: {rejected}**\n\n")

        fh.write("## Top recurring rejection reasons\n\n")
        fh.write("| reason | count |\n|---|---:|\n")
        for reason, count in rejection_reason_counts.most_common(20):
            fh.write(f"| {reason} | {count} |\n")

        fh.write("\n## Representative malformed_concatenated_row source pages\n\n")
        for r in malformed_samples:
            fh.write(
                f"- `{r['source_id']}` p.{r['page']} ({r['portfolio']}): "
                f"\"{r['raw_label'][:120]}\"\n"
            )

        fh.write("\n## Manual portfolio review (required by Task 6)\n\n")
        for portfolio in REQUIRED_REVIEW_PORTFOLIOS:
            counts = portfolio_class_counts.get(portfolio, Counter())
            fh.write(f"### {portfolio}\n\n")
            if not counts:
                fh.write("No facts found for this portfolio in the corpus.\n\n")
                continue
            fh.write("| classification | count |\n|---|---:|\n")
            for cls, count in counts.most_common():
                fh.write(f"| {cls} | {count} |\n")
            fh.write("\nSample rows:\n\n")
            for r in portfolio_samples.get(portfolio, [])[:8]:
                fh.write(
                    f"- [{r['classification']}] \"{r['raw_label'][:120]}\" "
                    f"(fy={r['financial_year']}, {r['source_id']} p.{r['page']})\n"
                )
            fh.write("\n")

        fh.write("### NDIA (label-matched within Health Disability and Ageing)\n\n")
        for r in ndia_samples[:10]:
            fh.write(
                f"- [{r['classification']}] \"{r['raw_label'][:120]}\" "
                f"(fy={r['financial_year']}, {r['source_id']} p.{r['page']})\n"
            )

    print(
        json.dumps(
            {
                "csv": str(out_csv),
                "md": str(out_md),
                "total": total,
                "accepted": accepted,
                "rejected": rejected,
                "by_class": dict(class_counts),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
