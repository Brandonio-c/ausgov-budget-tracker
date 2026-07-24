"""Content validation that never trusts a URL suffix or HTTP status alone."""

from __future__ import annotations

import csv
import gzip
import json
import re
import zipfile
from pathlib import Path

import openpyxl

from .models import ValidationResult


HTML_MARKERS = (
    b"<!doctype html", b"<html", b"<head", b"<body", b"<script",
)
CHALLENGE_MARKERS = (
    b"captcha", b"access denied", b"cloudflare", b"verify you are human",
    b"bot challenge", b"request blocked", b"sign in", b"log in",
)
EXECUTABLE_MARKERS = (b"MZ", b"\x7fELF")
OFFICE_CONTENT_TYPES = "[Content_Types].xml"


def detect_type(path: Path) -> str:
    head = path.read_bytes()[:8192]
    lower = head.lower().lstrip()
    if any(head.startswith(marker) for marker in EXECUTABLE_MARKERS):
        return "executable"
    if head.startswith(b"\x1f\x8b"):
        return "gz"
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if OFFICE_CONTENT_TYPES not in names:
                    return "zip"
                # xlsx/docx/pptx are all OOXML zips sharing [Content_Types].xml -
                # that alone doesn't tell them apart, and previously anything with
                # it was called "xlsx" even when it was really a Word/PowerPoint
                # file, which then failed hard when force-fed to openpyxl.
                if "xl/workbook.xml" in names:
                    return "xlsx"
                if "word/document.xml" in names:
                    return "docx"
                if "ppt/presentation.xml" in names:
                    return "pptx"
                return "zip"
        except zipfile.BadZipFile:
            return "invalid_zip"
    if any(lower.startswith(marker) for marker in HTML_MARKERS):
        return "html"
    text = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = head.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return "binary"
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")):
        return "json"
    if "\t" in text:
        return "tsv"
    if "," in text or "\n" in text:
        return "csv"
    return "text"


