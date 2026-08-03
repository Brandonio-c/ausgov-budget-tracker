#!/usr/bin/env python3
"""Task 8 follow-up (semantic-defect milestone): apply the Task 5 label-
quality classifier to federal_pbs_programs_s6_bridge, a second, older
PBS-derived dataset discovered during production audit re-verification.

federal_pbs_programs_all was reloaded via scripts/ingest/
reload_pbs_programs_all.py (a full extract -> validate -> classify -> load
pipeline, using the mapping's replace_on_reload flag). This bridge dataset
predates that crosswalk, has no replace_on_reload flag, and is loaded by a
different extractor (scripts/ingest/extractors/pbs_programs_s6_bridge.py)
directly into same_group edges under Statement 6 budget-mode function
paths - discovered still leaking the same kind of malformed/concatenated
rows (e.g. "(Asialink Business) 3,700 3,774 - - - Powering Australia
Industry Growth Centre 3,500 ...") into both budget mode and, via the
related-navigation cascade, local-government actuals paths.

Rather than modify that dataset's ingest pipeline (out of proportion to
the remaining scope of this milestone), this performs a direct, one-time,
classifier-driven cleanup of the facts already in data/facts.db: any fact
whose node name's final path segment (the label actually shown to users -
these node names are "Function / Subfunction / Label", matching the
display_name() rsplit-on-last-" / " behaviour the real API uses) is not
positively classified as program/outcome/component is moved to
facts_pending_attribution (preserving it, not discarding it) and removed
from facts. Uses the same before/after node-staleness logic as
cleanup_stale_pbs_nodes.py (imported, not duplicated) to safely remove
now-orphaned nodes/edges afterward. Never touches any other source.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from cleanup_stale_pbs_nodes import cleanup, fact_bearing_pbs_node_ids  # noqa: E402
from pbs_label_classifier import classify_label  # noqa: E402

DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
SOURCE_KEY = "federal_pbs_programs_s6_bridge"


def _label_for_classification(node_name: str) -> str:
    """Match display_name()'s rsplit-on-last-" / " behaviour - the actual
    text shown to a user in the UI - not just the first path segment."""
    if " / " in node_name:
        return node_name.rsplit(" / ", 1)[-1]
    return node_name


def cleanup_bridge_labels(conn: sqlite3.Connection) -> dict:
    conn.execute("PRAGMA foreign_keys = ON")
    before_ids = fact_bearing_pbs_node_ids(conn, SOURCE_KEY)

    rows = conn.execute(
        """
        SELECT f.id, n.name, f.fact_key, f.financial_year, f.period_granularity,
               f.measure_type, f.accounting_basis, f.estimate_status, f.amount_aud,
               f.quantity, f.unit, f.currency, f.source_document_id,
               f.source_retrieval_id, f.source_locator_json, f.retrieved_at
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        WHERE d.source_key = ?
        """,
        (SOURCE_KEY,),
    ).fetchall()

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    class_counts: dict[str, int] = {}
    quarantined = 0
    for row in rows:
        (
            fact_id, node_name, fact_key, fy, granularity, measure_type,
            accounting_basis, estimate_status, amount, quantity, unit,
            currency, source_document_id, retrieval_id, locator_json, retrieved_at,
        ) = row
        label = _label_for_classification(node_name)
        result = classify_label(label)
        class_counts[result.classification] = class_counts.get(result.classification, 0) + 1
        if result.publishable:
            continue
        conn.execute(
            """
            INSERT INTO facts_pending_attribution (
                fact_key, financial_year, period_granularity, measure_type,
                accounting_basis, estimate_status, amount_aud, quantity, unit,
                currency, source_document_id, source_retrieval_id,
                source_locator_json, retrieved_at, is_publishable,
                quarantine_reason, quarantined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(fact_key) DO UPDATE SET
                quarantine_reason = excluded.quarantine_reason,
                quarantined_at = excluded.quarantined_at
            """,
            (
                fact_key, fy, granularity, measure_type, accounting_basis,
                estimate_status, amount, quantity, unit, currency,
                source_document_id, retrieval_id, locator_json, retrieved_at,
                f"Label quality: classified as '{result.classification}' "
                f"({result.rejection_reason}) - not a program/outcome/component",
                now,
            ),
        )
        conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        quarantined += 1

    cleanup_result = cleanup(conn, before_ids, SOURCE_KEY)
    return {
        "source_key": SOURCE_KEY,
        "input_facts": len(rows),
        "quarantined": quarantined,
        "published": len(rows) - quarantined,
        "label_quality_class_counts": class_counts,
        **cleanup_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    conn = sqlite3.connect(str(args.db))
    try:
        result = cleanup_bridge_labels(conn)
        conn.commit()
    finally:
        conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
