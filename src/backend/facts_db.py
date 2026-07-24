import os
import sqlite3
from pathlib import Path

DEFAULT_FACTS_DB = Path(__file__).resolve().parent.parent.parent / "data" / "facts.db"
FACTS_DB_FILE = Path(os.environ.get("FACTS_DB_PATH", DEFAULT_FACTS_DB))


def get_facts_connection() -> sqlite3.Connection:
    if not FACTS_DB_FILE.exists():
        raise FileNotFoundError(
            f"{FACTS_DB_FILE} not found — run scripts/ingest/schema_migrate.py first"
        )
    conn = sqlite3.connect(f"file:{FACTS_DB_FILE}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
