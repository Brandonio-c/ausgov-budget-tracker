"""Optional browser rendering used only to expose ordinary public links."""

from __future__ import annotations

from ..discovery import extract_assets, serialize_assets
from ..models import Asset, Source
from .base import AdapterContext, BaseAdapter


class BrowserDiscoveryAdapter(BaseAdapter):
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]:
        if not context.run.browser_fallback:
            return [], {"error": "browser fallback disabled", "candidates": [], "rejected": []}
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return [], {"error": "Python Playwright is not installed", "candidates": [], "rejected": []}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(source.landing_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(2_000)
            html = page.content().encode("utf-8")
            final_url = page.url
            browser.close()
        assets, rejected = extract_assets(source, final_url, html)
        return assets, {
            "rendered_url": final_url,
            "candidates": serialize_assets(assets),
            "rejected": rejected,
            "browser_used_for_discovery_only": True,
        }
