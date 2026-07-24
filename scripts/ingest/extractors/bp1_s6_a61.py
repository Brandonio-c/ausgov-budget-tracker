#!/usr/bin/env python3
"""Extract BP1 Statement 6 Table A.6.1 → staging CSV with hierarchical categories."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import (  # noqa: E402
    SKIP_LINE,
    YEARS,
    iter_pdf_pages,
    parse_amount_line,
)

DEFAULT_PDF = (
    REPO_ROOT
    / "data/raw/federal/federal_budget_statement_6_2026_27/snapshots/20260720T215815Z/files/bp1_bs-6.pdf"
)
OUT = REPO_ROOT / "data/staging/breakdowns/bp1_s6_a61.csv"

LANDING = "https://budget.gov.au/"
RESOURCE = "https://budget.gov.au/2026-27/content/bp1/download/bp1_bs-6.pdf"

FUNCTION_HEADERS = [
    "General public services",
    "Defence",
    "Public order and safety",
    "Education",
    "Health",
    "Social security and welfare",
    "Housing and community amenities",
    "Recreation and culture",
    "Fuel and energy",
    "Agriculture, forestry and fishing",
    "Mining, manufacturing and construction",
    "Transport and communication",
    "Other economic affairs",
    "Other purposes",
]

STATUS_BY_FY = {
    "2024-25": "estimated_actual",
    "2025-26": "estimated_actual",
    "2026-27": "budget",
    "2027-28": "forward_estimate",
    "2028-29": "forward_estimate",
    "2029-30": "forward_estimate",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" .")


def _match_function(label: str) -> str | None:
    n = _norm(label).lower()
    for fn in FUNCTION_HEADERS:
        if n == fn.lower():
            return fn
    # fuzzy for split headers
    for fn in FUNCTION_HEADERS:
        if n.replace(" ", "") == fn.lower().replace(" ", ""):
            return fn
    return None


def _match_total(label: str) -> str | None:
    n = _norm(label)
    m = re.match(r"^Total\s+(.+)$", n, re.I)
    if not m:
        return None
    rest = m.group(1).strip()
    hit = _match_function(rest)
    if hit:
        return hit
    # "Total expenses"
    if rest.lower() == "expenses":
        return "Total expenses"
    return rest


def extract(pdf: Path = DEFAULT_PDF) -> list[dict]:
    current_fn: str | None = None
    pending: list[str] = []
    rows: list[dict] = []

    for page_no, text in iter_pdf_pages(pdf):
        if "Table A.6.1" not in text and "function and sub-function" not in text.lower():
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or SKIP_LINE.match(line):
                continue

            parsed = parse_amount_line(line)
            if parsed is None:
                pending.append(_norm(line))
                joined = _norm(" ".join(pending))
                fn = _match_function(joined)
                if fn:
                    current_fn = fn
                    pending = []
                continue

            label_part, amounts = parsed
            if pending:
                label = _norm(" ".join(pending + [label_part]))
                pending = []
            else:
                label = _norm(label_part)

            total_fn = _match_total(label)
            if total_fn == "Total expenses":
                current_fn = None
                continue
            if total_fn:
                current_fn = total_fn
                category = total_fn
                kind = "total"
            else:
                fn_only = _match_function(label)
                if fn_only:
                    # Function with a single total line (Defence, Fuel and energy, Mining…)
                    current_fn = fn_only
                    category = fn_only
                    kind = "total"
                else:
                    if not current_fn:
                        continue
                    category = f"{current_fn} / {label}"
                    kind = "subfunction"

            for fy, amount in zip(YEARS, amounts):
                rows.append(
                    {
                        "fy": fy,
                        "amount": amount,
                        "category": category,
                        "estimate_status": STATUS_BY_FY[fy],
                        "row_kind": kind,
                        "locator": (
                            f"pdf:bp1_bs-6.pdf | page:{page_no} | Table A.6.1 | "
                            f"function:{current_fn or category} | col:{fy} | unit:$m"
                        ),
                        "landing_url": LANDING,
                        "resource_url": RESOURCE,
                    }
                )
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


def main() -> int:
    rows = extract()
    path = write_csv(rows)
    print({"rows": len(rows), "path": str(path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
