#!/usr/bin/env python3
"""Load Queensland Treasury's quarterly Consolidated Fund Financial
Report (CFFR) "Quarterly Statement" Year-to-Date data into data/facts.db
(item 7.4, quarterly slice).

Reads scripts/ingest/extractors/qld_cffr_quarterly_ytd.py's extraction
(26 real quarterly editions, FY2016-17 Q3..FY2025-26 Q3), classifies
every row against config/measure-semantics/qld_cffr_quarterly.yaml,
validates it, and publishes it under one of 9 dedicated
qld_cffr_quarterly_ytd_* measure types/compatibility_groups (see
scripts/ingest/migrations/027_qld_cffr_quarterly_ytd_measures.sql) -
none of which can ever share a compatibility_group with the already-
loaded annual qld_cffr_* measures (a different vintage) or any accrual
GFS/PBS/MFS measure (this source is explicitly Gross Cash Basis).

The stock measure qld_cffr_quarterly_ytd_opening_balance uses
period_start=None (a balance has no accumulation start), matching the
convention already established for the annual qld_cffr_opening_balance.
qld_cffr_quarterly_ytd_closing_balance also uses period_start=None
(a point-in-time stock at the quarter end date).

fact_key includes an explicit Q{quarter} component (mirroring the
convention already established for QLD on-time-payments,
load_qld_on_time_payments.py's own build_fact_key) - without it, the
same financial_year's 3 quarterly editions (Sep/Dec/Mar, all sharing
the same measure_type/accounting_basis/estimate_status/jurisdiction)
would collide under a single annual-style fact_key.

Revision policy: identical to every other loader in this program - a
fact_key is identity-complete; if a future re-acquisition ever produces
a different amount for the same identity, apply() below detects it
explicitly and REFUSES to silently overwrite, quarantining it pending an
explicit revision-policy decision.

Usage:
    python3 scripts/ingest/load_qld_cffr_quarterly_ytd.py --dry-run   (default)
    python3 scripts/ingest/load_qld_cffr_quarterly_ytd.py --apply
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
from qld_cffr_quarterly_ytd import extract_all  # noqa: E402
from schema_migrate import migrate  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "qld_cffr_quarterly.yaml"
QUARANTINE_PATH = REPO_ROOT / "data" / "staging" / "quarantine" / "qld_cffr_quarterly_ytd_load_quarantine.jsonl"
SOURCE_ID = "qld_cffr_quarterly_ytd"

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Queensland Treasury",
    "title": "Consolidated Fund Financial Report (quarterly Year-to-Date editions)",
    "jurisdiction": "QLD",
    "government_level": "state",
    "source_family": "qld_cffr_quarterly_ytd",
}

_STOCK_MEASURES = {"qld_cffr_quarterly_ytd_opening_balance", "qld_cffr_quarterly_ytd_closing_balance"}

_MEASURE_TYPE_BY_KEY = {
    "opening_balance": "qld_cffr_quarterly_ytd_opening_balance",
    "closing_balance": "qld_cffr_quarterly_ytd_closing_balance",
    "collections_from_departments": "qld_cffr_quarterly_ytd_collections_from_departments",
    "investment_interest": "qld_cffr_quarterly_ytd_investment_interest",
    "dividends_income_tax_equivalents": "qld_cffr_quarterly_ytd_dividends_income_tax_equivalents",
    "non_appropriated_equity_adjustments": "qld_cffr_quarterly_ytd_non_appropriated_equity_adjustments",
    "superannuation_lsl_qgif_alcs_contributions": "qld_cffr_quarterly_ytd_superannuation_lsl_qgif_alcs_contributions",
    "other_receipts": "qld_cffr_quarterly_ytd_other_receipts",
    "appropriations_provided_to_departments": "qld_cffr_quarterly_ytd_appropriations_provided_to_departments",
}

# quarter -> (month, day) of the quarter's own end date, within the FY's
# first calendar year (Q1/Q2) or second calendar year (Q3).
_QUARTER_END = {1: (9, 30), 2: (12, 31), 3: (3, 31)}


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def build_fact_key(
    *, financial_year: str, quarter: int, measure_type: str, accounting_basis: str, estimate_status: str, jurisdiction: str
) -> str:
    return f"{SOURCE_ID}|{financial_year}|Q{quarter}|{measure_type}|{accounting_basis}|{estimate_status}|{jurisdiction}"


def quarter_end_date(fy: str, quarter: int) -> str:
    y1 = int(fy.split("-")[0])
    month, day = _QUARTER_END[quarter]
    year = y1 if quarter in (1, 2) else y1 + 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def classify_and_validate(row: dict, semantics: dict) -> tuple[dict | None, str]:
    """Returns (prepared_fact_dict_or_None, quarantine_reason_or_empty)."""
    measure_type = _MEASURE_TYPE_BY_KEY.get(row["measure_key"])
    if measure_type is None or measure_type not in semantics["measures"]:
        return None, "unrecognized_measure_key"

    spec = semantics["measures"][measure_type]

    if not row.get("locator") or not row.get("cached_copy_path"):
        return None, "missing_source_cell"
    source_file = REPO_ROOT / row["cached_copy_path"]
    if not source_file.is_file():
        return None, "source_file_missing_on_disk"

    jurisdiction = SOURCE_DOCUMENT_META["jurisdiction"]
    accounting_basis = spec["accounting_basis"]
    estimate_status = spec["estimate_status"]
    is_stock = measure_type in _STOCK_MEASURES

    y1 = row["fy"].split("-")[0]
    fy_start = f"{y1}-07-01"
    q_end = quarter_end_date(row["fy"], row["quarter"])

    fact_key = build_fact_key(
        financial_year=row["fy"], quarter=row["quarter"], measure_type=measure_type,
        accounting_basis=accounting_basis, estimate_status=estimate_status, jurisdiction=jurisdiction,
    )

    return (
        {
            "fact_key": fact_key,
            "financial_year": row["fy"],
            "period_start": None if is_stock else fy_start,
            "period_end": fy_start if measure_type == "qld_cffr_quarterly_ytd_opening_balance" else q_end,
            "period_granularity": "year_to_date",
            "measure_type": measure_type,
            "accounting_basis": accounting_basis,
            "estimate_status": estimate_status,
            "amount_aud": row["amount"],
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
            SOURCE_DOCUMENT_META["source_key"], SOURCE_DOCUMENT_META["publisher"],
            SOURCE_DOCUMENT_META["title"], SOURCE_DOCUMENT_META["jurisdiction"],
            SOURCE_DOCUMENT_META["government_level"], SOURCE_DOCUMENT_META["source_family"],
        ),
    )
    return cur.lastrowid


def ensure_measure_node(conn: sqlite3.Connection, doc_id: int, measure_type: str, label: str) -> int:
    canonical_key = f"{SOURCE_ID}|node|{measure_type}"
    row = conn.execute("SELECT id FROM nodes WHERE canonical_key = ?", (canonical_key,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES (?, 'category', ?, ?, ?, ?)
        """,
        (canonical_key, label, SOURCE_DOCUMENT_META["jurisdiction"], SOURCE_DOCUMENT_META["government_level"], doc_id),
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
            quarantine.append({"reason": reason, "fy": row["fy"], "quarter": row["quarter"], "measure_key": row["measure_key"]})
        else:
            prepared.append(fact)

    to_insert: list[dict] = []
    superseded_conflicts: list[dict] = []
    for fact in prepared:
        existing = conn.execute(
            "SELECT id, amount_aud FROM facts WHERE fact_key = ?", (fact["fact_key"],)
        ).fetchone()
        if existing is None:
            to_insert.append(fact)
            continue
        existing_amount = existing[1]
        if existing_amount is not None and abs(float(existing_amount) - float(fact["amount_aud"])) < 0.01:
            continue  # already loaded, identical - idempotent no-op
        superseded_conflicts.append(
            {
                "reason": "amount_conflict_with_existing_fact",
                "fact_key": fact["fact_key"],
                "existing_amount_aud": existing_amount,
                "new_amount_aud": fact["amount_aud"],
            }
        )

    result = {
        "source_id": SOURCE_ID,
        "rows_extracted": len(extracted_rows),
        "rows_quarantined_by_extractor": len(extractor_quarantine),
        "rows_validated_publishable": len(prepared),
        "rows_quarantined_by_loader": len(quarantine) - len(extractor_quarantine),
        "facts_already_present_idempotent_skip": len(prepared) - len(to_insert) - len(superseded_conflicts),
        "facts_to_insert": len(to_insert),
        "revision_conflicts_quarantined": len(superseded_conflicts),
        "nodes_inserted": 0,
        "mode": "apply" if apply else "dry-run",
    }
    quarantine.extend(superseded_conflicts)

    if apply and to_insert:
        doc_id = ensure_source_document(conn)
        measure_labels = {m: semantics["measures"][m] for m in {f["measure_type"] for f in to_insert}}
        node_ids = {}
        nodes_before = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        for measure_type in measure_labels:
            row = conn.execute(
                "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
            ).fetchone()
            label = row[0] if row else measure_type
            node_ids[measure_type] = ensure_measure_node(conn, doc_id, measure_type, label)
        nodes_after = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        result["nodes_inserted"] = nodes_after - nodes_before

        for fact in to_insert:
            locator_json = json.dumps({"locator": fact["locator"], "cached_copy_path": fact["cached_copy_path"]})
            cur = conn.execute(
                """
                INSERT INTO facts (
                    fact_key, financial_year, period_start, period_end, period_granularity,
                    measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
                    source_document_id, source_locator_json, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'AUD', 'AUD', ?, ?, datetime('now'))
                """,
                (
                    fact["fact_key"], fact["financial_year"], fact["period_start"], fact["period_end"],
                    fact["period_granularity"], fact["measure_type"], fact["accounting_basis"],
                    fact["estimate_status"], fact["amount_aud"], doc_id, locator_json,
                ),
            )
            fact_id = cur.lastrowid
            conn.execute(
                "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
                (fact_id, node_ids[fact["measure_type"]]),
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
