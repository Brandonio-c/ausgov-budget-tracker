#!/usr/bin/env python3
"""Generalized PBS program-expense extractor for Commonwealth PBS PDFs.

Looks for Table 2.1-style program expense rows with trailing year columns ($'000).
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import SKIP_LINE, iter_pdf_pages  # noqa: E402

OUT_DIR = REPO_ROOT / "data/staging/breakdowns"
LANDING = "https://budget.gov.au/content/pbs/index.htm"

FIVE_TAIL = re.compile(
    r"^(?P<label>.*?)(?P<nums>(?:\s+-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|\s+-?\d+(?:\.\d+)?){3,6})\s*$"
)
YEARS_DEFAULT = ["2024-25", "2025-26", "2026-27", "2027-28", "2028-29", "2029-30"]

STATUS_BY_FY = {
    "2024-25": "actual",
    "2025-26": "estimated_actual",
    "2026-27": "budget",
    "2027-28": "forward_estimate",
    "2028-29": "forward_estimate",
    "2029-30": "forward_estimate",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_thousands(tok: str) -> int | None:
    try:
        return int(float(tok.replace(",", "")) * 1000)
    except ValueError:
        return None


def extract_pdf(pdf: Path, *, portfolio: str) -> list[dict]:
    rows: list[dict] = []
    capturing = False
    pending: list[str] = []
    for page_no, text in iter_pdf_pages(pdf):
        if (
            re.search(r"Table\s+2\.1", text)
            or "Program expenses" in text
            or "Expenses for Outcome" in text
            or "Budgeted expenses for Outcome" in text
        ):
            capturing = True
        if not capturing:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if capturing and re.match(r"^Table\s+\d", line) and "2.1" not in line:
                capturing = False
                break
            if SKIP_LINE.match(line):
                continue
            m = FIVE_TAIL.match(line)
            if not m:
                pending.append(_norm(line))
                if len(pending) > 4:
                    pending = pending[-4:]
                continue
            label = _norm(m.group("label"))
            if pending:
                label = _norm(" ".join(pending + [label]))
                pending = []
            if len(label) < 4 or label.lower().startswith("total"):
                continue
            if re.match(r"^(?:Outcome|Program|Departmental|Administered)\b", label, re.I) and len(label) < 20:
                continue
            nums = re.findall(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?", m.group("nums"))
            if len(nums) < 3:
                continue
            years = YEARS_DEFAULT[-len(nums) :]
            for fy, tok in zip(years, nums):
                amount = _parse_thousands(tok)
                if amount is None:
                    continue
                rows.append(
                    {
                        "fy": fy,
                        "amount": amount,
                        "category": f"{portfolio} / {label}",
                        "estimate_status": STATUS_BY_FY.get(fy, "budget"),
                        "locator": f"pdf:{pdf.name} | page:{page_no} | program:{label} | fy:{fy} | unit:$000",
                        "landing_url": LANDING,
                        "resource_url": LANDING,
                    }
                )
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for r in rows:
        key = (r["fy"], r["category"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def discover_pbs_pdfs() -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for pdf in (REPO_ROOT / "data/raw").rglob("*.pdf"):
        name = pdf.name.lower()
        if "pbs" not in name and "portfolio-budget" not in name and "budget_statements" not in name:
            continue
        stem = pdf.stem
        # Prefer readable portfolio from transparency portal naming
        portfolio = re.sub(r"(?i)^\d{4}-\d{2}-?", "", stem)
        portfolio = portfolio.replace("-PBS", "").replace("_PBS", "").replace("-pbs", "")
        portfolio = portfolio.replace("_", " ").replace("-", " ").strip()[:80] or stem[:80]
        found.append((portfolio, pdf))
    return found


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    for portfolio, pdf in discover_pbs_pdfs():
        try:
            rows = extract_pdf(pdf, portfolio=portfolio)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"pdf": str(pdf), "error": str(exc)}))
            continue
        print(json.dumps({"pdf": pdf.name, "portfolio": portfolio, "rows": len(rows)}))
        all_rows.extend(rows)
    out = OUT_DIR / "pbs_programs_all.csv"
    if all_rows:
        with out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)
    print(json.dumps({"total_rows": len(all_rows), "out": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
