#!/usr/bin/env python3
"""Preview or quarantine published facts outside source-declared FY horizons."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from schema_migrate import migrate  # noqa: E402
from validate import FY_RE  # noqa: E402

DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
DEFAULT_MAPPINGS = REPO_ROOT / "config" / "mappings"


@dataclass(frozen=True)
class SourceHorizon:
    source_key: str
    minimum: str
    maximum: str
    mapping_path: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_horizons(mappings_dir: Path = DEFAULT_MAPPINGS) -> tuple[SourceHorizon, ...]:
    horizons: list[SourceHorizon] = []
    seen: dict[str, tuple[str, str]] = {}
    for path in sorted(mappings_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw = data.get("publication_horizon")
        if not raw:
            continue
        source_key = str(data.get("source_id") or "").strip()
        minimum = str(raw.get("min_financial_year") or "").strip()
        maximum = str(raw.get("max_financial_year") or "").strip()
        if (
            not source_key
            or not FY_RE.fullmatch(minimum)
            or not FY_RE.fullmatch(maximum)
            or minimum > maximum
        ):
            raise ValueError(f"Invalid publication_horizon in {path}")
        bounds = (minimum, maximum)
        if source_key in seen and seen[source_key] != bounds:
            raise ValueError(f"Conflicting publication horizons for {source_key}")
        seen[source_key] = bounds
        horizons.append(SourceHorizon(source_key, minimum, maximum, path))
    return tuple(horizons)


def audit(conn: sqlite3.Connection, horizons: tuple[SourceHorizon, ...]) -> dict[str, Any]:
    sources: dict[str, Any] = {}
    for horizon in horizons:
        rows = conn.execute(
            """
            SELECT f.financial_year, COUNT(*)
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = ?
              AND (f.financial_year < ? OR f.financial_year > ?)
            GROUP BY f.financial_year
            ORDER BY f.financial_year
            """,
            (horizon.source_key, horizon.minimum, horizon.maximum),
        ).fetchall()
        try:
            mapping_label = str(horizon.mapping_path.relative_to(REPO_ROOT))
        except ValueError:
            mapping_label = str(horizon.mapping_path)
        sources[horizon.source_key] = {
            "allowed": f"{horizon.minimum}..{horizon.maximum}",
            "mapping": mapping_label,
            "outlier_facts": sum(int(row[1]) for row in rows),
            "outlier_years": {str(row[0]): int(row[1]) for row in rows},
        }
    return {
        "declared_sources": len(horizons),
        "outlier_facts": sum(item["outlier_facts"] for item in sources.values()),
        "sources": sources,
    }


def quarantine(
    conn: sqlite3.Connection, horizons: tuple[SourceHorizon, ...]
) -> dict[str, Any]:
    conn.execute(
        "CREATE TEMP TABLE horizon_fact_ids (fact_id INTEGER PRIMARY KEY, reason TEXT NOT NULL)"
    )
    for horizon in horizons:
        reason_prefix = "source_horizon_outlier:"
        conn.execute(
            """
            INSERT INTO horizon_fact_ids (fact_id, reason)
            SELECT f.id,
                   ? || 'financial_year=' || f.financial_year || ';allowed=' || ?
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = ?
              AND (f.financial_year < ? OR f.financial_year > ?)
            """,
            (
                reason_prefix,
                f"{horizon.minimum}..{horizon.maximum}",
                horizon.source_key,
                horizon.minimum,
                horizon.maximum,
            ),
        )
    candidate_count = int(
        conn.execute("SELECT COUNT(*) FROM horizon_fact_ids").fetchone()[0]
    )
    conn.execute(
        """
        CREATE TEMP TABLE horizon_node_ids AS
        SELECT DISTINCT fn.node_id
        FROM fact_nodes fn JOIN horizon_fact_ids h ON h.fact_id = fn.fact_id
        """
    )
    stamp = _utc_now()
    conn.execute(
        """
        INSERT INTO facts_pending_attribution (
            fact_key, financial_year, period_start, period_end, period_granularity,
            measure_type, accounting_basis, estimate_status, amount_aud, quantity,
            unit, currency, is_consolidated, is_elimination,
            confidential_or_suppressed, source_document_id, source_retrieval_id,
            source_locator_json, source_record_hash, published_at, retrieved_at,
            notes, is_publishable, quarantine_reason, quarantined_at
        )
        SELECT
            f.fact_key, f.financial_year, f.period_start, f.period_end,
            f.period_granularity, f.measure_type, f.accounting_basis,
            f.estimate_status, f.amount_aud, f.quantity, f.unit, f.currency,
            f.is_consolidated, f.is_elimination, f.confidential_or_suppressed,
            f.source_document_id, f.source_retrieval_id, f.source_locator_json,
            f.source_record_hash, f.published_at, f.retrieved_at, f.notes, 0,
            h.reason, ?
        FROM facts f JOIN horizon_fact_ids h ON h.fact_id = f.id
        WHERE true
        ON CONFLICT(fact_key) DO UPDATE SET
            quarantine_reason = excluded.quarantine_reason,
            quarantined_at = excluded.quarantined_at,
            source_locator_json = excluded.source_locator_json,
            amount_aud = excluded.amount_aud,
            quantity = excluded.quantity
        """,
        (stamp,),
    )
    conn.execute("DELETE FROM facts WHERE id IN (SELECT fact_id FROM horizon_fact_ids)")
    deleted_facts = int(conn.execute("SELECT changes()").fetchone()[0])
    conn.execute(
        """
        DELETE FROM nodes
        WHERE id IN (SELECT node_id FROM horizon_node_ids)
          AND NOT EXISTS (SELECT 1 FROM fact_nodes fn WHERE fn.node_id = nodes.id)
          AND NOT EXISTS (
              SELECT 1 FROM breakdown_edges e
              WHERE e.parent_node_id = nodes.id OR e.child_node_id = nodes.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM node_edges e
              WHERE e.parent_node_id = nodes.id OR e.child_node_id = nodes.id
          )
        """
    )
    deleted_nodes = int(conn.execute("SELECT changes()").fetchone()[0])
    return {
        "candidate_facts": candidate_count,
        "quarantined_facts": deleted_facts,
        "deleted_orphan_nodes": deleted_nodes,
    }


def run(
    db_path: Path,
    mappings_dir: Path = DEFAULT_MAPPINGS,
    apply: bool = False,
) -> dict[str, Any]:
    horizons = load_horizons(mappings_dir)
    if apply:
        migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        before = audit(conn, horizons)
        if not apply:
            return {"applied": False, "audit": before}
        conn.execute("BEGIN IMMEDIATE")
        changes = quarantine(conn, horizons)
        after = audit(conn, horizons)
        conn.commit()
        return {"applied": True, "before": before, "changes": changes, "after": after}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--mappings-dir", type=Path, default=DEFAULT_MAPPINGS)
    parser.add_argument(
        "--apply", action="store_true", help="Move outliers to quarantine; default is preview"
    )
    args = parser.parse_args(argv)
    print(json.dumps(run(args.db, args.mappings_dir, args.apply), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
