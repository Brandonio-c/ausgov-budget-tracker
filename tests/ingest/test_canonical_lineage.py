from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from canonical_lineage import (  # noqa: E402
    audit_assignments,
    backfill_assignments,
    canonical_dataset_for_source,
    load_canonical_lineage,
)
from ingestion_coverage_audit import classify  # noqa: E402
from schema_migrate import migrate  # noqa: E402


def test_repository_lineage_uses_distinct_revenue_and_fbo_identities() -> None:
    assert (
        canonical_dataset_for_source("abs_gfs_commonwealth_130_revenue")
        == "abs_gfs_table1_revenue"
    )
    assert (
        canonical_dataset_for_source("federal_fbo_2024_25_function_subfunction")
        == "federal_fbo_appendix_a_2024_25"
    )
    assert (
        canonical_dataset_for_source("federal_budget_archive_function_series")
        == "federal_fbo_historical_archive"
    )


def test_one_fact_source_cannot_belong_to_two_canonical_datasets(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lineage.yaml"
    path.write_text(
        """
version: 1
datasets:
  - canonical_dataset_id: first
    fact_source_keys: [shared]
  - canonical_dataset_id: second
    fact_source_keys: [shared]
""".lstrip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="belongs to multiple canonical datasets"):
        load_canonical_lineage(str(path))


def test_backfill_assigns_only_configured_sources(tmp_path: Path) -> None:
    db = tmp_path / "facts.db"
    lineage_path = tmp_path / "lineage.yaml"
    lineage_path.write_text(
        """
version: 1
datasets:
  - canonical_dataset_id: canonical
    fact_source_keys: [canonical_source]
""".lstrip(),
        encoding="utf-8",
    )
    migrate(db)
    conn = sqlite3.connect(str(db))
    for source_key in ("canonical_source", "specialist_source"):
        doc_id = conn.execute(
            """
            INSERT INTO source_documents
                (source_key, publisher, title, jurisdiction, government_level, source_family)
            VALUES (?, 'Test', 'Test', 'AU', 'federal', 'test')
            """,
            (source_key,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO facts
                (fact_key, financial_year, period_granularity, measure_type,
                 accounting_basis, estimate_status, amount_aud, source_document_id,
                 source_locator_json, retrieved_at, canonical_dataset_id)
            VALUES (?, '2024-25', 'financial_year', 'gfs_expense', 'gfs',
                    'actual', 1, ?, '{}', '2026-08-08T00:00:00Z', 'stale')
            """,
            (f"{source_key}|fact", doc_id),
        )
    lineage = load_canonical_lineage(str(lineage_path))
    assert audit_assignments(conn, lineage)["mismatched_facts"] == 2
    result = backfill_assignments(conn, lineage)
    second = backfill_assignments(conn, lineage)
    conn.commit()
    assert result["after"]["mismatched_facts"] == 0
    assert result["rows_changed"] == 2
    assert second["rows_changed"] == 0
    rows = dict(
        conn.execute(
            """
            SELECT d.source_key, f.canonical_dataset_id
            FROM facts f JOIN source_documents d ON d.id = f.source_document_id
            """
        )
    )
    assert rows == {"canonical_source": "canonical", "specialist_source": None}
    conn.close()


def test_declared_partial_canonical_coverage_overrides_generic_full_heuristic() -> None:
    result = classify(
        "archive",
        acquired={"asset_count": 1, "formats": ["pdf"]},
        mapping_ids={"archive"},
        code_refs=set(),
        facts={"archive": {"fact_count": 10}},
        canonical_datasets=[
            {
                "canonical_dataset_id": "historical_archive",
                "fact_source_keys": ["archive"],
                "coverage_status": "partially_ingested",
            }
        ],
    )
    assert result["ingestion_status"] == "partially_ingested"
    assert result["next_ingestion_action"] == "continue_canonical_dataset_ingestion"
