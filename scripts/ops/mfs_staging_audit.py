#!/usr/bin/env python3
"""Task 4 of the MFS-aggregates milestone: run the existing extractor
(scripts/ingest/extractors/mfs_aggregates.py) across the full corpus,
classify every extracted row against the Task 3 semantic model
(config/measure-semantics/mfs.yaml), and produce a row-level staging
audit. Read-only - does not write to data/facts.db.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from mfs_aggregates import _find_latest_asset, extract_workbook  # noqa: E402

SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "mfs.yaml"
SOURCE_ID = "federal_mfs_aggregates"


def load_label_index(semantics: dict) -> dict[str, str]:
    """label -> measure_type, built from every measure's source_label_variants."""
    index: dict[str, str] = {}
    for measure_type, spec in semantics["measures"].items():
        for label in spec.get("source_label_variants") or []:
            if label in index and index[label] != measure_type:
                raise ValueError(
                    f"label {label!r} claimed by both {index[label]!r} and {measure_type!r} - "
                    "ambiguous mapping, must be resolved in config/measure-semantics/mfs.yaml"
                )
            index[label] = measure_type
    return index


def month_to_period_end(fy: str, month: str) -> str:
    """Last calendar day of `month` within financial year `fy` (e.g. '2015-16', 'August' -> '2015-08-31')."""
    y1, y2 = fy.split("-")
    year1, year2 = int(y1), int("20" + y2) if len(y2) == 2 else int(y2)
    month_num = {
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    }[month]
    year = year1 if month_num >= 7 else year2
    last_day = {
        1: 31, 2: 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 3: 31,
        4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
    }[month_num]
    return f"{year:04d}-{month_num:02d}-{last_day:02d}"


def financial_year_start(fy: str) -> str:
    y1 = fy.split("-")[0]
    return f"{y1}-07-01"


def main() -> int:
    semantics = yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))
    label_index = load_label_index(semantics)

    path = _find_latest_asset(SOURCE_ID)
    if path is None:
        print(f"no asset found for {SOURCE_ID}", file=sys.stderr)
        return 1

    rows, quarantine = extract_workbook(path, SOURCE_ID)

    # Detect duplicate (source_id, fy, month, measure_label) combinations -
    # the extractor emits one row per (sheet, column, row-label); if any
    # single sheet has two rows with the identical stripped label for the
    # same column, that is a genuine same-cell duplicate worth flagging.
    from collections import Counter

    key_counts = Counter((r["fy"], r["month"], r["measure_label"]) for r in rows)
    duplicated_keys = {k for k, n in key_counts.items() if n > 1}

    audit_rows = []
    for r in rows:
        measure_type = label_index.get(r["measure_label"])
        spec = semantics["measures"].get(measure_type) if measure_type else None
        publishable = measure_type is not None
        quarantine_reason = "" if publishable else "unrecognized_label"

        is_dup = (r["fy"], r["month"], r["measure_label"]) in duplicated_keys
        if is_dup:
            quarantine_reason = (quarantine_reason + ";" if quarantine_reason else "") + "duplicate_cell_in_sheet"
            publishable = False

        flow_or_stock = spec.get("flow_or_stock") if spec else ""
        period_start = financial_year_start(r["fy"]) if spec and spec.get("period_start") == "financial_year_start" else ""
        period_end = month_to_period_end(r["fy"], r["month"]) if spec else ""

        audit_rows.append(
            {
                "source_id": SOURCE_ID,
                "file": str(path.relative_to(REPO_ROOT)),
                "sheet": r["sheet"],
                "source_cell": r["locator"],
                "raw_label": r["measure_label"],
                "normalized_label": r["measure_label"],
                "financial_year": r["fy"],
                "reporting_month": r["month"],
                "period_start": period_start,
                "period_end": period_end,
                "period_granularity": "month",
                "measure_type": measure_type or "",
                "flow_or_stock": flow_or_stock,
                "amount": r["amount"],
                "source_unit": r["unit"],
                "normalized_unit": "AUD",
                "estimate_status": r["estimate_status"],
                "accounting_basis": spec.get("accounting_basis") if spec else "",
                "compatibility_group": spec.get("compatibility_group") if spec else "",
                "publishable": publishable,
                "quarantine_reason": quarantine_reason,
                "citation_locator": r["locator"],
            }
        )

    for q in quarantine:
        audit_rows.append(
            {
                "source_id": SOURCE_ID,
                "file": str(path.relative_to(REPO_ROOT)),
                "sheet": q.get("sheet", ""),
                "source_cell": q.get("column", ""),
                "raw_label": q.get("label", ""),
                "normalized_label": q.get("label", ""),
                "financial_year": "",
                "reporting_month": "",
                "period_start": "",
                "period_end": "",
                "period_granularity": "",
                "measure_type": "",
                "flow_or_stock": "",
                "amount": "",
                "source_unit": q.get("unit", ""),
                "normalized_unit": "",
                "estimate_status": "",
                "accounting_basis": "",
                "compatibility_group": "",
                "publishable": False,
                "quarantine_reason": q.get("reason", ""),
                "citation_locator": "",
            }
        )

    fieldnames = [
        "source_id", "file", "sheet", "source_cell", "raw_label", "normalized_label",
        "financial_year", "reporting_month", "period_start", "period_end",
        "period_granularity", "measure_type", "flow_or_stock", "amount",
        "source_unit", "normalized_unit", "estimate_status", "accounting_basis",
        "compatibility_group", "publishable", "quarantine_reason", "citation_locator",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for row in audit_rows:
        writer.writerow(row)

    n_publishable = sum(1 for r in audit_rows if r["publishable"])
    n_quarantined = len(audit_rows) - n_publishable
    unrecognized = sorted({r["raw_label"] for r in audit_rows if r["quarantine_reason"] == "unrecognized_label"})
    print(
        f"# total_audit_rows={len(audit_rows)} publishable={n_publishable} quarantined={n_quarantined} "
        f"unrecognized_labels={unrecognized} duplicated_keys={len(duplicated_keys)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
