#!/usr/bin/env python3
"""Extract NDIA "Payments data" (June 2026 edition) support class ->
support category detail: the only slice of this dataset verified safe to
treat as a genuine additive partition within the source (see the module
docstring below for the full forensics that shaped this deliberately
narrow scope).

Source: https://dataresearch.ndis.gov.au/datasets/payments-datasets

Unlike ndis_participant_plan_budgets.py's dataset (participant counts and
per-participant averages, never additive), PmtAmt here is an actual
aggregate dollar figure ("Total amount paid to participants in the
preceding 12 months"), and support class -> support category is a
VERIFIED, near-exact additive partition within this source: the 9
categories under "Capacity Building" sum to $9,400,383,000 against the
class total of $9,400,381,000 (a $2,000 rounding gap on $9.4B; Core and
Capital reconcile to the dollar). A single payment transaction belongs to
exactly one support class and category, so summing dollars is safe here
- unlike the participant dataset's support-class dimension, where a
person can hold multiple support classes at once, making a person-count
sum invalid.

The source's own implied grand total across support classes ($51.45B for
FY2025-26) is close to but NOT exactly the canonical NDIS Statement 6
expenditure figure ($53.778B) - a different accounting basis/period
("preceding 12 months" ending 30 June 2026 is a rolling actual-payments
window, not a Statement 6 estimate). This crossing is therefore
related_breakdown, never same_group, matching the established pattern for
every other cross-source NDIS attachment this mission has built.

Deliberately NOT extracted here (recorded during forensics, not
ingested): support-item-level detail (only published jointly with
geography, not as its own national marginal - reconstructing a national
item total needs summing across all 9 state/territory values first) and
any disability/age/geography cross-tabulation (the dataset's dimension-
availability pattern is non-uniform - 12 distinct "which fields are ALL
vs specific" combinations were found across the file - unlike the
participant dataset's clean single-dimension marginals). Both are real,
disclosed follow-on opportunities, not silently dropped.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
IN_CSV = (
    REPO_ROOT
    / "data/raw/federal/ndis_payments/snapshots"
    / "20260824T044821Z/files/payments-june-2026.csv"
)
OUT_CSV = REPO_ROOT / "data/staging/breakdowns/ndis_payment_amount.csv"

FY = "2025-26"  # 30 June 2026 = end of FY2025-26
REPORT_DATE = "30-Jun-26"
ROOT_NODE = "NDIA Payments"
LANDING_URL = "https://dataresearch.ndis.gov.au/datasets/payments-datasets"
RESOURCE_URL = "https://dataresearch.ndis.gov.au/media/4577/download?attachment"

MARGINAL_DIMS = (
    "SuppItemNmbr",
    "RsdsInStateCd",
    "RsdsInSrvcDstrctNm",
    "NDISDsbltyGrpNm",
    "NDIAAgeBnd",
)


def _clean(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip())


def _is_category_scope(row: dict) -> bool:
    """True only for rows scoped to (SuppClass, SuppCatNm) with every
    other dimension at 'ALL' - the verified-safe additive slice."""
    return all(row[d] == "ALL" for d in MARGINAL_DIMS)


def extract() -> list[dict]:
    if not IN_CSV.is_file():
        return []

    rows: list[dict] = []
    seen_classes: dict[str, str] = {}

    with IN_CSV.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row["RprtDt"] != REPORT_DATE:
                continue
            if not _is_category_scope(row):
                continue

            supp_class = row["SuppClass"]
            supp_cat = row["SuppCatNm"]
            if supp_class == "ALL":
                continue

            try:
                amount = float(row["PmtAmt"].replace(",", ""))
            except (TypeError, ValueError):
                continue

            class_label = _clean(supp_class)
            if supp_cat == "ALL":
                # Support class grand total (own row).
                category = f"{ROOT_NODE} / {class_label}"
                seen_classes[supp_class] = category
            else:
                category = f"{ROOT_NODE} / {class_label} / {_clean(supp_cat)}"

            rows.append(
                {
                    "fy": FY,
                    "category": category,
                    "amount": f"{amount:.2f}",
                    "estimate_status": "actual",
                    "locator": (
                        f"ndis:payments:jun-2026:{supp_class}:"
                        f"{supp_cat if supp_cat != 'ALL' else 'class-total'}"
                    ),
                    "landing_url": LANDING_URL,
                    "resource_url": RESOURCE_URL,
                }
            )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "fy",
        "category",
        "amount",
        "estimate_status",
        "locator",
        "landing_url",
        "resource_url",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print({"wrote": str(OUT_CSV), "rows": len(rows)})
    return rows


def main() -> int:
    extract()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
