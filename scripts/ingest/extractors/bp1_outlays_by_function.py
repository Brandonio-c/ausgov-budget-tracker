#!/usr/bin/env python3
"""Extract BP1 statistical appendix Table I — Commonwealth Budget Outlays by Function.

Used for pre-FBO / early-FBO years where standalone FBO Appendix A does not exist.
Table I in late-1990s BP1 papers carries a multi-year function series; earlier columns
are outcomes / estimated outcomes, later columns are budget estimates/forward estimates.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data/staging/breakdowns"

# "1. Total General Public Services   5180 5486 ..." or "1.  Total ..."
ROW_RE = re.compile(
    r"^(?P<label>\d+\.\s+[A-Za-z][A-Za-z ,/\-()]+?)\s+(?P<nums>(?:-?\d{1,6}\s+){3,}-?\d{1,6})\s*$"
)
FY_HEADER_RE = re.compile(
    r"(?P<first>\d{4}-\d{2})(?:\s+(?:\d{2}-\d{2}|\d{4}-\d{2}))+"
)


def _expand_fy_tokens(tokens: list[str], first_fy: str) -> list[str]:
    """Expand header tokens like 87-88 / 1996-97 into canonical YYYY-YY."""
    start_year = int(first_fy.split("-")[0])
    out: list[str] = []
    for i, tok in enumerate(tokens):
        tok = tok.strip()
        if re.fullmatch(r"\d{4}-\d{2}", tok):
            out.append(tok)
            start_year = int(tok.split("-")[0])
        elif re.fullmatch(r"\d{2}-\d{2}", tok):
            # relative to progressing series
            yy = int(tok[:2])
            # century from previous absolute year
            century = start_year // 100 * 100
            y = century + yy
            if out:
                prev = int(out[-1].split("-")[0])
                if y < prev:
                    y += 100
            else:
                y = start_year if yy == start_year % 100 else century + yy
            out.append(f"{y}-{tok[3:5]}")
            start_year = y
        else:
            raise ValueError(f"bad fy token {tok!r}")
    return out


def extract_table_i(
    pdf: Path,
    *,
    target_fys: list[str],
    landing_url: str,
    resource_url: str,
) -> list[dict]:
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(pdf), "-"],
        text=True,
        errors="replace",
    )
    pages = text.split("\f")
    table_page = None
    for i, page in enumerate(pages):
        if re.search(
            r"Table I\s*-\s*Commonwealth Budget (?:Underlying )?Outlays by Function \(\$m\)",
            page,
        ):
            table_page = page
            # include continuation pages until Table II
            for j in range(i + 1, min(i + 4, len(pages))):
                if re.search(r"Table II\s*-", pages[j]):
                    break
                if re.search(r"^\s*\d+\.\s+", pages[j], re.M) or "Defence" in pages[j]:
                    table_page += "\n" + pages[j]
            break
    if not table_page:
        raise ValueError(f"Table I not found in {pdf}")

    header_m = None
    for line in table_page.splitlines():
        if re.search(r"\d{4}-\d{2}", line) and re.search(r"\d{2}-\d{2}", line):
            # strip leading label junk
            nums = re.findall(r"\d{4}-\d{2}|\d{2}-\d{2}", line)
            if len(nums) >= 4:
                header_m = nums
                break
    if not header_m:
        raise ValueError(f"FY header not found in Table I of {pdf}")

    first = next(t for t in header_m if re.fullmatch(r"\d{4}-\d{2}", t))
    fys = _expand_fy_tokens(header_m, first)
    target_idx = {fy: fys.index(fy) for fy in target_fys if fy in fys}
    if not target_idx:
        raise ValueError(f"none of {target_fys} in header {fys}")

    rows: list[dict] = []
    for line in table_page.splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        label = re.sub(r"\s+", " ", m.group("label")).strip()
        # drop leading "1. "
        label_clean = re.sub(r"^\d+\.\s+", "", label)
        # skip "Total ..." aggregate if desired? keep Total General Public Services etc.
        nums = [int(x) for x in m.group("nums").split()]
        if len(nums) != len(fys):
            # padded/truncated lines — skip rather than misalign
            continue
        for fy, idx in target_idx.items():
            amount = nums[idx] * 1_000_000
            rows.append(
                {
                    "fy": fy,
                    "amount": amount,
                    "category": label_clean,
                    "locator": (
                        f"BP1 Table I Outlays by Function | {label_clean} | fy:{fy} | "
                        f"unit:$m | pdf:{pdf.name}"
                    ),
                    "landing_url": landing_url,
                    "resource_url": resource_url,
                }
            )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--fy", action="append", required=True, help="target FY (repeatable)")
    ap.add_argument("--landing-url", required=True)
    ap.add_argument("--resource-url", required=True)
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR / "bp1_outlays_by_function_pre_fbo.csv",
    )
    args = ap.parse_args()
    rows = extract_table_i(
        args.pdf,
        target_fys=args.fy,
        landing_url=args.landing_url,
        resource_url=args.resource_url,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["fy", "amount", "category", "locator", "landing_url", "resource_url"],
        )
        w.writeheader()
        w.writerows(rows)
    print({"rows": len(rows), "out": str(args.out), "fys": sorted({r["fy"] for r in rows})})
    return 0


if __name__ == "__main__":
    sys.exit(main())
