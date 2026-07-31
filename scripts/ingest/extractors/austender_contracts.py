#!/usr/bin/env python3
"""Top AusTender contracts under Defence / Health / Infrastructure (historical CN).

Source on disk: 2019-20 Australian Government Contract Data (AusTender CN export).
Published FY is 2019-20 — Actuals cascade uses nearest-FY fallback with a banner.
Hang under Statement 6 function parents as Contracts / UNSPSC / supplier leaves.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_CSV = REPO_ROOT / "data/staging/breakdowns/austender_contracts_topn.csv"
XLSX = (
    REPO_ROOT
    / "data/raw/federal/federal_austender_ocds_api/snapshots/20260721T024615Z/files"
    / "2019-20-australian-government-contract-data.xlsx"
)
LANDING = "https://www.tenders.gov.au/"
FY = "2019-20"
TOP_N_PER_PARENT = 40
TOP_UNSPSC_PER_PARENT = 12

AGENCY_PARENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"department of defence|defence material|defence housing", re.I), "Defence"),
    (
        re.compile(
            r"department of health|aged care|digital health|national health|"
            r"therapeutic goods|cancer australia",
            re.I,
        ),
        "Health",
    ),
    (
        re.compile(
            r"infrastructure|transport|regional development|communications|"
            r"civil aviation|airservices",
            re.I,
        ),
        "Transport and communication",
    ),
]


def _clean(s: str, limit: int = 90) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return (s.replace(" / ", " – ")[:limit] or "Unknown").strip()


def _parent_for_agency(agency: str) -> str | None:
    for pattern, parent in AGENCY_PARENTS:
        if pattern.search(agency or ""):
            return parent
    return None


def extract() -> list[dict]:
    import openpyxl

    if not XLSX.is_file():
        raise FileNotFoundError(XLSX)

    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else "" for c in next(it)]
    # Collect contracts per parent
    by_parent: dict[str, list[tuple[float, str, str, str]]] = defaultdict(list)
    # (value, unspsc, supplier, description)

    for row in it:
        d = dict(zip(header, row))
        agency = str(d.get("Agency Name") or "")
        parent = _parent_for_agency(agency)
        if not parent:
            continue
        try:
            value = float(d.get("Applicable Value") or d.get("Value") or 0)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        unspsc = _clean(str(d.get("UNSPSC Title") or "Other procurement"), 70)
        supplier = _clean(str(d.get("Supplier Name") or "Unknown supplier"), 70)
        desc = _clean(str(d.get("Description") or supplier), 70)
        by_parent[parent].append((value, unspsc, supplier, desc))
    wb.close()

    rows: list[dict] = []
    resource = XLSX.as_posix()

    for parent, items in by_parent.items():
        items.sort(key=lambda x: -x[0])
        # Aggregate by UNSPSC for mid ring
        unspsc_tot: dict[str, float] = defaultdict(float)
        unspsc_contracts: dict[str, list[tuple[float, str]]] = defaultdict(list)
        for value, unspsc, supplier, desc in items:
            unspsc_tot[unspsc] += value
            unspsc_contracts[unspsc].append((value, f"{supplier} – {desc}"[:90]))

        top_cats = sorted(unspsc_tot.items(), key=lambda x: -x[1])[:TOP_UNSPSC_PER_PARENT]
        # Folder aggregate for "Contracts (AusTender FY)" under parent
        contracts_folder = f"{parent} / Contracts (AusTender {FY})"
        rows.append(
            {
                "fy": FY,
                "amount": f"{sum(unspsc_tot.values()):.2f}",
                "category": contracts_folder,
                "estimate_status": "contract",
                "locator": f"austender:{FY}:contracts-folder",
                "landing_url": LANDING,
                "resource_url": resource,
            }
        )
        for unspsc, total in top_cats:
            cat = f"{parent} / Contracts (AusTender {FY}) / {unspsc}"
            rows.append(
                {
                    "fy": FY,
                    "amount": f"{total:.2f}",
                    "category": cat,
                    "estimate_status": "contract",
                    "locator": f"austender:{FY}:unspsc:{unspsc}",
                    "landing_url": LANDING,
                    "resource_url": resource,
                }
            )
            # Top suppliers under category
            top = sorted(unspsc_contracts[unspsc], key=lambda x: -x[0])[: max(3, TOP_N_PER_PARENT // TOP_UNSPSC_PER_PARENT)]
            for val, label in top:
                rows.append(
                    {
                        "fy": FY,
                        "amount": f"{val:.2f}",
                        "category": f"{cat} / {_clean(label)}",
                        "estimate_status": "contract",
                        "locator": f"austender:{FY}:contract:{label[:40]}",
                        "landing_url": LANDING,
                        "resource_url": resource,
                    }
                )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "fy",
        "amount",
        "category",
        "estimate_status",
        "locator",
        "landing_url",
        "resource_url",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(
        {
            "wrote": str(OUT_CSV),
            "rows": len(rows),
            "parents": {k: len(v) for k, v in by_parent.items()},
        }
    )
    return rows


def main() -> int:
    extract()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
