import os
import sqlite3
from pathlib import Path

DEFAULT_DB_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "spending.db"
DB_FILE = Path(os.environ.get("SPENDING_DB_PATH", DEFAULT_DB_FILE))


def get_connection() -> sqlite3.Connection:
    if not DB_FILE.exists():
        raise FileNotFoundError(
            f"{DB_FILE} not found — run scripts/fetch_sources.py then scripts/build_processed_db.py first"
        )
    conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
