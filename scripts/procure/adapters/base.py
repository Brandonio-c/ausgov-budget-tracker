"""Base adapter and the single validated asset-fetch implementation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from ..http_client import DownloadTooLarge, HTTPClient, HTTPFailure
from ..models import AcquisitionResult, Asset, RunContext, Source, Status
from ..storage import DiskBudget, SnapshotStore, safe_filename
from ..validation import validate_file


@dataclass(slots=True)
class AdapterContext:
    run: RunContext
    http: HTTPClient
    store: SnapshotStore
    budget: DiskBudget


class Adapter(Protocol):
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]: ...
    def fetch(self, source: Source, asset: Asset, context: AdapterContext) -> AcquisitionResult: ...


def _content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", value, re.I)
    return safe_filename(match.group(1).strip()) if match else None


class BaseAdapter:
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]:
        raise NotImplementedError

    def fetch(self, source: Source, asset: Asset, context: AdapterContext) -> AcquisitionResult:
        retrieved_at = datetime.now(timezone.utc).isoformat()
        if context.run.dry_run or context.run.discover_only:
            return AcquisitionResult(
                source_id=source.id,
                status=Status.DISCOVERED_ONLY,
                asset_instance_id=asset.asset_instance_id,
                requested_url=asset.requested_url,
                financial_year=asset.financial_year,
                retrieved_at=retrieved_at,
            )

        per_source_max = source.validation.get("max_bytes")
        max_bytes = min(context.run.max_file_bytes, per_source_max) if per_source_max else context.run.max_file_bytes
        claimed = max_bytes
        if not context.budget.claim(None, max_bytes):
            return AcquisitionResult(
                source_id=source.id,
                status=Status.DEFERRED_LARGE_VOLUME,
                asset_instance_id=asset.asset_instance_id,
                requested_url=asset.requested_url,
                financial_year=asset.financial_year,
                retrieved_at=retrieved_at,
                error_type="disk_budget",
                error_message="safe run byte budget exhausted",
            )

        part = context.store.part_path(source, asset)
        try:
            response = context.http.download(asset.requested_url, part, max_bytes=max_bytes)
            actual = part.stat().st_size if part.exists() else 0
            context.budget.settle(claimed, actual)
            filename = (
                _content_disposition_filename(response.headers.get("content-disposition"))
                or asset.filename_hint
                or Path(response.final_url.split("?", 1)[0]).name
                or asset.asset_instance_id
            )
            context.store.write_headers(source, asset.asset_instance_id, response.headers)
            validation = validate_file(
                part,
                asset.expected_formats,
                min_bytes=int(source.validation.get("min_bytes", 1)),
                max_bytes=max_bytes,
            )
            if not validation.valid:
                stored = context.store.quarantine(source, asset, part, validation)
                challenge = "challenge" in (validation.error or "").lower() or "captcha" in (validation.error or "").lower()
                return AcquisitionResult(
                    source_id=source.id,
                    status=Status.BLOCKED_CAPTCHA_OR_WAF if challenge else Status.INVALID_CONTENT,
                    asset_instance_id=asset.asset_instance_id,
                    requested_url=asset.requested_url,
                    final_url=response.final_url,
                    redirect_chain=response.redirect_chain,
                    stored_path=stored,
                    original_filename=filename,
                    bytes=actual,
                    http_status=response.status,
                    response_mime=response.headers.get("content-type"),
                    detected_type=validation.detected_type,
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                    retrieved_at=retrieved_at,
                    validation_status=validation.status,
                    validation_warnings=validation.warnings,
                    financial_year=asset.financial_year,
                    retry_count=response.retries,
                    error_type="content_validation",
                    error_message=validation.error,
                )
            digest, stored, unchanged = context.store.commit_validated(source, asset, part, filename)
            return AcquisitionResult(
                source_id=source.id,
                status=Status.UNCHANGED if unchanged else Status.DOWNLOADED,
                asset_instance_id=asset.asset_instance_id,
                requested_url=asset.requested_url,
                final_url=response.final_url,
                redirect_chain=response.redirect_chain,
                stored_path=stored,
                original_filename=filename,
                stored_filename=Path(stored).name,
                bytes=actual,
                sha256=digest,
                http_status=response.status,
                response_mime=response.headers.get("content-type"),
                detected_type=validation.detected_type,
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
                retrieved_at=retrieved_at,
                validation_status=validation.status,
                validation_warnings=validation.warnings,
                financial_year=asset.financial_year,
                retry_count=response.retries,
                metadata=asset.metadata,
            )
        except DownloadTooLarge as error:
            context.budget.settle(claimed, part.stat().st_size if part.exists() else 0)
            return AcquisitionResult(
                source_id=source.id,
                status=Status.DEFERRED_LARGE_VOLUME,
                asset_instance_id=asset.asset_instance_id,
                requested_url=asset.requested_url,
                retrieved_at=retrieved_at,
                financial_year=asset.financial_year,
                error_type=type(error).__name__,
                error_message=str(error),
            )
        except HTTPFailure as error:
            context.budget.settle(claimed, part.stat().st_size if part.exists() else 0)
            if error.status in {401, 403}:
                status = Status.BLOCKED_AUTH
            elif error.status:
                status = Status.HTTP_ERROR
            else:
                status = Status.NETWORK_ERROR
            return AcquisitionResult(
                source_id=source.id,
                status=status,
                asset_instance_id=asset.asset_instance_id,
                requested_url=asset.requested_url,
                retrieved_at=retrieved_at,
                financial_year=asset.financial_year,
                retryable=error.retryable,
                retry_count=error.retries,
                http_status=error.status,
                error_type=type(error).__name__,
                error_message=str(error),
            )
