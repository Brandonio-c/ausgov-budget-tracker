#!/usr/bin/env python3
"""Print the current manual/blocked acquisition queue vs what's already on disk.

Reads config/procurement_sources.yaml, data/raw/**/latest.json, and the known
block-class map from the 2026-07-22 handoff. Suggests the next command for each
outstanding source (headed browser session vs batch import vs automated fetch).

Usage:
    python scripts/procure_acquisition_queue.py
    python scripts/procure_acquisition_queue.py --json
    python scripts/procure_acquisition_queue.py --status need
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from procure.registry import DEFAULT_REGISTRY, RegistryError, load_registry  # noqa: E402
from procure.storage import write_json_atomic  # noqa: E402

REPO_ROOT = DEFAULT_REGISTRY.parents[1]

# Block classes from ops/manual-acquisition-handoff-20260722.md — kept here so
# the queue does not re-litigate classifications that already had independent repro.
BLOCK_CLASS: dict[str, str] = {
    "act_actual_financial_publications": "cloudflare",
    "act_budget_2026_27": "cloudflare",
    "nt_budget_2026_27": "cloudflare",
    "nt_treasury_annual_reports": "cloudflare",
    "sa_budget_2026_27": "cloudflare",
    "sa_councils_in_focus": "cloudflare",
    "sa_final_budget_outcome_and_cfr": "cloudflare",
    "sa_tenders_contracts": "cloudflare",
    "tas_local_cdc": "cloudflare",
    "vic_local_budget_and_reporting_models": "cloudflare",
    "vic_local_vgc_abs_returns": "cloudflare",
    "vic_budget_2026_27": "section_io",
    "vic_dtf_annual_report_bpo": "section_io",
    "vic_financial_report_2024_25": "section_io",
    "nsw_buy_register": "cloudfront",
    "federal_grantconnect": "cloudfront",
    "federal_cfs_2024_25": "stream_reset",
    "federal_dss_pbs_2026_27": "stream_reset",
    "federal_dva_pbs_2026_27": "stream_reset",
    "federal_health_disability_ageing_pbs_2026_27": "stream_reset",
    "federal_ndia_pbs_2026_27": "stream_reset",
    "federal_social_services_pbs_2025_26_archive": "stream_reset",
    "services_australia_annual_reports": "stream_reset",
    "qld_qgip_expenditure": "aws_waf",
}

NO_BULK = {
    "federal_austender_weekly_export",
    "nt_local_grants_commission_return",
    "wa_tenders",
    "wa_mycouncil",
    # Confirmed 2026-07-22: interactive portals / agency-by-agency browse only —
    # no single public bulk dump (same class as wa_tenders / austender weekly).
    "sa_councils_in_focus",  # dashboard + council login; LGGC underlying returns not published as bulk files here
    "sa_tenders_contracts",  # awarded contracts listed per agency; no statewide export
    # Confirmed 2026-07-24: no single public bulk file for these registry rows.
    "federal_transparency_pbs_set_16",  # TP has no bulk PBS zip; individual 2025-26 PBS already acquired
    "qld_sds_machine_readable_2025_26",  # QLD open-data SDS machine pack not published for 2025-26
    "vic_local_govt_financial",  # VAGO local-gov financials are portal/browse, not one bulk export
}

# Historical candidate note — source is now direct_file; kept only if registry
# somehow reverts off direct_file while latest.json is still missing.
CANDIDATE = {
    "nt_awarded_government_contracts": "direct_file ExportTenderers on tendersonline.nt.gov.au",
}

FLAKY = {"qld_local_qao_2025"}

DOMAIN_GROUPS: dict[str, list[str]] = {
    "act_treasury": ["act_actual_financial_publications", "act_budget_2026_27"],
    "nt": ["nt_budget_2026_27", "nt_treasury_annual_reports"],
    "sa": [
        "sa_budget_2026_27",
        "sa_final_budget_outcome_and_cfr",
        "sa_councils_in_focus",
        "sa_tenders_contracts",
    ],
    "vic_dtf": ["vic_budget_2026_27", "vic_dtf_annual_report_bpo", "vic_financial_report_2024_25"],
    "vic_local": ["vic_local_budget_and_reporting_models", "vic_local_vgc_abs_returns"],
    "tas": ["tas_local_cdc"],
    "nsw_cloudfront": ["nsw_buy_register"],
    "grantconnect": ["federal_grantconnect"],
    "services_australia": ["services_australia_annual_reports"],
    "qld_data": ["qld_qgip_expenditure"],
    "stream_reset_done": [
        "federal_dss_pbs_2026_27",
        "federal_dva_pbs_2026_27",
        "federal_health_disability_ageing_pbs_2026_27",
        "federal_ndia_pbs_2026_27",
        "federal_social_services_pbs_2025_26_archive",
        "federal_cfs_2024_25",
    ],
}


def _latest_path(source) -> Path | None:
    path = REPO_ROOT / "data" / "raw" / source.government_level / source.id / "latest.json"
    return path if path.is_file() else None


def _asset_count(latest: Path) -> int:
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    return len(payload.get("assets") or [])


def _domain_group(source_id: str) -> str | None:
    for name, members in DOMAIN_GROUPS.items():
        if source_id in members:
            return name
    return None


def _suggest(status: str, source_id: str, landing_url: str, block_class: str | None) -> str:
    if status == "done":
        return "(already on disk)"
    if status == "no_bulk":
        return "(no public bulk file — skip)"
    if status == "candidate":
        return f"python scripts/procure_sources.py --source-ids {source_id} --read-timeout 120"
    if status == "flaky":
        return (
            f"python scripts/procure_sources.py --source-ids {source_id} "
            f"# sparse retry; else: python scripts/procure_browser_session.py --source-id {source_id}"
        )
    if block_class:
        group = _domain_group(source_id)
        if group:
            return f"python scripts/procure_browser_session.py --domain-group {group}"
        return f"python scripts/procure_browser_session.py --source-id {source_id}"
    return f"# open {landing_url} then drop into data/manual_inbox/_downloads/"


def classify(source) -> dict[str, Any]:
    latest = _latest_path(source)
    inbox_readme = REPO_ROOT / "data" / "manual_inbox" / source.id / "README.md"
    block_class = BLOCK_CLASS.get(source.id)
    host = urlparse(source.landing_url).hostname or ""

    if source.id in NO_BULK:
        status = "no_bulk"
    elif source.id in FLAKY or bool(source.access.get("known_flaky")):
        status = "done" if latest else "flaky"
    elif source.id in CANDIDATE and source.access_method.value != "direct_file":
        status = "done" if latest else "candidate"
    elif latest:
        status = "done"
    elif block_class or source.access_method.value in {"manual", "web_portal"}:
        status = "need"
    else:
        status = "automated"

    return {
        "source_id": source.id,
        "status": status,
        "title": source.title,
        "landing_url": source.landing_url,
        "host": host,
        "block_class": block_class,
        "domain_group": _domain_group(source.id),
        "access_method": source.access_method.value,
        "priority": source.priority,
        "government_level": source.government_level,
        "asset_count": _asset_count(latest) if latest else 0,
        "latest_json": str(latest.relative_to(REPO_ROOT)) if latest else None,
        "inbox_readme": str(inbox_readme.relative_to(REPO_ROOT)) if inbox_readme.is_file() else None,
        "candidate_note": CANDIDATE.get(source.id),
        "suggested_command": _suggest(status, source.id, source.landing_url, block_class),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument(
        "--status",
        help="comma-separated statuses to include (need,done,no_bulk,flaky,candidate,automated)",
    )
    parser.add_argument(
        "--write",
        type=Path,
        help="also write the full queue JSON to this path (default under data/.procurement/reports/)",
    )
    parser.add_argument("--all-sources", action="store_true", help="include fully automated sources too")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        _, sources = load_registry()
    except RegistryError as error:
        print(f"registry error: {error}", file=sys.stderr)
        return 1

    rows = [classify(source) for source in sources]
    if not args.all_sources:
        rows = [row for row in rows if row["status"] != "automated"]

    wanted = None
    if args.status:
        wanted = {item.strip() for item in args.status.split(",") if item.strip()}
        rows = [row for row in rows if row["status"] in wanted]

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "items": rows,
    }

    out_path = args.write
    if out_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = REPO_ROOT / "data" / ".procurement" / "reports" / f"acquisition-queue-{stamp}.json"
    write_json_atomic(out_path, payload)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"acquisition queue  counts={counts}")
        print(f"wrote {out_path.relative_to(REPO_ROOT)}")
        print()
        for row in sorted(rows, key=lambda item: (item["status"], item["block_class"] or "", item["source_id"])):
            assets = f" assets={row['asset_count']}" if row["asset_count"] else ""
            block = f" [{row['block_class']}]" if row["block_class"] else ""
            print(f"{row['status']:10} {row['source_id']}{block}{assets}")
            print(f"           {row['suggested_command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
