#!/usr/bin/env python3
"""Remap selected PBS portfolio program rows onto Statement 6 function paths."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
IN_CSV = REPO_ROOT / "data/staging/breakdowns/pbs_programs_all.csv"
OUT_CSV = REPO_ROOT / "data/staging/breakdowns/pbs_programs_s6_bridge.csv"

# Portfolio substring (lower) → Statement 6 budget function
PORTFOLIO_TO_S6 = [
    ("defence", "Defence"),
    ("veteran", "Social security and welfare"),
    ("social services", "Social security and welfare"),
    ("employment", "Social security and welfare"),
    ("education", "Education"),
    ("health", "Health"),
    ("home affairs", "Public order and safety"),
    ("attorney", "Public order and safety"),
    ("infrastructure", "Transport and communication"),
    ("industry", "Other economic affairs"),
    ("science and resources", "Other economic affairs"),
    ("climate", "Fuel and energy"),
    ("agriculture", "Agriculture, forestry and fishing"),
    ("treasury", "General public services"),
    ("finance", "General public services"),
    ("prime minister", "General public services"),
    ("foreign affairs", "General public services"),
]

# Optional subfunction hints from program labels
SUBFUNCTION_HINTS = [
    (re.compile(r"higher education|university", re.I), "Higher education"),
    (re.compile(r"school|primary|secondary|early learning", re.I), "School education"),
    (re.compile(r"vocational|vet\b|skills", re.I), "Vocational and industry training"),
    (re.compile(r"aged care|age pension|seniors", re.I), "Assistance to the aged"),
    (re.compile(r"disabilit|ndis|carer", re.I), "Assistance to people with disabilities"),
    (re.compile(r"job ?seeker|unemploy|working age", re.I), "Assistance to the unemployed and the sick"),
    (re.compile(r"child care|families|ftb|parenting", re.I), "Assistance to families with children"),
    (re.compile(r"veteran", re.I), "Assistance to veterans and dependants"),
    (re.compile(r"medical|pharma|hospital|medicare|health workforce", re.I), "Medical services and benefits"),
    (re.compile(r"road", re.I), "Road transport"),
    (re.compile(r"rail", re.I), "Rail transport"),
    (re.compile(r"air\b|aviation", re.I), "Air transport"),
    (re.compile(r"sea\b|maritime|port", re.I), "Sea transport"),
    (re.compile(r"communication|broadband|nbn|spectrum", re.I), "Communication"),
    (re.compile(r"court|legal|attorney|justice", re.I), "Courts and legal services"),
    (re.compile(r"police|border|immigration|customs", re.I), "Police and fire protection services"),
    (re.compile(r"energy|fuel|electric|hydrogen|renewable", re.I), "Fuel and energy"),
    (re.compile(r"workforce|personnel|people", re.I), "Defence"),
    (re.compile(r"capability|sustainment|acquisition|operations?", re.I), "Defence"),
]

NOISE = re.compile(
    r"\$'?000|estimate \$|Forward Estimate|E stimate|Resourcing|"
    r"Administered payment|Departmental payment|operating activities|"
    r"Net increase/\(decrease\) in cash|Closing balance attributable|"
    r"RECONCILIATION OF CASH|Payables|appropriations|"
    r"Appropriation Bill|Supply Bill|s74 external|Special accounts|"
    r"Estimated Budget Forward|Ordinary annual services|"
    r"Expenses not requiring appropriation|Sub-total transactions",
    re.I,
)

# Prefer program-like leaves when remapping noisy portfolios
PREFER_PROGRAM = re.compile(
    r"^Program\s+\d|Total funded expenditure|Outcome\s+\d|"
    r"Key cost category|Support for |Assistance |National Disability|"
    r"Child Care|Aged Care|Job Seeker|Medical Benefits|Pharmaceutical",
    re.I,
)


def _s6_function(portfolio: str) -> str | None:
    p = (portfolio or "").lower()
    for key, fn in PORTFOLIO_TO_S6:
        if key in p:
            return fn
    return None


def _subfunction(function: str, program_label: str) -> str:
    for pattern, sub in SUBFUNCTION_HINTS:
        if pattern.search(program_label or ""):
            if function == "Defence" and sub == "Defence":
                return "Defence programs"
            if function == "Education" and "education" in sub.lower():
                return sub
            if function == "Health" and "medical" in sub.lower():
                return sub
            if function == "Social security and welfare" and sub.startswith("Assistance"):
                return sub
            if function == "Transport and communication":
                return sub
            if function == "Public order and safety":
                return sub
            if function == "Other economic affairs":
                return "Other economic affairs nec"
            if function == "Fuel and energy":
                return "Fuel and energy"
            if function == "Agriculture, forestry and fishing":
                return "Agriculture"
            if function == "General public services":
                return "General public services nec"
    defaults = {
        "Defence": "Defence programs",
        "Education": "General administration",
        "Health": "Health services",
        "Social security and welfare": "Other welfare programs",
        "Transport and communication": "Other transport and communication",
        "Public order and safety": "Other public order and safety",
        "Other economic affairs": "Other economic affairs nec",
        "Fuel and energy": "Fuel and energy",
        "Agriculture, forestry and fishing": "Agriculture",
        "General public services": "General public services nec",
    }
    return defaults.get(function, "General administration")


def _clean_program(label: str) -> str:
    label = re.sub(r"\s+", " ", label or "").strip()
    label = re.sub(r"\s*Total funded expenditure\s*\[.\]\s*", " ", label, flags=re.I)
    label = re.sub(r"^Program\s+\d+(?:\.\d+)?\s*[-:]\s*", "", label, flags=re.I)
    label = re.sub(r"^Key cost category\s*/\s*", "", label, flags=re.I)
    return label.strip(" -")[:120] or "Program"


def _is_noise(program_label: str) -> bool:
    if NOISE.search(program_label or ""):
        return True
    if len(program_label) < 4 or len(program_label) > 160:
        return True
    if program_label.count("$") >= 2:
        return True
    # Reject pure numeric soup / ledger lines
    if re.search(r"\d{1,3}(?:,\d{3}){2,}", program_label) and not PREFER_PROGRAM.search(
        program_label
    ):
        return True
    return False


def remap_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    keep_fy = {"2024-25", "2025-26", "2023-24"}
    for r in rows:
        fy = str(r.get("fy") or "")
        if fy and fy not in keep_fy:
            continue
        portfolio = r.get("portfolio") or ""
        if not portfolio and " / " in (r.get("category") or ""):
            portfolio = r["category"].split(" / ", 1)[0]
        function = _s6_function(portfolio)
        if not function:
            continue
        program_label = r.get("program_label") or (
            r.get("category", "").split(" / ", 1)[-1] if r.get("category") else ""
        )
        if _is_noise(program_label):
            continue
        port_l = portfolio.lower()
        original = any(
            k in port_l
            for k in ("defence", "education", "home affairs", "infrastructure", "industry", "science and resources")
        )
        newly = not original
        if newly and not PREFER_PROGRAM.search(program_label):
            continue
        try:
            amt = abs(float(r.get("amount") or 0))
        except (TypeError, ValueError):
            continue
        if amt < 100_000:
            continue
        if amt > 200_000_000_000:
            continue
        sub = _subfunction(function, program_label)
        program = _clean_program(program_label)
        if len(program) < 3:
            continue
        if function == "Defence":
            category = f"{function} / {program}"
        else:
            category = f"{function} / {sub} / {program}"
        out.append(
            {
                "fy": r["fy"],
                "amount": r["amount"],
                "category": category,
                "estimate_status": r.get("estimate_status") or "budget",
                "locator": (
                    f"{r.get('locator', '')} | s6_bridge:{function}/{sub} | "
                    f"portfolio:{portfolio}"
                ).strip(" |"),
                "landing_url": r.get("landing_url") or "",
                "resource_url": r.get("resource_url") or "",
            }
        )
    # Prefer one amount per path+fy+status (largest)
    best: dict[tuple, dict] = {}
    for r in out:
        key = (r["fy"], r["estimate_status"], r["category"].lower())
        prev = best.get(key)
        if prev is None or abs(float(r["amount"])) > abs(float(prev["amount"])):
            best[key] = r
    return list(best.values())


def main() -> int:
    if not IN_CSV.is_file():
        print(f"missing input {IN_CSV}; run pbs_programs_all first", file=sys.stderr)
        return 2
    with IN_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    remapped = remap_rows(rows)
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
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(remapped)
    by_fn: dict[str, int] = {}
    for r in remapped:
        fn = r["category"].split(" / ", 1)[0]
        by_fn[fn] = by_fn.get(fn, 0) + 1
    print({"rows": len(remapped), "by_function": by_fn, "out": str(OUT_CSV)})
    return 0 if remapped else 2


if __name__ == "__main__":
    raise SystemExit(main())
