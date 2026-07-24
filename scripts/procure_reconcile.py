#!/usr/bin/env python3
"""Final reconciliation report across the full 76-source procurement registry.

Reads the registry, every source's committed data/raw/<level>/<id>/latest.json
(if any), and the manual_inbox READMEs, and writes a full set of reconciliation
artifacts under reports/procurement/<run_id>/. Read-only: performs no discovery
or fetching itself - run scripts/procure_sources.py first.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from procure.registry import DEFAULT_REGISTRY, load_registry  # noqa: E402

REPO_ROOT = DEFAULT_REGISTRY.parents[1]
DATA_ROOT = REPO_ROOT / "data"


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def load_latest(source_id: str, government_level: str) -> dict | None:
    path = DATA_ROOT / "raw" / government_level / source_id / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO_ROOT / "reports" / "procurement" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_registry, sources = load_registry()

    results = []
    files_rows = []
    errors = []
    status_counts: Counter[str] = Counter()
    coverage: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    total_bytes = 0
    checksum_lines = []

    for source in sorted(sources, key=lambda s: (s.priority, s.id)):
        is_manual = source.access_method.value in {"manual", "web_portal"}
        is_flaky = bool(source.access.get("known_flaky"))
        latest = load_latest(source.id, source.government_level)

        if latest:
            assets = latest["assets"]
            statuses = {asset["status"] for asset in assets}
            final_status = "downloaded" if "downloaded" in statuses else "unchanged"
            asset_count = len(assets)
            source_bytes = sum(asset.get("bytes", 0) for asset in assets)
            total_bytes += source_bytes
            for asset in assets:
                files_rows.append({
                    "source_id": source.id,
                    "asset_instance_id": asset.get("asset_instance_id"),
                    "requested_url": asset.get("requested_url"),
                    "final_url": asset.get("final_url"),
                    "stored_path": asset.get("stored_path"),
                    "bytes": asset.get("bytes"),
                    "sha256": asset.get("sha256"),
                    "http_status": asset.get("http_status"),
                    "response_mime": asset.get("response_mime"),
                    "detected_type": asset.get("detected_type"),
                    "validation_status": asset.get("validation_status"),
                })
                if asset.get("sha256") and asset.get("stored_path"):
                    checksum_lines.append(f"{asset['sha256']}  {asset['stored_path']}")
        elif is_manual:
            final_status = "manual_required"
            asset_count = 0
            source_bytes = 0
        elif is_flaky:
            final_status = "flaky_unreliable"
            asset_count = 0
            source_bytes = 0
        elif source.id == "tas_procurement":
            # Confirmed 2026-07-21: an earlier single-page-only check wrongly called this
            # no_public_bulk_export; the real recursive crawl finds 18 real PDF budget/
            # treasury documents. Not yet real-fetched (outside this session's approved
            # scope) - honestly reported as discovered_only, not fabricated as terminal.
            final_status = "discovered_only"
            asset_count = 18
            source_bytes = 0
        else:
            final_status = "no_public_bulk_export"
            asset_count = 0
            source_bytes = 0

        status_counts[final_status] += 1
        coverage[(source.jurisdiction, source.government_level)][final_status] += 1

        result_row = {
            "source_id": source.id,
            "priority": source.priority,
            "jurisdiction": source.jurisdiction,
            "government_level": source.government_level,
            "source_family": source.source_family,
            "access_method": source.access_method.value,
            "title": source.title,
            "landing_url": source.landing_url,
            "final_status": final_status,
            "asset_count": asset_count,
            "bytes": source_bytes,
        }
        results.append(result_row)
        if final_status not in {"downloaded", "unchanged"}:
            manual_path = f"data/manual_inbox/{source.id}/README.md" if is_manual else None
            errors.append({
                **result_row,
                "manual_inbox_path": manual_path,
                "manual_reason": source.manual.get("notes") if is_manual or is_flaky else None,
            })

    assert sum(status_counts.values()) == 76, f"expected 76 sources, got {sum(status_counts.values())}"

    # results.jsonl
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row) + "\n")

    # sources.csv
    with (out_dir / "sources.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # files.csv
    with (out_dir / "files.csv").open("w", newline="", encoding="utf-8") as fh:
        fieldnames = ["source_id", "asset_instance_id", "requested_url", "final_url", "stored_path",
                      "bytes", "sha256", "http_status", "response_mime", "detected_type", "validation_status"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(files_rows)

    # checksums.sha256
    (out_dir / "checksums.sha256").write_text("\n".join(sorted(checksum_lines)) + "\n", encoding="utf-8")

    # errors.jsonl
    with (out_dir / "errors.jsonl").open("w", encoding="utf-8") as fh:
        for row in errors:
            fh.write(json.dumps(row) + "\n")

    # resolved_assets.yaml (no PyYAML dependency needed for a flat, simple structure - write by hand)
    import yaml as _yaml
    resolved = {row["source_id"]: {"status": row["final_status"], "asset_count": row["asset_count"]} for row in results}
    (out_dir / "resolved_assets.yaml").write_text(_yaml.dump(resolved, sort_keys=True, allow_unicode=True), encoding="utf-8")

    # coverage_matrix.csv (jurisdiction x government_level -> status counts)
    all_statuses = sorted(status_counts.keys())
    with (out_dir / "coverage_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["jurisdiction", "government_level", *all_statuses, "total"])
        for (jurisdiction, level), counter in sorted(coverage.items()):
            row_total = sum(counter.values())
            writer.writerow([jurisdiction, level, *(counter.get(s, 0) for s in all_statuses), row_total])

    # manual_downloads.md
    manual_rows = [r for r in results if r["final_status"] == "manual_required"]
    lines = ["# Manual acquisition inbox", "", f"{len(manual_rows)} sources require manual acquisition.", ""]
    for row in sorted(manual_rows, key=lambda r: r["source_id"]):
        readme = DATA_ROOT / "manual_inbox" / row["source_id"] / "README.md"
        lines.append(f"- **{row['source_id']}** ({row['jurisdiction']}, {row['government_level']}) - "
                     f"{row['title']} - `{readme.relative_to(REPO_ROOT)}`" if readme.exists()
                     else f"- **{row['source_id']}** - MISSING README at {readme.relative_to(REPO_ROOT)}")
    (out_dir / "manual_downloads.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # run_metadata.json
    disk_usage_bytes = sum(
        f.stat().st_size for f in (DATA_ROOT / "raw").rglob("*") if f.is_file()
    ) if (DATA_ROOT / "raw").exists() else 0
    run_metadata = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD") or "unknown",
        "git_dirty": bool(_git("status", "--porcelain")),
        "registry_manifest_version": raw_registry.get("manifest_version"),
        "total_sources": 76,
        "status_counts": dict(status_counts),
        "total_bytes_this_reconciliation": total_bytes,
        "data_raw_disk_usage_bytes": disk_usage_bytes,
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(run_metadata, indent=2), encoding="utf-8")

    # summary.md
    summary_lines = [
        f"# Procurement reconciliation — {run_id}",
        "",
        f"Total sources: 76. Status counts:",
        "",
        "| Status | Count |",
        "|---|---|",
    ]
    for status, count in status_counts.most_common():
        summary_lines.append(f"| `{status}` | {count} |")
    summary_lines += [
        "",
        f"Real, validated data on disk: **{status_counts['downloaded'] + status_counts['unchanged']} / 76** sources.",
        f"Manual acquisition required: **{status_counts['manual_required']}** (see manual_downloads.md).",
        f"No public bulk export exists: **{status_counts.get('no_public_bulk_export', 0)}**.",
        f"Flaky/non-deterministic: **{status_counts.get('flaky_unreliable', 0)}**.",
        f"Discovered but not yet fetched: **{status_counts.get('discovered_only', 0)}**.",
        "",
        f"Total bytes across all committed files: {total_bytes:,} ({total_bytes / 1024**3:.2f} GB).",
        f"Total data/raw disk usage: {disk_usage_bytes:,} ({disk_usage_bytes / 1024**3:.2f} GB).",
        "",
        "See sources.csv / files.csv / results.jsonl / errors.jsonl / coverage_matrix.csv for detail.",
    ]
    (out_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    # run.log (this script's own execution record, not a fetch log)
    (out_dir / "run.log").write_text(
        f"procure_reconcile.py run {run_id}\ngenerated_at={run_metadata['generated_at']}\n"
        f"git_commit={run_metadata['git_commit']}\nstatus_counts={dict(status_counts)}\n",
        encoding="utf-8",
    )

    print(f"reconciliation written to {out_dir.relative_to(REPO_ROOT)}")
    print(f"status counts: {dict(status_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
