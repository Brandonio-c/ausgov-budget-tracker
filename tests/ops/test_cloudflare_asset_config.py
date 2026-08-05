"""Regression test for the Cloudflare nested-route rendering issue
(Task 1 of the adapter-repair-followup milestone -
ops/reports/cloudflare-route-triage-*.md).

This cannot exercise the real Cloudflare edge behavior from a local
test environment (the investigation found that even `wrangler dev`'s
local Miniflare simulation does not reliably reproduce production
behavior for this specific bug - see the triage report), so this test
only guards against the two config regressions that are directly
verifiable: `not_found_handling` reverting to `"single-page-application"`
(which was the confirmed root cause - it applies SPA-fallback behavior
to any Sec-Fetch-Mode: navigate request regardless of whether the asset
actually exists, wrong for this multi-page static export), and the
defensive `Cache-Control: no-store` override for HTML responses being
silently removed from asset-worker.js.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WRANGLER_CONFIG = REPO_ROOT / "src" / "frontend" / "wrangler.vibefactory.toml"
ASSET_WORKER = REPO_ROOT / "src" / "frontend" / "asset-worker.js"


def test_not_found_handling_is_not_single_page_application():
    text = WRANGLER_CONFIG.read_text(encoding="utf-8")
    assert 'not_found_handling = "404-page"' in text
    assert 'not_found_handling = "single-page-application"' not in text


def test_asset_worker_forces_no_store_for_html_responses():
    text = ASSET_WORKER.read_text(encoding="utf-8")
    assert "no-store" in text
    assert "text/html" in text
