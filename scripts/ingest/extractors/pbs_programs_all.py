#!/usr/bin/env python3
"""Generalized PBS program-expense extractor for Commonwealth PBS PDFs.

Looks for Table 2.1-style program expense rows with trailing year columns ($'000).
Tracks per-source_id provenance and dedupes across Transparency Portal / agency copies.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import SKIP_LINE, iter_pdf_pages  # noqa: E402
from extractors.pbs_year_resolve import (  # noqa: E402
    parse_year_header_line,
    resolve_years_for_nums,
    template_for_budget_year,
)

OUT_DIR = REPO_ROOT / "data/staging/breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data/staging/quarantine"
LANDING = "https://budget.gov.au/content/pbs/index.htm"

FIVE_TAIL = re.compile(
    r"^(?P<label>.*?)(?P<nums>(?:\s+-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|\s+-?\d+(?:\.\d+)?){3,6})\s*$"
)

# Retained only for status hints when headers provide FYs; never used to invent columns.
STATUS_BY_FY = {
    "2024-25": "actual",
    "2025-26": "estimated_actual",
    "2026-27": "budget",
    "2027-28": "forward_estimate",
    "2028-29": "forward_estimate",
    "2029-30": "forward_estimate",
}

PORTFOLIO_ALIASES = {
    "defence": "Defence",
    "education": "Education",
    "industry": "Industry Science and Resources",
    "science": "Industry Science and Resources",
    "resources": "Industry Science and Resources",
    "infrastructure": "Infrastructure Transport Regional Development Communications Sport and the Arts",
    "home affairs": "Home Affairs",
    "attorney": "Attorney-General's",
    "health": "Health Disability and Ageing",
    "social services": "Social Services",
    "treasury": "Treasury",
    "finance": "Finance",
    "foreign affairs": "Foreign Affairs and Trade",
    "climate": "Climate Change Energy the Environment and Water",
    "agriculture": "Agriculture Fisheries and Forestry",
    "employment": "Employment and Workplace Relations",
    "prime minister": "Prime Minister and Cabinet",
    "veterans": "Veterans' Affairs",
    "pmc": "Prime Minister and Cabinet",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _relative_or_str(path: Path) -> str:
    """repo-relative path when possible, else str(path) - unit tests exercise
    extract_pdf() with fake paths not under REPO_ROOT (e.g. Path("fake.pdf")),
    which must not raise from an unconditional relative_to()."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _parse_thousands(tok: str) -> int | None:
    try:
        return int(float(tok.replace(",", "")) * 1000)
    except ValueError:
        return None


def _portfolio_from_source(source_id: str, stem: str) -> str:
    blob = f"{source_id} {stem}".lower().replace("_", " ").replace("-", " ")
    for key, label in PORTFOLIO_ALIASES.items():
        if key in blob:
            return label
    portfolio = re.sub(r"(?i)^\d{4}-\d{2}-?", "", stem)
    portfolio = portfolio.replace("-PBS", "").replace("_PBS", "").replace("-pbs", "")
    portfolio = portfolio.replace("federal_pbs_", "").replace("federal_", "")
    portfolio = re.sub(r"\d{4}_\d{2}", "", portfolio)
    portfolio = portfolio.replace("_", " ").replace("-", " ").strip()
    return _norm(portfolio)[:80] or stem[:80]


START_MARKERS = re.compile(
    r"Table\s+2\.1|"
    r"Program expenses|"
    r"Expenses for Outcome|"
    r"Budgeted expenses for Outcome|"
    r"Budget Expenses and Performance|"
    r"Budgeted Expenses and Performance|"
    r"Cost Summary for Program|"
    r"Planned Expenditure by Key Cost Category",
    re.I,
)

# Tables that are part of Outcome expense sections — do not abort capture.
KEEP_TABLE = re.compile(
    r"Table\s+\d+.*(?:Cost Summary|Budgeted Resources|Program|Outcome|Key Cost)",
    re.I,
)

