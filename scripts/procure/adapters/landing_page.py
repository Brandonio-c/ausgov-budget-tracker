"""Static, bounded landing-page discovery."""

from __future__ import annotations

import hashlib
from collections import deque
from urllib.parse import urljoin, urlparse

from ..discovery import extract_assets, serialize_assets
from ..http_client import DownloadTooLarge, HTTPClient, HTTPFailure
from ..models import Asset, Source
from .base import AdapterContext, BaseAdapter

# Separate, smaller ceiling than the 20MB asset-discovery cap in get_bytes() - this
# is "is it even sane to crawl this as another page", not "is this a valid asset".
MAX_CRAWL_PAGE_BYTES = 5 * 1024 * 1024


def _looks_like_crawlable_page(http: HTTPClient, url: str) -> bool:
    """HEAD-check a secondary link before treating it as another page to scrape.

    A link only matched by the keyword heuristic below (see caller) can just as
    easily be a large binary document as a real HTML page with more links on it.
    Fetching it blind with the same full-body get_bytes() used for page scraping
    risks streaming a multi-hundred-MB file into memory before hitting the
    discovery cap. HEAD first; if the server won't say (no HEAD support, missing
    content-type/length), treat it as not crawlable rather than guessing.
    """
    try:
        response = http.head(url)
    except HTTPFailure:
        return False
    if response.status >= 400:
        return False
    content_type = response.headers.get("content-type", "")
    if content_type and "html" not in content_type.lower():
        return False
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_CRAWL_PAGE_BYTES:
                return False
        except ValueError:
            pass
    return True


class LandingPageAdapter(BaseAdapter):
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]:
        maximum_depth = int(source.access.get("discovery", {}).get("max_depth", 1))
        queue = deque([(source.landing_url, 0)])
        visited: set[str] = set()
        assets: list[Asset] = []
        rejected: list[dict] = []
        pages: list[dict] = []
        skipped_as_binary: list[dict] = []
        while queue and len(visited) < 25:
            page_url, depth = queue.popleft()
            if page_url in visited:
                continue
            visited.add(page_url)
            if depth == 0:
                # the entry point itself - nothing to discover without it, so a
                # failure here still surfaces as this source's own status.
                response = context.http.get_bytes(page_url)
            else:
                # a recursed link: never let one bad secondary link (oversized or
                # blocked) kill discovery for the whole source - skip and move on.
                try:
                    response = context.http.get_bytes(page_url)
                except (DownloadTooLarge, HTTPFailure) as error:
                    skipped_as_binary.append({"url": page_url, "reason": type(error).__name__})
                    continue
            page_assets, page_rejected = extract_assets(source, response.final_url, response.body or b"")
            assets.extend(page_assets)
            rejected.extend(page_rejected)
            pages.append({
                "requested_url": page_url,
                "final_url": response.final_url,
                "status": response.status,
                "headers": response.headers,
                "sha256": hashlib.sha256(response.body or b"").hexdigest(),
            })
            if depth < maximum_depth:
                for candidate in page_rejected:
                    url = candidate.get("url", "")
                    text = f"{url} {candidate.get('text', '')}".lower()
                    if candidate.get("reason") == "format_not_expected" and any(
                        token in text for token in ("archive", "previous", "budget", "publication", "report", "data")
                    ):
                        if urlparse(url).hostname == urlparse(response.final_url).hostname:
                            target = urljoin(response.final_url, url)
                            if _looks_like_crawlable_page(context.http, target):
                                queue.append((target, depth + 1))
                            else:
                                skipped_as_binary.append({"url": target, "reason": "head_check_not_html_or_too_large"})
        unique = {asset.requested_url: asset for asset in assets}
        resolved = list(unique.values())
        return resolved, {
            "pages": pages,
            "candidates": serialize_assets(resolved),
            "rejected": rejected,
            "skipped_as_binary": skipped_as_binary,
            "bounded_max_depth": maximum_depth,
            "bounded_max_pages": 25,
        }
