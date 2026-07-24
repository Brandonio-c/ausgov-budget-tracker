"""Shared ABS GFS Table_4 (expenses) + Table_3 (balance sheet liabilities) melt."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
FY_RE = re.compile(r"^\d{4}-\d{2}$")

# Liability lines kept from Table_3 (skip assets / net worth / section headers).
LIABILITY_KEEP = frozenset(
    {
        "Currency and deposits",
        "Advances",
        "Other loans and placements",
        "Debt securities",
        "Provisions for defined benefit superannuation",
        "Other liabilities",
        "Total Liabilities",
    }
)

JURISDICTION_MAP = {
    "abs_gfs_commonwealth_130": ("Commonwealth", "federal", "national"),
    "abs_gfs_state_nsw_231": ("NSW", "state", "state"),
    "abs_gfs_state_vic_232": ("VIC", "state", "state"),
    "abs_gfs_state_qld_233": ("QLD", "state", "state"),
    "abs_gfs_state_sa_234": ("SA", "state", "state"),
    "abs_gfs_state_wa_235": ("WA", "state", "state"),
    "abs_gfs_state_tas_236": ("TAS", "state", "state"),
    "abs_gfs_state_nt_237": ("NT", "territory", "territory"),
    "abs_gfs_state_act_238": ("ACT", "territory", "territory"),
    "abs_gfs_local_nsw_331": ("NSW", "local", "local"),
    "abs_gfs_local_vic_332": ("VIC", "local", "local"),
    "abs_gfs_local_qld_333": ("QLD", "local", "local"),
    "abs_gfs_local_sa_334": ("SA", "local", "local"),
    "abs_gfs_local_wa_335": ("WA", "local", "local"),
    "abs_gfs_local_tas_336": ("TAS", "local", "local"),
    "abs_gfs_local_nt_337": ("NT", "local", "local"),
}


def resolve_stored_path(source_dir: Path) -> tuple[Path, dict[str, Any]]:
    data = json.loads((source_dir / "latest.json").read_text(encoding="utf-8"))
    asset = data["assets"][0]
    stored = Path(asset["stored_path"])
    fp = REPO_ROOT / "data" / stored if not stored.is_absolute() else stored
    if not fp.exists():
        fp = REPO_ROOT / stored
    return fp, asset


def _find_fy_header(df: pd.DataFrame, sheet_label: str, path: Path) -> tuple[int, list[str], list[int]]:
    header_idx = None
    for i in range(min(15, len(df))):
        vals = [str(v).strip() for v in df.iloc[i].tolist() if pd.notna(v)]
        if sum(1 for v in vals if FY_RE.match(v)) >= 2:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"No FY header in {sheet_label}: {path}")

    years: list[str] = []
    year_cols: list[int] = []
    for j, v in enumerate(df.iloc[header_idx].tolist()):
        if isinstance(v, str) and FY_RE.match(v.strip()):
            years.append(v.strip())
            year_cols.append(j)
        elif FY_RE.match(str(v).strip()) if pd.notna(v) else False:
            years.append(str(v).strip())
            year_cols.append(j)
    return header_idx, years, year_cols


def melt_table4(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Table_4", header=None)
    header_idx, years, year_cols = _find_fy_header(df, "Table_4", path)

    rows = []
    for i in range(header_idx + 1, len(df)):
        label = df.iloc[i, 0]
        if pd.isna(label):
            continue
        label = str(label).strip()
        if not label or label.lower().startswith("released"):
            continue
        amounts = [df.iloc[i, j] for j in year_cols]
        if all(pd.isna(a) for a in amounts):
            continue
        for fy, j in zip(years, year_cols):
            val = df.iloc[i, j]
            if pd.isna(val):
                continue
            try:
                amount_m = float(val)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "fy": fy,
                    "category": label,
                    "amount": amount_m * 1_000_000,  # $m → AUD
                    "locator": f"sheet:Table_4 | purpose:{label} | fy:{fy} | unit:$m",
                }
            )
    return pd.DataFrame(rows)


def melt_table3_liabilities(path: Path) -> pd.DataFrame:
    """Melt ABS GFS Table_3 balance-sheet liability lines (end-of-year stocks)."""
    df = pd.read_excel(path, sheet_name="Table_3", header=None)
    header_idx, years, year_cols = _find_fy_header(df, "Table_3", path)

    rows = []
    in_liabilities = False
    for i in range(header_idx + 1, len(df)):
        label = df.iloc[i, 0]
        if pd.isna(label):
            continue
        label = str(label).strip()
        if not label or label.lower().startswith("released"):
            continue
        low = label.lower()
        if low == "liabilities":
            in_liabilities = True
            continue
        if low in {"equals", "assets"} or low.startswith("gfs net") or low.startswith("net financial"):
            in_liabilities = False
            continue
        if not in_liabilities:
            continue
        # Normalise whitespace that ABS sometimes pads into labels.
        label = re.sub(r"\s+", " ", label).strip()
        if label not in LIABILITY_KEEP:
            continue
        amounts = [df.iloc[i, j] for j in year_cols]
        if all(pd.isna(a) for a in amounts):
            continue
        for fy, j in zip(years, year_cols):
            val = df.iloc[i, j]
            if pd.isna(val):
                continue
            try:
                amount_m = float(val)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "fy": fy,
                    "category": label,
                    "amount": amount_m * 1_000_000,  # $m → AUD
                    "locator": f"sheet:Table_3 | liability:{label} | fy:{fy} | unit:$m",
                }
            )
    return pd.DataFrame(rows)


def _export_melted(
    source_id: str,
    staging_dir: Path,
    melted: pd.DataFrame,
    out_name: str | None = None,
) -> dict[str, Any]:
    matches = list((REPO_ROOT / "data" / "raw").rglob(source_id))
    matches = [m for m in matches if m.is_dir() and (m / "latest.json").exists()]
    if not matches:
        raise FileNotFoundError(source_id)
    source_dir = matches[0]
    fp, asset = resolve_stored_path(source_dir)
    juris, gov_level, _ = JURISDICTION_MAP[source_id]
    landing = (
        "https://www.abs.gov.au/statistics/economy/government/"
        "government-finance-statistics-annual/latest-release"
    )
    resource = asset.get("final_url") or asset.get("requested_url") or landing
    melted = melted.copy()
    melted["landing_url"] = landing
    melted["resource_url"] = resource
    staging_dir.mkdir(parents=True, exist_ok=True)
    out = staging_dir / (out_name or f"{source_id}.csv")
    melted.to_csv(out, index=False)
    return {
        "source_id": source_id,
        "path": out,
        "rows": len(melted),
        "cached_copy_path": str(fp.relative_to(REPO_ROOT)),
        "jurisdiction": juris,
        "government_level": gov_level,
        "landing_url": landing,
        "resource_url": resource,
        "file": str(fp),
    }


def export_source(source_id: str, staging_dir: Path) -> dict[str, Any]:
    matches = list((REPO_ROOT / "data" / "raw").rglob(source_id))
    matches = [m for m in matches if m.is_dir() and (m / "latest.json").exists()]
    if not matches:
        raise FileNotFoundError(source_id)
    fp, _ = resolve_stored_path(matches[0])
    return _export_melted(source_id, staging_dir, melt_table4(fp))


def export_liabilities(source_id: str, staging_dir: Path) -> dict[str, Any]:
    """Export Table_3 liability stocks; staging/mapping use a distinct source_id."""
    matches = list((REPO_ROOT / "data" / "raw").rglob(source_id))
    matches = [m for m in matches if m.is_dir() and (m / "latest.json").exists()]
    if not matches:
        raise FileNotFoundError(source_id)
    fp, _ = resolve_stored_path(matches[0])
    liab_id = f"{source_id}_liabilities"
    meta = _export_melted(
        source_id,
        staging_dir,
        melt_table3_liabilities(fp),
        out_name=f"{liab_id}.csv",
    )
    meta["source_id"] = liab_id
    meta["base_source_id"] = source_id
    return meta
