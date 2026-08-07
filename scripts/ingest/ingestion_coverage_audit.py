#!/usr/bin/env python3
"""Repository-wide acquisition→ingestion coverage audit.

Joins procurement registry, data/raw/**/latest.json, config/mappings, ingest
code references, and facts.db counts. Writes timestamped JSON + Markdown under
ops/reports/.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from procure.registry import load_registry  # noqa: E402

FACTS_DB = REPO_ROOT / "data" / "facts.db"
RAW = REPO_ROOT / "data" / "raw"
MAPPINGS = REPO_ROOT / "config" / "mappings"
INGEST = REPO_ROOT / "scripts" / "ingest"
REPORTS = REPO_ROOT / "ops" / "reports"
CANONICAL_DATASETS = REPO_ROOT / "config" / "lineage" / "canonical_datasets.yaml"

STATUSES = (
    "fully_ingested",
    "partially_ingested",
    "acquired_not_ingested",
    "adapter_missing",
    "adapter_broken",
    "reference_only",
    "duplicate_source",
    "no_useful_fiscal_data",
    "officially_unavailable",
    "not_acquired",
)

# Handoff / alias IDs whose content is already ingested under a canonical key.
DUPLICATE_ALIASES: dict[str, str] = {
    "abs_gfs_commonwealth_2024_25": "abs_gfs_commonwealth_130",
    "abs_gfs_nsw_state_2024_25": "abs_gfs_state_nsw_231",
    "abs_gfs_vic_state_2024_25": "abs_gfs_state_vic_232",
    "abs_gfs_qld_state_2024_25": "abs_gfs_state_qld_233",
    "abs_gfs_sa_state_2024_25": "abs_gfs_state_sa_234",
    "abs_gfs_wa_state_2024_25": "abs_gfs_state_wa_235",
    "abs_gfs_tas_state_2024_25": "abs_gfs_state_tas_236",
    "abs_gfs_nt_state_2024_25": "abs_gfs_state_nt_237",
    "abs_gfs_act_state_2024_25": "abs_gfs_state_act_238",
    "abs_gfs_nsw_local_2024_25": "abs_gfs_local_nsw_331",
    "abs_gfs_vic_local_2024_25": "abs_gfs_local_vic_332",
    "abs_gfs_qld_local_2024_25": "abs_gfs_local_qld_333",
    "abs_gfs_sa_local_2024_25": "abs_gfs_local_sa_334",
    "abs_gfs_wa_local_2024_25": "abs_gfs_local_wa_335",
    "abs_gfs_tas_local_2024_25": "abs_gfs_local_tas_336",
    "abs_gfs_nt_local_2024_25": "abs_gfs_local_nt_337",
    "federal_fbo_appendix_a_2024_25": "federal_fbo_2024_25_function_subfunction",
    "federal_social_services_pbs_2025_26_archive": "federal_pbs_programs_all",
    "federal_pbs_2025_26_social_services_portfolio": "federal_pbs_programs_all",
    # Earlier handoff IDs duplicate the later canonical 2026-27 registry
    # entries byte-for-byte (matching latest.json SHA-256 values).
    "federal_defence_pbs_2026_27": "federal_pbs_2026_27_defence",
    "federal_dss_pbs_2026_27": "federal_pbs_2026_27_social_services",
    "federal_dva_pbs_2026_27": "federal_pbs_2026_27_veterans_affairs",
    "federal_education_pbs_2026_27": "federal_pbs_2026_27_education",
    "federal_health_disability_ageing_pbs_2026_27": "federal_pbs_2026_27_health_disability_ageing",
    "federal_ndia_pbs_2026_27": "federal_pbs_2026_27_ndia",
    "sa_final_budget_outcome_cfr_2024_25": "sa_final_budget_outcome_and_cfr",
    "sa_lggc_council_database_reports": "sa_lggc_publications_database_reports",
    "nt_grants_commission_annual_reports": "nt_local_grants_commission_reports",
    "federal_cfs_2024_25_notes": "federal_cfs_2024_25",
}

NO_BULK = {
    "federal_austender_weekly_export",
    "nt_local_grants_commission_return",
    "wa_tenders",
    "wa_mycouncil",
    "sa_councils_in_focus",
    "sa_tenders_contracts",
    "federal_transparency_pbs_set_16",
    # qld_sds_machine_readable_2025_26 removed 2026-07-31: official CKAN CSV
    # resources are confirmed real and live (verified directly), just gated by
    # QLD's known WAF challenge on direct download - that's an acquisition
    # blocker (browser session pending), not an absence of a bulk export.
    # vic_local_govt_financial removed 2026-07-31: raw file, its meta.json, and
    # all 1,700 facts' citations fully reconcile on disk (verified directly) -
    # this source was only misclassified because the disk-detection check
    # below requires latest.json, which this source predates.
}

REFERENCE_ONLY = {
    "cofog_a_classification",
    "commonwealth_balance_sheet_user_guide",
    "abn_bulk_extract_resource_index",
    "anzsic_2006_revision_2",
    "federal_pbs_index_2026_27",
}

# Visualization-value ranks for acquired-not-ingested prioritisation (lower = higher value).
VALUE_RANK_RULES: list[tuple[int, re.Pattern[str], str]] = [
    (10, re.compile(r"^federal_pbs_|_pbs_"), "commonwealth_pbs_program_depth"),
    (20, re.compile(r"^abs_asna_|^abs_qna_|^abs_state_accounts"), "gdp_gva_gsp"),
    (25, re.compile(r"^abs_taxation"), "tax_revenue_detail"),
    (30, re.compile(r"borrowing|tcorp|tcv|qtc|safa|watc|nttc|tascorp|aofm_"), "debt_instruments"),
    (35, re.compile(r"cfs_|csc_|superannuation|pss_css"), "superannuation_liabilities"),
    (40, re.compile(r"_sds_|agency_statements|budget_tables|budget_paper|budgeted_financial"), "state_budget_depth"),
    (50, re.compile(r"local_|lggc|qao_local|vgc|olg_"), "local_government"),
    (60, re.compile(r"^federal_mfs_"), "monthly_financial_statements_slice"),
    (70, re.compile(r"grantconnect|austender|dss_|ndis_|invoice"), "grants_contracts_payments"),
    (90, re.compile(r".*"), "other"),
]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _latest_info(source_id: str) -> dict[str, Any] | None:
    matches = [
        m
        for m in RAW.rglob(source_id)
        if m.is_dir() and m.name == source_id and (m / "latest.json").exists()
    ]
    if not matches:
        return None
    path = matches[0]
    data = json.loads((path / "latest.json").read_text(encoding="utf-8"))
    assets = data.get("assets") or []
    formats: list[str] = []
    files: list[str] = []
    for asset in assets:
        stored = asset.get("stored_path") or ""
        files.append(stored)
        det = (asset.get("detected_type") or Path(stored).suffix.lstrip(".") or "").lower()
        if det:
            formats.append(det)
    return {
        "latest_json": str(path.relative_to(REPO_ROOT) / "latest.json"),
        "asset_count": len(assets),
        "files": files[:20],
        "formats": sorted(set(formats)),
        "run_id": data.get("run_id"),
    }


def _mapping_ids() -> set[str]:
    out: set[str] = set()
    for path in MAPPINGS.glob("*.yaml"):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        sid = doc.get("source_id") or path.stem
        out.add(str(sid))
    return out


def _ingest_code_refs() -> set[str]:
    refs: set[str] = set()
    pattern = re.compile(r"['\"]([a-z][a-z0-9_]{6,})['\"]")
    for path in INGEST.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            token = match.group(1)
            if any(
                token.startswith(p)
                for p in (
                    "abs_",
                    "federal_",
                    "nsw_",
                    "vic_",
                    "qld_",
                    "sa_",
                    "wa_",
                    "tas_",
                    "nt_",
                    "act_",
                    "aofm_",
                    "csc_",
                    "commonwealth_",
                )
            ):
                refs.add(token)
    return refs


def _facts_by_source(conn: sqlite3.Connection | None) -> dict[str, dict[str, Any]]:
    if conn is None:
        return {}
    rows = conn.execute(
        """
        SELECT d.source_key,
               COUNT(*) AS fact_count,
               GROUP_CONCAT(DISTINCT f.measure_type) AS measures,
               MAX(LENGTH(n.name) - LENGTH(REPLACE(n.name, '/', '')) + 1) AS max_depth
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        LEFT JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        LEFT JOIN nodes n ON n.id = fn.node_id
        GROUP BY d.source_key
        """
    ).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for source_key, fact_count, measures, max_depth in rows:
        out[source_key] = {
            "fact_count": int(fact_count),
            "measures": [m for m in (measures or "").split(",") if m],
            "hierarchy_depth": int(max_depth or 1),
        }
    return out


def _facts_by_origin(
    conn: sqlite3.Connection | None,
    datasets: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Summarise facts by the raw source ID retained in their citation.

    Generalised adapters publish under one source_document key, but retain
    the originating registry source as ``source_id:<id>`` in every locator.
    Reading that field gives the coverage audit truthful per-source lineage
    without duplicating source_documents or changing published facts.
    """
    if conn is None:
        return {}
    source_keys = sorted(
        {
            key
            for dataset in datasets
            if dataset.get("origin_lineage") == "locator_source_id"
            for key in (dataset.get("fact_source_keys") or [])
        }
    )
    if not source_keys:
        return {}
    placeholders = ",".join("?" for _ in source_keys)
    rows = conn.execute(
        f"""
        SELECT f.measure_type,
               n.name,
               json_extract(f.source_locator_json, '$.locator') AS locator
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        LEFT JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        LEFT JOIN nodes n ON n.id = fn.node_id
        WHERE d.source_key IN ({placeholders})
          AND json_extract(f.source_locator_json, '$.locator') LIKE '%source_id:%'
        """,
        source_keys,
    ).fetchall()
    counts: Counter[str] = Counter()
    measures: dict[str, set[str]] = {}
    depths: dict[str, int] = {}
    pattern = re.compile(r"(?:^|\|\s*)source_id:([^|]+)")
    for measure_type, node_name, locator in rows:
        match = pattern.search(locator or "")
        if not match:
            continue
        source_id = match.group(1).strip()
        counts[source_id] += 1
        measures.setdefault(source_id, set()).add(measure_type)
        depth = (str(node_name).count("/") + 1) if node_name else 1
        depths[source_id] = max(depths.get(source_id, 1), depth)
    return {
        source_id: {
            "fact_count": count,
            "measures": sorted(measures[source_id]),
            "hierarchy_depth": depths[source_id],
        }
        for source_id, count in counts.items()
    }


