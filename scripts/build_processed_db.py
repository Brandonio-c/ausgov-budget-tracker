"""Build data/processed/spending.db from whatever raw sources were fetched.

For every source in sources.yaml with a successful raw file present, runs its
configured parser and writes normalized rows into a single SQLite table.
Sources that failed to fetch are reported, not silently skipped.
"""
import importlib
import json
import sqlite3
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from unified_registry import phase1_sources

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = Path(__file__).resolve().parent / "sources.yaml.retired"  # retired M11
RAW_DIR = BASE_DIR / "data" / "raw"
DB_FILE = BASE_DIR / "data" / "processed" / "spending.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS spending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    financial_year TEXT NOT NULL,
    level_of_government TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    department TEXT,
    amount_aud REAL NOT NULL,
    source_document_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    source_context_json TEXT NOT NULL
);
"""


def main() -> int:
    sources = phase1_sources()

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DROP TABLE IF EXISTS spending")
    conn.execute(SCHEMA)

    coverage = []
    for source in sources:
        source_dir = RAW_DIR / source["level"] / source["id"]
        meta_file = source_dir / f"{source['id']}.meta.json"
        raw_file = source_dir / source["raw_filename"]

        if not meta_file.exists():
            coverage.append((source["id"], "not_fetched", 0))
            continue

        meta = json.loads(meta_file.read_text())
        if meta.get("status") != "ok" or not raw_file.exists():
            coverage.append((source["id"], meta.get("status", "unknown"), 0))
            continue

        parser = importlib.import_module(f"parsers.{source['parser']}")
        rows = parser.parse(raw_file, meta)
        conn.executemany(
            """INSERT INTO spending
               (financial_year, level_of_government, jurisdiction, category, subcategory,
                department, amount_aud, source_document_name, source_url, retrieved_at,
                source_context_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    r.financial_year, r.level_of_government, r.jurisdiction, r.category,
                    r.subcategory, r.department, r.amount_aud, r.source_document_name,
                    r.source_url, r.retrieved_at,
                    json.dumps(r.source_context, ensure_ascii=False, separators=(",", ":")),
                )
                for r in rows
            ],
        )
        coverage.append((source["id"], "ok", len(rows)))

    conn.commit()

    print(f"{'source':<30}{'status':<15}{'rows'}")
    for source_id, status, row_count in coverage:
        print(f"{source_id:<30}{status:<15}{row_count}")

    total = conn.execute("SELECT COUNT(*), SUM(amount_aud) FROM spending").fetchone()
    print(f"\nTotal rows: {total[0]:,}  |  Total amount_aud: ${total[1]:,.2f}" if total[0] else "\nNo rows written.")
    conn.close()
    return 0 if any(status == "ok" for _, status, _ in coverage) else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
