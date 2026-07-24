#!/usr/bin/env python3
"""Extract Statement 6 component tables for SSW / Health / Education / Defence."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import SKIP_LINE, YEARS, iter_pdf_pages, parse_amount_line  # noqa: E402

DEFAULT_PDF = (
    REPO_ROOT
    / "data/raw/federal/federal_budget_statement_6_2026_27/snapshots/20260720T215815Z/files/bp1_bs-6.pdf"
)
OUT = REPO_ROOT / "data/staging/breakdowns/bp1_s6_components.csv"
LANDING = "https://budget.gov.au/"
RESOURCE = "https://budget.gov.au/2026-27/content/bp1/download/bp1_bs-6.pdf"

STATUS_BY_FY = {
    "2024-25": "estimated_actual",
    "2025-26": "estimated_actual",
    "2026-27": "budget",
    "2027-28": "forward_estimate",
    "2028-29": "forward_estimate",
    "2029-30": "forward_estimate",
}

# (table_id, parent_path, start_marker)
# parent_path is Function / Sub-function used in A.6.1
COMPONENT_TABLES = [
    (
        "Table 6.8.1",
        "Health / Medical services and benefits",
        "Trends in the major components of the medical services and",
    ),
    (
        "Table 6.8.2",
        "Health / Pharmaceutical benefits and services",
        "Trends in the major components of the pharmaceutical benefits and",
    ),
    (
        "Table 6.9.1",
        "Social security and welfare / Assistance to the aged",
        "Trends in the major components of the assistance to the aged",
    ),
    (
        "Table 6.9.2",
        "Social security and welfare / Assistance to people with disabilities",
        "Trends in the major components of the assistance to people with",
    ),
    (
        "Table 6.9.3",
        "Social security and welfare / Assistance to families with children",
        "Trends in the major components of the assistance to families with",
    ),
]

# Education/Defence publish sub-function summaries only (no 6.x.y component tables).
SUMMARY_TABLES = [
    (
        "Table 6.5",
        "Defence",
        "Table 6.5: Summary of expenses – defence",
    ),
    (
        "Table 6.7",
        "Education",
        "Table 6.7: Summary of expenses – education",
    ),
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract(pdf: Path = DEFAULT_PDF) -> list[dict]:
    pages = list(iter_pdf_pages(pdf))
    rows: list[dict] = []

    for table_id, parent_path, marker in COMPONENT_TABLES:
        capturing = False
        pending: list[str] = []
        for page_no, text in pages:
            if marker.lower() in text.lower() or table_id in text:
                capturing = True
            if not capturing:
                continue
            for raw in text.splitlines():
                line = raw.strip()
                if not line or SKIP_LINE.match(line):
                    continue
                if line.startswith("Table 6.") and table_id not in line and capturing:
                    # moved to next table
                    if "Trends in the major components" in line or (
                        line.startswith("Table 6.") and table_id not in line
                    ):
                        if table_id not in line and line.startswith("Table 6."):
                            capturing = False
                            break
                parsed = parse_amount_line(line)
                if parsed is None:
                    pending.append(_norm(line))
                    continue
                label_part, amounts = parsed
                label = _norm(" ".join(pending + [label_part])) if pending else _norm(label_part)
                pending = []
                if label.lower().startswith("total"):
                    continue
                # Component tables are Estimates only for 2025-26..2029-30 in body;
                # AMOUNT_TAIL expects 6 numbers — these tables have 5 estimate cols.
                # parse_amount_line requires 6; if we got 6, first may be missing actual.
                # Table 6.9.2 text: "National Disability Insurance Scheme(b)   53,778 56,125 ..."
                # That's 5 numbers. Our regex needs 6 — skip or pad.
                if len(amounts) == 6:
                    year_amounts = list(zip(YEARS, amounts))
                else:
                    continue
                category = f"{parent_path} / {label}"
                for fy, amount in year_amounts:
                    rows.append(
                        {
                            "fy": fy,
                            "amount": amount,
                            "category": category,
                            "estimate_status": STATUS_BY_FY[fy],
                            "row_kind": "component",
                            "locator": (
                                f"pdf:bp1_bs-6.pdf | page:{page_no} | {table_id} | "
                                f"component:{label} | col:{fy} | unit:$m"
                            ),
                            "landing_url": LANDING,
                            "resource_url": RESOURCE,
                        }
                    )
            if not capturing:
                break
    return rows


def write_csv(rows: list[dict], path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "fy",
        "amount",
        "category",
        "estimate_status",
        "row_kind",
        "locator",
        "landing_url",
        "resource_url",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def extract_summary_tables(pdf: Path) -> list[dict]:
    """Defence / Education Table 6.5 / 6.7 sub-function rows (5 estimate years)."""
    from extractors import parse_amount_token

    pages = list(iter_pdf_pages(pdf))
    rows: list[dict] = []
    estimate_years = YEARS[1:]

    for table_id, function, marker in SUMMARY_TABLES:
        capturing = False
        for page_no, text in pages:
            if marker.lower() in text.lower() or (
                table_id in text and f"Summary of expenses" in text
            ):
                capturing = True
            if not capturing:
                continue
            stop = False
            for raw in text.splitlines():
                line = raw.strip()
                if not line:
                    continue
                if capturing and line.startswith("Table 6.") and table_id not in line:
                    stop = True
                    break
                if SKIP_LINE.match(line):
                    continue
                m = FIVE_TAIL.match(line)
                if not m:
                    continue
                label = _norm(m.group("label"))
                label = re.sub(r"\s*\([a-z]\)\s*$", "", label, flags=re.I).strip()
                if not label or label.lower().startswith("total"):
                    continue
                # Skip nested indent lines that are part of schools breakdown if
                # they look like government/non-government under Schools — keep them
                # as Education / <label> peers (matches A.6.1 style).
                nums = [parse_amount_token(t) for t in m.group("nums").split()]
                category = f"{function} / {label}" if label.lower() != function.lower() else function
                for fy, amount in zip(estimate_years, nums):
                    rows.append(
                        {
                            "fy": fy,
                            "amount": amount,
                            "category": category,
                            "estimate_status": STATUS_BY_FY[fy],
                            "row_kind": "sub_function_summary",
                            "locator": (
                                f"pdf:bp1_bs-6.pdf | page:{page_no} | {table_id} | "
                                f"sub_function:{label} | col:{fy} | unit:$m"
                            ),
                            "landing_url": LANDING,
                            "resource_url": RESOURCE,
                        }
                    )
            if stop:
                capturing = False
    return rows


def main() -> int:
    # Component tables use 5 estimate years — extend parser locally for 5-col lines.
    rows = extract_five_col(DEFAULT_PDF) + extract_summary_tables(DEFAULT_PDF)
    path = write_csv(rows)
    print({"rows": len(rows), "path": str(path)})
    return 0


FIVE_TAIL = re.compile(
    r"^(?P<label>.*?)(?P<nums>(?:\s+-?\d{1,3}(?:,\d{3})+|\s+-?\d+){5})\s*$"
)


def extract_five_col(pdf: Path) -> list[dict]:
    from extractors import parse_amount_token

    pages = list(iter_pdf_pages(pdf))
    rows: list[dict] = []
    estimate_years = YEARS[1:]  # 2025-26 .. 2029-30

    for table_id, parent_path, marker in COMPONENT_TABLES:
        capturing = False
        pending: list[str] = []
        for page_no, text in pages:
            stop = False
            for raw in text.splitlines():
                line = raw.strip()
                if not line:
                    continue
                if not capturing:
                    # Start only at this table's own header (avoids same-page prior tables)
                    if table_id in line and "Trends in the major components" in line:
                        capturing = True
                    elif marker.lower() in line.lower() and table_id.split()[-1] in line:
                        capturing = True
                    continue
                if line.startswith("Table 6.") and table_id not in line:
                    stop = True
                    break
                if SKIP_LINE.match(line):
                    continue
                m = FIVE_TAIL.match(line)
                if not m:
                    low = line.lower()
                    if (
                        low.startswith("component")
                        or low.startswith("table 6.")
                        or "trends in" in low
                    ):
                        pending = []
                    elif not low.startswith("table") and not low.startswith("component"):
                        pending.append(_norm(line))
                    continue
                label_part = _norm(m.group("label"))
                if pending and any(
                    x in " ".join(pending).lower()
                    for x in ("trends in", "sub-function", "sets out", "major components")
                ):
                    pending = []
                label = _norm(" ".join(pending + [label_part])) if pending else label_part
                pending = []
                label = re.sub(r"^(?:.*?\bexpense\s+)", "", label, flags=re.I).strip()
                label = re.sub(r"\s*\([a-z]\)\s*$", "", label, flags=re.I).strip()
                if label.lower().startswith("total") or not label or len(label) < 3:
                    continue
                nums = [parse_amount_token(t) for t in m.group("nums").split()]
                category = f"{parent_path} / {label}"
                for fy, amount in zip(estimate_years, nums):
                    rows.append(
                        {
                            "fy": fy,
                            "amount": amount,
                            "category": category,
                            "estimate_status": STATUS_BY_FY[fy],
                            "row_kind": "component",
                            "locator": (
                                f"pdf:bp1_bs-6.pdf | page:{page_no} | {table_id} | "
                                f"component:{label} | col:{fy} | unit:$m"
                            ),
                            "landing_url": LANDING,
                            "resource_url": RESOURCE,
                        }
                    )
            if stop:
                capturing = False
                break
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
