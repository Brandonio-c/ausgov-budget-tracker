#!/usr/bin/env python3
"""Inventory handoff ALREADY_ON_DISK rows against data/raw/*/latest.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "data" / "new" / "ausgov_additional_data_handoff.yaml"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "ops" / "reports" / "handoff-on-disk-inventory.md"


def _latest_dirs(source_key: str) -> list[Path]:
    if not source_key:
        return []
    return [p for p in RAW.rglob(source_key) if p.is_dir() and (p / "latest.json").exists()]


def _asset_ok(source_dir: Path) -> dict:
    data = json.loads((source_dir / "latest.json").read_text(encoding="utf-8"))
    assets = data.get("assets") or []
    present = []
    missing = []
    for asset in assets:
        stored = Path(asset.get("stored_path") or "")
        candidates = [
            ROOT / "data" / stored if not stored.is_absolute() else stored,
            ROOT / stored,
            source_dir / "files" / stored.name,
        ]
        hit = next((c for c in candidates if c.exists() and c.is_file()), None)
        if hit:
            present.append({"path": str(hit), "bytes": hit.stat().st_size, "sha256": asset.get("sha256")})
        else:
            missing.append(str(stored))
    return {
        "source_dir": str(source_dir.relative_to(ROOT)),
        "asset_count": len(assets),
        "present": len(present),
        "missing_paths": missing,
        "bytes": sum(p["bytes"] for p in present),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, default=HANDOFF)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    doc = yaml.safe_load(args.handoff.read_text(encoding="utf-8"))
    rows = [
        s
        for s in doc.get("sources") or []
        if s.get("already_on_disk") or s.get("action_bucket") == "INGEST_FIRST_ALREADY_ON_DISK"
    ]
    confirmed = []
    orphans = []
    for row in rows:
        key = (row.get("repo_source_key") or row.get("proposed_source_id") or "").strip()
        dirs = _latest_dirs(key)
        if not dirs:
            orphans.append(row)
            continue
        info = _asset_ok(dirs[0])
        if info["present"] == 0:
            orphans.append({**row, "_inventory": info})
        else:
            confirmed.append({**row, "_inventory": info})

    # Promote orphans: clear already_on_disk marker conceptually in report
    lines = [
        "# Handoff on-disk inventory",
        "",
        f"Generated from `{args.handoff.relative_to(ROOT)}`.",
        "",
        f"- Already-on-disk rows checked: **{len(rows)}**",
        f"- Confirmed with files: **{len(confirmed)}**",
        f"- Orphans (promote to download): **{len(orphans)}**",
        "",
        "## Confirmed",
        "",
        "| proposed_source_id | repo_source_key | assets | bytes |",
        "|---|---|---:|---:|",
    ]
    for row in sorted(confirmed, key=lambda r: r["proposed_source_id"]):
        inv = row["_inventory"]
        lines.append(
            f"| `{row['proposed_source_id']}` | `{row.get('repo_source_key') or ''}` | "
            f"{inv['present']}/{inv['asset_count']} | {inv['bytes']:,} |"
        )
    lines += ["", "## Orphans — promote to download", ""]
    if not orphans:
        lines.append("_None._")
    else:
        lines += [
            "| proposed_source_id | repo_source_key | direct_file_url |",
            "|---|---|---|",
        ]
        for row in sorted(orphans, key=lambda r: r["proposed_source_id"]):
            lines.append(
                f"| `{row['proposed_source_id']}` | `{row.get('repo_source_key') or ''}` | "
                f"{row.get('direct_file_url') or ''} |"
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "checked": len(rows),
        "confirmed": len(confirmed),
        "orphans": len(orphans),
        "orphan_ids": [r["proposed_source_id"] for r in orphans],
        "report": str(args.out.relative_to(ROOT)),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
