#!/usr/bin/env python3
"""Extract Statement 11 net debt (11.4) and CGS face value (11.5) → staging CSVs."""

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
OUT_DIR = REPO_ROOT / "data/staging/breakdowns"

LANDING = "https://budget.gov.au/content/bp1/index.htm"
RESOURCE = "https://budget.gov.au/content/bp1/download/bp1_bs-11.pdf"

FY_RE = re.compile(r"^(?P<fy>\d{4}-\d{2})(?:\s*\([eE]\))?\s+(?P<rest>.+)$")
NUM = re.compile(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?")


def _parse_millions(tok: str) -> int | None:
    if tok.lower() in {"na", "-", "–", "—"}:
        return None
    try:
        return int(float(tok.replace(",", ""))) * 1_000_000
    except ValueError:
        return None


def extract_table(pdf: Path, table_id: str, category: str) -> list[dict]:
    rows: list[dict] = []
    active = False
    for page_no, text in iter_pdf_pages(pdf):
        if f"Table {table_id}" in text:
            active = True
        elif active and re.search(r"Table 11\.\d+", text) and f"Table {table_id}" not in text:
            active = False
        if not active:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            m = FY_RE.match(line)
            if not m:
                continue
            fy = m.group("fy")
            tokens = NUM.findall(m.group("rest"))
            if not tokens:
                continue
            amount = _parse_millions(tokens[0])
            if amount is None:
                continue
            status = "forward_estimate" if "(e)" in line.lower() else "audited_actual"
            rows.append(
                {
                    "fy": fy,
                    "amount": amount,
                    "category": category,
                    "estimate_status": status,
                    "locator": f"pdf:bp1_bs-11.pdf | page:{page_no} | Table {table_id} | {fy}",
                    "landing_url": LANDING,
                    "resource_url": RESOURCE,
                }
            )
    seen: set[str] = set()
    out = []
    for row in rows:
        if row["fy"] in seen:
            continue
        seen.add(row["fy"])
        out.append(row)
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["fy", "amount", "category", "estimate_status", "locator", "landing_url", "resource_url"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    pdf = DEFAULT_PDF
    if not pdf.exists():
        print(f"missing {pdf}", file=sys.stderr)
        return 1
    net = extract_table(pdf, "11.4", "Net debt")
    face = extract_table(pdf, "11.5", "CGS face value")
    write_csv(OUT_DIR / "federal_statement_11_net_debt.csv", net)
    write_csv(OUT_DIR / "federal_statement_11_cgs_face_value.csv", face)
    print({"net_debt_rows": len(net), "cgs_face_rows": len(face)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
