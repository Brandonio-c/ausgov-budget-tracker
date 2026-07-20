import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RAW_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
RAW_DATA_DIR = Path(os.environ.get("SPENDING_RAW_DATA_PATH", DEFAULT_RAW_DATA_DIR))

CONTENT_TYPES = {
    ".csv": "text/csv; charset=utf-8",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@dataclass(frozen=True)
class SourceFile:
    path: Path
    content_type: str
    source_id: str


def resolve_source_file(level: str, source_url: str) -> SourceFile | None:
    """Resolve a DB row to a successful pipeline download without leaving data/raw.

    The pipeline sidecar is authoritative: it records the source id, public URL,
    successful fetch status, byte count, and raw filename together. Only known
    spreadsheet formats are exposed.
    """
    level_dir = (RAW_DATA_DIR / level).resolve()
    if not level_dir.is_dir() or RAW_DATA_DIR.resolve() not in level_dir.parents:
        return None

    for meta_path in level_dir.glob("*/*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue

        if (
            meta.get("status") != "ok"
            or meta.get("level") != level
            or meta.get("source_url") != source_url
            or not isinstance(meta.get("raw_file"), str)
        ):
            continue

        source_dir = meta_path.parent.resolve()
        raw_path = (source_dir / Path(meta["raw_file"]).name).resolve()
        if raw_path.parent != source_dir or level_dir not in raw_path.parents:
            continue

        content_type = CONTENT_TYPES.get(raw_path.suffix.lower())
        if not content_type or not raw_path.is_file():
            continue

        expected_bytes = meta.get("bytes")
        if isinstance(expected_bytes, int) and raw_path.stat().st_size != expected_bytes:
            continue

        return SourceFile(
            path=raw_path,
            content_type=content_type,
            source_id=str(meta.get("id", source_dir.name)),
        )

    return None