def _load_canonical_datasets() -> list[dict[str, Any]]:
    if not CANONICAL_DATASETS.is_file():
        return []
    doc = yaml.safe_load(CANONICAL_DATASETS.read_text(encoding="utf-8")) or {}
    return doc.get("datasets") or []


def _family_coverage(
    source_id: str,
    detected_formats: list[str],
    datasets: list[dict[str, Any]],
    facts: dict[str, dict[str, Any]],
) -> tuple[str, str] | None:
    """Return (canonical_dataset_id, coverage_status) if this source is
    served by a shared family adapter (declared in canonical_datasets.yaml)
    rather than its own dedicated mapping - e.g. one of the 63 individual
    PBS portfolio PDFs, ingested via the generalized pbs_programs_all
    extractor rather than a per-source_id mapping file. None if no
    declared family matches, the family has zero facts loaded, or this
    source's own asset formats aren't among the family's handled_formats
    (e.g. an HTML index page that matches the source_id pattern but isn't
    actually processed by the extractor)."""
    for ds in datasets:
        prefixes = ds.get("raw_source_id_prefixes") or []
        if not any(p in source_id for p in prefixes):
            continue
        handled = ds.get("handled_formats")
        if handled and not (set(detected_formats) & set(handled)):
            continue
        keys = ds.get("fact_source_keys") or []
        if any(int((facts.get(k) or {}).get("fact_count") or 0) > 0 for k in keys):
            return ds["canonical_dataset_id"], ds.get("coverage_status") or "partially_ingested"
    return None


