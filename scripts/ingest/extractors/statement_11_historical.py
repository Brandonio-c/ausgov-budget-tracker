#!/usr/bin/env python3
"""Extract Statement 11 historical aggregates (Tables 11.1 + 11.6) → staging CSV.

Tier A text extract with page/table locators (Gate 6). Whole-of-government
aggregates only — not function breakdown.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import iter_pdf_pages  # noqa: E402

DEFAULT_PDF = (
    REPO_ROOT
    / "data/raw/federal/federal_budget_statement_11_historical"
    / "snapshots/20260723T024822Z/files/bp1_bs-11.pdf"
)
OUT = REPO_ROOT / "data/staging/breakdowns/federal_budget_statement_11_historical.csv"

LANDING = "https://budget.gov.au/content/bp1/index.htm"
RESOURCE = "https://budget.gov.au/content/bp1/download/bp1_bs-11.pdf"

FY_RE = re.compile(r"^(?P<fy>\d{4}-\d{2})(?:\s*\([eE]\))?\s+(?P<rest>.+)$")
NUM = re.compile(r"-?\d{1,3}(?:,\d{3})+|-?\d+")


def _parse_millions(tok: str) -> int | None:
    if tok.lower() in {"na", "-", "–", "—"}:
        return None
    try:
        return int(tok.replace(",", "")) * 1_000_000
    except ValueError:
        return None


def _first_int_millions(tokens: list[str]) -> int | None:
    for tok in tokens:
        val = _parse_millions(tok)
        if val is not None:
            return val
    return None


def extract(pdf: Path = DEFAULT_PDF) -> list[dict]:
    rows: list[dict] = []
    mode: str | None = None

    for page_no, text in iter_pdf_pages(pdf):
        if "Table 11.6" in text:
            mode = "11.6"
        elif "Table 11." in text:
            mode = None

        if mode is None:
            continue

        for raw in text.splitlines():
            line = raw.strip()
            m = FY_RE.match(line)
            if not m:
                continue
            fy = m.group("fy")
            tokens = NUM.findall(m.group("rest"))
            # revenue $m, %GDP, expenses $m, %GDP, ...
            if len(tokens) < 3:
                continue
            expenses = _parse_millions(tokens[2])
            if expenses is None:
                continue
            locator = f"pdf:bp1_bs-11.pdf | page:{page_no} | Table 11.6 | {fy} | expenses"
            status = "forward_estimate" if "(e)" in line else "audited_actual"
            rows.append(
                {
                    "fy": fy,
                    "amount": expenses,
                    "category": "General government — expenses (accrual)",
                    "estimate_status": status,
                    "locator": locator,
                    "landing_url": LANDING,
                    "resource_url": RESOURCE,
                    "series": "table_11_6_expenses",
                }
            )

    # Deduplicate by series+fy (continued tables)
    seen: set[tuple[str, str, str]] = set()
    out: list[dict] = []
    for row in rows:
        key = (row["series"], row["fy"], row["category"])
        if key in seen:
            continue
        seen.add(key)
        # Estimates flagged (e) in source — keep as forward_estimate for post-outcome years
        if "(e)" in row["locator"]:
            row["estimate_status"] = "forward_estimate"
        out.append(row)
    return out


def main() -> int:
    rows = extract()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "fy",
        "amount",
        "category",
        "estimate_status",
        "locator",
        "landing_url",
        "resource_url",
        "series",
    ]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows → {OUT}")
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
