#!/usr/bin/env python3
"""Extract Health Top-20 programs from Statement 6 Table 6.1.3 as PBS-bridge."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import SKIP_LINE, YEARS, iter_pdf_pages, parse_amount_token  # noqa: E402

BRIDGE_PDF = (
    REPO_ROOT
    / "data/raw/federal/federal_budget_statement_6_2026_27/snapshots/20260720T215815Z/files/bp1_bs-6.pdf"
)
OUT = REPO_ROOT / "data/staging/breakdowns/pbs_programs_health.csv"
LANDING = "https://www.health.gov.au/resources/collections/budget"
RESOURCE = (
    "https://www.health.gov.au/sites/default/files/2025-05/"
    # Prefer Statement 6 bridge amounts; locator cites Table 6.1.3.
    "placeholder-health-pbs.pdf"
)
# Actual cached Health PBS (2025-26 portal copy) for citation landing when present
HEALTH_PBS_CACHED = (
    REPO_ROOT
    / "data/raw/federal/federal_transparency_portal/snapshots/20260722T043324Z/files/"
    "2025-26-Health-and-Aged-Care-PBS.pdf"
)

STATUS_BY_FY = {
    "2025-26": "estimated_actual",
    "2026-27": "budget",
    "2027-28": "forward_estimate",
    "2028-29": "forward_estimate",
    "2029-30": "forward_estimate",
}

HEALTH_PROGRAMS = {
    "Medical Benefits": "Health / Medical services and benefits",
    "Assistance to the States for Healthcare Services": (
        "Health / Assistance to the states for public hospitals"
    ),
    "Pharmaceutical Benefits": "Health / Pharmaceutical benefits and services",
}

FIVE_TAIL = re.compile(
    r"^(?P<label>.*?)(?P<nums>(?:\s+-?\d{1,3}(?:,\d{3})+|\s+-?\d+){5})\s*$"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract(pdf: Path = BRIDGE_PDF) -> list[dict]:
    rows: list[dict] = []
    capturing = False
    pending: list[str] = []
    estimate_years = YEARS[1:]
    resource = (
        "https://budget.gov.au/2026-27/content/bp1/download/bp1_bs-6.pdf"
    )
    landing = "https://budget.gov.au/"

    for page_no, text in iter_pdf_pages(pdf):
        if "Table 6.1.3" in text and "Top 20 programs" in text:
            capturing = True
        if not capturing:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if capturing and line.startswith("Table 6.") and "6.1.3" not in line:
                capturing = False
                break
            if SKIP_LINE.match(line) or line.startswith("Program"):
                continue
            m = FIVE_TAIL.match(line)
            if not m:
                pending.append(_norm(line))
                continue
            label_part = _norm(m.group("label"))
            label_part = re.sub(r"\s+Health\s*$", "", label_part)
            label_part = re.sub(r"\s+SSW\s*$", "", label_part)
            label_part = re.sub(r"\s+Education\s*$", "", label_part)
            label = _norm(" ".join(pending + [label_part])) if pending else label_part
            pending = []
            label = re.sub(r"\s*\([a-z]\)\s*$", "", label, flags=re.I)
            parent = None
            for prog, path in HEALTH_PROGRAMS.items():
                if prog.lower() in label.lower():
                    parent = path
                    label = prog
                    break
            if not parent:
                continue
            nums = [parse_amount_token(t) for t in m.group("nums").split()]
            category = f"{parent} / {label}"
            for fy, amount in zip(estimate_years, nums):
                rows.append(
                    {
                        "fy": fy,
                        "amount": amount,
                        "category": category,
                        "estimate_status": STATUS_BY_FY[fy],
                        "row_kind": "program",
                        "locator": (
                            f"pdf:bp1_bs-6.pdf | page:{page_no} | Table 6.1.3 | "
                            f"program:{label} | col:{fy} | unit:$m | "
                            f"bridge:health_pbs"
                        ),
                        "landing_url": landing,
                        "resource_url": resource,
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
    print({"rows": len(rows), "path": str(path), "health_pbs_cached": HEALTH_PBS_CACHED.exists()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