def _value_rank(source_id: str) -> tuple[int, str]:
    for rank, pattern, label in VALUE_RANK_RULES:
        if pattern.search(source_id):
            return rank, label
    return 99, "other"


def classify(
    source_id: str,
    *,
    acquired: dict[str, Any] | None,
    mapping_ids: set[str],
    code_refs: set[str],
    facts: dict[str, dict[str, Any]],
    origin_facts: dict[str, dict[str, Any]] | None = None,
    canonical_datasets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fact_info = facts.get(source_id) or {}
    fact_count = int(fact_info.get("fact_count") or 0)
    # Also count alias canonical facts for duplicate detection display
    canonical = DUPLICATE_ALIASES.get(source_id)
    if fact_count == 0 and canonical and canonical in facts:
        fact_count = int(facts[canonical]["fact_count"])
        fact_info = facts[canonical]

    has_mapping = source_id in mapping_ids or source_id in code_refs
    has_files = acquired is not None and acquired.get("asset_count", 0) > 0

    family = None
    origin_fact_info = (origin_facts or {}).get(source_id) or {}
    if fact_count == 0 and origin_fact_info:
        fact_count = int(origin_fact_info.get("fact_count") or 0)
        fact_info = origin_fact_info
    if (
        canonical is None
        and fact_count > 0
        and has_files
        and canonical_datasets
        and source_id in (origin_facts or {})
    ):
        family = _family_coverage(
            source_id, (acquired or {}).get("formats") or [], canonical_datasets, facts
        )

    if source_id in NO_BULK:
        status = "officially_unavailable"
        reason = "no_public_bulk_export"
        next_action = "leave_as_no_bulk"
    elif source_id in REFERENCE_ONLY and has_files:
        status = "reference_only"
        reason = "classification_or_index_asset_not_fiscal_time_series"
        next_action = "keep_as_reference"
    elif source_id in DUPLICATE_ALIASES:
        status = "duplicate_source"
        reason = f"canonical={DUPLICATE_ALIASES[source_id]}"
        next_action = "do_not_double_ingest"
    elif not has_files:
        status = "not_acquired"
        reason = "no_latest_json"
        next_action = "acquire_or_exclude"
    elif family is not None:
        canonical_dataset_id, family_status = family
        status = family_status
        reason = f"covered_via_family_adapter:{canonical_dataset_id}"
        next_action = "maintain_family_adapter"
    elif fact_count > 0 and has_mapping:
        # Heuristic: PBS aggregator covers many PDFs — treat portfolio PBS as partial if only via aggregator
        if source_id.startswith("federal_pbs_") and source_id not in (
            "federal_pbs_programs_all",
            "federal_dss_pbs_programs",
            "federal_health_pbs_programs",
        ):
            status = "partially_ingested"
            reason = "covered_via_pbs_programs_all_aggregator"
            next_action = "improve_per_portfolio_lineage"
        else:
            status = "fully_ingested"
            reason = None
            next_action = "maintain"
    elif fact_count > 0:
        status = "partially_ingested"
        reason = "facts_present_without_dedicated_mapping_file"
        next_action = "add_explicit_mapping"
    elif has_mapping and has_files:
        status = "adapter_broken"
        reason = "mapping_or_adapter_exists_but_zero_facts"
        next_action = "fix_or_re_run_adapter"
    elif has_files and not has_mapping:
        status = "adapter_missing"
        reason = "acquired_on_disk_no_ingest_wiring"
        next_action = "build_adapter"
    else:
        status = "acquired_not_ingested"
        reason = "on_disk_not_loaded"
        next_action = "ingest"

    rank, viz_bucket = _value_rank(source_id)
    return {
        "ingestion_status": status,
        "fact_count": int(fact_info.get("fact_count") or 0),
        "measures": fact_info.get("measures") or [],
        "hierarchy_depth": fact_info.get("hierarchy_depth"),
        "has_mapping": has_mapping,
        "reason_for_zero_facts": reason if fact_count == 0 else None,
        "next_ingestion_action": next_action,
        "viz_value_rank": rank,
        "viz_bucket": viz_bucket,
        "canonical_of": canonical,
        "adapter_family": family[0] if family is not None else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=FACTS_DB)
    parser.add_argument("--write-dir", type=Path, default=REPORTS)
    args = parser.parse_args(argv)

    _, sources = load_registry()
    mapping_ids = _mapping_ids()
    code_refs = _ingest_code_refs()
    canonical_datasets = _load_canonical_datasets()
    conn = sqlite3.connect(str(args.db)) if args.db.exists() else None
    facts = _facts_by_source(conn)
    origin_facts = _facts_by_origin(conn, canonical_datasets)
    total_facts = 0
    if conn:
        total_facts = int(conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0])
        conn.close()

    rows: list[dict[str, Any]] = []
    for source in sources:
        acquired = _latest_info(source.id)
        classified = classify(
            source.id,
            acquired=acquired,
            mapping_ids=mapping_ids,
            code_refs=code_refs,
            facts=facts,
            origin_facts=origin_facts,
            canonical_datasets=canonical_datasets,
        )
        rows.append(
            {
                "source_id": source.id,
                "publisher": source.publisher,
                "jurisdiction": source.jurisdiction,
                "government_level": source.government_level,
                "source_family": source.source_family,
                "priority": source.priority,
                "title": source.title,
                "landing_url": source.landing_url,
                "acquisition_status": "acquired" if acquired else "missing",
                "files_on_disk": (acquired or {}).get("files") or [],
                "detected_formats": (acquired or {}).get("formats") or [],
                "asset_count": (acquired or {}).get("asset_count") or 0,
                "latest_json": (acquired or {}).get("latest_json"),
                "parser_or_adapter": (
                    "mapping:" + source.id
                    if source.id in mapping_ids
                    else ("code_ref" if source.id in code_refs else None)
                ),
                **classified,
            }
        )

    # Orphan latest.json dirs not in registry
    registry_ids = {s.id for s in sources}
    for latest in RAW.rglob("latest.json"):
        sid = latest.parent.name
        if sid in registry_ids:
            continue
        acquired = _latest_info(sid)
        classified = classify(
            sid,
            acquired=acquired,
            mapping_ids=mapping_ids,
            code_refs=code_refs,
            facts=facts,
            origin_facts=origin_facts,
            canonical_datasets=canonical_datasets,
        )
        rows.append(
            {
                "source_id": sid,
                "publisher": None,
                "jurisdiction": None,
                "government_level": latest.parent.parent.name,
                "source_family": "orphan_raw",
                "priority": None,
                "title": sid,
                "landing_url": None,
                "acquisition_status": "acquired",
                "files_on_disk": (acquired or {}).get("files") or [],
                "detected_formats": (acquired or {}).get("formats") or [],
                "asset_count": (acquired or {}).get("asset_count") or 0,
                "latest_json": (acquired or {}).get("latest_json"),
                "parser_or_adapter": None,
                **classified,
            }
        )

    status_counts = Counter(r["ingestion_status"] for r in rows)
    backlog = [
        r
        for r in rows
        if r["ingestion_status"]
        in {"acquired_not_ingested", "adapter_missing", "adapter_broken", "partially_ingested"}
        and r["acquisition_status"] == "acquired"
        and r["next_ingestion_action"] != "maintain_family_adapter"
    ]
    backlog.sort(key=lambda r: (r["viz_value_rank"], r["source_id"]))

    stamp = _utc_stamp()
    args.write_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "facts_db_total": total_facts,
        "registry_sources": len(sources),
        "rows": len(rows),
        "status_counts": dict(status_counts),
        "mapping_yaml_count": len(mapping_ids),
        "items": rows,
        "priority_backlog": backlog[:80],
    }
    json_path = args.write_dir / f"ingestion-coverage-{stamp}.json"
    md_path = args.write_dir / f"ingestion-coverage-{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"# Ingestion coverage audit ({stamp})",
        "",
        f"- Registry sources: **{len(sources)}**",
        f"- Audit rows (registry + orphans): **{len(rows)}**",
        f"- facts.db total facts: **{total_facts:,}**",
        f"- Mapping YAML files: **{len(mapping_ids)}**",
        "",
        "## Status counts",
        "",
    ]
    for status in STATUSES + ("not_acquired",):
        if status in status_counts:
            lines.append(f"- `{status}`: **{status_counts[status]}**")
    lines += ["", "## Priority backlog (top 40)", "", "| rank | status | source_id | viz_bucket | facts | next |", "|---:|---|---|---|---:|---|"]
    for row in backlog[:40]:
        lines.append(
            f"| {row['viz_value_rank']} | `{row['ingestion_status']}` | `{row['source_id']}` | "
            f"{row['viz_bucket']} | {row['fact_count']} | {row['next_ingestion_action']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {json_path.relative_to(REPO_ROOT)}")
    print(f"wrote {md_path.relative_to(REPO_ROOT)}")
    print(f"status_counts={dict(status_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
