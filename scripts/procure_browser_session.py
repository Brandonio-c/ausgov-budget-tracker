#!/usr/bin/env python3
"""Headed Playwright session for sources blocked by WAF / stream-reset.

Policy: does NOT solve CAPTCHAs, spoof fingerprints, or retry-storm. It opens a
real Chromium profile (persistent under data/.procurement/browser-profiles/),
navigates to the landing page, and if a challenge is detected it pauses so a
human can clear it in the visible window. After the gate is clear, it downloads
explicit --url targets and/or discovers ordinary public file links, writes them
into data/manual_inbox/_downloads/ with .url sidecars, then imports via
procure_manual_import.py.

Usage:
    python scripts/procure_browser_session.py --source-id act_budget_2026_27
    python scripts/procure_browser_session.py --domain-group sa
    python scripts/procure_browser_session.py --source-id qld_qgip_expenditure \\
        --url https://...csv --url https://...csv
    python scripts/procure_browser_session.py --source-id X --no-import
    python scripts/procure_browser_session.py --source-id X --headless  # only if profile already warm
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from procure.discovery import extract_assets, filename_from_url  # noqa: E402
from procure.registry import DEFAULT_REGISTRY, RegistryError, filter_sources, load_registry  # noqa: E402
from procure.storage import safe_filename  # noqa: E402
from procure.validation import CHALLENGE_MARKERS  # noqa: E402
from procure_acquisition_queue import DOMAIN_GROUPS  # noqa: E402

REPO_ROOT = DEFAULT_REGISTRY.parents[1]
DOWNLOADS = REPO_ROOT / "data" / "manual_inbox" / "_downloads"
PROFILES = REPO_ROOT / "data" / ".procurement" / "browser-profiles"

CHALLENGE_TITLE_RE = re.compile(
    r"just a moment|attention required|access denied|request blocked|verify you are human|captcha|challenge",
    re.I,
)
CHALLENGE_BODY_RE = re.compile(
    r"cf-mitigated|cdn-cgi/challenge|section\.io|request blocked|verify you are human|"
    r"checking your browser|enable javascript and cookies|aws.?waf|captcha",
    re.I,
)


def _load_urls_file(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "urls" in payload:
        payload = payload["urls"]
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list or {{urls: [...]}}")
    urls: list[str] = []
    for item in payload:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict) and item.get("url"):
            urls.append(str(item["url"]))
    return urls


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-id", help="single registry source id")
    parser.add_argument("--domain-group", help=f"one of: {', '.join(sorted(DOMAIN_GROUPS))}")
    parser.add_argument("--url", action="append", default=[], help="explicit file URL to download (repeatable)")
    parser.add_argument(
        "--urls-file",
        type=Path,
        help="JSON file: list of URL strings, or list of {url,name} objects, or {urls:[...]}",
    )
    parser.add_argument("--profile", help="override persistent profile directory name")
    parser.add_argument("--headless", action="store_true", help="headless Chromium (only useful with a warm profile)")
    parser.add_argument("--wait-seconds", type=int, default=300, help="max seconds to wait for a human to clear a challenge")
    parser.add_argument("--poll-seconds", type=float, default=3.0, help="challenge poll interval")
    parser.add_argument("--no-import", action="store_true", help="download only; skip procure_manual_import")
    parser.add_argument("--no-discover", action="store_true", help="do not discover links from the landing page")
    parser.add_argument("--timeout-ms", type=int, default=90_000)
    return parser.parse_args(argv)


def _is_challenge_html(html: str, title: str = "") -> bool:
    if title and CHALLENGE_TITLE_RE.search(title):
        return True
    sample = html[:200_000]
    if CHALLENGE_BODY_RE.search(sample):
        return True
    lower = sample.lower().encode("utf-8", errors="ignore")
    return any(marker in lower for marker in CHALLENGE_MARKERS if marker not in {b"sign in", b"log in"})


def _profile_dir(host: str, override: str | None) -> Path:
    name = override or safe_filename(host or "default")
    path = PROFILES / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _wait_for_clear(page, wait_seconds: int, poll_seconds: float) -> bool:
    deadline = time.time() + wait_seconds
    print(
        "CHALLENGE DETECTED — clear it in the browser window "
        f"(waiting up to {wait_seconds}s; or press Enter here once clear).",
        flush=True,
    )
    while time.time() < deadline:
        # Non-blocking stdin check when attached to a TTY.
        if sys.stdin.isatty():
            import select

            readable, _, _ = select.select([sys.stdin], [], [], 0)
            if readable:
                sys.stdin.readline()
                html = page.content()
                title = page.title()
                if not _is_challenge_html(html, title):
                    print("challenge cleared (Enter).", flush=True)
                    return True
                print("still looks like a challenge page; keep waiting…", flush=True)
        try:
            page.wait_for_timeout(int(poll_seconds * 1000))
            html = page.content()
            title = page.title()
            if not _is_challenge_html(html, title):
                print("challenge cleared (page content).", flush=True)
                return True
        except Exception as error:  # noqa: BLE001
            print(f"poll error: {error}", flush=True)
            time.sleep(poll_seconds)
    print("timed out waiting for challenge clearance", file=sys.stderr)
    return False


def _extension_for(url: str, content_type: str | None, body: bytes) -> str:
    name = filename_from_url(url, "download")
    if "." in name:
        return Path(name).suffix.lstrip(".").lower() or "bin"
    if body.startswith(b"%PDF-"):
        return "pdf"
    if body.startswith(b"PK"):
        return "xlsx"
    if content_type:
        lowered = content_type.lower()
        if "pdf" in lowered:
            return "pdf"
        if "csv" in lowered:
            return "csv"
        if "sheet" in lowered or "excel" in lowered:
            return "xlsx"
        if "zip" in lowered:
            return "zip"
        if "json" in lowered:
            return "json"
    return "bin"


def _save_download(
    source_id: str,
    url: str,
    body: bytes,
    content_type: str | None,
    label: str | None = None,
) -> Path:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    ext = _extension_for(url, content_type, body)
    hint = filename_from_url(url, source_id)
    stem_label = label or Path(hint).stem
    stem_label = safe_filename(stem_label)[:80]
    if label or stem_label != source_id:
        filename = f"{source_id}__{stem_label}.{ext}"
    else:
        filename = f"{source_id}.{ext}"
    # Avoid colliding when multiple files share a stem.
    path = DOWNLOADS / filename
    if path.exists():
        digest_prefix = str(abs(hash(url)))[:8]
        path = DOWNLOADS / f"{source_id}__{stem_label}-{digest_prefix}.{ext}"
    path.write_bytes(body)
    path.with_name(path.name + ".url").write_text(url.strip() + "\n", encoding="utf-8")
    print(f"  saved {path.name} ({len(body)} bytes)", flush=True)
    return path


def _import_file(source_id: str, path: Path, source_url: str) -> int:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "procure_manual_import.py"),
            source_id,
            str(path),
            "--source-url",
            source_url,
        ],
        cwd=REPO_ROOT,
    ).returncode


def _download_via_context(context, url: str, timeout_ms: int) -> tuple[bytes, str | None, str]:
    response = context.request.get(url, timeout=timeout_ms)
    body = response.body()
    headers = {key.lower(): value for key, value in response.headers.items()}
    return body, headers.get("content-type"), response.url


def process_source(
    source,
    urls: list[str],
    *,
    headless: bool,
    profile_override: str | None,
    wait_seconds: int,
    poll_seconds: float,
    timeout_ms: int,
    no_discover: bool,
    no_import: bool,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    host = urlparse(source.landing_url).hostname or "default"
    profile = _profile_dir(host, profile_override)
    result: dict[str, Any] = {
        "source_id": source.id,
        "landing_url": source.landing_url,
        "profile": str(profile.relative_to(REPO_ROOT)),
        "downloaded": [],
        "errors": [],
        "challenge": False,
    }

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=headless,
            accept_downloads=True,
            viewport={"width": 1400, "height": 900},
            # Several Commonwealth hosts silently reset HTTP/2 streams
            # (INTERNAL_ERROR). Prefer HTTP/1.1 for those connections.
            args=["--disable-http2"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            try:
                page.goto(source.landing_url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as error:  # noqa: BLE001
                result["errors"].append(f"goto failed: {type(error).__name__}: {error}")
                return result
            try:
                page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 30_000))
            except Exception:
                page.wait_for_timeout(2_000)
            try:
                html = page.content()
            except Exception:
                page.wait_for_load_state("domcontentloaded", timeout=10_000)
                html = page.content()
            title = page.title()
            if _is_challenge_html(html, title):
                result["challenge"] = True
                if headless:
                    result["errors"].append(
                        "challenge page in headless mode — re-run without --headless so a human can clear it"
                    )
                    return result
                if not _wait_for_clear(page, wait_seconds, poll_seconds):
                    result["errors"].append("challenge not cleared in time")
                    return result
                html = page.content()

            targets = list(urls)
            if not no_discover and not targets:
                assets, rejected = extract_assets(source, page.url, html.encode("utf-8"))
                targets = [asset.requested_url for asset in assets]
                result["discovered"] = len(targets)
                result["rejected_count"] = len(rejected)
                if not targets:
                    result["errors"].append(
                        "no downloadable assets discovered; pass --url explicitly or download by hand"
                    )

            for index, url in enumerate(targets):
                try:
                    body, content_type, final_url = _download_via_context(context, url, timeout_ms)
                    if not body:
                        result["errors"].append(f"empty body: {url}")
                        continue
                    if _is_challenge_html(body[:8_000].decode("utf-8", errors="ignore")):
                        result["errors"].append(f"challenge/HTML instead of file: {url}")
                        continue
                    label = None
                    if len(targets) > 1:
                        label = filename_from_url(url, f"file{index+1}").rsplit(".", 1)[0]
                    path = _save_download(source.id, final_url or url, body, content_type, label=label)
                    entry = {"url": final_url or url, "path": str(path.relative_to(REPO_ROOT)), "bytes": len(body)}
                    if not no_import:
                        code = _import_file(source.id, path, final_url or url)
                        entry["import_exit"] = code
                        if code != 0:
                            result["errors"].append(f"import failed for {path.name}")
                    result["downloaded"].append(entry)
                except Exception as error:  # noqa: BLE001
                    result["errors"].append(f"{url}: {type(error).__name__}: {error}")
        finally:
            context.close()
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.source_id and not args.domain_group:
        print("provide --source-id and/or --domain-group", file=sys.stderr)
        return 2
    if args.domain_group and args.domain_group not in DOMAIN_GROUPS:
        print(f"unknown domain group: {args.domain_group}", file=sys.stderr)
        print(f"known: {', '.join(sorted(DOMAIN_GROUPS))}", file=sys.stderr)
        return 2

    try:
        _, sources = load_registry()
    except RegistryError as error:
        print(f"registry error: {error}", file=sys.stderr)
        return 1

    source_ids: list[str] = []
    if args.domain_group:
        source_ids.extend(DOMAIN_GROUPS[args.domain_group])
    if args.source_id:
        if args.source_id not in source_ids:
            source_ids.append(args.source_id)

    matches = filter_sources(sources, source_ids=set(source_ids))
    by_id = {source.id: source for source in matches}
    missing = [source_id for source_id in source_ids if source_id not in by_id]
    if missing:
        print(f"unknown source ids: {', '.join(missing)}", file=sys.stderr)
        return 1

    explicit_urls = list(args.url)
    if args.urls_file:
        explicit_urls.extend(_load_urls_file(args.urls_file))

    # Skip sources that already have latest.json unless explicit URLs were given
    # for a multi-file top-up, or the caller named a single source id.
    run_results = []
    overall_errors = 0
    for source_id in source_ids:
        source = by_id[source_id]
        latest = REPO_ROOT / "data" / "raw" / source.government_level / source.id / "latest.json"
        if latest.is_file() and not explicit_urls and args.domain_group and not args.source_id:
            print(f"--- skip {source_id} (already has latest.json) ---", flush=True)
            continue
        print(f"--- browser session {source_id} ---", flush=True)
        # Explicit URLs apply when a single source is targeted.
        urls = list(explicit_urls) if (args.source_id == source_id or len(source_ids) == 1) else []
        outcome = process_source(
            source,
            urls,
            headless=args.headless,
            profile_override=args.profile,
            wait_seconds=args.wait_seconds,
            poll_seconds=args.poll_seconds,
            timeout_ms=args.timeout_ms,
            no_discover=args.no_discover,
            no_import=args.no_import,
        )
        run_results.append(outcome)
        if outcome["errors"] or not outcome["downloaded"]:
            overall_errors += 1
        print(json.dumps({k: outcome[k] for k in ("source_id", "challenge", "downloaded", "errors")}, indent=2))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = REPO_ROOT / "data" / ".procurement" / "reports" / f"browser-session-{stamp}.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"results": run_results}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {report.relative_to(REPO_ROOT)}")
    return 1 if overall_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
