from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from quarantine_source_horizon_outliers import run  # noqa: E402
from schema_migrate import migrate  # noqa: E402


def _seed(db: Path) -> None:
    migrate(db)
    conn = sqlite3.connect(str(db))
    doc_id = conn.execute(
        """
        INSERT INTO source_documents
            (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('test_source', 'Test', 'Test', 'AU', 'federal', 'test')
        """
    ).lastrowid
    for year in ("2024-25", "2099-00"):
        node_id = conn.execute(
            """
            INSERT INTO nodes
                (canonical_key, node_type, name, jurisdiction, government_level,
                 source_document_id)
            VALUES (?, 'category', ?, 'AU', 'federal', ?)
            """,
            (f"node|{year}", year, doc_id),
        ).lastrowid
        fact_id = conn.execute(
            """
            INSERT INTO facts
                (fact_key, financial_year, period_granularity, measure_type,
                 accounting_basis, estimate_status, amount_aud, source_document_id,
                 source_locator_json, retrieved_at)
            VALUES (?, ?, 'financial_year', 'gfs_expense', 'gfs', 'actual',
                    2099, ?, '{"locator":"test"}', '2026-08-08T00:00:00Z')
            """,
            (f"fact|{year}", year, doc_id),
        ).lastrowid
        conn.execute(
            "INSERT INTO fact_nodes VALUES (?, ?, 'primary')", (fact_id, node_id)
        )
    conn.commit()
    conn.close()


def _mapping(path: Path) -> Path:
    path.mkdir()
    (path / "test.yaml").write_text(
        """
source_id: test_source
publication_horizon:
  min_financial_year: 2012-13
  max_financial_year: 2024-25
""".lstrip(),
        encoding="utf-8",
    )
    return path


def test_preview_is_read_only_and_apply_moves_outlier_to_quarantine(
    tmp_path: Path,
) -> None:
    db = tmp_path / "facts.db"
    mappings = _mapping(tmp_path / "mappings")
    _seed(db)
    preview = run(db, mappings, apply=False)
    assert preview["audit"]["outlier_facts"] == 1

    applied = run(db, mappings, apply=True)
    assert applied["changes"] == {
        "candidate_facts": 1,
        "quarantined_facts": 1,
        "deleted_orphan_nodes": 1,
    }
    assert applied["after"]["outlier_facts"] == 0
    conn = sqlite3.connect(str(db))
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 1
    reason = conn.execute(
        "SELECT quarantine_reason FROM facts_pending_attribution WHERE fact_key='fact|2099-00'"
    ).fetchone()[0]
    assert reason == (
        "source_horizon_outlier:"
        "financial_year=2099-00;allowed=2012-13..2024-25"
    )
    conn.close()
