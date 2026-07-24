#!/usr/bin/env python3
"""Summarise facts_pending_attribution."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"


def report(db_path: Path = DEFAULT_DB) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT fact_key, financial_year, measure_type, quarantine_reason, quarantined_at
        FROM facts_pending_attribution
        ORDER BY quarantined_at DESC, fact_key
        """
    ).fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    return {"count": len(items), "items": items}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = report(args.db)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"quarantined={data['count']}")
        for item in data["items"]:
            print(f"- {item['fact_key']}: {item['quarantine_reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
