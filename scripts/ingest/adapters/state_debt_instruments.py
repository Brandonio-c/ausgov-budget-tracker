"""Parse state borrowing-authority captures into instrument-level debt rows."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

INSTRUMENT_FIXED = "Fixed-rate bonds"
INSTRUMENT_INDEXED = "Indexed bonds"
INSTRUMENT_FRN = "Floating-rate notes"
INSTRUMENT_SHORT = "Short-term notes"
INSTRUMENT_OTHER = "Other funding instruments"

_AS_AT_RE = re.compile(
    r"(?:as at|as of|week ending|bonds on issue week ending|page capture)[:\s]*"
    r"([0-9]{1,2}[\s\-/][A-Za-z]{3,9}[\s\-/][0-9]{2,4}|[0-9]{1,2}[./\-][0-9]{1,2}[./\-][0-9]{2,4})",
    re.I,
)
_AMOUNT_RE = re.compile(
    r"(?:A\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(billion|bn|million|m)?",
    re.I,
)
_DATE_TOKEN = r"[0-9]{1,2}[\s\-/][A-Za-z]{3,9}[\s\-/][0-9]{2,4}|[0-9]{1,2}[./\-][0-9]{1,2}[./\-][0-9]{2,4}"
_COUPON_TOKEN = r"(?:[0-9]+(?:\.[0-9]+)?\s*%|(?:AONIA|BBSW|3m BBSW)\s*[+\-]?\s*[0-9]+(?:\.[0-9]+)?\s*(?:bps|bp)?|[+\-]?[0-9]+(?:\.[0-9]+)?\s*(?:bps|bp))"


@dataclass
class InstrumentRow:
    instrument_type: str
    security_name: str
    maturity_date: str | None
    coupon: str | None
    isin: str | None
    face_value_aud: float
    as_at: date
    currency: str = "AUD"
    valuation_basis: str = "face_value_outstanding"
    authority: str = ""
    source_url: str = ""
    locator: str = ""

    def category(self) -> str:
        detail = self.security_name
        authority = (self.authority or "Authority").strip()
        return f"Debt securities / {authority} / {self.instrument_type} / {detail}"

    def financial_year(self) -> str:
        y = self.as_at.year
        if self.as_at.month >= 7:
            return f"{y}-{str(y + 1)[2:]}"
        return f"{y - 1}-{str(y)[2:]}"

    def to_fact_dict(self) -> dict:
        vb = self.valuation_basis
        if vb in {"face_value_outstanding", "face"}:
            vb_norm = "face_value"
        elif "fair" in vb:
            vb_norm = "fair_value"
        else:
            vb_norm = vb or "unspecified"
        is_type_aggregate = (
            self.security_name.lower() in {self.instrument_type.lower(), "total"}
            or "aggregate" in (self.locator or "").lower()
            or (vb_norm == "fair_value" and not self.isin)
        )
        granularity = "instrument_type_aggregate" if is_type_aggregate else "individual_security"
        bits = [
            f"authority:{self.authority}" if self.authority else None,
            f"instrument_type:{self.instrument_type}",
            f"security_name:{self.security_name}",
            f"isin:{self.isin}" if self.isin else None,
            f"coupon:{self.coupon}" if self.coupon else None,
            f"maturity_date:{self.maturity_date}" if self.maturity_date else None,
            f"face_value_outstanding:{self.face_value_aud:.2f}",
            f"currency:{self.currency}",
            f"valuation_basis:{vb_norm}",
            f"amount_granularity:{granularity}",
            f"as_at_date:{self.as_at.isoformat()}",
            f"source_url:{self.source_url}" if self.source_url else None,
            self.locator or None,
        ]
        return {
            "fy": self.financial_year(),
            "category": self.category(),
            "amount": self.face_value_aud,
            "locator": " | ".join(b for b in bits if b),
            "landing_url": self.source_url or "",
            "resource_url": self.source_url or "",
            "as_at_date": self.as_at.isoformat(),
            "observation_date": self.as_at.isoformat(),
            "valuation_basis": vb_norm,
            "amount_granularity": granularity,
            "authority": self.authority,
            "isin": self.isin or "",
            "maturity_date": self.maturity_date or "",
            "coupon": self.coupon or "",
        }


def parse_as_at(text: str, default: date | None = None) -> date:
    text = (text or "").replace("\u200b", "")
    m = _AS_AT_RE.search(text)
    if m:
        dt = _parse_date(m.group(1))
        if dt:
            return dt
    # Only accept an explicit as_at_note CSV header value, never the first maturity.
    for line in text.splitlines()[:3]:
        if line.lower().startswith("as_at_note"):
            m2 = re.search(_DATE_TOKEN, line)
            if m2:
                dt = _parse_date(m2.group(0))
                if dt:
                    return dt
    return default or date.today()


def _parse_date(token: str) -> date | None:
    token = re.sub(r"\s+", " ", (token or "").strip().replace("-", " ").replace("/", " ").replace(".", " "))
    for fmt in ("%d %b %Y", "%d %B %Y", "%d %m %Y", "%d %m %y", "%Y %m %d"):
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue
    # 17-Jul-26 / 21 Jul 2026 already normalized with spaces
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{2,4})$", token)
    if m:
        d, mon, y = m.groups()
        y = int(y)
        if y < 100:
            y += 2000
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(f"{int(d)} {mon} {y}", fmt).date()
            except ValueError:
                continue
    return None


def _parse_amount(raw: str) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in {"nan", "none", "-", "total"}:
        return None
    m = _AMOUNT_RE.search(s.replace(",", ""))
    if not m:
        try:
            return abs(float(s.replace(",", "").replace("A$", "").strip()))
        except ValueError:
            return None
    num = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit.startswith("b"):
        return abs(num * 1_000_000_000)
    if unit.startswith("m") or unit == "":
        # bare numbers from weekly sheets are $m face
        if unit.startswith("m") or abs(num) < 1_000_000:
            return abs(num * 1_000_000) if unit.startswith("m") or abs(num) < 500_000 else abs(num)
    return abs(num)


def _normalize_coupon(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = re.sub(r"\s+", " ", str(raw)).strip()
    if not s or s.lower() in {"nan", "none", ""}:
        return None
    return s


def _security_name(maturity: str | None, coupon: str | None, isin: str | None = None) -> str:
    bits = [b for b in [maturity, coupon] if b]
    name = " ".join(bits) if bits else (isin or "unknown")
    return name


def _classify_from_section(section: str) -> str:
    s = section.lower()
    if any(k in s for k in ("floating", "frn", "bbsw", "aonia")):
        return INSTRUMENT_FRN
    if any(k in s for k in ("index", "cib", "capital indexed", "annuity")):
        return INSTRUMENT_INDEXED
    if any(k in s for k in ("short", "promissory", "commercial paper", "note programme", "pn ")):
        return INSTRUMENT_SHORT
    if any(k in s for k in ("benchmark", "fixed", "bond", "green")):
        return INSTRUMENT_FIXED
    return INSTRUMENT_OTHER


def _pdf_text(path: Path) -> str:
    try:
        out = subprocess.check_output(
            ["pdftotext", "-layout", str(path), "-"],
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
        return out.decode("utf-8", errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)


def _split_csv_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current = "table"
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if buf:
                sections.append((current, buf))
            current = line.lstrip("#").strip() or "table"
            buf = []
            continue
        if line.startswith("as_at_note"):
            continue
        if line.strip():
            buf.append(line)
    if buf:
        sections.append((current, buf))
    return sections


def parse_sectioned_csv(
    path: Path,
    *,
    authority: str,
    source_url: str = "",
    default_as_at: date | None = None,
) -> list[InstrumentRow]:
    text = path.read_text(encoding="utf-8", errors="replace")
    as_at = parse_as_at(text.splitlines()[0] if text else "", default_as_at)
    rows: list[InstrumentRow] = []
    for section, lines in _split_csv_sections(text):
        if len(lines) < 2:
            continue
        header = [c.strip() for c in lines[0].split(",")]
        # handle quoted commas poorly — use pandas
        from io import StringIO

        try:
            df = pd.read_csv(StringIO("\n".join(lines)))
        except Exception:
            continue
        df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
        cols = {c.lower(): c for c in df.columns}
        mat_col = next((cols[k] for k in cols if "maturity" in k), None)
        coup_col = next((cols[k] for k in cols if "coupon" in k), None)
        isin_col = next((cols[k] for k in cols if "isin" in k), None)
        amt_col = next(
            (
                cols[k]
                for k in cols
                if any(x in k for x in ("outstanding", "amount", "face", "nominal", "issue"))
            ),
            None,
        )
        if amt_col is None:
            continue
        instrument = _classify_from_section(section)
        # TCV table 2 has Face Value + Nominal — prefer Face Value for indexed
        if "face value" in {c.lower() for c in df.columns}:
            amt_col = next(c for c in df.columns if c.lower().startswith("face"))
            instrument = INSTRUMENT_INDEXED
        for _, r in df.iterrows():
            mat = str(r.get(mat_col)).strip() if mat_col and pd.notna(r.get(mat_col)) else None
            if not mat or mat.lower() in {"maturity", "total", "nan", ""}:
                continue
            if mat.lower().startswith("total"):
                continue
            row_blob = " ".join(str(v) for v in r.values if pd.notna(v)).lower()
            if row_blob.startswith("total") or re.search(r"\btotal\b", str(mat).lower()):
                continue
            coup = _normalize_coupon(r.get(coup_col) if coup_col else None)
            # FRN coupons often look like +2.00 without %
            if instrument == INSTRUMENT_FIXED and coup and re.match(r"^[+\-]?[0-9.]+$", coup):
                instrument_row_type = INSTRUMENT_FRN
            else:
                instrument_row_type = instrument
            if coup and re.search(r"bbsw|aonia|bp", coup, re.I):
                instrument_row_type = INSTRUMENT_FRN
            isin = None
            if isin_col and pd.notna(r.get(isin_col)):
                isin = str(r.get(isin_col)).strip() or None
            amount = _parse_amount(r.get(amt_col))
            if amount is None or amount <= 0:
                continue
            # TCV/QTC/WATC CSV amounts are in $m when bare
            if amount < 1_000_000:
                amount *= 1_000_000
            mat_fmt = None
            if mat:
                d = _parse_date(mat)
                mat_fmt = d.strftime("%d %b %Y") if d else mat
            name = _security_name(mat_fmt, coup, isin)
            rows.append(
                InstrumentRow(
                    instrument_type=instrument_row_type,
                    security_name=name,
                    maturity_date=mat_fmt,
                    coupon=coup,
                    isin=isin,
                    face_value_aud=amount,
                    as_at=as_at,
                    authority=authority,
                    source_url=source_url,
                    locator=f"file:{path.name} | section:{section}",
                )
            )
    return rows


def parse_tcv_amount_csv(path: Path, source_url: str = "") -> list[InstrumentRow]:
    text = path.read_text(encoding="utf-8", errors="replace")
    as_at = parse_as_at(text, date(2026, 7, 17))
    # Explicit table order on amount-on-issue page: fixed, indexed, FRN
    type_order = [INSTRUMENT_FIXED, INSTRUMENT_INDEXED, INSTRUMENT_FRN]
    sections = _split_csv_sections(text)
    rows: list[InstrumentRow] = []
    for idx, (section, lines) in enumerate(sections):
        instrument = type_order[idx] if idx < len(type_order) else _classify_from_section(section)
        from io import StringIO

        try:
            df = pd.read_csv(StringIO("\n".join(lines)))
        except Exception:
            continue
        df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
        for _, r in df.iterrows():
            mat = str(r.iloc[0]).strip() if pd.notna(r.iloc[0]) else ""
            if not mat or mat.lower() in {"maturity", "nan"}:
                continue
            coupon = None
            amount = None
            if "Coupon Rate" in df.columns:
                coupon = _normalize_coupon(r.get("Coupon Rate"))
                amount = _parse_amount(r.get("Nominal Amount $m"))
            elif "Face Value $m" in df.columns:
                amount = _parse_amount(r.get("Face Value $m"))
                instrument = INSTRUMENT_INDEXED
            else:
                amount = _parse_amount(r.get(df.columns[-1]))
            if amount is None or amount <= 0:
                continue
            if amount < 1_000_000:
                amount *= 1_000_000
            d = _parse_date(mat)
            mat_fmt = d.strftime("%d %b %Y") if d else mat
            if coupon and re.search(r"bbsw|bp", coupon, re.I):
                instrument = INSTRUMENT_FRN
            rows.append(
                InstrumentRow(
                    instrument_type=instrument,
                    security_name=_security_name(mat_fmt, coupon),
                    maturity_date=mat_fmt,
                    coupon=coupon,
                    isin=None,
                    face_value_aud=amount,
                    as_at=as_at,
                    authority="TCV",
                    source_url=source_url
                    or "https://www.tcv.vic.gov.au/tcv-bonds/outstanding-borrowing/amount-on-issue",
                    locator=f"file:{path.name} | section:{section or instrument}",
                )
            )
    return rows


def parse_tcorp_weekly_pdf(path: Path, source_url: str = "") -> list[InstrumentRow]:
    text = _pdf_text(path)
    as_at = parse_as_at(text, date(2026, 7, 17))
    # Drop chart/legend noise after the main tables.
    text = re.split(r"FINANCIAL YEAR TO DATE ISSUANCE|TCORP MATURITY PROFILE", text)[0]
    rows: list[InstrumentRow] = []
    for m in re.finditer(
        rf"({_COUPON_TOKEN})\s+({_DATE_TOKEN})\s+([0-9][0-9,]*(?:\.[0-9]+)?)",
        text,
        re.I,
    ):
        coupon, mat, amt = m.groups()
        coupon = coupon.strip()
        amount = _parse_amount(amt)
        if amount is None or amount <= 0:
            continue
        if amount < 1_000_000:
            amount *= 1_000_000
        d = _parse_date(mat)
        mat_fmt = d.strftime("%d %b %Y") if d else mat
        instrument = INSTRUMENT_FRN if re.search(r"bp|bbsw|aonia", coupon, re.I) else INSTRUMENT_FIXED
        rows.append(
            InstrumentRow(
                instrument_type=instrument,
                security_name=_security_name(mat_fmt, coupon),
                maturity_date=mat_fmt,
                coupon=coupon,
                isin=None,
                face_value_aud=amount,
                as_at=as_at,
                authority="TCorp",
                source_url=source_url,
                locator=f"file:{path.name}",
            )
        )
    seen: set[tuple[str, str, float]] = set()
    deduped: list[InstrumentRow] = []
    for r in rows:
        key = (r.instrument_type, r.security_name, round(r.face_value_aud, 2))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def parse_qtc_weekly_pdf(path: Path, source_url: str = "") -> list[InstrumentRow]:
    text = _pdf_text(path)
    as_at = parse_as_at(text, date(2026, 7, 17))
    rows: list[InstrumentRow] = []
    # Two-column layout: capture every coupon/maturity/amount triple on each line.
    for m in re.finditer(
        rf"({_COUPON_TOKEN})\s+({_DATE_TOKEN})\s+([0-9][0-9,]*(?:\.[0-9]+)?)",
        text,
        re.I,
    ):
        coupon, mat, amt = m.groups()
        window_start = max(0, m.start() - 120)
        window_end = min(len(text), m.end() + 40)
        window = text[window_start:window_end].upper()
        if "TOTAL" in coupon.upper():
            continue
        amount = _parse_amount(amt)
        if amount is None or amount <= 0:
            continue
        if amount < 1_000_000:
            amount *= 1_000_000
        d = _parse_date(mat)
        mat_fmt = d.strftime("%d %b %Y") if d else mat
        if re.search(r"bbsw|bp", coupon, re.I):
            inst = INSTRUMENT_FRN
        elif (
            "20-Aug-30" in mat.replace(" ", "-")
            or (mat_fmt and "20 Aug 2030" == mat_fmt)
        ) and 200_000_000 <= amount <= 300_000_000:
            inst = INSTRUMENT_INDEXED
        else:
            inst = INSTRUMENT_FIXED
        rows.append(
            InstrumentRow(
                instrument_type=inst,
                security_name=_security_name(mat_fmt, coupon.strip()),
                maturity_date=mat_fmt,
                coupon=coupon.strip(),
                isin=None,
                face_value_aud=amount,
                as_at=as_at,
                authority="QTC",
                source_url=source_url,
                locator=f"file:{path.name}",
            )
        )
    # Deduplicate identical securities (chart labels can repeat table rows)
    seen: set[tuple[str, str | None, float]] = set()
    deduped: list[InstrumentRow] = []
    for r in rows:
        key = (r.security_name, r.instrument_type, round(r.face_value_aud, 2))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def parse_safa_weekly_pdf(path: Path, source_url: str = "") -> list[InstrumentRow]:
    text = _pdf_text(path)
    as_at = parse_as_at(text, date(2026, 7, 17))
    rows: list[InstrumentRow] = []
    # Prefer the as-at column (last large number on instrument lines)
    for line in text.splitlines():
        m = re.search(
            rf"({_COUPON_TOKEN})\s+({_DATE_TOKEN})\s+.*?([0-9][0-9,]*(?:\.[0-9]+)?)\s*$",
            line.strip(),
            re.I,
        )
        if not m:
            continue
        coupon, mat, amt = m.groups()
        amount = _parse_amount(amt)
        if amount is None or amount <= 0:
            continue
        if amount < 1_000_000:
            amount *= 1_000_000
        d = _parse_date(mat)
        mat_fmt = d.strftime("%d %b %Y") if d else mat
        inst = INSTRUMENT_FRN if re.search(r"aonia|bbsw|bp", coupon, re.I) else INSTRUMENT_FIXED
        rows.append(
            InstrumentRow(
                instrument_type=inst,
                security_name=_security_name(mat_fmt, coupon.strip()),
                maturity_date=mat_fmt,
                coupon=coupon.strip(),
                isin=None,
                face_value_aud=amount,
                as_at=as_at,
                authority="SAFA",
                source_url=source_url,
                locator=f"file:{path.name}",
            )
        )
    return rows


def resolve_raw_file(repo_root: Path, source_id: str) -> tuple[Path, str] | None:
    matches = [
        m
        for m in (repo_root / "data" / "raw").rglob(source_id)
        if m.is_dir() and (m / "latest.json").exists()
    ]
    if not matches:
        return None
    import json

    data = json.loads((matches[0] / "latest.json").read_text(encoding="utf-8"))
    assets = data.get("assets") or []
    source_url = ""
    if assets:
        source_url = assets[0].get("requested_url") or ""
        stored = Path(assets[0]["stored_path"])
        fp = repo_root / "data" / stored if not stored.is_absolute() else stored
        if fp.exists():
            return fp, source_url
    cands = [
        c
        for c in matches[0].rglob("*.*")
        if c.suffix.lower() in {".xlsx", ".xls", ".csv", ".pdf"}
    ]
    return (cands[0], source_url) if cands else None


# One primary instrument feed per jurisdiction to avoid double-counting identical captures.
SOURCE_PARSERS = {
    "vic_tcv_amount_on_issue": ("VIC", "state", "TCV", "tcv_amount"),
    "nsw_tcorp_bonds_on_issue": ("NSW", "state", "TCorp", "tcorp_pdf"),
    "qld_qtc_aud_bond_outstandings": ("QLD", "state", "QTC", "qtc_pdf"),
    "sa_safa_weekly_funding_update": ("SA", "state", "SAFA", "safa_pdf"),
    "wa_watc_funding_sources": ("WA", "state", "WATC", "sectioned_csv"),
    "nt_nttc_borrowing_strategy": ("NT", "territory", "NTTC", "nttc_csv"),
    "tas_tascorp_annual_report_2024_25": ("TAS", "state", "TASCORP", "tascorp_annual"),
}


def parse_nttc_csv(path: Path, source_url: str = "") -> list[InstrumentRow]:
    # Bond schedule on the strategy page is undated; promissory-note note cites 30 June 2024.
    as_at = date(2024, 6, 30)
    rows = parse_sectioned_csv(
        path, authority="NTTC", source_url=source_url, default_as_at=as_at
    )
    # Merge ISINs from the identifier section onto amount rows.
    text = path.read_text(encoding="utf-8", errors="replace")
    isins: dict[str, str] = {}
    for section, lines in _split_csv_sections(text):
        if "identifier" not in section.lower() and "isin" not in section.lower():
            continue
        from io import StringIO

        try:
            df = pd.read_csv(StringIO("\n".join(lines)))
        except Exception:
            continue
        df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
        mat_c = next((c for c in df.columns if "maturity" in c.lower()), None)
        isin_c = next((c for c in df.columns if "isin" in c.lower()), None)
        coup_c = next((c for c in df.columns if "coupon" in c.lower()), None)
        if not mat_c or not isin_c:
            continue
        for _, r in df.iterrows():
            mat = str(r.get(mat_c)).strip()
            d = _parse_date(mat)
            mat_fmt = d.strftime("%d %b %Y") if d else mat
            coup = _normalize_coupon(r.get(coup_c) if coup_c else None)
            key = _security_name(mat_fmt, coup)
            isins[key] = str(r.get(isin_c)).strip()
    for r in rows:
        r.as_at = as_at
        r.instrument_type = INSTRUMENT_FIXED
        if r.security_name in isins:
            r.isin = isins[r.security_name]
    return [r for r in rows if r.face_value_aud > 0]


def parse_tascorp_annual_pdf(path: Path, source_url: str = "") -> list[InstrumentRow]:
    """TASCORP does not publish a maturity/ISIN schedule; capture instrument-type face values."""
    text = _pdf_text(path)
    as_at = date(2025, 6, 30)
    rows: list[InstrumentRow] = []
    # Prefer 2025 fair-value liability lines near "Fixed rate bonds*"
    patterns = [
        (INSTRUMENT_FIXED, r"Fixed rate bonds\*?\s+([0-9,]+\.[0-9]+)\s+[0-9,]+\.[0-9]+\s+[-\d.]+\s+([0-9,]+\.[0-9]+)"),
        (INSTRUMENT_FRN, r"Floating rate notes\s+([-\d.]+)\s+([0-9,]+\.[0-9]+)"),
        (INSTRUMENT_OTHER, r"Other bonds\s+([-\d.]+)\s+([0-9,]+\.[0-9]+)"),
        (INSTRUMENT_SHORT, r"Commercial paper\s+([-\d.]+)\s+([0-9,]+\.[0-9]+)"),
    ]
    # Take the first 2025 block totals (Total column)
    block = text
    if "30 June 2025" in text or "2025" in text:
        # use segment before "30 June 2024" fair-value table when present
        parts = re.split(r"30 June 2024\s+Level 1", text, maxsplit=1)
        block = parts[0]
    for inst, pat in patterns:
        m = re.search(pat, block)
        if not m:
            continue
        # last capture is Total $m
        amount = _parse_amount(m.group(m.lastindex))
        if amount is None or amount <= 0:
            continue
        if amount < 1_000_000:
            amount *= 1_000_000
        rows.append(
            InstrumentRow(
                instrument_type=inst,
                security_name=f"{inst} (portfolio total)",
                maturity_date=None,
                coupon=None,
                isin=None,
                face_value_aud=amount,
                as_at=as_at,
                authority="TASCORP",
                source_url=source_url,
                locator=f"file:{path.name} | note:fair_value_liabilities | valuation_basis:fair_value",
                valuation_basis="fair_value",
            )
        )
    return rows


def parse_source(path: Path, kind: str, authority: str, source_url: str = "") -> list[InstrumentRow]:
    if kind == "tcv_amount":
        return parse_tcv_amount_csv(path, source_url=source_url)
    if kind == "tcorp_pdf":
        return parse_tcorp_weekly_pdf(path, source_url=source_url)
    if kind == "qtc_pdf":
        rows = parse_qtc_weekly_pdf(path, source_url=source_url)
        # Enrich ISINs from the companion benchmark CSV when present.
        repo_raw = path
        while repo_raw.name != "raw" and repo_raw.parent != repo_raw:
            repo_raw = repo_raw.parent
        hits = list(repo_raw.rglob("qld_qtc_benchmark_bonds.csv")) if repo_raw.name == "raw" else []
        if not hits:
            hits = list(path.parents[4].rglob("qld_qtc_benchmark_bonds.csv")) if len(path.parents) > 4 else []
        if hits and rows:
            bench_rows = parse_sectioned_csv(
                hits[0],
                authority="QTC",
                source_url=source_url,
                default_as_at=rows[0].as_at,
            )
            by_key: dict[str, str] = {}
            for b in bench_rows:
                if not b.isin:
                    continue
                by_key[b.security_name] = b.isin
                if b.maturity_date:
                    by_key[b.maturity_date] = b.isin
            for r in rows:
                if r.security_name in by_key:
                    r.isin = by_key[r.security_name]
                elif r.maturity_date and r.maturity_date in by_key:
                    r.isin = by_key[r.maturity_date]
        return rows
    if kind == "safa_pdf":
        return parse_safa_weekly_pdf(path, source_url=source_url)
    if kind == "sectioned_csv":
        rows = parse_sectioned_csv(path, authority=authority, source_url=source_url)
        for r in rows:
            if r.instrument_type == INSTRUMENT_OTHER and authority in {"QTC", "WATC", "NTTC"}:
                r.instrument_type = INSTRUMENT_FIXED
        return rows
    if kind == "nttc_csv":
        return parse_nttc_csv(path, source_url=source_url)
    if kind == "tascorp_annual":
        return parse_tascorp_annual_pdf(path, source_url=source_url)
    return []
