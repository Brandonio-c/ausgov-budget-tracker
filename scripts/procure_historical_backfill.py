#!/usr/bin/env python3
"""Multi-year historical backfill for ABS GFS previous releases and FBO archives.

Populates registry parents:
  - abs_gfs_previous_releases
  - federal_budget_archive_function_series

Reuses procure HTTPClient + SnapshotStore + BaseAdapter.fetch — does not invent
a new access_method.

Examples:
  python scripts/procure_historical_backfill.py --series abs_gfs --years 2007-08:2023-24
  python scripts/procure_historical_backfill.py --series fbo_archive --years 1996-97:2023-24
  python scripts/procure_historical_backfill.py --series pre_fbo_budget --years 1983-84:1995-96
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from procure.adapters.base import AdapterContext, BaseAdapter  # noqa: E402
from procure.discovery import filename_from_url, infer_financial_year  # noqa: E402
from procure.http_client import DownloadTooLarge, HTTPClient, HTTPFailure  # noqa: E402
from procure.models import Asset, RunContext, Source  # noqa: E402
from procure.registry import load_registry  # noqa: E402
from procure.storage import (  # noqa: E402
    DiskBudget,
    SnapshotStore,
    safe_filename,
    write_json_atomic,
)

GIB = 1024**3
REPO_ROOT = Path(__file__).resolve().parents[1]

ABS_BASE = "https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual"
ABS_AUSSTATS = "https://www.abs.gov.au/AUSSTATS/abs@.nsf/Lookup/5512.0Main+Features1{fy}"
ARCHIVE_BASE = "https://archive.budget.gov.au"

FY_RE = re.compile(r"^(\d{4})-(\d{2})$")


def parse_years(spec: str) -> list[str]:
    """Accept '2007-08:2023-24' or comma-separated years."""
    if ":" in spec:
        start, end = spec.split(":", 1)
        years = []
        y = start.strip()
        while True:
            years.append(y)
            if y == end.strip():
                break
            m = FY_RE.match(y)
            if not m:
                raise SystemExit(f"bad FY: {y}")
            next_start = int(m.group(1)) + 1
            next_end = (int(m.group(1)) + 2) % 100
            y = f"{next_start}-{next_end:02d}"
            if len(years) > 80:
                raise SystemExit("year range too large")
        return years
    return [item.strip() for item in spec.split(",") if item.strip()]


def _git(*args: str) -> str:
    import subprocess

    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def source_by_id(source_id: str) -> Source:
    _, sources = load_registry()
    for source in sources:
        if source.id == source_id:
            return source
    raise SystemExit(f"unknown source id: {source_id}")


def build_context(args: argparse.Namespace) -> AdapterContext:
    data_root = REPO_ROOT / "data"
    run = RunContext(
        run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        repo_root=REPO_ROOT,
        data_root=data_root,
        reports_root=data_root / ".procurement" / "reports",
        git_commit=_git("rev-parse", "HEAD") or "unknown",
        git_dirty=bool(_git("status", "--porcelain")),
        max_total_bytes=args.max_total_bytes,
        max_file_bytes=args.max_file_bytes,
        dry_run=args.dry_run,
        discover_only=False,
        browser_fallback=False,
    )
    http = HTTPClient(
        connect_timeout=args.connect_timeout,
        read_timeout=args.read_timeout,
        retries=args.retries,
    )
    store = SnapshotStore(run)
    budget = DiskBudget(data_root, args.max_total_bytes)
    return AdapterContext(run=run, http=http, store=store, budget=budget)


def _get_html(http: HTTPClient, url: str) -> tuple[int | None, str, str]:
    try:
        response = http.get_bytes(url, max_bytes=20 * 1024 * 1024)
        body = (response.body or b"").decode("utf-8", errors="replace")
        # AUSSTATS often serves latin-1
        if "\x00" not in body and len(body) < 100:
            body = (response.body or b"").decode("latin-1", errors="replace")
        return response.status, body, response.final_url
    except HTTPFailure as error:
        return error.status, "", url
    except DownloadTooLarge:
        return None, "", url
    except Exception:  # noqa: BLE001
        return None, "", url


def _probe_url_ok(http: HTTPClient, url: str) -> bool:
    """Return True if URL looks like a real file (not HTML challenge/404)."""
    try:
        response = http.get_bytes(url, max_bytes=64 * 1024)
        ctype = (response.headers.get("content-type") or "").lower()
        body = response.body or b""
        if response.status >= 400:
            return False
        if "text/html" in ctype:
            return False
        if body[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
            return False
        return True
    except DownloadTooLarge:
        # Large binary exceeded probe cap — treat as present.
        return True
    except Exception:  # noqa: BLE001
        return False


def _pdf_or_xlsx_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        absolute = urljoin(base_url, href)
        path = urlparse(absolute).path.lower()
        if any(path.endswith(ext) for ext in (".pdf", ".xlsx", ".xls", ".zip")):
            urls.append(absolute)
        elif "download" in path and ("workbook" in absolute.lower() or "55120" in absolute.lower()):
            urls.append(absolute)
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def discover_abs_year(http: HTTPClient, fy: str) -> dict:
    """Discover All-workbooks.zip and/or 55120DO workbooks for one ABS GFS year."""
    tried: list[dict] = []
    candidates: list[str] = []

    zip_url = f"{ABS_BASE}/{fy}/All-workbooks.zip"
    landing = f"{ABS_BASE}/{fy}"
    st, html, final_landing = _get_html(http, landing)
    tried.append({"url": landing, "status": st})
    if st and st < 400 and html:
        links = _pdf_or_xlsx_links(html, final_landing)
        zip_links = [u for u in links if "all-workbooks" in u.lower() or u.lower().endswith(".zip")]
        xlsx_links = [u for u in links if "55120" in u.lower() or u.lower().endswith(".xlsx")]
        if zip_links:
            candidates.extend(zip_links)
        elif xlsx_links:
            candidates.extend(xlsx_links)

    # Conventional modern zip path (works 2017-18+)
    if _probe_url_ok(http, zip_url):
        candidates.append(zip_url)
        tried.append({"url": zip_url, "status": "ok"})
    else:
        tried.append({"url": zip_url, "status": "missing"})

    # Legacy AUSSTATS DetailsPage (pre-modern URL scheme) — subscriber.nsf log links
    if not any(u.lower().endswith(".zip") or "all-workbooks" in u.lower() for u in candidates):
        details = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/5512.0{fy}?OpenDocument"
        st2, html2, final2 = _get_html(http, details)
        tried.append({"url": details, "status": st2})
        if st2 and st2 < 400 and html2:
            # subscriber.nsf/log?openagent&FILENAME.xls&...
            for match in re.finditer(
                r'(/AUSSTATS/subscriber\.nsf/log\?openagent&[^\"\'>\s]+)',
                html2,
                re.I,
            ):
                candidates.append(urljoin(final2, match.group(1).replace("&amp;", "&")))
            # Also follow Main Features page if DetailsPage empty
            if not candidates:
                aus = ABS_AUSSTATS.format(fy=fy)
                st3, html3, final3 = _get_html(http, aus)
                tried.append({"url": aus, "status": st3})
                if st3 and st3 < 400 and html3:
                    for match in re.finditer(
                        r'(DetailsPage/5512\.0[^\"\'>\s]+)',
                        html3,
                        re.I,
                    ):
                        hop = urljoin(final3, "/AUSSTATS/abs@.nsf/" + match.group(1))
                        st4, html4, final4 = _get_html(http, hop)
                        tried.append({"url": hop, "status": st4})
                        if st4 and st4 < 400 and html4:
                            for m2 in re.finditer(
                                r'(/AUSSTATS/subscriber\.nsf/log\?openagent&[^\"\'>\s]+)',
                                html4,
                                re.I,
                            ):
                                candidates.append(urljoin(final4, m2.group(1).replace("&amp;", "&")))

    # Prefer a single All-workbooks.zip; else take legacy xls cubes (cap at 20)
    zips = [u for u in candidates if u.lower().endswith(".zip") or "all-workbooks" in u.lower()]
    if zips:
        chosen = zips[:1]
    else:
        # Prefer commonwealth/state/local expense tables (do001–do018-ish)
        xls = []
        seen: set[str] = set()
        for u in candidates:
            key = u.split("&")[1] if "openagent&" in u else u
            if key in seen:
                continue
            seen.add(key)
            if re.search(r"55120do\d+", u, re.I) or u.lower().endswith((".xls", ".xlsx")):
                xls.append(u)
        chosen = xls[:20]
    return {"fy": fy, "tried": tried, "candidates": candidates, "chosen": chosen}


def discover_fbo_year(http: HTTPClient, fy: str) -> dict:
    """Discover FBO PDF via index-page parsing (not fixed filename probes).

    Treasury changed FBO filenames almost every year (_consolidated, -Consolidated,
    _Combined, _web, doubled .pdf, etc.). Directory listings often 403, but
    archive.budget.gov.au/<fy>/index.htm reliably links the real file.
    """
    tried: list[dict] = []
    discovered: list[str] = []

    index_pages = [
        f"{ARCHIVE_BASE}/{fy}/index.htm",
        f"{ARCHIVE_BASE}/{fy}/",
        f"{ARCHIVE_BASE}/{fy}/fbo/index.htm",
        f"{ARCHIVE_BASE}/{fy}/fbo/",
        f"{ARCHIVE_BASE}/{fy}-october/index.htm",
        f"{ARCHIVE_BASE}/{fy}-october/fbo/",
        f"{ARCHIVE_BASE}/{fy}-october/fbo/download/",
        f"{ARCHIVE_BASE}/{fy}/final_outcome/",
        f"{ARCHIVE_BASE}/{fy}/final_outcome/index.htm",
    ]
    for index in index_pages:
        st, html, final = _get_html(http, index)
        tried.append({"url": index, "status": st})
        if not (st and st < 400 and html):
            continue
        for u in _pdf_or_xlsx_links(html, final):
            if re.search(r"fbo|final[_\s-]?outcome|appendix[_-]?a|05_appendix", u, re.I):
                discovered.append(u)
        for match in re.finditer(
            r'href=["\']([^"\']*(?:fbo|final_outcome|appendix)[^"\']*\.pdf[^"\']*)["\']',
            html,
            re.I,
        ):
            discovered.append(urljoin(final, match.group(1)))

    y0, y1 = fy.split("-")
    seeds = [
        f"{ARCHIVE_BASE}/{fy}/fbo/download/05_appendix_a.pdf",
        f"{ARCHIVE_BASE}/{fy}-october/fbo/download/05_appendix_a.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/fbo_{fy}_consolidated.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/{fy}_FBO_Consolidated.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO-{fy}-Consolidated.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO-{fy}-Consolidated.pdf.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO_{fy}_Consolidated.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO_Consolidated.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO-{fy}.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO_{fy}.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO_{fy}_Combined.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/FBO_{fy}_web.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/{y0}_{y1}_FBO.pdf",
        f"{ARCHIVE_BASE}/{fy}/final_outcome/fbo.pdf",
        f"{ARCHIVE_BASE}/{fy}/fbo/fbo.pdf",
    ]
    discovered.extend(seeds)

    seen: set[str] = set()
    ordered: list[str] = []
    for u in discovered:
        if not u or u in seen:
            continue
        seen.add(u)
        ordered.append(u)

    def rank(u: str) -> tuple[int, str]:
        low = u.lower()
        if re.search(r"appendix[_-]?a|05_appendix", low):
            return (0, u)
        if "consolidat" in low or "combined" in low:
            return (1, u)
        if "web" in low:
            return (2, u)
        if "fbo" in low or "final_outcome" in low:
            return (3, u)
        return (9, u)

    ranked = sorted(ordered, key=rank)
    pick: list[str] = []
    for u in ranked:
        if _probe_url_ok(http, u):
            pick.append(u)
            break
    return {"fy": fy, "tried": tried, "candidates": ordered, "chosen": pick}


def discover_pre_fbo_year(http: HTTPClient, fy: str) -> dict:
    """Best-effort discovery of pre-FBO budget statement PDFs (1983-84–1995-96)."""
    tried: list[dict] = []
    probes = [
        f"{ARCHIVE_BASE}/{fy}/index.htm",
        f"{ARCHIVE_BASE}/{fy}/",
        f"{ARCHIVE_BASE}/{fy}/statement3/bst03.pdf",
        f"{ARCHIVE_BASE}/{fy}/downloads/Budget_{fy}.pdf",
        f"{ARCHIVE_BASE}/{fy}/downloads/budget_{fy}.pdf",
        f"{ARCHIVE_BASE}/{fy}/downloads/Budget_Paper_No.1.pdf",
        f"{ARCHIVE_BASE}/{fy}/downloads/Budget_{fy}_-_BP1_-_Statement_No_2.pdf",
        f"{ARCHIVE_BASE}/{fy}/bp1/bp1.pdf",
        # Some mid-1980s years only expose numbered papers at the year root
        # (e.g. 1985-86/1985-86_Budget_Paper_No.7.pdf); index.htm may 404.
        f"{ARCHIVE_BASE}/{fy}/{fy}_Budget_Paper_No.1.pdf",
        f"{ARCHIVE_BASE}/{fy}/{fy}_Budget_Paper_No.7.pdf",
        f"{ARCHIVE_BASE}/{fy}/Budget_{fy}.pdf",
        f"{ARCHIVE_BASE}/{fy}/Budget_{fy}_-_BP1_-_Statement_No_2.pdf",
    ]
    if fy == "1987-88":
        probes.append(f"{ARCHIVE_BASE}/1987-88/downloads/Budget_1987-88.pdf")
    if fy == "1996-97":
        probes.append(f"{ARCHIVE_BASE}/1996-97/statement3/bst03.pdf")

    chosen: list[str] = []
    for url in probes:
        st, html, final = _get_html(http, url)
        tried.append({"url": url, "status": st})
        if st and st < 400:
            if url.lower().endswith(".pdf"):
                if _probe_url_ok(http, final or url):
                    chosen.append(final or url)
            elif html:
                links = _pdf_or_xlsx_links(html, final)
                ranked = sorted(
                    links,
                    key=lambda u: (
                        0
                        if re.search(
                            r"statement|outlay|bst0|budget_paper|bp1|downloads/Budget",
                            u,
                            re.I,
                        )
                        else 1,
                        u,
                    ),
                )
                for u in ranked:
                    if _probe_url_ok(http, u):
                        chosen.append(u)
                    if len(chosen) >= 3:
                        break

    seen: set[str] = set()
    unique = []
    for u in chosen:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return {"fy": fy, "tried": tried, "candidates": unique, "chosen": unique[:3]}


def download_urls(
    source: Source,
    context: AdapterContext,
    urls: list[str],
    *,
    fy: str,
    series: str,
) -> list[dict]:
    adapter = BaseAdapter()
    results: list[dict] = []
    for index, url in enumerate(urls):
        if not _probe_url_ok(context.http, url):
            results.append({"url": url, "fy": fy, "status": "probe_failed"})
            continue
        hint = filename_from_url(url, f"{series}_{fy}_{index+1}")
        # AUSSTATS subscriber.nsf embeds filename as openagent&NAME.xls&...
        m = re.search(r"openagent&([^&]+\.(?:xls|xlsx|zip|pdf))", url, re.I)
        if m:
            hint = m.group(1)
        # Prefix FY so multi-year assets don't collide
        if fy not in hint:
            hint = f"{fy}_{hint}"
        asset = Asset(
            source_id=source.id,
            asset_instance_id=f"{source.id}:{fy}:{safe_filename(hint).rsplit('.', 1)[0]}",
            requested_url=url,
            title=f"{source.title} ({fy})",
            expected_formats=source.formats,
            financial_year=fy or infer_financial_year(url),
            filename_hint=hint,
            discovery_url=source.landing_url,
            metadata={"adapter": "historical_backfill", "series": series},
        )
        if context.run.dry_run:
            results.append({"url": url, "fy": fy, "status": "dry_run", "asset": asset.asset_instance_id})
            continue
        acquisition = adapter.fetch(source, asset, context)
        results.append(
            {
                "url": url,
                "fy": fy,
                "status": acquisition.status.value,
                "bytes": acquisition.bytes,
                "stored_path": acquisition.stored_path,
                "error": acquisition.error_message,
            }
        )
        print(
            f"  {acquisition.status.value:20s} {fy} {hint[:60]} bytes={acquisition.bytes}",
            flush=True,
        )
    return results


def run_series(series: str, years: list[str], context: AdapterContext, args: argparse.Namespace) -> dict:
    if series == "abs_gfs":
        source = source_by_id("abs_gfs_previous_releases")
        discover = discover_abs_year
    elif series == "fbo_archive":
        source = source_by_id("federal_budget_archive_function_series")
        # Skip 2024-25 — already under federal_fbo_2024_25_function_subfunction
        years = [y for y in years if y != "2024-25"]
        discover = discover_fbo_year
    elif series == "pre_fbo_budget":
        source = source_by_id("federal_budget_archive_function_series")
        discover = discover_pre_fbo_year
    else:
        raise SystemExit(f"unknown series: {series}")

    context.store.prepare_snapshot(source)
    discovery_log: list[dict] = []
    download_log: list[dict] = []

    print(f"=== {series} → {source.id} ({len(years)} years) run={context.run.run_id} ===", flush=True)
    for fy in years:
        print(f"-- discover {fy}", flush=True)
        meta = discover(context.http, fy)
        discovery_log.append(meta)
        chosen = meta.get("chosen") or []
        if not chosen:
            print(f"  no candidates for {fy}", flush=True)
            download_log.append({"fy": fy, "status": "no_candidates"})
            continue
        # For FBO, stop after first successful download of the year
        year_results = download_urls(source, context, chosen, fy=fy, series=series)
        download_log.extend(year_results)
        if series in {"fbo_archive", "pre_fbo_budget"}:
            ok = any(r.get("status") in {"downloaded", "unchanged"} for r in year_results)
            if ok:
                continue

    evidence = {
        "series": series,
        "years": years,
        "discovery": discovery_log,
        "downloads": download_log,
        "run_id": context.run.run_id,
    }
    context.store.write_discovery(source, evidence)

    # Build latest.json from successful assets in this run
    success = [
        {
            "status": item["status"],
            "requested_url": item.get("url"),
            "stored_path": item.get("stored_path"),
            "bytes": item.get("bytes"),
            "financial_year": item.get("fy"),
        }
        for item in download_log
        if item.get("status") in {"downloaded", "unchanged"}
    ]
    if success and not args.dry_run:
        context.store.update_latest(source, success)
        context.store.write_acquisition(source, {"assets": success, "series": series})

    report = {
        "run_id": context.run.run_id,
        "series": series,
        "source_id": source.id,
        "years": years,
        "downloaded": sum(1 for i in download_log if i.get("status") == "downloaded"),
        "unchanged": sum(1 for i in download_log if i.get("status") == "unchanged"),
        "failed_or_missing": sum(
            1
            for i in download_log
            if i.get("status") not in {"downloaded", "unchanged"}
        ),
        "disk_budget": context.budget.as_dict(),
        "downloads": download_log,
    }
    write_json_atomic(
        context.run.reports_root / f"{context.run.run_id}-{series}.json",
        report,
    )
    print(
        f"report: data/.procurement/reports/{context.run.run_id}-{series}.json "
        f"downloaded={report['downloaded']} unchanged={report['unchanged']} "
        f"other={report['failed_or_missing']}",
        flush=True,
    )
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--series",
        required=True,
        choices=["abs_gfs", "fbo_archive", "pre_fbo_budget"],
    )
    parser.add_argument(
        "--years",
        required=True,
        help="FY range start:end (e.g. 2007-08:2023-24) or comma-separated list",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-total-bytes", type=int, default=8 * GIB)
    parser.add_argument("--max-file-bytes", type=int, default=600 * 1024**2)
    parser.add_argument("--connect-timeout", type=float, default=15)
    parser.add_argument("--read-timeout", type=float, default=180)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    years = parse_years(args.years)
    context = build_context(args)
    report = run_series(args.series, years, context, args)
    # Non-zero only if nothing at all succeeded and not dry-run
    if args.dry_run:
        return 0
    if report["downloaded"] + report["unchanged"] == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
