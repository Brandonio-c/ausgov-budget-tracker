#!/usr/bin/env python3
"""Reconcile borrowing-authority leaf sums to published control totals (report only)."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FACTS_DB = REPO_ROOT / "data" / "facts.db"
REPORTS = REPO_ROOT / "ops" / "reports"

CONTROL_TOTALS = {
    "nsw_tcorp_bonds_on_issue": {
        "authority": "TCorp",
        "as_at": "2026-07-17",
        "valuation_basis": "face_value",
        "control_aud": 213_752_000_000.0,
        "note": "Weekly bonds outstanding total",
    },
    "vic_tcv_amount_on_issue": {
        "authority": "TCV",
        "as_at": "2026-07-17",
        "valuation_basis": "face_value",
        "control_aud": 214_333_000_000.0,
        "note": "Amount on issue CSV total",
    },
    "qld_qtc_aud_bond_outstandings": {
        "authority": "QTC",
        "as_at": "2026-07-17",
        "valuation_basis": "face_value",
        "control_aud": 175_929_000_000.0,
        "note": "Weekly AUD bond outstandings",
    },
    "sa_safa_weekly_funding_update": {
        "authority": "SAFA",
        "as_at": "2026-07-17",
        "valuation_basis": "face_value",
        "control_aud": 45_629_000_000.0,
        "note": "Weekly funding update",
    },
    "wa_watc_funding_sources": {
        "authority": "WATC",
        "as_at": "2026-07-24",
        "valuation_basis": "face_value",
        "control_aud": 50_440_000_000.0,
        "note": "Funding sources 41,330+9,110",
    },
    "nt_nttc_borrowing_strategy": {
        "authority": "NTTC",
        "as_at": "2024-06-30",
        "valuation_basis": "face_value",
        "control_aud": 13_900_000_000.0,
        "note": "Borrowing strategy ISIN schedule",
    },
    "tas_tascorp_annual_report_2024_25": {
        "authority": "TASCORP",
        "as_at": "2025-06-30",
        "valuation_basis": "fair_value",
        "control_aud": 15_038_000_000.0,
        "note": "Annual report instrument-type fair values",
    },
}


def _leaf_sum(conn: sqlite3.Connection, source_id: str) -> tuple[float, int, str | None]:
    rows = conn.execute(
        """
        SELECT f.amount_aud, f.source_locator_json, n.name, f.amount_granularity
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        LEFT JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        LEFT JOIN nodes n ON n.id = fn.node_id
        WHERE d.source_key = ?
          AND f.measure_type IN ('borrowing_authority_debt_outstanding', 'gross_debt_face_value')
        """,
        (source_id,),
    ).fetchall()
    total = 0.0
    n_leaf = 0
    as_at = None
    for amount, locator_json, name, gran in rows:
        loc = locator_json or ""
        name = name or ""
        gran = gran or ""
        if "roll_up:sum_instruments" in loc:
            continue
        # Prefer rows with explicit granularity (post schema-005 semantics).
        if gran == "instrument_type_aggregate" and name.count("/") < 3:
            # Parent-type aggregate with children present — skip when deeper leaves exist.
            continue
        is_leaf = (
            gran == "individual_security"
            or "amount_granularity:individual_security" in loc
            or (gran == "instrument_type_aggregate" and name.count("/") >= 3)
            or (not gran and name.count("/") >= 2 and "roll_up:" not in loc)
        )
        if not is_leaf:
            continue
        total += float(amount)
        n_leaf += 1
        m = re.search(r"as_at_date:(\d{4}-\d{2}-\d{2})", loc)
        if m:
            as_at = m.group(1)
    return total, n_leaf, as_at


def main() -> int:
    conn = sqlite3.connect(str(FACTS_DB))
    results = []
    for source_id, meta in CONTROL_TOTALS.items():
        leaf_sum, n_leaf, as_at = _leaf_sum(conn, source_id)
        control = meta["control_aud"]
        diff = abs(leaf_sum - control)
        pct = (diff / control * 100.0) if control else 0.0
        if pct <= 0.5:
            status = "pass"
        elif pct <= 2.0:
            status = "warning"
        else:
            status = "failure"
        results.append(
            {
                "source_id": source_id,
                "authority": meta["authority"],
                "valuation_basis": meta["valuation_basis"],
                "observation_date": as_at or meta["as_at"],
                "published_control_aud": control,
                "sum_of_parsed_leaves_aud": leaf_sum,
                "absolute_difference_aud": diff,
                "percentage_difference": round(pct, 4),
                "leaf_count": n_leaf,
                "status": status,
                "note": meta["note"],
            }
        )
    conn.close()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"debt-reconciliation-{stamp}.json"
    md = REPORTS / f"debt-reconciliation-{stamp}.md"
    json_path.write_text(json.dumps({"generated_at": stamp, "results": results}, indent=2), encoding="utf-8")
    lines = [
        f"# Debt reconciliation ({stamp})",
        "",
        "Thresholds: pass ≤0.5%, warning ≤2%, failure >2%.",
        "",
        "| authority | as_at | basis | control $m | leaves $m | Δ% | status | leaves |",
        "|---|---|---|---:|---:|---:|---|---:|",
    ]
    for r in results:
        lines.append(
            f"| {r['authority']} | {r['observation_date']} | {r['valuation_basis']} | "
            f"{r['published_control_aud']/1e6:,.1f} | {r['sum_of_parsed_leaves_aud']/1e6:,.1f} | "
            f"{r['percentage_difference']:.3f} | {r['status']} | {r['leaf_count']} |"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(md.relative_to(REPO_ROOT)), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
