"""Immutable snapshot storage, disk budgeting, deduplication and quarantine."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import Asset, RunContext, Source, ValidationResult


GIB = 1024**3
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(value: str, fallback: str = "download") -> str:
    name = Path(value.replace("\\", "/")).name.strip().strip(".")
    name = SAFE_NAME.sub("-", name).strip("-._")
    if not name:
        name = fallback
    return name[:240]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class DiskBudget:
    def __init__(self, root: Path, requested_cap: int | None = None):
        root.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(root)
        reserve = max(int(usage.free * 0.20), 10 * GIB)
        safe_available = max(0, usage.free - reserve)
        self.total = usage.total
        self.free_at_start = usage.free
        self.reserve = reserve
        self.cap = min(safe_available, requested_cap) if requested_cap else safe_available
        self.used = 0
        self._lock = threading.Lock()

    def claim(self, expected: int | None, maximum: int) -> bool:
        amount = min(expected, maximum) if expected is not None else maximum
        with self._lock:
            if amount > self.cap - self.used:
                return False
            self.used += amount
            return True

    def settle(self, claimed: int, actual: int) -> None:
        with self._lock:
            self.used = max(0, self.used - claimed + actual)

    def as_dict(self) -> dict[str, int]:
        return {
            "filesystem_bytes": self.total,
            "free_bytes_at_start": self.free_at_start,
            "reserved_bytes": self.reserve,
            "run_cap_bytes": self.cap,
            "accounted_bytes": self.used,
        }


class SnapshotStore:
    def __init__(self, context: RunContext):
        self.context = context
        self.raw_root = context.data_root / "raw"
        self.quarantine_root = context.data_root / "quarantine" / context.run_id
        self.state_root = context.data_root / ".procurement" / "checkpoints" / context.run_id

    def source_root(self, source: Source) -> Path:
        return self.raw_root / source.government_level / source.id

    def snapshot_root(self, source: Source) -> Path:
        return self.source_root(source) / "snapshots" / self.context.run_id

    def prepare_snapshot(self, source: Source) -> Path:
        root = self.snapshot_root(source)
        (root / "files").mkdir(parents=True, exist_ok=True)
        (root / "headers").mkdir(parents=True, exist_ok=True)
        return root

    def part_path(self, source: Source, asset: Asset) -> Path:
        name = safe_filename(asset.filename_hint or asset.asset_instance_id)
        path = self.snapshot_root(source) / "files" / f".{name}.part"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def existing_hash(self, source: Source, digest: str) -> str | None:
        index_path = self.source_root(source) / "hashes.json"
        if not index_path.exists():
            return None
        return json.loads(index_path.read_text(encoding="utf-8")).get(digest)

    def _record_hash(self, source: Source, digest: str, relative_path: str) -> None:
        index_path = self.source_root(source) / "hashes.json"
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
        index[digest] = relative_path
        write_json_atomic(index_path, index)

    def commit_validated(
        self,
        source: Source,
        asset: Asset,
        temporary: Path,
        filename: str,
    ) -> tuple[str, str, bool]:
        digest = sha256_file(temporary)
        existing = self.existing_hash(source, digest)
        if existing:
            temporary.unlink(missing_ok=True)
            return digest, existing, True
        destination = self.snapshot_root(source) / "files" / safe_filename(filename)
        if destination.exists():
            destination = destination.with_name(f"{destination.stem}-{digest[:10]}{destination.suffix}")
        os.replace(temporary, destination)
        relative = str(destination.relative_to(self.context.data_root))
        self._record_hash(source, digest, relative)
        return digest, relative, False

    def quarantine(
        self,
        source: Source,
        asset: Asset,
        temporary: Path,
        validation: ValidationResult,
    ) -> str:
        destination = self.quarantine_root / source.id / safe_filename(
            asset.filename_hint or asset.asset_instance_id
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination = destination.with_name(destination.name + ".duplicate")
        os.replace(temporary, destination)
        write_json_atomic(
            destination.with_suffix(destination.suffix + ".json"),
            {"source_id": source.id, "asset": asdict(asset), "validation": asdict(validation)},
        )
        return str(destination.relative_to(self.context.data_root))

    def write_discovery(self, source: Source, value: dict[str, Any]) -> None:
        write_json_atomic(self.snapshot_root(source) / "discovery.json", value)

    def write_acquisition(self, source: Source, value: dict[str, Any]) -> None:
        write_json_atomic(self.snapshot_root(source) / "acquisition.json", value)

    def write_headers(self, source: Source, asset_id: str, headers: dict[str, str]) -> None:
        name = safe_filename(asset_id) + ".json"
        write_json_atomic(self.snapshot_root(source) / "headers" / name, headers)

    def update_latest(
        self,
        source: Source,
        assets: list[dict[str, Any]],
        *,
        merge: bool = False,
    ) -> None:
        validated = [
            asset for asset in assets
            if asset.get("status") in {"downloaded", "unchanged"} and asset.get("stored_path")
        ]
        if not validated:
            return

        if merge:
            latest_path = self.source_root(source) / "latest.json"
            existing: list[dict[str, Any]] = []
            if latest_path.exists():
                try:
                    payload = json.loads(latest_path.read_text(encoding="utf-8"))
                    existing = list(payload.get("assets") or [])
                except (OSError, json.JSONDecodeError):
                    existing = []
            by_key: dict[str, dict[str, Any]] = {}
            for asset in existing + validated:
                key = str(asset.get("sha256") or asset.get("stored_path") or "")
                if not key:
                    continue
                by_key[key] = asset
            validated = list(by_key.values())

        updated_at = None
        for asset in validated:
            stamp = asset.get("retrieved_at") or asset.get("imported_at")
            if stamp and (updated_at is None or str(stamp) > str(updated_at)):
                updated_at = stamp

        write_json_atomic(
            self.source_root(source) / "latest.json",
            {"run_id": self.context.run_id, "updated_at": updated_at, "assets": validated},
        )
