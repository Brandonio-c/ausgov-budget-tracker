#!/usr/bin/env python3
"""Extract NDIA "Participant Numbers and Plan Budgets" (June 2026 edition)
into two staged measures: participant counts and average committed plan
budget per participant - both related, non-additive evidence attached to
the existing canonical NDIS expenditure node, never a partition of it.

Source: https://dataresearch.ndis.gov.au/datasets/participant-datasets
Data dictionary confirms (see data/raw/federal/
ndis_participant_numbers_and_plan_budgets/snapshots/*/files/
participant-plan-budgets-data-rules.docx):
  - ActvPrtcpnt: "Low participant counts have been modified... to protect
    privacy. The aggregated totals have not been modified." Empirically,
    rows with fewer than 11 participants are suppressed to "<11"; larger
    "<N" values also appear on some marginal/aggregate cells (a distinct,
    undocumented non-exhaustive-cascade case) - in both cases "<N" is
    faithfully represented as an upper bound, never as an exact count.
  - AvgAnlsdCmtdSuppBdgt: removed (blank) whenever ActvPrtcpnt is exactly
    "<11"; NOT removed for other "<N" cases (empirically confirmed - not
    assumed).

Only MARGINAL slices are emitted (all dimensions but one held at "ALL"),
per the mission's explicit warning against fabricating a fake cross-product
hierarchy from independent orthogonal dimensions. Geography is the one
genuine two-level nesting the source supports (every service district
maps to exactly one state, confirmed empirically, except the shared
"Other" catch-all bucket which is scoped per-state here to avoid
conflating unrelated states' "Other" cells).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
IN_CSV = (
    REPO_ROOT
    / "data/raw/federal/ndis_participant_numbers_and_plan_budgets/snapshots"
    / "20260824T035116Z/files/participant-plan-budgets-june-2026.csv"
)
OUT_COUNT_CSV = REPO_ROOT / "data/staging/breakdowns/ndis_participant_count.csv"
OUT_BUDGET_CSV = REPO_ROOT / "data/staging/breakdowns/ndis_average_committed_plan_budget.csv"

FY = "2025-26"  # 30 June 2026 = end of FY2025-26
REPORT_DATE = "30JUN2026"
# Deliberately distinct root node names for the two measures (not just two
# source_keys) - build_related_subtree() (breakdown_graph.py) keys its
# result dict by child node NAME when multiple related_breakdown edges
# attach to the same canonical parent without an edge_set_ids filter
# (dashboard_item_children's call site), so two measures sharing one root
# name silently overwrite each other in that combined view. Found live
# while verifying this exact attachment; see federal-deep-data-mission-*
# .md, Loop 8 (a disclosed, unfixed defect from Loop 7 - working around it
# here rather than touching that fragile shared function).
COUNT_ROOT_NODE = "NDIA Participant Statistics"
BUDGET_ROOT_NODE = "NDIA Average Committed Plan Budget"
LANDING_URL = "https://dataresearch.ndis.gov.au/datasets/participant-datasets"
RESOURCE_URL = "https://dataresearch.ndis.gov.au/media/4573/download"

STATE_NAMES = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "SA": "South Australia",
    "WA": "Western Australia",
    "TAS": "Tasmania",
    "NT": "Northern Territory",
    "ACT": "Australian Capital Territory",
    "OT": "Other territories",
    "State_Missing": "State not recorded",
}


def _clean(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip())


def _parse_count(raw: str) -> tuple[float | None, bool]:
    """Returns (value, is_upper_bound). value is None only for malformed input."""
    raw = (raw or "").strip()
    if not raw:
        return None, False
    if raw.startswith("<"):
        try:
            return float(raw[1:].replace(",", "")), True
        except ValueError:
            return None, False
    try:
        return float(raw.replace(",", "")), False
    except ValueError:
        return None, False


def _parse_budget(raw: str) -> float | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _is_marginal(row: dict, *, except_dims: set[str]) -> bool:
    """True if every dimension NOT in except_dims is held at 'ALL'."""
    dims = {
        "state": row["StateCd"],
        "district": row["SrvcDstrctNm"],
        "disability": row["DsbltyGrpNm"],
        "age": row["AgeBnd"],
        "support": row["SuppClass"],
    }
    for dim, value in dims.items():
        if dim in except_dims:
            continue
        if value != "ALL":
            return False
    return True


def extract() -> list[dict]:
    if not IN_CSV.is_file():
        return []

    rows: list[dict] = []

    def emit(category_suffix: str, count_raw: str, budget_raw: str, locator_suffix: str) -> None:
        count, is_bound = _parse_count(count_raw)
        budget = _parse_budget(budget_raw)
        if count is None or count <= 0:
            return
        rows.append(
            {
                "fy": FY,
                "category_suffix": category_suffix,
                "participant_count": f"{count:.0f}",
                "count_is_upper_bound": "1" if is_bound else "0",
                "avg_committed_plan_budget": f"{budget:.2f}" if budget is not None else "",
                "estimate_status": "actual",
                "locator": f"ndis:participant-plan-budgets:jun-2026:{locator_suffix}",
                "landing_url": LANDING_URL,
                "resource_url": RESOURCE_URL,
            }
        )

    with IN_CSV.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row["RprtDt"] != REPORT_DATE:
                continue

            state = row["StateCd"]
            district = row["SrvcDstrctNm"]
            disability = row["DsbltyGrpNm"]
            age = row["AgeBnd"]
            support = row["SuppClass"]

            # Grand national total: all five dimensions ALL.
            if _is_marginal(row, except_dims=set()):
                emit("", row["ActvPrtcpnt"], row["AvgAnlsdCmtdSuppBdgt"], "total")
                continue

            # Geography: state alone (district=ALL, others=ALL).
            if state != "ALL" and _is_marginal(row, except_dims={"state"}):
                state_label = STATE_NAMES.get(state, state)
                emit(
                    f"Participants by geography / {_clean(state_label)}",
                    row["ActvPrtcpnt"],
                    row["AvgAnlsdCmtdSuppBdgt"],
                    f"geo:{state}",
                )
                continue

            # Geography: state + district (others=ALL) - genuine two-level nesting.
            if (
                state != "ALL"
                and district != "ALL"
                and _is_marginal(row, except_dims={"state", "district"})
            ):
                state_label = STATE_NAMES.get(state, state)
                district_label = (
                    f"{state_label} - Other" if district == "Other" else district
                )
                emit(
                    f"Participants by geography / {_clean(state_label)} / "
                    f"{_clean(district_label)}",
                    row["ActvPrtcpnt"],
                    row["AvgAnlsdCmtdSuppBdgt"],
                    f"geo:{state}:{district}",
                )
                continue

            # Disability group alone.
            if disability != "ALL" and _is_marginal(row, except_dims={"disability"}):
                label = "Missing (reported)" if disability == "DsbltyGrp_Missing" else disability
                emit(
                    f"Participants by disability group / {_clean(label)}",
                    row["ActvPrtcpnt"],
                    row["AvgAnlsdCmtdSuppBdgt"],
                    f"disability:{disability}",
                )
                continue

            # Age band alone.
            if age != "ALL" and _is_marginal(row, except_dims={"age"}):
                emit(
                    f"Participants by age band / {_clean(age)}",
                    row["ActvPrtcpnt"],
                    row["AvgAnlsdCmtdSuppBdgt"],
                    f"age:{age}",
                )
                continue

            # Support class alone.
            if support != "ALL" and _is_marginal(row, except_dims={"support"}):
                emit(
                    f"Participants by support class / {_clean(support)}",
                    row["ActvPrtcpnt"],
                    row["AvgAnlsdCmtdSuppBdgt"],
                    f"support:{support}",
                )
                continue

            # Every other pattern is a joint cross-tabulation cell (e.g.
            # state x disability, or all five specific) - deliberately not
            # emitted here. See the module docstring: exposing these would
            # mean fabricating an arbitrary nesting order across orthogonal
            # dimensions the source does not itself impose.

    # Intermediate folder nodes (e.g. "Participants by age band", "...
    # geography / New South Wales") need their own fact for the same_group
    # traversal to reach past them (build_same_group_subtree() requires
    # every node it walks to have one - see breakdown_graph.py). Their
    # value is deliberately the GRAND TOTAL's own count/average, never a
    # recomputed sum of their children: empirically, summing children only
    # reconstructs the true total for genuinely mutually-exclusive,
    # exhaustive dimensions (age band and disability group sum to exactly
    # 782,013; state sums to exactly 782,013) but NOT for others -
    # support class sums to 1,611,496 (participants hold multiple support
    # classes at once, so classes are not mutually exclusive) and district
    # sums to only 762,917 (small-cell suppression drops some districts'
    # exact contribution). Rather than sum some dimensions and not others
    # (an inconsistent, easy-to-misread rule), every folder simply carries
    # the same total population/average the root already reports - it is a
    # pure navigation label, not a new figure.
    grand_total = next((r for r in rows if r["category_suffix"] == ""), None)
    if grand_total is not None:
        existing_suffixes = {r["category_suffix"] for r in rows}
        folder_suffixes: set[str] = set()
        for r in rows:
            suffix = r["category_suffix"]
            if not suffix:
                continue
            parts = suffix.split(" / ")
            for depth in range(1, len(parts)):
                folder_suffixes.add(" / ".join(parts[:depth]))
        folder_suffixes -= existing_suffixes
        for suffix in sorted(folder_suffixes):
            rows.append(
                {
                    "fy": FY,
                    "category_suffix": suffix,
                    "participant_count": grand_total["participant_count"],
                    "count_is_upper_bound": grand_total["count_is_upper_bound"],
                    "avg_committed_plan_budget": grand_total["avg_committed_plan_budget"],
                    "estimate_status": "actual",
                    "locator": "ndis:participant-plan-budgets:jun-2026:folder-aggregate",
                    "landing_url": LANDING_URL,
                    "resource_url": RESOURCE_URL,
                }
            )

    def _with_category(source_rows: list[dict], root: str) -> list[dict]:
        out = []
        for r in source_rows:
            suffix = r["category_suffix"]
            category = f"{root} / {suffix}" if suffix else root
            out.append({**r, "category": category})
        return out

    OUT_COUNT_CSV.parent.mkdir(parents=True, exist_ok=True)
    count_rows = _with_category(rows, COUNT_ROOT_NODE)
    count_fields = [
        "fy",
        "category",
        "participant_count",
        "count_is_upper_bound",
        "estimate_status",
        "locator",
        "landing_url",
        "resource_url",
    ]
    with OUT_COUNT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=count_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(count_rows)

    # Budget CSV excludes rows where the source withheld the average (blank
    # avg_committed_plan_budget) - never write a blank amount_aud for a
    # mapping that requires one; the count measure above still includes
    # these rows (their participant count is a valid "<11" upper bound).
    budget_rows = _with_category(
        [r for r in rows if r["avg_committed_plan_budget"] != ""], BUDGET_ROOT_NODE
    )
    budget_fields = [
        "fy",
        "category",
        "avg_committed_plan_budget",
        "estimate_status",
        "locator",
        "landing_url",
        "resource_url",
    ]
    with OUT_BUDGET_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=budget_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(budget_rows)

    print(
        {
            "wrote": [str(OUT_COUNT_CSV), str(OUT_BUDGET_CSV)],
            "count_rows": len(count_rows),
            "budget_rows": len(budget_rows),
            "suppressed_no_budget": len(count_rows) - len(budget_rows),
        }
    )
    return count_rows


def main() -> int:
    extract()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