def _validate_zip(path: Path, *, max_uncompressed: int, max_ratio: int = 300) -> list[str]:
    # Real xlsx files from government reporting templates can carry a bloated but
    # entirely legitimate xl/styles.xml (thousands of near-duplicate style defs)
    # that alone compresses over 100:1 - confirmed on a real NDIS dataset file.
    # The actual zip-bomb defense is max_uncompressed (the absolute total below),
    # which this ratio check is secondary to, so it can afford to be less strict.
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > 100_000:
            raise ValueError("ZIP contains more than 100,000 members")
        total = 0
        for member in members:
            normalized = Path(member.filename.replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ValueError(f"unsafe ZIP member path: {member.filename}")
            total += member.file_size
            if total > max_uncompressed:
                raise ValueError("ZIP uncompressed size exceeds safety limit")
            if member.compress_size and member.file_size / member.compress_size > max_ratio:
                raise ValueError(f"ZIP expansion ratio exceeds {max_ratio}:1")
        corrupt = archive.testzip()
        if corrupt:
            raise ValueError(f"ZIP CRC failure: {corrupt}")
        if not members:
            warnings.append("ZIP archive is empty")
    return warnings


def _validate_pdf(path: Path) -> list[str]:
    warnings: list[str] = []
    try:
        from pypdf import PdfReader
    except ImportError:
        if b"%%EOF" not in path.read_bytes()[-4096:]:
            raise ValueError("PDF EOF marker is missing")
        warnings.append("pypdf unavailable; used signature and EOF validation")
        return warnings
    reader = PdfReader(path, strict=False)
    if reader.is_encrypted:
        # Government PDFs are commonly owner-password-restricted (blocks
        # editing/printing) while remaining freely readable with no user
        # password - try the empty password before giving up.
        if reader.decrypt("") == 0:
            raise ValueError("PDF requires a password to read (not just owner-restricted)")
        warnings.append("PDF is owner-password-restricted; opened read-only with an empty user password")
    if len(reader.pages) < 1:
        raise ValueError("PDF has no readable pages")
    return warnings


def _open_text(path: Path):
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        return path.open("r", encoding=encoding, errors="strict", newline="")
    return path.open("r", encoding="utf-8-sig", errors="replace", newline="")


def _validate_delimited(path: Path, delimiter: str) -> list[str]:
    with _open_text(path) as handle:
        rows = csv.reader(handle, delimiter=delimiter)
        first = next(rows, None)
        if not first or not any(str(value).strip() for value in first):
            raise ValueError("delimited file contains no non-empty records")
    return []


def _validate_gzip(path: Path) -> list[str]:
    with gzip.open(path, "rb") as handle:
        chunk = handle.read(8192)
    if not chunk:
        raise ValueError("gzip archive is empty")
    return []


def validate_file(
    path: Path,
    expected_formats: list[str],
    *,
    min_bytes: int = 1,
    max_bytes: int | None = None,
    max_zip_uncompressed: int = 10 * 1024**3,
) -> ValidationResult:
    size = path.stat().st_size
    detected = detect_type(path)
    expected = {item.lower().lstrip(".") for item in expected_formats}
    try:
        if size < min_bytes:
            raise ValueError(f"file is smaller than minimum {min_bytes} bytes")
        if max_bytes is not None and size > max_bytes:
            raise ValueError(f"file exceeds configured maximum {max_bytes} bytes")
        if detected == "executable":
            raise ValueError("executable payload rejected")
        if detected in {"invalid_zip", "binary", "text"}:
            raise ValueError(f"unrecognized or invalid content: {detected}")
        if detected == "html":
            sample = path.read_bytes()[:128_000].lower()
            if any(marker in sample for marker in CHALLENGE_MARKERS):
                raise ValueError("HTML login, access-denied, CAPTCHA, or challenge page detected")
            if "html" not in expected and "web" not in expected:
                raise ValueError("HTML returned where a data/document file was expected")

        warnings: list[str] = []
        compatible = detected in expected or (detected == "tsv" and "csv" in expected) or (
            detected == "gz" and expected.intersection({"gz", "jsonl", "json"})
        )
        if not compatible and expected and not expected.intersection({"download", "dashboard", "export"}):
            warnings.append(f"detected {detected}; registry expected {sorted(expected)}")

        if detected == "pdf":
            warnings.extend(_validate_pdf(path))
        elif detected in {"zip", "xlsx", "docx", "pptx"}:
            warnings.extend(_validate_zip(path, max_uncompressed=max_zip_uncompressed))
            if detected == "xlsx":
                # openpyxl gates format support on the filename suffix unless given a
                # file-like object; the staged download is a `.part` path, so it must
                # be opened as a stream here or every real xlsx fails validation.
                with path.open("rb") as handle:
                    workbook = openpyxl.load_workbook(handle, read_only=True, data_only=False)
                    if not workbook.sheetnames:
                        raise ValueError("XLSX has no worksheets")
                    workbook.close()
        elif detected == "xls":
            pass
        elif detected == "csv":
            warnings.extend(_validate_delimited(path, ","))
        elif detected == "tsv":
            warnings.extend(_validate_delimited(path, "\t"))
        elif detected == "json":
            with path.open("r", encoding="utf-8-sig") as handle:
                json.load(handle)
        elif detected == "gz":
            warnings.extend(_validate_gzip(path))
        elif detected == "html":
            if not re.search(br"<(?:html|body|a|main)\b", path.read_bytes()[:128_000], re.I):
                raise ValueError("declared HTML has no recognizable document structure")

        return ValidationResult(True, detected, "valid", warnings)
    except Exception as error:  # noqa: BLE001 - untrusted external content; any parse failure is "invalid", never a crash
        return ValidationResult(False, detected, "invalid", error=f"{type(error).__name__}: {error}")