PROGRAM_TOTAL = re.compile(
    r"Program\s+\d+(?:\.\d+)?\b.*?Total funded expenditure",
    re.I,
)
NUMS_ONLY = re.compile(
    r"^(?:-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)(?:\s+(?:-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)){2,6}\s*$"
)
KEY_COST_ROW = re.compile(
    r"^(?:\d+\s+)?(?P<label>[A-Za-z][A-Za-z0-9 ,\-&/]+?)\s+"
    r"(?P<nums>(?:-?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s+|$)){3,6})\s*$"
)
# Some PBS documents wrap a table's year/status header across many short lines
# instead of one ("2025-26 2026-27 ..." then "Estimated" / "Actual" / "Budget"
# / " Estimate" / "Forward" each on its own line, then "$'000 $'000 ..." on
# another). None of these carry label information, but without this check they
# fall through to the generic `pending.append()` path and get spliced onto the
# next real row's label - confirmed on federal_pbs_2026_27_defence, where this
# corrupted nearly every row on pages using this multi-line header layout.
HEADER_FRAGMENT_ONLY = re.compile(
    r"^(?:Estimated|Actual|Budget|Estimate|Forward|Revised|Outcome|"
    r"(?:\$'?000|\$m)(?:\s+(?:\$'?000|\$m))*)\s*$",
    re.I,
)
# A label followed entirely by dash/nil placeholders (no digits at all) - a
# real zero-value row, not garbage, but its dashes don't match any numeric
# regex so it would otherwise be swallowed into `pending` and glued onto the
# next row's label instead of being recognised as its own (zero) row.
NIL_ROW = re.compile(r"^(?P<label>[A-Za-z][A-Za-z0-9 ,\-&/()\[\]]*?)\s+(?:-\s+){2,}-\s*$")


def _is_start_page(text: str) -> bool:
    return bool(START_MARKERS.search(text))


def _should_stop_table(line: str) -> bool:
    if not re.match(r"^Table\s+\d", line):
        return False
    if "2.1" in line or KEEP_TABLE.search(line):
        return False
    # Abort only on unrelated major tables / section financial statements
    if re.search(r"Budgeted Financial Statements|Explanatory Tables|Section\s+3", line, re.I):
        return True
    return False


def _budget_year_from_source(source_id: str, stem: str) -> str | None:
    blob = f"{source_id} {stem}"
    m = re.search(r"(20\d{2})[_-](\d{2})", blob)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def _append_year_rows(
    rows: list[dict],
    quarantine: list[dict],
    *,
    label: str,
    nums: list[str],
    portfolio: str,
    source_id: str,
    source_url: str,
    pdf: Path,
    page_no: int,
    unit: str,
    header_cols,
    source_budget_year: str | None,
    table_caption: str | None,
    prefer: bool = False,
    use_template: bool = False,
) -> None:
    if len(nums) < 3:
        return
    template = (
        template_for_budget_year(source_budget_year)
        if use_template and source_budget_year
        else None
    )
    year_cols, reason = resolve_years_for_nums(
        nums,
        header_cols=header_cols,
        source_budget_year=source_budget_year,
        layout_template=template,
    )
    if year_cols is None:
        quarantine.append(
            {
                "reason": reason,
                "label": label,
                "nums": " ".join(nums),
                "portfolio": portfolio,
                "source_id": source_id,
                "page": page_no,
                "pdf": pdf.name,
                "quality_status": "quarantined",
            }
        )
        return
    for col, tok in zip(year_cols, nums):
        if unit == "$m":
            try:
                amount = int(float(tok.replace(",", "")) * 1_000_000)
            except ValueError:
                continue
        else:
            amount = _parse_thousands(tok)
            if amount is None:
                continue
        status = col.estimate_status or STATUS_BY_FY.get(col.financial_year, "budget")
        rows.append(
            {
                "fy": col.financial_year,
                "amount": amount,
                "category": f"{portfolio} / {label}",
                "portfolio": portfolio,
                "program_label": label,
                "estimate_status": status,
                "source_id_origin": source_id,
                "prefer_program_total": prefer,
                "source_budget_year": source_budget_year,
                "column_header_original": col.column_header_original,
                "year_inference_method": col.inference_method,
                "year_inference_confidence": col.confidence,
                "table_caption": table_caption,
                "page_number": page_no,
                "quality_status": "ok",
                "cached_copy_path": _relative_or_str(pdf),
                "locator": (
                    f"source_id:{source_id} | pdf:{pdf.name} | page:{page_no} | "
                    f"program:{label} | fy:{col.financial_year} | unit:{unit} | "
                    f"infer:{col.inference_method}/{col.confidence}"
                ),
                "landing_url": source_url or LANDING,
                "resource_url": source_url or LANDING,
            }
        )


