#!/usr/bin/env python3
"""Load QLD Government On-Time Payment (small business) quarterly compliance
data into data/facts.db (item 7.5).

Reads scripts/ingest/extractors/qld_on_time_payments.py's extraction,
classifies each row against config/measure-semantics/qld_on_time_payments.yaml,
and publishes one of 8 dedicated qld_otp_* measure types - none shares a
compatibility_group with any expenditure/procurement measure. Count/day/
percentage measures are written to facts.quantity (never amount_aud);
only the two genuine payment-value measures use amount_aud.

The "node" for each fact is the agency, identified by the literal filename-
derived code from its source file (e.g. "dpc") - never expanded to a
guessed department name (see the extractor's module docstring for why).

Usage:
    python3 scripts/ingest/load_qld_on_time_payments.py --dry-run   (default)
    python3 scripts/ingest/load_qld_on_time_payments.py --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import yaml  # noqa: E402
from qld_on_time_payments import extract_all  # noqa: E402
from schema_migrate import migrate  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "qld_on_time_payments.yaml"
QUARANTINE_PATH = REPO_ROOT / "data" / "staging" / "quarantine" / "qld_on_time_payments_load_quarantine.jsonl"
SOURCE_ID = "qld_on_time_payment_reports"

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Queensland Government (multiple agencies)",
    "title": "QLD Government On-Time Payment (small business) quarterly compliance reports",
    "jurisdiction": "QLD",
    "government_level": "state",
    "source_family": "qld_on_time_payments",
}

# Quarter -> (start_month, start_year_offset, end_month, end_day, end_year_offset),
# offsets relative to the financial year's first calendar year (e.g. FY2020-21 -> 2020).
_QUARTER_BOUNDS = {
    1: ((7, 1, 0), (9, 30, 0)),
    2: ((10, 1, 0), (12, 31, 0)),
    3: ((1, 1, 1), (3, 31, 1)),
    4: ((4, 1, 1), (6, 30, 1)),
}


def _measure_label(measure: str) -> str:
    return {
        "eligible_claims": "eligible claims for penalty interest smallbus",
        "penalty_interest_paid": "penalty interest paid smallbus",
        "total_eligible_invoices": "total eligible and undisputed invs smallbus",
        "invoices_paid_late": "eligible and undisputed invs paid late smallbus",
        "value_paid_late": "value eligible and undisputed inv paid late smallbus",
        "mean_days_paid_late": "mean days paid late eligible and undisputed inv smallbus",
        "pct_late_smallbus": "percent of all late payments smallbus",
        "pct_late_others": "percent of all late payments others",
    }[measure]


_MEASURE_TYPE_BY_KEY = {
    "eligible_claims": "qld_otp_eligible_claims",
    "penalty_interest_paid": "qld_otp_penalty_interest_paid",
    "total_eligible_invoices": "qld_otp_total_eligible_invoices",
    "invoices_paid_late": "qld_otp_invoices_paid_late",
    "value_paid_late": "qld_otp_value_paid_late",
    "mean_days_paid_late": "qld_otp_mean_days_paid_late",
    "pct_late_smallbus": "qld_otp_pct_late_smallbus",
    "pct_late_others": "qld_otp_pct_late_others",
}

# Measures whose value is a genuine dollar figure - everything else (counts,
# days, percentages) is stored in facts.quantity, never amount_aud.
_AMOUNT_AUD_MEASURES = {"penalty_interest_paid", "value_paid_late"}


def quarter_period(fy: str, quarter: int) -> tuple[str, str]:
    y1 = int(fy.split("-")[0])
    (start_m, start_d, start_off), (end_m, end_d, end_off) = _QUARTER_BOUNDS[quarter]
    start = f"{y1 + start_off:04d}-{start_m:02d}-{start_d:02d}"
    end = f"{y1 + end_off:04d}-{end_m:02d}-{end_d:02d}"
    return start, end


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def build_fact_key(*, financial_year: str, quarter: int, agency_code: str, measure_type: str, estimate_status: str) -> str:
    return f"{SOURCE_ID}|{financial_year}|Q{quarter}|{agency_code}|{measure_type}|{estimate_status}"


def classify_and_validate(row: dict, semantics: dict) -> tuple[dict | None, str]:
    measure_key = row["measure"]
    measure_type = _MEASURE_TYPE_BY_KEY.get(measure_key)
    if measure_type is None or measure_type not in semantics["measures"]:
        return None, "unrecognized_measure_key"

    spec = semantics["measures"][measure_type]
    try:
        period_start, period_end = quarter_period(row["fy"], row["quarter"])
    except (KeyError, ValueError):
        return None, "period_undeterminable"

    if not row.get("locator") or not row.get("cached_copy_path"):
        return None, "missing_source_cell"
    source_file = REPO_ROOT / row["cached_copy_path"]
    if not source_file.is_file():
        return None, "source_file_missing_on_disk"

    fact_key = build_fact_key(
        financial_year=row["fy"],
        quarter=row["quarter"],
        agency_code=row["agency_code"],
        measure_type=measure_type,
        estimate_status=spec["estimate_status"],
    )

    is_amount = measure_key in _AMOUNT_AUD_MEASURES
    return (
        {
            "fact_key": fact_key,
            "financial_year": row["fy"],
            "period_start": period_start,
            "period_end": period_end,
            "period_granularity": "quarter",
            "measure_type": measure_type,
            "accounting_basis": spec["accounting_basis"],
            "estimate_status": spec["estimate_status"],
            "amount_aud": row["value"] if is_amount else None,
            "quantity": None if is_amount else row["value"],
            "unit": spec["unit"],
            "agency_code": row["agency_code"],
            "locator": row["locator"],
            "cached_copy_path": row["cached_copy_path"],
        },
        "",
    )


def ensure_source_document(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM source_documents WHERE source_key = ?", (SOURCE_DOCUMENT_META["source_key"],)
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            SOURCE_DOCUMENT_META["source_key"],
            SOURCE_DOCUMENT_META["publisher"],
            SOURCE_DOCUMENT_META["title"],
            SOURCE_DOCUMENT_META["jurisdiction"],
            SOURCE_DOCUMENT_META["government_level"],
            SOURCE_DOCUMENT_META["source_family"],
        ),
    )
    return cur.lastrowid


def ensure_agency_node(conn: sqlite3.Connection, doc_id: int, agency_code: str) -> int:
    canonical_key = f"{SOURCE_ID}|agency|{agency_code}"
    row = conn.execute("SELECT id FROM nodes WHERE canonical_key = ?", (canonical_key,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES (?, 'category', ?, ?, ?, ?)
        """,
        (canonical_key, agency_code, SOURCE_DOCUMENT_META["jurisdiction"], SOURCE_DOCUMENT_META["government_level"], doc_id),
    )
    return cur.lastrowid


