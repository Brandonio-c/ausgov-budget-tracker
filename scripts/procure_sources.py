#!/usr/bin/env python3
"""Discover and (optionally) fetch documents for config/procurement_sources.yaml.

This is the orchestrator for the 76-source procurement registry: it dispatches
each source to its `scripts/procure/adapters` implementation by
`access_method`, runs `discover()` then `fetch()`, and writes a per-run JSON
report under `data/.procurement/reports/`.

Entirely independent of the legacy pipeline (`scripts/fetch_sources.py` +
`scripts/sources.yaml` + `scripts/build_processed_db.py`), which this script
never reads or writes: new sources land under
`data/raw/<government_level>/<id>/snapshots/<run_id>/`, a versioned layout
distinct from the legacy flat `data/raw/<level>/<legacy_id>/<file>` files
that the deployed app's database build depends on.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from procure.adapters import (  # noqa: E402
    AdapterContext,
    BrowserDiscoveryAdapter,
    CKANAdapter,
    DirectFileAdapter,
    LandingPageAdapter,
    ManualAdapter,
    OCDSAdapter,
    SocrataAdapter,
)
from procure.http_client import DownloadTooLarge, HTTPClient, HTTPFailure  # noqa: E402
from procure.models import (  # noqa: E402
    SUCCESS_STATUSES,
    AccessType,
    RunContext,
    SourceResult,
    Status,
)
from procure.registry import (  # noqa: E402
    DEFAULT_REGISTRY,
    RegistryError,
    filter_sources,
    load_registry,
)
from procure.storage import DiskBudget, SnapshotStore, write_json_atomic  # noqa: E402

GIB = 1024**3
REPO_ROOT = DEFAULT_REGISTRY.parents[1]

ADAPTERS = {
    AccessType.DIRECT_FILE: DirectFileAdapter(),
    AccessType.CKAN_API: CKANAdapter(),
    AccessType.SOCRATA_API: SocrataAdapter(),
    AccessType.OCDS_API: OCDSAdapter(),
    AccessType.LANDING_PAGE: LandingPageAdapter(),
    AccessType.WEB_PORTAL: ManualAdapter(),
    AccessType.MANUAL: ManualAdapter(),
}


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def _split(value: str | None) -> set[str] | None:
    return {item.strip() for item in value.split(",") if item.strip()} if value else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-ids", help="comma-separated source ids to restrict to")
    parser.add_argument("--priorities", help="comma-separated priorities, e.g. P1,P2")
    parser.add_argument("--jurisdictions", help="comma-separated jurisdictions")
    parser.add_argument("--levels", help="comma-separated government levels")
    parser.add_argument("--families", help="comma-separated source families")
    parser.add_argument("--automation", help="comma-separated automation tiers")
    parser.add_argument("--dry-run", action="store_true", help="discover, but never write downloaded files to disk")
    parser.add_argument("--discover-only", action="store_true", help="same effect as --dry-run; kept as a separate, clearer flag name")
    parser.add_argument("--no-browser-fallback", action="store_true", help="disable the Playwright fallback for zero-asset landing pages")
    parser.add_argument("--max-total-bytes", type=int, default=2 * GIB)
    parser.add_argument("--max-file-bytes", type=int, default=500 * 1024**2)
    parser.add_argument("--connect-timeout", type=float, default=10)
    parser.add_argument("--read-timeout", type=float, default=30, help="low by default for discovery passes; raise for real downloads")
    parser.add_argument("--retries", type=int, default=1, help="low by default so one unresponsive host can't stall the whole run")
    parser.add_argument("--limit", type=int, help="stop after N sources (smoke testing)")
    return parser.parse_args(argv)


def build_run_context(args: argparse.Namespace) -> RunContext:
    data_root = REPO_ROOT / "data"
    return RunContext(
        run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        repo_root=REPO_ROOT,
        data_root=data_root,
        reports_root=data_root / ".procurement" / "reports",
        git_commit=_git("rev-parse", "HEAD") or "unknown",
        git_dirty=bool(_git("status", "--porcelain")),
        max_total_bytes=args.max_total_bytes,
        max_file_bytes=args.max_file_bytes,
        dry_run=args.dry_run,
        discover_only=args.discover_only,
        browser_fallback=not args.no_browser_fallback,
    )


def run_source(source, context: AdapterContext) -> SourceResult:
    now = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
    result = SourceResult(
        source_id=source.id,
        status=Status.NOT_FOUND,
        priority=source.priority,
        publisher=source.publisher,
        jurisdiction=source.jurisdiction,
        government_level=source.government_level,
        source_family=source.source_family,
        access_method=source.access_method.value,
        automation=source.automation,
        landing_url=source.landing_url,
        started_at=now(),
    )
    if not source.enabled:
        result.status = Status.SKIPPED_DISABLED
        result.finished_at = now()
        return result

    adapter = ADAPTERS[source.access_method]
    known_flaky = bool(source.access.get("known_flaky"))
    # Sparse retries for known-flaky hosts (e.g. qld_local_qao_2025): a few spaced
    # attempts, stop on first non-empty discovery. Cap is small on purpose so we
    # never hammer adaptive bot-mitigation. Override with access.flaky_max_attempts.
    max_discover_attempts = 1
    flaky_gap_seconds = 0.0
    if known_flaky:
        max_discover_attempts = max(1, int(source.access.get("flaky_max_attempts", 3)))
        flaky_gap_seconds = float(source.access.get("flaky_gap_seconds", 45))

    assets: list = []
    evidence: dict = {}
    last_error: Exception | None = None
    for attempt in range(1, max_discover_attempts + 1):
        try:
            assets, evidence = adapter.discover(source, context)
            if not assets and source.access_method is AccessType.LANDING_PAGE and context.run.browser_fallback:
                browser_assets, browser_evidence = BrowserDiscoveryAdapter().discover(source, context)
                evidence = {**evidence, "browser_fallback": browser_evidence}
                assets = browser_assets
            if isinstance(evidence, dict):
                evidence["discover_attempt"] = attempt
                evidence["discover_attempts_max"] = max_discover_attempts
            context.store.write_discovery(source, evidence)
            if assets or not known_flaky:
                break
            # Empty discovery on a flaky source — wait and try again, unless last attempt.
            if attempt < max_discover_attempts and flaky_gap_seconds > 0:
                time.sleep(flaky_gap_seconds)
        except (HTTPFailure, DownloadTooLarge, ValueError) as error:
            last_error = error
            if attempt < max_discover_attempts and known_flaky and flaky_gap_seconds > 0:
                time.sleep(flaky_gap_seconds)
                continue
            if isinstance(error, HTTPFailure) and error.status in {401, 403}:
                result.status = Status.BLOCKED_AUTH
            elif isinstance(error, HTTPFailure):
                result.status = Status.HTTP_ERROR
            else:
                result.status = Status.REGISTRY_ERROR
            result.error_type = type(error).__name__
            result.error_message = str(error)
            result.retryable = getattr(error, "retryable", False)
            result.finished_at = now()
            return result

    if known_flaky and not assets:
        # Still empty after sparse retries — honest flaky status; suggest browser session.
        result.status = Status.FLAKY_UNRELIABLE
        result.manual_reason = (
            source.manual.get("notes")
            or "sparse discovery retries returned no assets; try procure_browser_session.py"
        )
        if isinstance(evidence, dict):
            result.error_message = evidence.get("error") or "empty discovery after flaky retries"
        elif last_error is not None:
            result.error_message = str(last_error)
        result.finished_at = now()
        return result

    result.discovered_asset_count = len(assets)
    result.attempted_urls = [asset.requested_url for asset in assets]

    if not assets:
        is_manual = source.access_method in {AccessType.MANUAL, AccessType.WEB_PORTAL}
        requires_browser = bool(source.access.get("requires_browser"))
        if requires_browser:
            result.status = Status.BROWSER_REQUIRED
        elif is_manual:
            result.status = Status.MANUAL_REQUIRED
        else:
            result.status = Status.NO_PUBLIC_BULK_EXPORT
        result.manual_reason = evidence.get("reason") if isinstance(evidence, dict) else None
        result.finished_at = now()
        return result

    acquisitions = []
    for asset in assets:
        acquisition = adapter.fetch(source, asset, context)
        acquisitions.append(acquisition)
        if acquisition.status == Status.DOWNLOADED:
            result.downloaded_file_count += 1
        elif acquisition.status == Status.UNCHANGED:
            result.unchanged_file_count += 1
        elif acquisition.status not in SUCCESS_STATUSES and acquisition.status != Status.DISCOVERED_ONLY:
            result.failed_asset_count += 1
        result.bytes += acquisition.bytes
        result.retry_count += acquisition.retry_count

    result.assets = acquisitions
    context.store.write_acquisition(source, {"assets": [item.as_dict() for item in acquisitions]})
    context.store.update_latest(source, [item.as_dict() for item in acquisitions])

    if context.run.dry_run or context.run.discover_only:
        result.status = Status.DISCOVERED_ONLY
    elif result.downloaded_file_count or result.unchanged_file_count:
        result.status = Status.DOWNLOADED if result.downloaded_file_count else Status.UNCHANGED
    elif result.failed_asset_count:
        result.status = acquisitions[-1].status
    else:
        result.status = Status.PARTIAL

    result.finished_at = now()
    return result


def status_counts(results: list[SourceResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        _, sources = load_registry()
        sources = filter_sources(
            sources,
            source_ids=_split(args.source_ids),
            priorities=_split(args.priorities),
            jurisdictions=_split(args.jurisdictions),
            levels=_split(args.levels),
            families=_split(args.families),
            automation=_split(args.automation),
        )
    except RegistryError as error:
        print(f"registry error: {error}", file=sys.stderr)
        return 1

    if args.limit:
        sources = sources[: args.limit]
    if not sources:
        print("no sources matched the given filters", file=sys.stderr)
        return 1

    run_context = build_run_context(args)
    http = HTTPClient(
        connect_timeout=args.connect_timeout,
        read_timeout=args.read_timeout,
        retries=args.retries,
    )
    store = SnapshotStore(run_context)
    budget = DiskBudget(run_context.data_root, run_context.max_total_bytes)
    context = AdapterContext(run=run_context, http=http, store=store, budget=budget)

    results: list[SourceResult] = []
    for source in sources:
        store.prepare_snapshot(source)
        result = run_source(source, context)
        results.append(result)
        print(f"{result.status.value:24s} {source.priority:3s} {source.id:45s} assets={result.discovered_asset_count}")

    counts = status_counts(results)
    summary = {
        "run_id": run_context.run_id,
        "git_commit": run_context.git_commit,
        "git_dirty": run_context.git_dirty,
        "dry_run": run_context.dry_run,
        "discover_only": run_context.discover_only,
        "source_count": len(results),
        "disk_budget": budget.as_dict(),
        "status_counts": counts,
        "sources": [result.as_dict(include_assets=True) for result in results],
    }
    write_json_atomic(run_context.reports_root / f"{run_context.run_id}.json", summary)

    print(f"\nreport: data/.procurement/reports/{run_context.run_id}.json")
    print(f"status counts: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
