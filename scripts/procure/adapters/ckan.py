"""CKAN package metadata and multi-resource adapter."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from ..discovery import filename_from_url, infer_financial_year
from ..http_client import HTTPFailure
from ..models import Asset, Source
from ..storage import safe_filename
from .base import AdapterContext, BaseAdapter


def normalize_ckan_format(raw_format: str) -> str:
    """CKAN publishers use inconsistent free-text format labels for the same
    real format - "excel (.xlsx)", "excel (xlsx)", "XLSX" all mean xlsx, and
    data.gov.au's "csv-geo-au"/"csv-geo-nz" convention is still plain CSV with
    geo metadata attached. Extract the real token rather than exact-matching
    the raw label.
    """
    value = (raw_format or "").lower().strip().lstrip(".")
    if not value:
        return value
    match = re.search(r"\(\.?([a-z0-9]+)\)", value)
    if match:
        return match.group(1)
    if value.startswith("csv"):
        return "csv"
    return value


def ckan_endpoint_and_package(source: Source) -> tuple[str, str]:
    parsed = urlparse(source.landing_url)
    path = parsed.path.rstrip("/")
    package_id = source.access.get("package_id")
    if not package_id:
        marker = "/dataset/"
        if marker not in path:
            raise ValueError("CKAN landing URL has no /dataset/<package> path")
        package_id = path.split(marker, 1)[1].split("/", 1)[0]
    prefix = "/data" if path.startswith("/data/dataset/") else ""
    endpoint = source.access.get("endpoint") or f"{parsed.scheme}://{parsed.netloc}{prefix}/api/3/action/package_show"
    return endpoint, package_id


def ckan_search_endpoint(source: Source) -> str:
    parsed = urlparse(source.landing_url)
    prefix = "/data" if parsed.path.startswith("/data/") else ""
    return source.access.get("search_endpoint") or f"{parsed.scheme}://{parsed.netloc}{prefix}/api/3/action/package_search"


class CKANAdapter(BaseAdapter):
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]:
        search_q = source.access.get("package_search_q")
        if search_q:
            return self._discover_from_search(source, context, search_q)
        endpoint, package_id = ckan_endpoint_and_package(source)
        response = context.http.get_bytes(f"{endpoint}?id={package_id}")
        payload = json.loads(response.body or b"{}")
        if not payload.get("success"):
            raise HTTPFailure("CKAN package_show returned success=false")
        package = payload["result"]
        accepted, rejected = self._resources_from_package(source, package, package_id, response.final_url)
        if not source.storage.get("multi_file", True) and accepted:
            rejected.extend({"url": asset.requested_url, "reason": "multi_file_disabled"} for asset in accepted[1:])
            accepted = accepted[:1]
        evidence = {
            "endpoint": endpoint,
            "package_id": package_id,
            "package_title": package.get("title"),
            "package_metadata": package,
            "candidates": [asset.requested_url for asset in accepted],
            "rejected": rejected,
        }
        return accepted, evidence

    def _discover_from_search(self, source: Source, context: AdapterContext, search_q: str) -> tuple[list[Asset], dict]:
        endpoint = ckan_search_endpoint(source)
        rows = int(source.access.get("package_search_rows", 100))
        max_packages = int(source.access.get("package_search_max_packages", 200))
        package_pattern = source.access.get("package_name_regex")
        package_regex = re.compile(package_pattern, re.I) if package_pattern else None
        latest_only = bool(source.access.get("latest_resource_only", True))
        accepted: list[Asset] = []
        rejected: list[dict] = []
        packages_meta: list[dict] = []
        start = 0
        while start < max_packages:
            response = context.http.get_bytes(f"{endpoint}?q={search_q}&rows={rows}&start={start}")
            payload = json.loads(response.body or b"{}")
            if not payload.get("success"):
                raise HTTPFailure("CKAN package_search returned success=false")
            result = payload["result"]
            batch = result.get("results") or []
            if not batch:
                break
            for package in batch:
                package_id = package.get("name") or package.get("id")
                if package_regex and package_id and not package_regex.search(str(package_id)):
                    rejected.append({"package_id": package_id, "reason": "package_name_regex_mismatch"})
                    continue
                package_assets, package_rejected = self._resources_from_package(
                    source, package, str(package_id), response.final_url, latest_only=latest_only
                )
                accepted.extend(package_assets)
                rejected.extend(package_rejected)
                packages_meta.append({"package_id": package_id, "title": package.get("title"), "assets": len(package_assets)})
                if len(packages_meta) >= max_packages:
                    break
            if len(batch) < rows or len(packages_meta) >= max_packages:
                break
            start += rows
        unique = {asset.requested_url: asset for asset in accepted}
        resolved = list(unique.values())
        evidence = {
            "endpoint": endpoint,
            "package_search_q": search_q,
            "packages": packages_meta,
            "candidates": [asset.requested_url for asset in resolved],
            "rejected": rejected,
        }
        return resolved, evidence

    def _resources_from_package(
        self,
        source: Source,
        package: dict,
        package_id: str,
        discovery_url: str,
        *,
        latest_only: bool = False,
    ) -> tuple[list[Asset], list[dict]]:
        resource_id = source.access.get("resource_id")
        name_pattern = source.access.get("resource_name_regex")
        regex = re.compile(name_pattern, re.I) if name_pattern else None
        accepted: list[Asset] = []
        rejected: list[dict] = []
        resources = list(package.get("resources") or [])
        if latest_only:
            matching = []
            for resource in resources:
                resource_format = normalize_ckan_format(str(resource.get("format") or ""))
                if source.formats and resource_format not in {item.lower().lstrip(".") for item in source.formats}:
                    continue
                matching.append(resource)
            if matching:
                resources = [matching[-1]]
        for resource in resources:
            resource_format = normalize_ckan_format(str(resource.get("format") or ""))
            name = resource.get("name") or resource.get("description") or resource.get("id") or "resource"
            reason = None
            if resource_id and resource.get("id") != resource_id:
                reason = "resource_id_mismatch"
            elif regex and not regex.search(name):
                reason = "resource_name_regex_mismatch"
            elif source.formats and resource_format not in {item.lower().lstrip(".") for item in source.formats}:
                reason = "format_not_expected"
            if reason:
                rejected.append({"package_id": package_id, "id": resource.get("id"), "name": name, "url": resource.get("url"), "reason": reason})
                continue
            url = resource.get("url")
            if not url:
                rejected.append({"package_id": package_id, "id": resource.get("id"), "name": name, "reason": "missing_url"})
                continue
            filename = filename_from_url(url, f"{safe_filename(package_id)}__{safe_filename(name)}.{resource_format or 'dat'}")
            period = infer_financial_year(f"{name} {package.get('title', '')} {url}")
            accepted.append(
                Asset(
                    source_id=source.id,
                    asset_instance_id=f"{source.id}:{package_id}:{safe_filename(resource.get('id') or name)}",
                    requested_url=url,
                    title=f"{package.get('title') or package_id} — {name}",
                    expected_formats=source.formats,
                    financial_year=period,
                    filename_hint=filename,
                    discovery_url=discovery_url,
                    metadata={
                        "adapter": "ckan",
                        "package_id": package_id,
                        "resource_id": resource.get("id"),
                        "resource_format": resource_format,
                    },
                )
            )
        return accepted, rejected
