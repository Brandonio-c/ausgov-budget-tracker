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
    ("education", "Education"),
    ("home affairs", "Public order and safety"),
    ("infrastructure", "Transport and communication"),
    ("industry", "Other economic affairs"),
    ("science and resources", "Other economic affairs"),
]

# Optional subfunction hints from program labels
SUBFUNCTION_HINTS = [
    (re.compile(r"higher education|university", re.I), "Higher education"),
    (re.compile(r"school|primary|secondary", re.I), "School education"),
    (re.compile(r"vocational|vet\b|skills", re.I), "Vocational and industry training"),
    (re.compile(r"road", re.I), "Road transport"),
    (re.compile(r"rail", re.I), "Rail transport"),
    (re.compile(r"air\b|aviation", re.I), "Air transport"),
    (re.compile(r"sea\b|maritime|port", re.I), "Sea transport"),
    (re.compile(r"communication|broadband|nbn|spectrum", re.I), "Communication"),
    (re.compile(r"court|legal|attorney|justice", re.I), "Courts and legal services"),
    (re.compile(r"police|border|immigration|customs", re.I), "Police and fire protection services"),
    (re.compile(r"workforce|personnel|people", re.I), "Defence"),
    (re.compile(r"capability|sustainment|acquisition|operations?", re.I), "Defence"),
]


def _s6_function(portfolio: str) -> str | None:
    p = (portfolio or "").lower()
    for key, fn in PORTFOLIO_TO_S6:
        if key in p:
            return fn
    return None


def _subfunction(function: str, program_label: str) -> str:
    for pattern, sub in SUBFUNCTION_HINTS:
        if pattern.search(program_label or ""):
            # Keep Defence flat under function when hint is Defence itself
            if function == "Defence" and sub == "Defence":
                return "Defence programs"
            if function == "Education" and "education" in sub.lower():
                return sub
            if function == "Transport and communication":
                return sub
            if function == "Public order and safety":
                return sub
            if function == "Other economic affairs":
                return "Other economic affairs nec"
    defaults = {
        "Defence": "Defence programs",
        "Education": "General administration",
        "Transport and communication": "Other transport and communication",
        "Public order and safety": "Other public order and safety",
        "Other economic affairs": "Other economic affairs nec",
    }
    return defaults.get(function, "General administration")


def _clean_program(label: str) -> str:
    label = re.sub(r"\s+", " ", label or "").strip()
    label = re.sub(r"\s*Total funded expenditure\s*\[.\]\s*", " ", label, flags=re.I)
    label = re.sub(r"^Program\s+\d+(?:\.\d+)?\s*[-:]\s*", "", label, flags=re.I)
    label = re.sub(r"^Key cost category\s*/\s*", "", label, flags=re.I)
    return label.strip(" -")[:120] or "Program"


def remap_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        portfolio = r.get("portfolio") or ""
        # Fallback: parse portfolio from category prefix
        if not portfolio and " / " in (r.get("category") or ""):
            portfolio = r["category"].split(" / ", 1)[0]
        function = _s6_function(portfolio)
        if not function:
            continue
        program_label = r.get("program_label") or (
            r.get("category", "").split(" / ", 1)[-1] if r.get("category") else ""
        )
        # Skip very noisy OCR labels
        if re.search(r"\$'?000|estimate \$|Forward Estimate|E stimate|Resourcing", program_label, re.I):
            continue
        if len(program_label) < 4 or len(program_label) > 160:
            continue
        if program_label.count("$") >= 2:
            continue
        sub = _subfunction(function, program_label)
        program = _clean_program(program_label)
        # Defence A.6.1 is a single function total — hang programs directly under it.
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
    # Dedupe by path/fy/status/amount keeping first
    best: dict[tuple, dict] = {}
    for r in out:
        key = (r["fy"], r["estimate_status"], r["category"].lower(), int(float(r["amount"])))
        if key not in best:
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