def extract_pdf(
    pdf: Path,
    *,
    portfolio: str,
    source_id: str,
    source_url: str = LANDING,
    allow_template_fallback: bool = True,
) -> list[dict]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    capturing = False
    pending: list[str] = []
    header_cols = None
    table_caption: str | None = None
    source_budget_year = _budget_year_from_source(source_id, pdf.stem)
    for page_no, text in iter_pdf_pages(pdf):
        if _is_start_page(text):
            capturing = True
        if not capturing:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if capturing and _should_stop_table(line):
                capturing = False
                pending = []
                header_cols = None
                break
            # Capture / refresh year headers (including continuation pages) -
            # must run before SKIP_LINE: a genuine multi-year header line often
            # starts with a bare "20XX-XX" token, which SKIP_LINE's generic
            # "\d{4}-\d{2}" rule would otherwise eat, silently losing the
            # header and forcing every row on the table onto the (sometimes
            # mismatched) budget-year template fallback instead of the real,
            # page-specific header.
            parsed_header = parse_year_header_line(line)
            if parsed_header and len(parsed_header) >= 3:
                header_cols = parsed_header
                table_caption = line[:200]
                continue

            if SKIP_LINE.match(line):
                continue

            # Bare status/unit fragment from a multi-line-wrapped header - carries
            # no label, must not be treated as one (see HEADER_FRAGMENT_ONLY above).
            if HEADER_FRAGMENT_ONLY.match(line):
                continue

            # A real (zero-value) row whose dashes don't match any numeric regex -
            # drop cleanly rather than let it corrupt the next row's label.
            if NIL_ROW.match(line):
                pending = []
                continue

            common = dict(
                portfolio=portfolio,
                source_id=source_id,
                source_url=source_url,
                pdf=pdf,
                page_no=page_no,
                header_cols=header_cols,
                source_budget_year=source_budget_year,
                table_caption=table_caption,
                use_template=allow_template_fallback and header_cols is None,
            )

            # Defence-style: label line then numeric-only follow-on
            if pending and NUMS_ONLY.match(line):
                label = _norm(" ".join(pending))
                pending = []
                nums = re.findall(
                    r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?", line
                )
                prefer = bool(PROGRAM_TOTAL.search(label))
                if prefer or re.search(r"Program\s+\d+", label, re.I):
                    _append_year_rows(
                        rows,
                        quarantine,
                        label=label,
                        nums=nums,
                        unit="$000",
                        prefer=prefer,
                        **common,
                    )
                continue

            m = FIVE_TAIL.match(line)
            if not m:
                # Key cost category rows in $m (Defence Table 4b style)
                if portfolio == "Defence":
                    km = KEY_COST_ROW.match(line)
                    if km and not line.lower().startswith("total"):
                        label = _norm(km.group("label"))
                        if label and not re.match(r"^(?:Serial|Note)\b", label, re.I):
                            nums = re.findall(
                                r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?",
                                km.group("nums"),
                            )
                            if len(nums) >= 3 and any("." in n or "," in n for n in nums):
                                _append_year_rows(
                                    rows,
                                    quarantine,
                                    label=f"Key cost category / {label}",
                                    nums=nums,
                                    unit="$m",
                                    prefer=True,
                                    **common,
                                )
                                continue
                pending.append(_norm(line))
                if len(pending) > 4:
                    pending = pending[-4:]
                continue

            label = _norm(m.group("label"))
            if pending:
                label = _norm(" ".join(pending + [label]))
                pending = []
            if len(label) < 4:
                continue
            prefer = bool(PROGRAM_TOTAL.search(label))
            if label.lower().startswith("total") and not prefer:
                continue
            if (
                re.match(r"^(?:Outcome|Program|Departmental|Administered)\b", label, re.I)
                and len(label) < 20
                and not prefer
            ):
                continue
            if re.match(r"^(?:Employees|Suppliers|Other expenses)\b", label, re.I):
                continue
            nums = re.findall(
                r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?", m.group("nums")
            )
            _append_year_rows(
                rows,
                quarantine,
                label=label,
                nums=nums,
                unit="$000",
                prefer=prefer,
                **common,
            )

    # Prefer program-total / key-cost rows over duplicate generic lines
    best: dict[tuple, dict] = {}
    for r in rows:
        key2 = (
            r["fy"],
            r["estimate_status"],
            _norm(r["program_label"]).lower(),
            int(r["amount"]),
        )
        prev = best.get(key2)
        if prev is None:
            best[key2] = r
            continue
        if r.get("prefer_program_total") and not prev.get("prefer_program_total"):
            best[key2] = r
        elif len(r["category"]) > len(prev["category"]):
            best[key2] = r
    cleaned = []
    for r in best.values():
        label = r.get("program_label") or ""
        if portfolio == "Defence":
            cleaned_label = _clean_defence_program_label(label)
            if not cleaned_label:
                continue
            r["program_label"] = cleaned_label
            r["category"] = f"{portfolio} / {cleaned_label}"
            r.pop("prefer_program_total", None)
            cleaned.append(r)
            continue
        if re.search(r"\$'?000|Forward Estimate|E stimate|Resourcing", label, re.I):
            if not r.get("prefer_program_total"):
                continue
        r.pop("prefer_program_total", None)
        cleaned.append(r)
    # Persist quarantine sidecar for this extract
    if quarantine:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        qpath = QUARANTINE_DIR / f"pbs_quarantine_{source_id}.jsonl"
        with qpath.open("a", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    return cleaned


def _clean_defence_program_label(label: str) -> str | None:
    """Keep only Program totals and key cost categories from Defence PBS noise."""
    label = _norm(label)
    m = re.search(
        r"(Program\s+\d+(?:\.\d+)?\b.{0,120}?)\s+Total funded expenditure",
        label,
        re.I,
    )
    if m:
        prog = re.sub(r"\s+", " ", m.group(1)).strip(" -")
        if len(prog) >= 8:
            return f"{prog} Total funded expenditure"
    m = re.search(
        r"\b(Workforce|Operations|Capability Acquisition Program|"
        r"Capability Sustainment Program|Operating)\b",
        label,
        re.I,
    )
    if m and "Total" not in label:
        return f"Key cost category / {m.group(1)}"
    if re.match(r"^Key cost category\s*/", label, re.I):
        return label
    return None


def discover_pbs_pdfs() -> list[tuple[str, str, Path, str]]:
    """Return (portfolio, source_id, pdf_path, source_url)."""
    found: list[tuple[str, str, Path, str]] = []
    raw = REPO_ROOT / "data/raw"
    for latest in raw.rglob("latest.json"):
        source_id = latest.parent.name
        if "pbs" not in source_id.lower() and "portfolio_budget" not in source_id.lower():
            continue
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            continue
        for asset in data.get("assets") or []:
            stored = asset.get("stored_path") or ""
            if not stored.lower().endswith(".pdf"):
                continue
            pdf = REPO_ROOT / "data" / stored
            if not pdf.exists():
                pdf = REPO_ROOT / stored
            if not pdf.exists():
                continue
            portfolio = _portfolio_from_source(source_id, pdf.stem)
            url = asset.get("requested_url") or LANDING
            found.append((portfolio, source_id, pdf, url))
    # Fallback glob for PDFs not linked via latest.json naming
    if not found:
        for pdf in raw.rglob("*.pdf"):
            name = pdf.name.lower()
            if "pbs" not in name and "portfolio-budget" not in name:
                continue
            sid = pdf.parent.parent.parent.name if "snapshots" in pdf.parts else pdf.stem
            found.append((_portfolio_from_source(sid, pdf.stem), sid, pdf, LANDING))
    return found


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    by_source: dict[str, int] = {}
    for portfolio, source_id, pdf, url in discover_pbs_pdfs():
        try:
            rows = extract_pdf(pdf, portfolio=portfolio, source_id=source_id, source_url=url)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"pdf": str(pdf), "source_id": source_id, "error": str(exc)}))
            continue
        print(
            json.dumps(
                {
                    "pdf": pdf.name,
                    "source_id": source_id,
                    "portfolio": portfolio,
                    "rows": len(rows),
                }
            )
        )
        by_source[source_id] = by_source.get(source_id, 0) + len(rows)
        all_rows.extend(rows)

    # Cross-document dedupe: same portfolio/program/fy/status/amount → keep first with richest locator
    deduped: dict[tuple, dict] = {}
    for r in all_rows:
        key = (
            r["portfolio"],
            _norm(r["program_label"]).lower(),
            r["fy"],
            r["estimate_status"],
            int(r["amount"]),
        )
        prev = deduped.get(key)
        if prev is None or len(r["locator"]) > len(prev["locator"]):
            deduped[key] = r
    final_rows = list(deduped.values())

    out = OUT_DIR / "pbs_programs_all.csv"
    if final_rows:
        with out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(final_rows[0].keys()))
            writer.writeheader()
            writer.writerows(final_rows)
    print(
        json.dumps(
            {
                "total_rows": len(final_rows),
                "raw_rows": len(all_rows),
                "sources": len(by_source),
                "by_source_top": dict(sorted(by_source.items(), key=lambda x: -x[1])[:15]),
                "out": str(out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
