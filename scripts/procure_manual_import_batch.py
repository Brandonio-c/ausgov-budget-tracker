#!/usr/bin/env python3
"""Batch-import manually downloaded files after you've saved them yourself.

Does not fetch anything from the internet - it only looks at files already on
disk. Drop files into a folder named `<source_id>.<ext>` (e.g.
`act_budget_2026_27.pdf`) and this runs procure_manual_import.py for every
match, skipping any source_id with no file present yet, so you can re-run this
repeatedly as you collect more files.

Provenance for `--source-url` (first match wins):
  1. Sidecar `<filename>.url` containing a single URL
  2. Optional `manifest.json` in the folder mapping filename → source_url
  3. Otherwise omitted (manual import falls back to the registry landing_url)

Usage:
    python scripts/procure_manual_import_batch.py [folder]

folder defaults to data/manual_inbox/_downloads/
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_NAMES = {"manifest.json"}


def _load_manifest(folder: Path) -> dict[str, str]:
    path = folder / "manifest.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"warning: could not read {path}: {error}", file=sys.stderr)
        return {}
    if not isinstance(payload, dict):
        print(f"warning: {path} is not a JSON object", file=sys.stderr)
        return {}
    return {str(key): str(value) for key, value in payload.items() if value}


def _source_url_for(file_path: Path, manifest: dict[str, str]) -> str | None:
    sidecar = Path(str(file_path) + ".url")
    if sidecar.is_file():
        url = sidecar.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        if url:
            return url
    return manifest.get(file_path.name) or manifest.get(str(file_path))


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    folder = Path(argv[0]) if argv else REPO_ROOT / "data" / "manual_inbox" / "_downloads"

    if not folder.is_dir():
        print(f"no such folder: {folder}", file=sys.stderr)
        return 1

    manual_ids = sorted(
        p.name
        for p in (REPO_ROOT / "data" / "manual_inbox").iterdir()
        if p.is_dir() and p.name != "_downloads"
    )
    manifest = _load_manifest(folder)

    found = 0
    failures = 0
    for source_id in manual_ids:
        matches = [
            f
            for f in folder.iterdir()
            if f.is_file()
            and f.name not in SKIP_NAMES
            and not f.name.endswith(".url")
            and f.stem.split("__")[0] == source_id
        ]
        if not matches:
            continue
        for file_path in sorted(matches, key=lambda path: path.name):
            found += 1
            print(f"--- importing {source_id} <- {file_path.name} ---")
            command = [
                sys.executable,
                str(REPO_ROOT / "scripts" / "procure_manual_import.py"),
                source_id,
                str(file_path),
            ]
            source_url = _source_url_for(file_path, manifest)
            if source_url:
                command.extend(["--source-url", source_url])
                print(f"  source-url: {source_url}")
            result = subprocess.run(command, cwd=REPO_ROOT)
            if result.returncode != 0:
                failures += 1
                print(f"  FAILED: {source_id} ({file_path.name})", file=sys.stderr)

    if found == 0:
        print(f"no matching files found in {folder}")
        print("expected filenames like <source_id>.<ext>, e.g. act_budget_2026_27.pdf")
        print("optional provenance: <file>.url sidecar or manifest.json")
    else:
        print(f"\nprocessed {found} file(s); failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
