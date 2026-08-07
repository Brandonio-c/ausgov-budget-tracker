from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest/extractors"))

import reload_tas_tafr_narrative_backfill as loader  # noqa: E402
import tas_tafr_narrative_backfill as extractor  # noqa: E402
from schema_migrate import migrate  # noqa: E402


@pytest.mark.parametrize("token, expected", [("4 602", 4602), ("(291)", -291), ("53)", 53)])
def test_number_parsing(token, expected):
    assert extractor.parse_number(token) == expected


def test_explicit_2008_columns_exclude_total_state(tmp_path):
    path = tmp_path / "edition.pdf"
    path.write_bytes(b"placeholder")
    spec = extractor.EDITION_SPECS["2008-09"]
    operating = """Revenue from transactions 4 131  4 286  3 986  6 591  6 205
Expenses from transactions 4 026  4 365  3 932  6 570  5 988
NET OPERATING BALANCE 106  (78)  53  20  217
Equals FISCAL BALANCE - SURPLUS/(DEFICIT) 30  (95)  102  (450)  202"""
    debt = "Net Debt  (1 031)  (1 123)  (982)"
    rows, quarantine = extractor.extract_page_texts(
        path=path,
        financial_year="2008-09",
        spec=spec,
        page_texts={spec["operating_page"]: operating, spec["debt_page"]: debt},
    )
    assert quarantine == []
    assert len(rows) == 10
    amounts = {(row["measure_type"], row["estimate_status"]): row["amount_million_aud"] for row in rows}
    assert amounts[("tas_ggs_revenue", "budget")] == 4131
    assert amounts[("tas_ggs_revenue", "actual")] == 4286
    assert amounts[("tas_ggs_net_debt", "actual")] == -982
    assert 6591 not in amounts.values()


def test_real_selected_cluster_extracts_exactly_30_rows():
    rows, quarantine = extractor.extract_all_editions()
    assert quarantine == []
    assert len(rows) == 30
    assert {row["financial_year"] for row in rows} == {"2007-08", "2008-09", "2009-10"}
    assert all("page:" in row["locator"] and "file:" in row["locator"] for row in rows)


def test_period_and_scale_semantics():
    semantics = loader.load_semantics()
    flow, reason = loader.classify({
        "financial_year": "2009-10", "measure_type": "tas_ggs_revenue", "estimate_status": "actual",
        "amount_million_aud": 4602, "publication_date": "2010-10-26",
        "locator": "page:8", "cached_copy_path": str((extractor.SNAPSHOT_DIR / "2009-10-TAFR.pdf").relative_to(REPO_ROOT)),
    }, semantics)
    assert reason == ""
    assert flow["amount_aud"] == 4_602_000_000
    assert flow["period_start"] == "2009-07-01"
    stock, reason = loader.classify({
        "financial_year": "2009-10", "measure_type": "tas_ggs_net_debt", "estimate_status": "actual",
        "amount_million_aud": -748, "publication_date": "2010-10-26",
        "locator": "page:12", "cached_copy_path": str((extractor.SNAPSHOT_DIR / "2009-10-TAFR.pdf").relative_to(REPO_ROOT)),
    }, semantics)
    assert reason == ""
    assert stock["period_start"] is None
    assert stock["period_end"] == "2010-06-30"


def test_loader_is_idempotent(tmp_path):
    db = tmp_path / "facts.db"
    migrate(db)
    conn = sqlite3.connect(db)
    first = loader.run(conn, apply=True, quarantine_path=tmp_path / "q.jsonl")
    second = loader.run(conn, apply=True, quarantine_path=tmp_path / "q.jsonl")
    assert first["facts_inserted"] == 30
    assert second["facts_inserted"] == 0
    assert second["facts_already_present_idempotent_skip"] == 30
    assert second["nodes_inserted"] == 0
    assert second["edges_inserted"] == 0
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 30
    conn.close()
