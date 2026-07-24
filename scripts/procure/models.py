"""Typed contracts shared by procurement adapters and reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class AccessType(str, Enum):
    DIRECT_FILE = "direct_file"
    CKAN_API = "ckan_api"
    SOCRATA_API = "socrata_api"
    OCDS_API = "ocds_api"
    LANDING_PAGE = "landing_page_discovery"
    WEB_PORTAL = "web_portal"
    MANUAL = "manual"


class Status(str, Enum):
    DOWNLOADED = "downloaded"
    UNCHANGED = "unchanged"
    PARTIAL = "partial"
    DISCOVERED_ONLY = "discovered_only"
    MANUAL_REQUIRED = "manual_required"
    BROWSER_REQUIRED = "browser_required"
    FLAKY_UNRELIABLE = "flaky_unreliable"
    BLOCKED_AUTH = "blocked_auth"
    BLOCKED_CAPTCHA_OR_WAF = "blocked_captcha_or_waf"
    NO_PUBLIC_BULK_EXPORT = "no_public_bulk_export"
    NOT_FOUND = "not_found"
    DEFERRED_LARGE_VOLUME = "deferred_large_volume"
    INVALID_CONTENT = "invalid_content"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    REGISTRY_ERROR = "registry_error"
    SKIPPED_DISABLED = "skipped_disabled"


SUCCESS_STATUSES = {Status.DOWNLOADED, Status.UNCHANGED}
RETRYABLE_STATUSES = {Status.HTTP_ERROR, Status.TIMEOUT, Status.NETWORK_ERROR}


@dataclass(slots=True)
class Source:
    id: str
    priority: str
    publisher: str
    jurisdiction: str
    government_level: str
    source_family: str
    title: str
    landing_url: str
    resource_url: str | None
    access_method: AccessType
    automation: str
    formats: list[str]
    enabled: bool = True
    access: dict[str, Any] = field(default_factory=dict)
    storage: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    manual: dict[str, Any] = field(default_factory=dict)
    research: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Asset:
    source_id: str
    asset_instance_id: str
    requested_url: str
    title: str
    expected_formats: list[str]
    financial_year: str | None = None
    filename_hint: str | None = None
    discovery_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    detected_type: str
    status: str
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class AcquisitionResult:
    source_id: str
    status: Status
    asset_instance_id: str | None = None
    requested_url: str | None = None
    final_url: str | None = None
    redirect_chain: list[str] = field(default_factory=list)
    stored_path: str | None = None
    original_filename: str | None = None
    stored_filename: str | None = None
    bytes: int = 0
    sha256: str | None = None
    http_status: int | None = None
    response_mime: str | None = None
    detected_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    retrieved_at: str | None = None
    validation_status: str | None = None
    validation_warnings: list[str] = field(default_factory=list)
    financial_year: str | None = None
    retryable: bool = False
    retry_count: int = 0
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


@dataclass(slots=True)
class SourceResult:
    source_id: str
    status: Status
    priority: str
    publisher: str
    jurisdiction: str
    government_level: str
    source_family: str
    access_method: str
    automation: str
    landing_url: str
    attempted_urls: list[str] = field(default_factory=list)
    discovered_asset_count: int = 0
    downloaded_file_count: int = 0
    unchanged_file_count: int = 0
    failed_asset_count: int = 0
    bytes: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    retry_count: int = 0
    manual_reason: str | None = None
    manual_instructions_path: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    retryable: bool = False
    assets: list[AcquisitionResult] = field(default_factory=list)

    def as_dict(self, include_assets: bool = False) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        if include_assets:
            value["assets"] = [asset.as_dict() for asset in self.assets]
        else:
            value.pop("assets", None)
        return value


@dataclass(slots=True)
class RunContext:
    run_id: str
    repo_root: Path
    data_root: Path
    reports_root: Path
    git_commit: str
    git_dirty: bool
    max_total_bytes: int
    max_file_bytes: int
    dry_run: bool = False
    discover_only: bool = False
    browser_fallback: bool = True
