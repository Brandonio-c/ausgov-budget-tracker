#!/usr/bin/env python3
"""Extract FBO Appendix A Table A.1 expenses by function/sub-function → staging CSV.

Works on digital-native FBO Appendix A PDFs (and many consolidated FBOs that
embed the same table). Prefer the Outcome column for the document's FY.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import SKIP_LINE, iter_pdf_pages  # noqa: E402

DEFAULT_PDF = (
    REPO_ROOT
    / "data/raw/federal/federal_fbo_2024_25_function_subfunction"
    / "snapshots/20260720T215815Z/files/05_appendix_a.pdf"
)
OUT_DIR = REPO_ROOT / "data/staging/breakdowns"

FUNCTION_HEADERS = [
    "General public services",
    "Defence",
    "Public order and safety",
    "Education",
    "Health",
    "Social security and welfare",
    "Housing and community amenities",
    "Recreation and culture",
    "Fuel and energy",
    "Agriculture, forestry and fishing",
    "Mining, manufacturing and construction",
    "Transport and communication",
    "Other economic affairs",
    "Other purposes",
]

NUM = r"-?\d{1,3}(?:,\d{3})+|-?\d+"
NUM_RE = re.compile(NUM)
LINE_TAIL = re.compile(
    rf"^(?P<label>.+?)(?P<nums>(?:\s+(?:{NUM})){{2,5}})\s*$"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" .")


def _match_function(label: str) -> str | None:
    n = _norm(label).lower()
    for fn in FUNCTION_HEADERS:
        if n == fn.lower() or n.replace(" ", "") == fn.lower().replace(" ", ""):
            return fn
    return None


def _parse_m(tok: str) -> int:
    return int(tok.replace(",", "")) * 1_000_000


def extract(
    pdf: Path,
    *,
    outcome_fy: str,
    landing_url: str,
    resource_url: str,
) -> list[dict]:
    """Extract rows; outcome_fy is the FBO year (e.g. 2024-25)."""
    current_fn: str | None = None
    rows: list[dict] = []
    in_table = False

    for page_no, text in iter_pdf_pages(pdf):
        if "Table A.1" in text or "expenses by function" in text.lower():
            in_table = True
        if not in_table:
            continue

        for raw in text.splitlines():
            line = raw.strip()
            if not line or SKIP_LINE.match(line):
                continue
            if line.startswith("$m") or line.startswith("Outcome") or "Estimate at" in line:
                continue

            fn = _match_function(line)
            if fn and not NUM_RE.search(line):
                current_fn = fn
                continue

            m = LINE_TAIL.match(line)
            if not m:
                continue
            label = _norm(m.group("label"))
            nums = [_parse_m(t) for t in m.group("nums").split()]
            if not label or len(nums) < 2:
                continue

            # Typical layout: prior Outcome | Estimate | Outcome | Change
            # Prefer the third column when 4 values (Outcome for document FY).
            if len(nums) >= 3:
                amount = nums[2]
            else:
                amount = nums[-1]

            total_fn = None
            tm = re.match(r"^Total\s+(.+)$", label, re.I)
            if tm:
                total_fn = _match_function(tm.group(1)) or tm.group(1)

            if total_fn:
                category = f"Total {total_fn}" if not str(total_fn).startswith("Total") else str(total_fn)
                if not category.lower().startswith("total"):
                    category = f"Total {category}"
                path = category
            elif current_fn:
                path = f"{current_fn} / {label}"
            else:
                # Bare function total line like "Defence 45,103 ..."
                bare = _match_function(label)
                if bare:
                    path = bare
                    current_fn = bare
                else:
                    path = label

            rows.append(
                {
                    "fy": outcome_fy,
                    "amount": amount,
                    "category": path,
                    "locator": (
                        f"pdf:{pdf.name} | page:{page_no} | Table A.1 | {path} | "
                        f"Outcome {outcome_fy}"
                    ),
                    "landing_url": landing_url,
                    "resource_url": resource_url,
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--fy", default="2024-25")
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR / "federal_fbo_2024_25_function_subfunction.csv",
    )
    parser.add_argument(
        "--landing-url",
        default="https://budget.gov.au/content/fbo/index.htm",
    )
    parser.add_argument(
        "--resource-url",
        default="https://archive.budget.gov.au/2024-25/fbo/download/05_appendix_a.pdf",
    )
    args = parser.parse_args(argv)
    rows = extract(
        args.pdf,
        outcome_fy=args.fy,
        landing_url=args.landing_url,
        resource_url=args.resource_url,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["fy", "amount", "category", "locator", "landing_url", "resource_url"]
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows → {args.out}")
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
