"""Bounded, auditable extraction of official download links."""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import PurePosixPath
from urllib.parse import parse_qs, unquote, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from .models import Asset, Source
from .storage import safe_filename

YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})[-–_/](20)?(\d{2})(?!\d)")
DOWNLOAD_WORDS = re.compile(r"download|data|table|appendix|budget|statement|report|export|workbook", re.I)
# A single generic word like "export" or "report" also matches ordinary page titles
# ("Export control", "Report a problem") that have nothing to do with data files -
# confirmed on wa_mycouncil, which grabbed a live "Export control" trade-compliance
# webpage this way. A rescue past the extension check now needs a second, genuinely
# stronger signal beyond that same weak word appearing in both the text and the URL.
STRONG_DOWNLOAD_PHRASES = re.compile(
    r"\bdownload\b|\bdataset\b|\bspreadsheet\b|\bworkbook\b|\bdata export\b|"
    r"\bexport (?:file|data|to (?:csv|excel|xlsx))\b|\bbulk export\b",
    re.I,
)
DATA_FILE_EXTENSIONS = {".csv", ".xlsx", ".xls", ".zip", ".pdf", ".docx", ".pptx", ".json", ".ods", ".ppt", ".doc", ".tsv"}


def _has_strong_download_url_signal(url: str) -> bool:
    # "download" as a path segment (common for CMS media endpoints with no file
    # extension at all, e.g. ndis.gov.au/media/8670/download?attachment) is an
    # unambiguous signal - unlike a bare "export" substring, no ordinary content
    # page has "/download" in its own path. "export" only counts as a genuine
    # path segment, not a substring of an unrelated word like "export-control".
    path = urlparse(url).path.lower()
    segments = path.split("/")
    return "download" in path or "export" in segments


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, parsed.params, parsed.query, ""))


def infer_financial_year(value: str) -> str | None:
    match = YEAR_PATTERN.search(unquote(value))
    if not match:
        return None
    return f"{match.group(1)}-{match.group(3)}"


def _url_path_suffix(url: str) -> str:
    """Return the file extension for a URL, including query-param filenames."""
    path_suffix = PurePosixPath(unquote(urlparse(url).path)).suffix.lower()
    if path_suffix:
        return path_suffix
    query = parse_qs(urlparse(url).query)
    for key in ("name", "filename", "file", "download"):
        values = query.get(key)
        if not values:
            continue
        candidate = PurePosixPath(unquote(values[0])).suffix.lower()
        if candidate:
            return candidate
    return path_suffix


def filename_from_url(url: str, fallback: str) -> str:
    path_name = PurePosixPath(unquote(urlparse(url).path)).name
    if path_name and "." in path_name:
        return safe_filename(path_name)
    query = parse_qs(urlparse(url).query)
    for key in ("filename", "file", "download"):
        if query.get(key):
            return safe_filename(query[key][0])
    return safe_filename(fallback)


def official_host_allowed(host: str, allowed_domains: set[str]) -> bool:
    host = host.lower().strip(".")
    if any(host == domain or host.endswith("." + domain) for domain in allowed_domains):
        return True
    return host.endswith(".gov.au") or host == "gov.au"


def extract_assets(source: Source, page_url: str, html: bytes) -> tuple[list[Asset], list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    discovery = source.access.get("discovery", {})
    allowed_extensions = {
        extension.lower() if str(extension).startswith(".") else f".{str(extension).lower()}"
        for extension in discovery.get("allowed_extensions", [])
        if extension not in {"download", "dashboard", "web", "export", "html"}
    }
    include = [re.compile(item, re.I) for item in discovery.get("include_regex", [])]
    exclude = [re.compile(item, re.I) for item in discovery.get("exclude_regex", [])]
    allowed_domains = {item.lower() for item in source.access.get("allowed_domains", [])}
    assets: list[Asset] = []
    rejected: list[dict] = []
    seen: set[str] = set()

    candidates: list[tuple[str, str, str]] = []
    for node in soup.select("a[href], link[href]"):
        href = node.get("href")
        if href:
            candidates.append((urljoin(page_url, href), node.get_text(" ", strip=True), "html_link"))
    for node in soup.select("[data-download-url], [data-file-url], [data-url]"):
        for attribute in ("data-download-url", "data-file-url", "data-url"):
            if node.get(attribute):
                candidates.append((urljoin(page_url, node[attribute]), node.get_text(" ", strip=True), attribute))

    for raw_url, text, evidence_type in candidates[:2000]:
        url = normalize_url(raw_url)
        if url in seen or urlparse(url).scheme not in {"http", "https"}:
            continue
        seen.add(url)
        host = urlparse(url).hostname or ""
        combined = f"{text} {url}"
        suffix = _url_path_suffix(url)
        reason = None
        if not official_host_allowed(host, allowed_domains):
            reason = "domain_not_allowed"
        elif any(pattern.search(combined) for pattern in exclude):
            reason = "excluded_by_registry"
        elif include and not any(pattern.search(combined) for pattern in include):
            reason = "no_include_pattern_match"
        elif allowed_extensions and suffix not in allowed_extensions:
            has_keyword = bool(DOWNLOAD_WORDS.search(text))
            has_strong_signal = (
                bool(STRONG_DOWNLOAD_PHRASES.search(text))
                or suffix in DATA_FILE_EXTENSIONS
                or _has_strong_download_url_signal(url)
            )
            if not (has_keyword and has_strong_signal):
                reason = "format_not_expected"
        if reason:
            rejected.append({"url": url, "text": text, "reason": reason})
            continue

        period = infer_financial_year(combined)
        filename = filename_from_url(url, f"{source.id}-{len(assets) + 1}")
        slug = safe_filename(PurePosixPath(filename).stem or f"asset-{len(assets) + 1}")
        asset_id = f"{source.id}:{period or 'undated'}:{slug}"
        assets.append(
            Asset(
                source_id=source.id,
                asset_instance_id=asset_id,
                requested_url=url,
                title=text or filename,
                expected_formats=source.formats,
                financial_year=period,
                filename_hint=filename,
                discovery_url=page_url,
                metadata={"evidence_type": evidence_type, "link_text": text},
            )
        )
    return assets, rejected


def serialize_assets(assets: list[Asset]) -> list[dict]:
    return [asdict(asset) for asset in assets]
