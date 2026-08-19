#!/usr/bin/env python3
"""Load the pre-2019 Final Budget Outcome (FBO) Appendix A/B: Expenses
by Function and Sub-function table into data/facts.db (item 8.1, first
four sub-generations: FY2004-05 through FY2018-19, the confirmed-
tractable years - see fbo_appendix_a_function.py's own module docstring
for the 3 distinct column layouts, including FY2017-18/FY2018-19's
5-column layout where "Estimate at Outcome" sits in a different
position than every earlier year).

Reads scripts/ingest/extractors/fbo_appendix_a_function.py's extraction,
classifies every row against config/measure-semantics/fbo_appendix_a_function.yaml,
validates it, and publishes it under one of 20 dedicated fbo_appendix_a_*
measure types/compatibility_groups (see
scripts/ingest/migrations/026_fbo_appendix_a_function_measures.sql) -
none of which can ever share a compatibility_group with any annual
GFS/PBS/MFS compatibility_group fact (this is the FBO's own Appendix A
function series, a different source/table).

All 20 measures are flows (financial-year expenses); unlike the QLD
CFFR loader this one has no stock-measure special-casing.

Revision policy: identical to every other loader in this program - a
fact_key is identity-complete (source family + financial year +
measure_type + accounting_basis + estimate_status + jurisdiction); if a
future re-acquisition ever produces a different amount for the same
identity, apply() below detects it explicitly and REFUSES to silently
overwrite, quarantining it pending an explicit revision-policy decision.

Usage:
    python3 scripts/ingest/load_fbo_appendix_a_function.py --dry-run   (default)
    python3 scripts/ingest/load_fbo_appendix_a_function.py --apply
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
from fbo_appendix_a_function import extract_all  # noqa: E402
from schema_migrate import migrate  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "fbo_appendix_a_function.yaml"
QUARANTINE_PATH = REPO_ROOT / "data" / "staging" / "quarantine" / "fbo_appendix_a_function_load_quarantine.jsonl"
SOURCE_ID = "fbo_appendix_a_function"

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Australian Government",
    "title": "Final Budget Outcome - Appendix A: Expenses by Function and Sub-function (pre-2019 editions)",
    "jurisdiction": "Commonwealth",
    "government_level": "federal",
    "source_family": "fbo_appendix_a_function",
}

_MEASURE_TYPE_BY_KEY = {
    "general_public_services": "fbo_appendix_a_general_public_services",
    "defence": "fbo_appendix_a_defence",
    "public_order_safety": "fbo_appendix_a_public_order_safety",
    "education": "fbo_appendix_a_education",
    "health": "fbo_appendix_a_health",
    "social_security_welfare": "fbo_appendix_a_social_security_welfare",
    "housing_community_amenities": "fbo_appendix_a_housing_community_amenities",
    "recreation_culture": "fbo_appendix_a_recreation_culture",
    "fuel_energy": "fbo_appendix_a_fuel_energy",
    "agriculture_forestry_fishing": "fbo_appendix_a_agriculture_forestry_fishing",
    "mining_manufacturing_construction": "fbo_appendix_a_mining_manufacturing_construction",
    "transport_communication": "fbo_appendix_a_transport_communication",
    "other_economic_affairs": "fbo_appendix_a_other_economic_affairs",
    "public_debt_interest": "fbo_appendix_a_public_debt_interest",
    "nominal_superannuation_interest": "fbo_appendix_a_nominal_superannuation_interest",
    "general_purpose_intergovt_transactions": "fbo_appendix_a_general_purpose_intergovt_transactions",
    "natural_disaster_relief": "fbo_appendix_a_natural_disaster_relief",
    "contingency_reserve": "fbo_appendix_a_contingency_reserve",
    "total_other_purposes": "fbo_appendix_a_total_other_purposes",
    "total_expenses": "fbo_appendix_a_total_expenses",
}


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def build_fact_key(*, financial_year: str, measure_type: str, accounting_basis: str, estimate_status: str, jurisdiction: str) -> str:
    return f"{SOURCE_ID}|{financial_year}|{measure_type}|{accounting_basis}|{estimate_status}|{jurisdiction}"


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

    y1 = row["fy"].split("-")[0]
    fy_start = f"{y1}-07-01"
    fy_end = f"{int(y1) + 1:04d}-06-30"

    fact_key = build_fact_key(
        financial_year=row["fy"], measure_type=measure_type,
        accounting_basis=accounting_basis, estimate_status=estimate_status, jurisdiction=jurisdiction,
    )

    return (
        {
            "fact_key": fact_key,
            "financial_year": row["fy"],
            "period_start": fy_start,
            "period_end": fy_end,
            "period_granularity": "financial_year",
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
            quarantine.append({"reason": reason, "fy": row["fy"], "measure_key": row["measure_key"]})
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
