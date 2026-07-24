#!/usr/bin/env python3
"""Idempotent schema migrate for data/facts.db (M0+).

Applies the hierarchical schema draft plus additive migrations tracked in
schema_migrations. Never touches data/processed/spending.db.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
DRAFT_SCHEMA = REPO_ROOT / "data" / "ausgov_budget_hierarchical_schema.sql"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY,
            migration_id TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL,
            checksum TEXT NOT NULL,
            notes TEXT
        )
        """
    )


def apply_sql(conn: sqlite3.Connection, sql: str) -> None:
    conn.executescript(sql)


def apply_migration(
    conn: sqlite3.Connection,
    migration_id: str,
    sql: str,
    notes: str = "",
) -> bool:
    """Apply one migration if not already recorded. Returns True if applied."""
    checksum = _sha256_text(sql)
    existing = conn.execute(
        "SELECT checksum FROM schema_migrations WHERE migration_id = ?",
        (migration_id,),
    ).fetchone()
    if existing:
        if existing["checksum"] != checksum:
            raise RuntimeError(
                f"Migration {migration_id} checksum mismatch: "
                f"stored={existing['checksum']} current={checksum}"
            )
        return False
    apply_sql(conn, sql)
    conn.execute(
        """
        INSERT INTO schema_migrations (migration_id, applied_at, checksum, notes)
        VALUES (?, ?, ?, ?)
        """,
        (migration_id, _utc_now(), checksum, notes),
    )
    return True


def load_draft_sql() -> str:
    if not DRAFT_SCHEMA.is_file():
        raise FileNotFoundError(f"Draft schema missing: {DRAFT_SCHEMA}")
    return DRAFT_SCHEMA.read_text(encoding="utf-8")


def m0_delta_sql() -> str:
    """Canonical additive M0 deltas (checksum-stable)."""
    return """
-- M0-001: measure definitions for payment timing / monthly / GFS actuals
INSERT OR IGNORE INTO measure_definitions
    (measure_type, label, description, additive_across_time, additive_across_nodes,
     default_accounting_basis, compatibility_group)
VALUES
    ('payment_timing_disclosure', 'Payment timing disclosure',
     'On-time / late payment aggregate disclosure; not comparable to expense totals.',
     1, 1, 'cash', 'cash_outflow'),
    ('monthly_actuals', 'Monthly actuals',
     'Monthly financial statement actuals (cash or accrual as declared).',
     1, 1, 'cash', 'actual_expense'),
    ('gfs_expense', 'GFS expense',
     'Government Finance Statistics expense (ABS / state GFS).',
     1, 1, 'gfs', 'actual_expense');

-- M0-002: native_unit on source_documents (applied conditionally in migrate())
-- ALTER TABLE source_documents ADD COLUMN native_unit TEXT;

-- M0-003: quarantine table for incomplete attribution (Gate 6)
CREATE TABLE IF NOT EXISTS facts_pending_attribution (
    id INTEGER PRIMARY KEY,
    fact_key TEXT NOT NULL UNIQUE,
    financial_year TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    period_granularity TEXT NOT NULL CHECK (
        period_granularity IN (
            'point_in_time', 'month', 'quarter', 'year_to_date',
            'financial_year', 'multi_year'
        )
    ),
    measure_type TEXT NOT NULL REFERENCES measure_definitions(measure_type),
    accounting_basis TEXT NOT NULL CHECK (
        accounting_basis IN (
            'cash', 'accrual', 'gfs', 'aasb', 'appropriation', 'commitment',
            'count', 'mixed', 'not_applicable'
        )
    ),
    estimate_status TEXT NOT NULL CHECK (
        estimate_status IN (
            'budget', 'forward_estimate', 'revised_estimate', 'estimated_actual',
            'actual', 'audited_actual', 'award', 'contract', 'invoice'
        )
    ),
    amount_aud NUMERIC,
    quantity NUMERIC,
    unit TEXT NOT NULL DEFAULT 'AUD',
    currency TEXT NOT NULL DEFAULT 'AUD',
    is_consolidated INTEGER NOT NULL DEFAULT 0 CHECK (is_consolidated IN (0, 1)),
    is_elimination INTEGER NOT NULL DEFAULT 0 CHECK (is_elimination IN (0, 1)),
    confidential_or_suppressed INTEGER NOT NULL DEFAULT 0
        CHECK (confidential_or_suppressed IN (0, 1)),
    source_document_id INTEGER REFERENCES source_documents(id),
    source_retrieval_id INTEGER REFERENCES source_retrievals(id),
    source_locator_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(source_locator_json)),
    source_record_hash TEXT,
    published_at TEXT,
    retrieved_at TEXT NOT NULL,
    notes TEXT,
    is_publishable INTEGER NOT NULL DEFAULT 0 CHECK (is_publishable IN (0, 1)),
    quarantine_reason TEXT NOT NULL,
    quarantined_at TEXT NOT NULL,
    CHECK (amount_aud IS NOT NULL OR quantity IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_facts_pending_fy_measure
    ON facts_pending_attribution(financial_year, measure_type, estimate_status);
"""


def ensure_native_unit_column(conn: sqlite3.Connection) -> None:
    cols = {
        r[1] for r in conn.execute("PRAGMA table_info(source_documents)").fetchall()
    }
    if "native_unit" not in cols:
        conn.execute("ALTER TABLE source_documents ADD COLUMN native_unit TEXT")


def discover_file_migrations() -> list[tuple[str, Path]]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [(p.stem, p) for p in files]


def migrate(db_path: Path = DEFAULT_DB) -> dict:
    conn = _connect(db_path)
    try:
        ensure_migration_table(conn)
        results: dict[str, str] = {}

        draft = load_draft_sql()
        applied = apply_migration(
            conn,
            "000_hierarchical_schema_draft",
            draft,
            notes="Base draft from data/ausgov_budget_hierarchical_schema.sql",
        )
        results["000_hierarchical_schema_draft"] = "applied" if applied else "noop"

        delta = m0_delta_sql()
        applied = apply_migration(
            conn,
            "001_m0_deltas",
            delta,
            notes=(
                "payment_timing_disclosure measures, native_unit, "
                "facts_pending_attribution"
            ),
        )
        results["001_m0_deltas"] = "applied" if applied else "noop"
        ensure_native_unit_column(conn)

        for mid, path in discover_file_migrations():
            sql = path.read_text(encoding="utf-8")
            applied = apply_migration(conn, mid, sql, notes=f"file:{path.name}")
            results[mid] = "applied" if applied else "noop"

        conn.commit()

        measures = {
            r[0]
            for r in conn.execute(
                "SELECT measure_type FROM measure_definitions"
            ).fetchall()
        }
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        return {
            "db_path": str(db_path),
            "migrations": results,
            "has_facts_pending_attribution": "facts_pending_attribution" in tables,
            "has_payment_timing_disclosure": "payment_timing_disclosure" in measures,
            "has_native_unit": "native_unit"
            in {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(source_documents)"
                ).fetchall()
            },
            "table_count": len(tables),
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate data/facts.db schema")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="Path to facts.db (default: data/facts.db)",
    )
    args = parser.parse_args(argv)
    summary = migrate(args.db)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
