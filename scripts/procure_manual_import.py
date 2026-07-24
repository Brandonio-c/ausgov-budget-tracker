#!/usr/bin/env python3
"""Import a manually downloaded file for a source automation cannot reach.

For sources classified `manual`/`web_portal` in config/procurement_sources.yaml,
or any source blocked at the WAF/login layer (see data/manual_inbox/<id>/README.md
for the acquisition steps this supports). Validates the file exactly like an
automated fetch would, then commits it into the same snapshot store layout
(data/raw/<government_level>/<id>/snapshots/<run_id>/files/) so manually- and
automatically-acquired sources are indistinguishable to downstream tooling.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from procure.models import Asset, RunContext  # noqa: E402
from procure.registry import DEFAULT_REGISTRY, RegistryError, filter_sources, load_registry  # noqa: E402
from procure.storage import SnapshotStore, safe_filename  # noqa: E402
from procure.validation import validate_file  # noqa: E402

REPO_ROOT = DEFAULT_REGISTRY.parents[1]


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source_id")
    parser.add_argument("file_path", type=Path)
    parser.add_argument("--source-url", help="the exact page/document URL the file was downloaded from (defaults to the registry landing_url)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        _, sources = load_registry()
        matches = filter_sources(sources, source_ids={args.source_id})
    except RegistryError as error:
        print(f"registry error: {error}", file=sys.stderr)
        return 1
    source = matches[0]

    if not args.file_path.is_file():
        print(f"not a file: {args.file_path}", file=sys.stderr)
        return 1

    run_context = RunContext(
        run_id=f"manual-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        repo_root=REPO_ROOT,
        data_root=REPO_ROOT / "data",
        reports_root=REPO_ROOT / "data" / ".procurement" / "reports",
        git_commit=_git("rev-parse", "HEAD") or "unknown",
        git_dirty=bool(_git("status", "--porcelain")),
        max_total_bytes=0,
        max_file_bytes=0,
        dry_run=False,
        discover_only=False,
        browser_fallback=False,
    )
    store = SnapshotStore(run_context)
    store.prepare_snapshot(source)

    validation = validate_file(
        args.file_path,
        source.formats,
        min_bytes=int(source.validation.get("min_bytes", 1)),
        max_bytes=source.validation.get("max_bytes"),
    )

    asset = Asset(
        source_id=source.id,
        asset_instance_id=f"{source.id}:manual:{safe_filename(args.file_path.stem)}",
        requested_url=args.source_url or source.landing_url,
        title=source.title,
        expected_formats=source.formats,
        filename_hint=args.file_path.name,
        discovery_url=source.landing_url,
        metadata={"adapter": "manual_import", "imported_at": datetime.now(timezone.utc).isoformat()},
    )

    if not validation.valid:
        quarantined = store.quarantine(source, asset, args.file_path, validation)
        print(f"REJECTED: {validation.error}")
        print(f"quarantined to {quarantined}")
        return 1

    digest, stored, unchanged = store.commit_validated(source, asset, args.file_path, args.file_path.name)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    result = {
        "source_id": source.id,
        "status": "unchanged" if unchanged else "downloaded",
        "stored_path": stored,
        "sha256": digest,
        "detected_type": validation.detected_type,
        "validation_warnings": validation.warnings,
        "requested_url": asset.requested_url,
        "retrieved_at": retrieved_at,
        "original_filename": args.file_path.name,
        "metadata": asset.metadata,
    }
    # Merge so multi-file sources (e.g. qld_qgip_expenditure) accumulate assets
    # across successive imports instead of overwriting latest.json each time.
    store.update_latest(source, [result], merge=True)
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