def run(conn: sqlite3.Connection, *, apply: bool, quarantine_path: Path = QUARANTINE_PATH) -> dict:
    semantics = load_semantics()
    extracted_rows, extractor_quarantine = extract_all()

    quarantine: list[dict] = [{"reason": q.get("reason", ""), **q} for q in extractor_quarantine]
    prepared: list[dict] = []
    for row in extracted_rows:
        fact, reason = classify_and_validate(row, semantics)
        if fact is None:
            quarantine.append({"reason": reason, "row": {k: v for k, v in row.items() if k != "locator"}})
        else:
            prepared.append(fact)

    to_insert: list[dict] = []
    superseded_conflicts: list[dict] = []
    for fact in prepared:
        existing = conn.execute(
            "SELECT id, amount_aud, quantity FROM facts WHERE fact_key = ?", (fact["fact_key"],)
        ).fetchone()
        if existing is None:
            to_insert.append(fact)
            continue
        existing_val = existing[1] if existing[1] is not None else existing[2]
        new_val = fact["amount_aud"] if fact["amount_aud"] is not None else fact["quantity"]
        if existing_val is not None and new_val is not None and abs(float(existing_val) - float(new_val)) < 0.01:
            continue  # already loaded, identical - idempotent no-op
        superseded_conflicts.append(
            {"reason": "value_conflict_with_existing_fact", "fact_key": fact["fact_key"], "existing": existing_val, "new": new_val}
        )

    result = {
        "source_id": SOURCE_ID,
        "rows_extracted": len(extracted_rows),
        "rows_quarantined_by_extractor": len(extractor_quarantine),
        "rows_validated_publishable": len(prepared),
        "rows_quarantined_by_loader": len(quarantine) - len(extractor_quarantine),
        "facts_already_present_idempotent_skip": len(prepared) - len(to_insert) - len(superseded_conflicts),
        "facts_to_insert": len(to_insert),
        "value_conflicts_quarantined": len(superseded_conflicts),
        "nodes_inserted": 0,
        "mode": "apply" if apply else "dry-run",
    }
    quarantine.extend(superseded_conflicts)

    if apply and to_insert:
        doc_id = ensure_source_document(conn)
        agency_codes = sorted({f["agency_code"] for f in to_insert})
        node_ids: dict[str, int] = {}
        nodes_before = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        for code in agency_codes:
            node_ids[code] = ensure_agency_node(conn, doc_id, code)
        nodes_after = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        result["nodes_inserted"] = nodes_after - nodes_before

        for fact in to_insert:
            locator_json = json.dumps({"locator": fact["locator"], "cached_copy_path": fact["cached_copy_path"]})
            cur = conn.execute(
                """
                INSERT INTO facts (
                    fact_key, financial_year, period_start, period_end, period_granularity,
                    measure_type, accounting_basis, estimate_status, amount_aud, quantity, unit, currency,
                    source_document_id, source_locator_json, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AUD', ?, ?, datetime('now'))
                """,
                (
                    fact["fact_key"], fact["financial_year"], fact["period_start"], fact["period_end"],
                    fact["period_granularity"], fact["measure_type"], fact["accounting_basis"],
                    fact["estimate_status"], fact["amount_aud"], fact["quantity"], fact["unit"],
                    doc_id, locator_json,
                ),
            )
            fact_id = cur.lastrowid
            conn.execute(
                "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
                (fact_id, node_ids[fact["agency_code"]]),
            )
        conn.commit()

    if quarantine:
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        with quarantine_path.open("w", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Default behavior; explicit no-op flag.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    migrate(args.db)
    conn = sqlite3.connect(str(args.db))
    result = run(conn, apply=args.apply)
    conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
