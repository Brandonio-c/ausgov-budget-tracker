#!/usr/bin/env python3
"""Aggregate GrantConnect awards under matched PBS / Statement 6 parents (FY 2024-25).

Reads quarterly GaPublishedDownload XLSX already on disk under
`data/raw/federal/federal_grantconnect/`, keeps rows whose PBS Program Name
references 24/25 (or falls in the Jul-2024…Jun-2025 publish quarters), matches
them to cascade parent nodes, and emits staging rows:

  {parent_path} / {grant_program}                  — program aggregate
  {parent_path} / {grant_program} / {recipient}    — top recipients

Grant $ never replaces GFS Actuals; they hang as same_group under PBS/components.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = REPO_ROOT / "data/raw/federal/federal_grantconnect"
OUT_CSV = REPO_ROOT / "data/staging/breakdowns/grantconnect_awards_2024_25.csv"
DEFAULT_DB = REPO_ROOT / "data/facts.db"
LANDING = "https://www.grants.gov.au/"

FY = "2024-25"
# Publish quarters covering Commonwealth FY 2024–25
FY_GLOBS = ("*2024q3*.xlsx", "*2024q4*.xlsx", "*2025q1*.xlsx", "*2025q2*.xlsx")

TOP_RECIPIENTS = 10
MIN_PROGRAM_AUD_FOR_RECIPIENTS = 1_000_000.0

# High-confidence GC PBS label (normalized leaf) → exact cascade node name
SEED_PARENTS: dict[str, str] = {
    "support for the child care system": (
        "Social security and welfare / Assistance to families with children / "
        "Support for the child care system"
    ),
    "child care subsidy": (
        "Social security and welfare / Assistance to families with children / "
        "Child Care Subsidy"
    ),
    "aged care services": (
        "Social security and welfare / Assistance to the aged / Aged Care Services"
    ),
    "aged care quality": (
        "Social security and welfare / Assistance to the aged / Aged care quality"
    ),
    "support for seniors": (
        "Social security and welfare / Assistance to the aged / Support for Seniors"
    ),
    "national disability insurance scheme": (
        "Social security and welfare / Assistance to people with disabilities / "
        "National Disability Insurance Scheme"
    ),
    "job seeker income support": (
        "Social security and welfare / Assistance to the unemployed and the sick / "
        "Job Seeker Income Support"
    ),
    "financial support for carers": (
        "Social security and welfare / Assistance to people with disabilities / "
        "Financial Support for Carers"
    ),
    "financial support for people with disability": (
        "Social security and welfare / Assistance to people with disabilities / "
        "Financial Support for People with Disability"
    ),
}

# Agency code prefix → Statement 6 A.6.1 function (fallback when no PBS leaf match)
AGENCY_TO_A61: list[tuple[str, str]] = [
    ("dohda", "Health"),
    ("dohac", "Health"),
    ("nhmrc", "Health"),
    ("ca ", "Health"),  # Cancer Australia
    ("dewr", "Education"),  # Employment / skills → Education COFOG wedge for MVP
    ("de ", "Education"),  # Department of Education — space avoids "Defence"
    ("arc", "Education"),
    ("dss", "Social security and welfare"),
    ("dva", "Social security and welfare"),
    ("niaa", "Social security and welfare"),
    ("ndia", "Social security and welfare"),
    ("dcceew", "Fuel and energy"),
    ("doaff", "Agriculture, forestry and fishing"),
    ("disr", "Other economic affairs"),
    ("austrade", "Other economic affairs"),
    ("dfat", "General public services"),
    ("dod", "Defence"),
    ("defence", "Defence"),
    ("ha ", "Public order and safety"),
    ("agd", "Public order and safety"),
    ("itrdcsa", "Transport and communication"),
    ("infrastructure", "Transport and communication"),
]

CASCADE_SOURCES = (
    "federal_dss_pbs_programs",
    "federal_health_pbs_programs",
    "federal_budget_statement_6_components",
)


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_gc_pbs(name: str) -> str:
    """Strip agency / FY / output codes from GrantConnect PBS Program Name."""
    s = re.sub(r"\s+", " ", (name or "").strip())
    s = re.sub(r"^[A-Za-z]{2,12}\s+24/25\s+", "", s)
    s = re.sub(r"^\([^)]+\)\s*", "", s)
    s = re.sub(
        r"^(?:Hlth|DHDA|DVA|DHAF|DE|DoHDA|ITRDCSA|DAFF|NIAA)\s+"
        r"Output\s+[\d.]+\s*-?\s*(?:Admin\s+[\d-]+\s+)?",
        "",
        s,
        flags=re.I,
    )
    s = re.sub(r"^Output\s+[\d.]+\s*-?\s*", "", s, flags=re.I)
    s = re.sub(r"^Program\s+[\d.]+\s*-?\s*", "", s, flags=re.I)
    s = re.sub(r"^[\d.]+\s*:\s*", "", s)
    s = re.sub(r"^[\d.]+\s+", "", s)
    return s.strip(" -:")


def _fy_xlsx_files() -> list[Path]:
    files: list[Path] = []
    for pat in FY_GLOBS:
        files.extend(sorted(RAW_ROOT.rglob(pat)))
    # Prefer manual snapshots; dedupe by filename
    by_name: dict[str, Path] = {}
    for p in files:
        by_name[p.name] = p
    return sorted(by_name.values(), key=lambda p: p.name)


def _load_header_rows(path: Path) -> tuple[list[str], list[tuple]]:
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("openpyxl required to read GrantConnect XLSX") from exc

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    header: list[str] | None = None
    for row in it:
        vals = [str(c).strip() if c is not None else "" for c in row]
        if any("PBS Program" in v for v in vals):
            header = vals
            break
    if not header:
        wb.close()
        return [], []
    data = list(it)
    wb.close()
    return header, data


def _build_leaf_index(conn: sqlite3.Connection) -> dict[str, list[tuple[int, str, str]]]:
    rows = conn.execute(
        f"""
        SELECT n.id, n.name, d.source_key
        FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key IN ({",".join("?" * len(CASCADE_SOURCES))})
        """,
        CASCADE_SOURCES,
    ).fetchall()
    index: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for nid, name, sk in rows:
        leaf = name.rsplit(" / ", 1)[-1]
        index[_norm(leaf)].append((int(nid), name, sk))
    return index


def _a61_index(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT n.name FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = 'federal_budget_statement_6_a61'
          AND n.name NOT LIKE '% / % / %'
        """
    ).fetchall()
    out: dict[str, str] = {}
    for (name,) in rows:
        # Prefer function-level (no slash) then first segment
        key = name.split(" / ", 1)[0] if " / " in name else name
        out[_norm(key)] = name if " / " not in name else key
        if " / " not in name:
            out[_norm(name)] = name
    # Ensure top-level function names exist even if only subfunctions present
    for (name,) in rows:
        top = name.split(" / ", 1)[0]
        out.setdefault(_norm(top), top)
    return out


