"""AOFM Commonwealth Government Securities portfolio melts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]

# Instrument line books only — portfolio aggregate duplicates these totals.
INSTRUMENT_SOURCES = {
    "aofm_treasury_bonds_dealt": "Treasury Bonds",
    "aofm_treasury_indexed_bonds_dealt": "Treasury Indexed Bonds",
    "aofm_treasury_notes_dealt": "Treasury Notes",
}


def resolve_latest(source_id: str) -> tuple[Path, dict[str, Any]]:
    matches = [
        m
        for m in (REPO_ROOT / "data" / "raw").rglob(source_id)
        if m.is_dir() and (m / "latest.json").exists()
    ]
    if not matches:
        raise FileNotFoundError(source_id)
    data = json.loads((matches[0] / "latest.json").read_text(encoding="utf-8"))
    asset = data["assets"][0]
    stored = Path(asset["stored_path"])
    fp = REPO_ROOT / "data" / stored if not stored.is_absolute() else stored
    if not fp.exists():
        fp = REPO_ROOT / stored
    if not fp.exists():
        cands = list(matches[0].rglob("*.xlsx")) + list(matches[0].rglob("*.csv"))
        if not cands:
            raise FileNotFoundError(fp)
        fp = cands[0]
    return fp, asset


def _fy_from_dt(dt: pd.Timestamp) -> str:
    y = dt.year if dt.month >= 7 else dt.year - 1
    return f"{y}-{str(y + 1)[-2:]}"


def _latest_date_row(df: pd.DataFrame, data_start: int) -> int | None:
    for i in range(len(df) - 1, data_start - 1, -1):
        dt = pd.to_datetime(df.iloc[i, 0], errors="coerce")
        if pd.isna(dt):
            continue
        nums = pd.to_numeric(df.iloc[i, 1:], errors="coerce")
        if nums.notna().any():
            return i
    return None


def melt_facevalue_sheet(path: Path, instrument: str) -> pd.DataFrame:
    """Melt AOFM FaceValue tab (dealt face value). Prefer liability (negative) cells."""
    xl = pd.ExcelFile(path)
    sheet = "FaceValue" if "FaceValue" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet, header=None)

    # Layout A: maturity columns (Treasury Bonds / TIBs / Notes line books)
    mat_row = None
    for i in range(min(20, len(df))):
        if str(df.iloc[i, 0]).strip().lower() == "maturity":
            mat_row = i
            break
    if mat_row is not None:
        coupon_row = mat_row + 1
        latest_i = _latest_date_row(df, mat_row + 2)
        if latest_i is None:
            return pd.DataFrame()
        as_at = pd.to_datetime(df.iloc[latest_i, 0])
        fy = _fy_from_dt(as_at)
        rows: list[dict[str, Any]] = []
        instrument_total = 0.0
        for j in range(1, df.shape[1]):
            val = pd.to_numeric(df.iloc[latest_i, j], errors="coerce")
            # Liability outstanding only (AOFM signs liabilities negative)
            if pd.isna(val) or val >= 0:
                continue
            amount = abs(float(val))
            mat = df.iloc[mat_row, j]
            coupon = df.iloc[coupon_row, j] if coupon_row < len(df) else None
            mat_ts = pd.to_datetime(mat, errors="coerce")
            if pd.notna(mat_ts):
                detail = mat_ts.strftime("%d %b %Y")
            else:
                detail = re.sub(r"\s+", " ", str(mat)).strip() if pd.notna(mat) else f"line_{j}"
            if pd.notna(coupon):
                try:
                    detail = f"{detail} {float(coupon):g}%"
                except (TypeError, ValueError):
                    pass
            instrument_total += amount
            rows.append(
                {
                    "fy": fy,
                    "category": f"{instrument} / {detail}",
                    "amount": amount,
                    "locator": (
                        f"sheet:FaceValue | instrument:{instrument} | maturity:{detail} | "
                        f"as_at:{as_at.date()} | unit:AUD_face_value_dealt"
                    ),
                }
            )
        if instrument_total > 0:
            rows.insert(
                0,
                {
                    "fy": fy,
                    "category": instrument,
                    "amount": instrument_total,
                    "locator": (
                        f"sheet:FaceValue | instrument:{instrument} | total | "
                        f"as_at:{as_at.date()} | unit:AUD_face_value_dealt"
                    ),
                },
            )
        return pd.DataFrame(rows)

    # Layout B: portfolio aggregate — Instrument row then time series of instrument totals
    inst_row = None
    for i in range(min(20, len(df))):
        if str(df.iloc[i, 0]).strip().lower() == "instrument":
            inst_row = i
            break
    if inst_row is None:
        return pd.DataFrame()
    latest_i = _latest_date_row(df, inst_row + 1)
    if latest_i is None:
        return pd.DataFrame()
    as_at = pd.to_datetime(df.iloc[latest_i, 0])
    fy = _fy_from_dt(as_at)
    wanted = {
        "treasury bonds": "Treasury Bonds",
        "treasury indexed bonds (capital indexed)": "Treasury Indexed Bonds",
        "treasury indexed bonds": "Treasury Indexed Bonds",
        "treasury notes": "Treasury Notes",
    }
    rows = []
    for j in range(1, df.shape[1]):
        label = re.sub(r"\s+", " ", str(df.iloc[inst_row, j])).strip()
        key = label.lower()
        if key.startswith("total") or key not in wanted:
            continue
        val = pd.to_numeric(df.iloc[latest_i, j], errors="coerce")
        if pd.isna(val) or val >= 0:
            continue
        cat = wanted[key]
        rows.append(
            {
                "fy": fy,
                "category": cat,
                "amount": abs(float(val)),
                "locator": (
                    f"sheet:FaceValue | instrument:{cat} | "
                    f"as_at:{as_at.date()} | unit:AUD_face_value_dealt"
                ),
            }
        )
    return pd.DataFrame(rows)


def melt_instrument_workbook(path: Path, instrument: str) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        # fallback flat CSV
        face_col = None
        for c in df.columns:
            if "face" in str(c).lower():
                face_col = c
                break
        if face_col is None:
            return pd.DataFrame()
        amount = abs(float(pd.to_numeric(df[face_col], errors="coerce").dropna().iloc[-1]))
        return pd.DataFrame(
            [
                {
                    "fy": "2024-25",
                    "category": instrument,
                    "amount": amount,
                    "locator": f"file:{path.name} | instrument:{instrument}",
                }
            ]
        )
    return melt_facevalue_sheet(path, instrument)


def export_aofm_instruments(staging_dir: Path) -> list[dict[str, Any]]:
    landing = "https://www.aofm.gov.au/data-hub"
    staging_dir.mkdir(parents=True, exist_ok=True)
    metas = []
    for source_id, instrument in INSTRUMENT_SOURCES.items():
        try:
            fp, asset = resolve_latest(source_id)
        except FileNotFoundError:
            continue
        melted = melt_instrument_workbook(fp, instrument)
        if melted.empty:
            continue
        resource = asset.get("final_url") or asset.get("requested_url") or landing
        melted["landing_url"] = landing
        melted["resource_url"] = resource
        out_id = f"{source_id}_facts"
        out = staging_dir / f"{out_id}.csv"
        melted.to_csv(out, index=False)
        metas.append(
            {
                "source_id": out_id,
                "base_source_id": source_id,
                "path": out,
                "rows": len(melted),
                "cached_copy_path": str(fp.relative_to(REPO_ROOT)),
                "jurisdiction": "Commonwealth",
                "government_level": "federal",
                "instrument": instrument,
                "resource_url": resource,
            }
        )
    return metas
