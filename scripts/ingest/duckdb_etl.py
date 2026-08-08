#!/usr/bin/env python3
"""DuckDB extract/transform for mapping YAML → normalised fact rows."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Mapping must be a mapping document: {path}")
    if "extends" in data:
        base_path = (path.parent / data["extends"]).resolve()
        base = load_mapping(base_path)
        merged = {**base, **{k: v for k, v in data.items() if k != "extends"}}
        for key in ("input", "columns", "attribution"):
            if key in base and key in data and isinstance(data[key], dict):
                merged[key] = {**base.get(key, {}), **data[key]}
        data = merged
    data["_mapping_path"] = str(path)
    return data


def resolve_input_path(mapping: dict[str, Any], repo_root: Path = REPO_ROOT) -> Path:
    raw = mapping["input"]["path"]
    p = Path(raw)
    if not p.is_absolute():
        p = repo_root / p
    return p.resolve()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_rows(mapping: dict[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Read source file via DuckDB and project logical columns."""
    src = resolve_input_path(mapping, repo_root)
    if not src.is_file():
        raise FileNotFoundError(f"Input not found: {src}")

    fmt = mapping["input"].get("format", src.suffix.lstrip(".")).lower()
    con = duckdb.connect()
    try:
        if fmt == "csv":
            con.execute(
                f"CREATE VIEW raw AS SELECT * FROM read_csv_auto('{src.as_posix()}', header=true)"
            )
        elif fmt == "parquet":
            con.execute(
                f"CREATE VIEW raw AS SELECT * FROM read_parquet('{src.as_posix()}')"
            )
        elif fmt in {"excel", "xlsx", "xls"}:
            sheet = mapping["input"].get("sheet")
            import pandas as pd

            df = pd.read_excel(src, sheet_name=sheet or 0)
            con.register("raw", df)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        cols = mapping["columns"]
        select_parts = []
        for logical, physical in cols.items():
            if isinstance(physical, str) and physical.startswith("literal:"):
                lit = physical.split(":", 1)[1].replace("'", "''")
                select_parts.append(f"'{lit}' AS {logical}")
            else:
                select_parts.append(f'"{physical}" AS {logical}')
        sql = f"SELECT {', '.join(select_parts)} FROM raw"
        rel = con.execute(sql).fetchdf()
    finally:
        con.close()

    attribution = mapping.get("attribution", {})
    cached = attribution.get("cached_copy_path")
    cached_by_year = attribution.get("cached_copy_path_by_financial_year") or {}
    if cached_by_year and not isinstance(cached_by_year, dict):
        raise ValueError("cached_copy_path_by_financial_year must be a mapping")
    fallback_cached = cached or mapping["input"]["path"]
    cached_path = resolve_input_path(
        {"input": {"path": fallback_cached}}, repo_root
    )
    sha = file_sha256(cached_path)
    retrieved_at = _utc_now()

    # A source_family covering many distinct source documents (e.g. one row per
    # portfolio PBS PDF) needs a per-row cached copy + hash, not one fixed value
    # for every row - confirmed as a real citation bug on pbs_programs_all,
    # which was stamping every one of 63 different portfolios' facts with the
    # same single Treasury PDF's path and hash. Opt in via
    # attribution.cached_copy_path_column (mirrors landing_url_column /
    # original_resource_url_column below); every other mapping keeps the
    # existing single-file behaviour unchanged.
    per_row_path_column = mapping.get("attribution", {}).get("cached_copy_path_column")
    sha_cache: dict[str, str] = {}

    rows: list[dict[str, Any]] = []
    for _, series in rel.iterrows():
        row = {k: (None if (isinstance(v, float) and v != v) else v) for k, v in series.items()}
        for key in ("landing_url", "original_resource_url", "locator"):
            if key in row and isinstance(row[key], str) and not row[key].strip():
                row[key] = None
        row["_source_id"] = mapping["source_id"]
        row["_measure_type"] = mapping["measure_type"]
        row["_accounting_basis"] = mapping["accounting_basis"]
        row_status = row.get("estimate_status")
        if isinstance(row_status, str) and row_status.strip():
            row["_estimate_status"] = row_status.strip()
        else:
            row["_estimate_status"] = mapping["estimate_status"]
        row["_period_granularity"] = mapping["period_granularity"]

        row_cached_path = cached_path
        row_sha = sha
        configured_year_path = cached_by_year.get(str(row.get("financial_year") or ""))
        if configured_year_path:
            resolved = resolve_input_path(
                {"input": {"path": str(configured_year_path)}}, repo_root
            )
            if not resolved.is_file():
                raise FileNotFoundError(resolved)
            row_cached_path = resolved
            row_sha = sha_cache.setdefault(str(resolved), file_sha256(resolved))
        if per_row_path_column:
            raw_path = row.get(per_row_path_column)
            if isinstance(raw_path, str) and raw_path.strip():
                resolved = resolve_input_path({"input": {"path": raw_path.strip()}}, repo_root)
                if resolved.is_file():
                    row_cached_path = resolved
                    row_sha = sha_cache.setdefault(str(resolved), file_sha256(resolved))

        row["_sha256"] = row_sha
        row["_retrieved_at"] = retrieved_at
        row["_cached_copy_path"] = str(row_cached_path)
        row["_local_path"] = str(src)

        attr = mapping.get("attribution", {})
        if "landing_url" in attr and "landing_url_column" not in attr:
            row["landing_url"] = attr["landing_url"]
        if "original_resource_url" in attr and "original_resource_url_column" not in attr:
            row["original_resource_url"] = attr["original_resource_url"]

        rows.append(row)
    return rows


def build_fact_key(mapping: dict[str, Any], row: dict[str, Any]) -> str:
    template = mapping.get(
        "fact_key_template",
        "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}",
    )
    ctx = {
        "source_id": mapping["source_id"],
        "measure_type": mapping["measure_type"],
        "estimate_status": row.get("_estimate_status") or mapping["estimate_status"],
        "financial_year": row.get("financial_year"),
        "node_name": row.get("node_name") or row.get("category") or "",
        **{k: v for k, v in row.items() if not k.startswith("_")},
    }
    return template.format(**ctx)