def resolve_parent(
    gc_pbs: str,
    leaf_index: dict[str, list[tuple[int, str, str]]],
    a61_index: dict[str, str],
) -> tuple[str, str] | None:
    """Return (parent_path, match_quality) or None."""
    leaf = strip_gc_pbs(gc_pbs)
    key = _norm(leaf)
    if not key:
        return None

    if key in SEED_PARENTS:
        return SEED_PARENTS[key], "seed"

    # Exact leaf against DSS / Health / components only
    hits = leaf_index.get(key) or []
    if hits:
        # Prefer DSS, then components, then health
        priority = {
            "federal_dss_pbs_programs": 0,
            "federal_health_pbs_programs": 1,
            "federal_budget_statement_6_components": 2,
        }
        hits = sorted(hits, key=lambda h: priority.get(h[2], 9))
        return hits[0][1], "exact_leaf"

    # Conservative contains: both sides >= 16 chars, one contains the other
    if len(key) >= 16:
        candidates: list[tuple[int, str, str]] = []
        for lk, vals in leaf_index.items():
            if len(lk) < 16:
                continue
            if key == lk or key in lk or lk in key:
                # Require high overlap ratio
                shorter, longer = (key, lk) if len(key) <= len(lk) else (lk, key)
                if len(shorter) / max(len(longer), 1) < 0.72:
                    continue
                candidates.extend(vals)
        if candidates:
            priority = {
                "federal_dss_pbs_programs": 0,
                "federal_health_pbs_programs": 1,
                "federal_budget_statement_6_components": 2,
            }
            candidates = sorted(candidates, key=lambda h: priority.get(h[2], 9))
            return candidates[0][1], "contains_leaf"

    # Agency → A.6.1 function fallback
    low = (gc_pbs or "").lower()
    for prefix, function in AGENCY_TO_A61:
        if low.startswith(prefix) or f" {prefix.strip()} " in f" {low} ":
            parent = a61_index.get(_norm(function))
            if parent:
                return parent, f"agency_a61:{function}"
            return function, f"agency_a61:{function}"
    return None


def _clean_label(s: str, limit: int = 100) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = s.replace(" / ", " – ")
    return (s[:limit] or "Unknown").strip()


