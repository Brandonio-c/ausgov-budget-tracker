#!/usr/bin/env python3
"""Current AusTender contracts under Defence / Health / Transport, via the
official OCDS (Open Contracting Data Standard) API at api.tenders.gov.au -
replaces the prior 2019-20 extraction (austender_contracts.py) with a
genuinely current sample and a real 4-level UNSPSC hierarchy (segment ->
family -> class -> commodity), decoded from the raw numeric classification
codes the OCDS API publishes (the AusTender weekly XLSX export, by
contrast, only ever exposes one flattened text category level - insufficient
for the mission's explicit "do not represent a raw UNSPSC code as one
opaque level" requirement).

Sample window: the most recent 8 complete weeks as at acquisition time
(2026-06-27 to 2026-08-22) - a full financial year would require ~1,200
paginated API requests (~112,000 releases for all of government); this
window is ~17,000 releases, filtered down to the same three portfolios the
prior extractor covered, and is a "top contracts" sample by design (like
its predecessor), not an exhaustive annual account.

UNSPSC titles decoded via a public reference table (O*NET Resource Center's
UNSPSC Reference, a standard third-party mirror of the same global UNSPSC
codeset AusTender itself uses for classification - not an AusTender-
published artifact, cited separately from the contract facts themselves).
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_CSV = REPO_ROOT / "data/staging/breakdowns/austender_contracts_topn.csv"
RELEASES_DIR = (
    REPO_ROOT
    / "data/raw/federal/federal_austender_ocds_api/snapshots/20260824T111930Z/files"
)
UNSPSC_XLSX = (
    REPO_ROOT
    / "data/raw/federal/federal_austender_ocds_api/snapshots/20260824T111930Z/files"
    / "unspsc_reference.xlsx"
)
LANDING = "https://www.tenders.gov.au/"
EDITION = "2026-Q3 sample"  # 8-week window, not a full financial year
FY = "2025-26"
TOP_N_PER_PARENT = 40
TOP_UNSPSC_CLASS_PER_PARENT = 12

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


def _load_unspsc_reference() -> dict[str, tuple[str, str, str, str]]:
    """8-digit code (at ANY granularity - segment/family/class/commodity,
    trailing digits zero-padded) -> (segment_title, family_title,
    class_title, commodity_title - the last two repeat the nearest known
    ancestor's title when the code itself is coarser than commodity).

    AusTender agencies frequently classify contracts at segment/family/
    class granularity (e.g. "40150000" - segment 40, family 15, class/
    commodity unset), not always down to the specific commodity - a
    reference table keyed only by full 8-digit commodity codes misses the
    overwhelming majority of real AusTender codes (empirically: 4,388
    Defence contracts checked, only 20 resolved against a commodity-only
    index). Indexing every level's own code (with trailing zeros, matching
    UNSPSC's own zero-padding convention) fixes this.
    """
    import openpyxl

    wb = openpyxl.load_workbook(UNSPSC_XLSX, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    next(it)  # header
    out: dict[str, tuple[str, str, str, str]] = {}
    for row in it:
        if not row or row[0] is None:
            continue
        commodity_code, commodity_title, class_code, class_title, family_code, family_title, segment_code, segment_title = row
        seg = _clean(str(segment_title), 60)
        fam = _clean(str(family_title), 60)
        cls = _clean(str(class_title), 60)
        com = _clean(str(commodity_title), 60)

        seg_key = str(int(segment_code)).zfill(8)
        fam_key = str(int(family_code)).zfill(8)
        cls_key = str(int(class_code)).zfill(8)
        com_key = str(int(commodity_code)).zfill(8)

        out.setdefault(seg_key, (seg, seg, seg, seg))
        out.setdefault(fam_key, (seg, fam, fam, fam))
        out.setdefault(cls_key, (seg, fam, cls, cls))
        out[com_key] = (seg, fam, cls, com)
    wb.close()
    return out


def _load_releases() -> list[dict]:
    releases: list[dict] = []
    for path in sorted(RELEASES_DIR.glob("window_*.json")):
        releases.extend(json.loads(path.read_text(encoding="utf-8")))
    return releases


def extract() -> list[dict]:
    if not RELEASES_DIR.is_dir() or not UNSPSC_XLSX.is_file():
        return []

    unspsc_ref = _load_unspsc_reference()
    releases = _load_releases()

    # (value, segment, family, cls, supplier, desc)
    by_parent: dict[str, list[tuple[float, str, str, str, str, str]]] = defaultdict(list)
    seen_contract_ids: set[str] = set()

    for rel in releases:
        parties = rel.get("parties") or []
        agency = next(
            (p.get("name") for p in parties if "procuringEntity" in (p.get("roles") or [])),
            None,
        )
        parent = _parent_for_agency(agency or "")
        if not parent:
            continue
        supplier = next(
            (p.get("name") for p in parties if "supplier" in (p.get("roles") or [])),
            "Unknown supplier",
        )
        for contract in rel.get("contracts") or []:
            cid = contract.get("id")
            if not cid or cid in seen_contract_ids:
                continue
            value_obj = contract.get("value") or {}
            try:
                value = float(value_obj.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            if value <= 0:
                continue
            items = contract.get("items") or []
            code = None
            for item in items:
                classification = item.get("classification") or {}
                if classification.get("scheme") == "UNSPSC" and classification.get("id"):
                    code = str(classification["id"]).zfill(8)
                    break
            if not code or code not in unspsc_ref:
                continue
            seen_contract_ids.add(cid)
            segment, family, cls, _commodity = unspsc_ref[code]
            desc = _clean(str(contract.get("description") or contract.get("title") or ""), 70)
            by_parent[parent].append((value, segment, family, cls, _clean(str(supplier), 70), desc))

    rows: list[dict] = []

    for parent, items in by_parent.items():
        items.sort(key=lambda x: -x[0])
        folder = f"{parent} / Contracts (AusTender {EDITION})"
        total_value = sum(v for v, *_ in items)
        rows.append(
            {
                "fy": FY,
                "amount": f"{total_value:.2f}",
                "category": folder,
                "estimate_status": "contract",
                "locator": f"austender-ocds:{EDITION}:contracts-folder:{parent}",
                "landing_url": LANDING,
                "resource_url": "https://api.tenders.gov.au/ocds/",
            }
        )

        # Aggregate by segment -> family -> class for the mid rings.
        seg_total: dict[str, float] = defaultdict(float)
        fam_total: dict[tuple[str, str], float] = defaultdict(float)
        cls_total: dict[tuple[str, str, str], float] = defaultdict(float)
        cls_items: dict[tuple[str, str, str], list[tuple[float, str, str]]] = defaultdict(list)
        for value, segment, family, cls, supplier, desc in items:
            seg_total[segment] += value
            fam_total[(segment, family)] += value
            cls_total[(segment, family, cls)] += value
            cls_items[(segment, family, cls)].append((value, supplier, desc))

        top_classes = sorted(cls_total.items(), key=lambda x: -x[1])[:TOP_UNSPSC_CLASS_PER_PARENT]
        emitted_segments: set[str] = set()
        emitted_families: set[tuple[str, str]] = set()
        for (segment, family, cls), cls_value in top_classes:
            if segment not in emitted_segments:
                rows.append(
                    {
                        "fy": FY,
                        "amount": f"{seg_total[segment]:.2f}",
                        "category": f"{folder} / {segment}",
                        "estimate_status": "contract",
                        "locator": f"austender-ocds:{EDITION}:segment:{segment}",
                        "landing_url": LANDING,
                        "resource_url": "https://api.tenders.gov.au/ocds/",
                    }
                )
                emitted_segments.add(segment)
            if (segment, family) not in emitted_families:
                rows.append(
                    {
                        "fy": FY,
                        "amount": f"{fam_total[(segment, family)]:.2f}",
                        "category": f"{folder} / {segment} / {family}",
                        "estimate_status": "contract",
                        "locator": f"austender-ocds:{EDITION}:family:{segment}:{family}",
                        "landing_url": LANDING,
                        "resource_url": "https://api.tenders.gov.au/ocds/",
                    }
                )
                emitted_families.add((segment, family))
            rows.append(
                {
                    "fy": FY,
                    "amount": f"{cls_value:.2f}",
                    "category": f"{folder} / {segment} / {family} / {cls}",
                    "estimate_status": "contract",
                    "locator": f"austender-ocds:{EDITION}:class:{segment}:{family}:{cls}",
                    "landing_url": LANDING,
                    "resource_url": "https://api.tenders.gov.au/ocds/",
                }
            )
            top_suppliers = sorted(
                cls_items[(segment, family, cls)], key=lambda x: -x[0]
            )[:5]
            for val, supplier, desc in top_suppliers:
                label = _clean(f"{supplier} – {desc}", 90)
                rows.append(
                    {
                        "fy": FY,
                        "amount": f"{val:.2f}",
                        "category": f"{folder} / {segment} / {family} / {cls} / {label}",
                        "estimate_status": "contract",
                        "locator": f"austender-ocds:{EDITION}:contract:{label[:40]}",
                        "landing_url": LANDING,
                        "resource_url": "https://api.tenders.gov.au/ocds/",
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
            "total_releases_scanned": len(releases),
        }
    )
    return rows


def main() -> int:
    extract()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
