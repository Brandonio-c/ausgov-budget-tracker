"""Integration tests against the fixture facts database."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "data" / "test" / "facts_fixture.db"


@pytest.fixture(scope="module", autouse=True)
def ensure_fixture_db():
    sys.path.insert(0, str(REPO / "scripts" / "ingest"))
    if not FIXTURE.is_file():
        from build_fixture_db import main as build

        assert build() == 0
    assert FIXTURE.is_file(), "fixture DB missing after build_fixture_db"
    os.environ["FACTS_DB_PATH"] = str(FIXTURE)
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = FIXTURE


def test_fixture_has_ratio_not_aud():
    import sqlite3

    conn = sqlite3.connect(str(FIXTURE))
    row = conn.execute(
        "SELECT unit, amount_aud, amount_value FROM facts WHERE measure_type='tax_to_gdp_ratio'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "percent"
    assert row[1] is None
    assert row[2] == 24.5


def test_migration_006_columns_present():
    import sqlite3

    conn = sqlite3.connect(str(FIXTURE))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(facts)")}
    conn.close()
    for col in ("amount_value", "view_family", "price_basis", "quality_status"):
        assert col in cols


def test_compatibility_rejects_mixed_units():
    sys.path.insert(0, str(REPO / "src"))
    from backend.compatibility import validate_fact_set

    d = validate_fact_set(
        [
            {"measure_type": "gdp_current", "unit": "AUD", "price_basis": "current_prices"},
            {"measure_type": "tax_to_gdp_ratio", "unit": "percent", "price_basis": "not_applicable"},
        ],
        view_family="gdp_current",
    )
    assert not d.allowed