def extract(db_path: Path = DEFAULT_DB) -> list[dict]:
    files = _fy_xlsx_files()
    if not files:
        raise FileNotFoundError(f"No GrantConnect FY XLSX under {RAW_ROOT}")

    conn = sqlite3.connect(str(db_path))
    try:
        leaf_index = _build_leaf_index(conn)
        a61_index = _a61_index(conn)
    finally:
        conn.close()

    # (parent_path, grant_program, recipient) -> amount
    program_totals: dict[tuple[str, str], float] = defaultdict(float)
    recipient_totals: dict[tuple[str, str, str], float] = defaultdict(float)
    match_stats: dict[str, int] = defaultdict(int)
    unmatched_labels: dict[str, float] = defaultdict(float)

    for path in files:
        header, data = _load_header_rows(path)
        if not header:
            continue
        for row in data:
            d = dict(zip(header, row))
            pbs = d.get("PBS Program Name")
            val = d.get("Value (AUD)")
            if pbs is None or val is None:
                continue
            try:
                amount = float(val)
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue
            pbs_s = str(pbs).strip()
            # Prefer 24/25-tagged rows; still keep FY-quarter files without tag
            if "24/25" not in pbs_s and "2024-25" not in pbs_s:
                # Skip clear other-year tags
                if re.search(r"2[0-9]/2[0-9]", pbs_s) and "24/25" not in pbs_s:
                    continue

            resolved = resolve_parent(pbs_s, leaf_index, a61_index)
            if not resolved:
                unmatched_labels[pbs_s] += amount
                match_stats["unmatched"] += 1
                continue
            parent_path, quality = resolved
            match_stats[quality] += 1

            grant_program = _clean_label(
                str(d.get("Grant Program") or d.get("Grant Activity") or "Grant program")
            )
            recipient = _clean_label(str(d.get("Recipient Name") or "Unknown recipient"), 80)

            program_totals[(parent_path, grant_program)] += amount
            recipient_totals[(parent_path, grant_program, recipient)] += amount

    rows: list[dict] = []
    resource = files[0].as_posix()

    for (parent_path, grant_program), amount in sorted(
        program_totals.items(), key=lambda x: -x[1]
    ):
        category = f"{parent_path} / {grant_program}"
        rows.append(
            {
                "fy": FY,
                "amount": f"{amount:.2f}",
                "category": category,
                "estimate_status": "award",
                "locator": f"grantconnect:{FY}:program:{grant_program}",
                "landing_url": LANDING,
                "resource_url": resource,
                "match_parent": parent_path,
                "layer": "grant_program",
            }
        )

        # Top recipients under large programs
        if amount < MIN_PROGRAM_AUD_FOR_RECIPIENTS:
            continue
        recs = [
            (rec, amt)
            for (p, g, rec), amt in recipient_totals.items()
            if p == parent_path and g == grant_program
        ]
        recs.sort(key=lambda x: -x[1])
        top = recs[:TOP_RECIPIENTS]
        other = sum(a for _, a in recs[TOP_RECIPIENTS:])
        for rec, amt in top:
            rows.append(
                {
                    "fy": FY,
                    "amount": f"{amt:.2f}",
                    "category": f"{category} / {rec}",
                    "estimate_status": "award",
                    "locator": f"grantconnect:{FY}:recipient:{rec}",
                    "landing_url": LANDING,
                    "resource_url": resource,
                    "match_parent": parent_path,
                    "layer": "recipient",
                }
            )
        if other > 0 and len(recs) > TOP_RECIPIENTS:
            rows.append(
                {
                    "fy": FY,
                    "amount": f"{other:.2f}",
                    "category": f"{category} / Other recipients ({len(recs) - TOP_RECIPIENTS})",
                    "estimate_status": "award",
                    "locator": f"grantconnect:{FY}:recipient:other",
                    "landing_url": LANDING,
                    "resource_url": resource,
                    "match_parent": parent_path,
                    "layer": "recipient",
                }
            )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "fy",
                "amount",
                "category",
                "estimate_status",
                "locator",
                "landing_url",
                "resource_url",
                "match_parent",
                "layer",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "wrote": str(OUT_CSV),
        "files": [p.name for p in files],
        "rows": len(rows),
        "programs": len(program_totals),
        "match_stats": dict(match_stats),
        "unmatched_top": sorted(unmatched_labels.items(), key=lambda x: -x[1])[:15],
        "matched_aud": sum(program_totals.values()),
        "unmatched_aud": sum(unmatched_labels.values()),
    }
    print(summary)
    return rows


def main(argv: list[str] | None = None) -> int:
    extract()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
