#!/usr/bin/env python3
"""Preview or apply canonical dataset IDs from the validated lineage registry."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from canonical_lineage import (
    DEFAULT_LINEAGE,
    audit_assignments,
    backfill_assignments,
    load_canonical_lineage,
)
from schema_migrate import migrate

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"


def run(db_path: Path, lineage_path: Path, apply: bool) -> dict:
    lineage = load_canonical_lineage(str(lineage_path))
    if apply:
        migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        if not apply:
            return {"applied": False, "audit": audit_assignments(conn, lineage)}
        conn.execute("BEGIN IMMEDIATE")
        result = backfill_assignments(conn, lineage)
        conn.commit()
        return {"applied": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--lineage", type=Path, default=DEFAULT_LINEAGE)
    parser.add_argument(
        "--apply", action="store_true", help="Write assignments; default is preview only"
    )
    args = parser.parse_args(argv)
    print(json.dumps(run(args.db, args.lineage, args.apply), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
