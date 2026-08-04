"""Central safe HTTP behavior for discovery and streamed downloads."""

from __future__ import annotations

import email.utils
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

RETRY_CODES = {429, 500, 502, 503, 504}
SAFE_HEADERS = {
    "content-type", "content-length", "content-disposition", "etag",
    "last-modified", "accept-ranges", "date", "server", "retry-after",
}


class DownloadTooLarge(RuntimeError):
    pass


class HTTPFailure(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, retryable: bool = False, retries: int = 0):
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.retries = retries


@dataclass(slots=True)
class HTTPResponse:
    status: int
    requested_url: str
    final_url: str
    redirect_chain: list[str]
    headers: dict[str, str]
    retries: int
    body: bytes | None = None
    path: Path | None = None


class HTTPClient:
    def __init__(
        self,
        *,
        connect_timeout: float = 10,
        read_timeout: float = 120,
        retries: int = 4,
        per_domain: int = 2,
        user_agent: str = "AusGovBudgetTracker-Procurement/0.1 (+https://github.com/Brandonio-c/ausgov-budget-tracker; contact=project-maintainer)",
    ):
        self.timeout = (connect_timeout, read_timeout)
        self.retries = retries
        self.per_domain = per_domain
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "*/*"})
        self._locks: dict[str, threading.BoundedSemaphore] = {}
        self._lock = threading.Lock()

    def _domain_lock(self, url: str) -> threading.BoundedSemaphore:
        domain = (urlparse(url).hostname or "").lower()
        with self._lock:
            return self._locks.setdefault(domain, threading.BoundedSemaphore(self.per_domain))

    @staticmethod
    def safe_headers(headers: requests.structures.CaseInsensitiveDict) -> dict[str, str]:
        return {key.lower(): value for key, value in headers.items() if key.lower() in SAFE_HEADERS}

    @staticmethod
    def _retry_delay(response: requests.Response | None, attempt: int) -> float:
        if response is not None and response.headers.get("Retry-After"):
            value = response.headers["Retry-After"]
            try:
                return min(120.0, float(value))
            except ValueError:
                try:
                    parsed = email.utils.parsedate_to_datetime(value).timestamp() - time.time()
                    return max(0.0, min(120.0, parsed))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(30.0, (2**attempt) + random.uniform(0, 1))

    def _request(self, method: str, url: str, **kwargs) -> tuple[requests.Response, int]:
        last_error: Exception | None = None
        lock = self._domain_lock(url)
        for attempt in range(self.retries + 1):
            response: requests.Response | None = None
            try:
                with lock:
                    response = self.session.request(
                        method, url, timeout=self.timeout, allow_redirects=True, **kwargs
                    )
                if response.status_code not in RETRY_CODES:
                    return response, attempt
                if attempt >= self.retries:
                    raise HTTPFailure(
                        f"HTTP {response.status_code} after {attempt} retries",
                        status=response.status_code,
                        retryable=True,
                        retries=attempt,
                    )
            except (requests.Timeout, requests.ConnectionError) as error:
                last_error = error
                if attempt >= self.retries:
                    raise HTTPFailure(
                        f"{type(error).__name__}: {error}",
                        retryable=True,
                        retries=attempt,
                    ) from error
            time.sleep(self._retry_delay(response, attempt))
        raise HTTPFailure(str(last_error or "request failed"), retryable=True, retries=self.retries)

    def head(self, url: str, *, headers: dict[str, str] | None = None) -> HTTPResponse:
        response, retries = self._request("HEAD", url, headers=headers or {})
        return HTTPResponse(
            response.status_code,
            url,
            response.url,
            [item.url for item in response.history] + [response.url],
            self.safe_headers(response.headers),
            retries,
        )

    def get_bytes(self, url: str, *, max_bytes: int = 20 * 1024**2, headers: dict[str, str] | None = None) -> HTTPResponse:
        response, retries = self._request("GET", url, headers=headers or {}, stream=True)
        if response.status_code >= 400:
            raise HTTPFailure(f"HTTP {response.status_code}", status=response.status_code, retries=retries)
        content = bytearray()
        for chunk in response.iter_content(128 * 1024):
            content.extend(chunk)
            if len(content) > max_bytes:
                raise DownloadTooLarge(f"response exceeds discovery limit {max_bytes}")
        return HTTPResponse(
            response.status_code,
            url,
            response.url,
            [item.url for item in response.history] + [response.url],
            self.safe_headers(response.headers),
            retries,
            body=bytes(content),
        )

    def download(
        self,
        url: str,
        destination_part: Path,
        *,
        max_bytes: int,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        request_headers = dict(headers or {})
        existing = destination_part.stat().st_size if destination_part.exists() else 0
        if existing:
            request_headers["Range"] = f"bytes={existing}-"
        response, retries = self._request("GET", url, headers=request_headers, stream=True)
        if response.status_code >= 400:
            raise HTTPFailure(f"HTTP {response.status_code}", status=response.status_code, retries=retries)
        append = existing > 0 and response.status_code == 206
        if not append:
            existing = 0
        content_length = response.headers.get("Content-Length")
        if content_length and existing + int(content_length) > max_bytes:
            raise DownloadTooLarge(f"declared response exceeds {max_bytes} bytes")
        destination_part.parent.mkdir(parents=True, exist_ok=True)
        mode = "ab" if append else "wb"
        written = existing
        with destination_part.open(mode) as handle:
            for chunk in response.iter_content(1024 * 1024):
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    raise DownloadTooLarge(f"stream exceeds {max_bytes} bytes")
                handle.write(chunk)
            handle.flush()
        return HTTPResponse(
            response.status_code,
            url,
            response.url,
            [item.url for item in response.history] + [response.url],
            self.safe_headers(response.headers),
            retries,
            path=destination_part,
        )
