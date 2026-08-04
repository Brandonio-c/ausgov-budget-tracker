#!/usr/bin/env python3
"""Build a small, committed-fixture facts DB for the CI Playwright e2e job
(Task 7 of the database-hygiene-and-CI-hardening milestone).

This is deliberately separate from build_fixture_db.py (used by
tests/integration, which only needs a couple of facts to exercise
backend compatibility logic directly): the e2e job drives the real
dashboard UI through a real browser, so it needs at least one fact per
mode/level combination that src/frontend/tests-e2e/dashboard.spec.ts
deep-links to - federal actuals, federal budget, QLD state actuals,
local government actuals, and GDP/ratios - plus a debt/liability fact so
the always-on debt widget has something to load. No production database
or raw-data corpus is used or required.

Note: src/frontend/tests-e2e/pbs-s6-crosswalk.spec.ts and
pbs-year-fallback.spec.ts are NOT exercised by this fixture - both
hardcode specific real fact_ids/node names resolved directly against the
live production database (see their own docstrings), so they cannot run
against any synthetic fixture without losing the specific real-world
regression they check. They remain local-only checks (run against
data/facts.db per Task 8's local validation), not part of CI.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ingest"))

from schema_migrate import migrate  # noqa: E402

OUT = REPO / "data" / "test" / "facts_e2e_fixture.db"


def main() -> int:
    if OUT.exists():
        OUT.unlink()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    migrate(OUT)
    conn = sqlite3.connect(str(OUT))

    def add_doc(source_key: str, jurisdiction: str, level: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
            VALUES (?, 'Test', 'Fixture', ?, ?, 'fixture')
            """,
            (source_key, jurisdiction, level),
        )
        return int(cur.lastrowid)

    def add_node(doc_id: int, canonical_key: str, name: str, jurisdiction: str, level: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
            VALUES (?, 'category', ?, ?, ?, ?)
            """,
            (canonical_key, name, jurisdiction, level, doc_id),
        )
        return int(cur.lastrowid)

    def add_fact(
        fact_key: str,
        doc_id: int,
        node_id: int,
        fy: str,
        amount: float,
        measure_type: str,
        estimate_status: str,
        accounting_basis: str = "gfs",
        amount_value: float | None = None,
        quantity: float | None = None,
        unit: str = "AUD",
    ) -> None:
        cur = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_granularity, measure_type, accounting_basis,
                estimate_status, amount_aud, amount_value, quantity, unit, currency, source_document_id,
                view_family, price_basis, quality_status, source_locator_json, source_record_hash,
                retrieved_at
            ) VALUES (
                ?, ?, 'financial_year', ?, ?,
                ?, ?, ?, ?, ?, 'AUD', ?,
                'actual_expense', 'unspecified', 'ok', '{}', ?,
                '2026-01-01T00:00:00Z'
            )
            """,
            (
                fact_key, fy, measure_type, accounting_basis,
                estimate_status, amount, amount_value, quantity, unit, doc_id,
                f"hash-{fact_key}",
            ),
        )
        fact_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
            (fact_id, node_id),
        )

    # Federal actuals + budget (Defence), FY2024-25 - two separate nodes so
    # the actuals/budget mode switch each gets a real, distinct amount.
    fed_doc = add_doc("fixture_federal_actuals", "Commonwealth", "federal")
    defence_actual = add_node(fed_doc, "fixture:defence:actual", "Defence", "Commonwealth", "federal")
    add_fact("fixture|defence|actual|2024-25", fed_doc, defence_actual, "2024-25", 1_000_000, "gfs_expense", "actual")

    fed_budget_doc = add_doc("fixture_federal_budget", "Commonwealth", "federal")
    defence_budget = add_node(fed_budget_doc, "fixture:defence:budget", "Defence", "Commonwealth", "federal")
    add_fact(
        "fixture|defence|budget|2024-25", fed_budget_doc, defence_budget, "2024-25",
        1_100_000, "budget_estimate", "budget",
    )

    # QLD state actuals, FY2024-25.
    qld_doc = add_doc("fixture_qld_state_actuals", "QLD", "state")
    qld_node = add_node(qld_doc, "fixture:qld:health", "Health", "QLD", "state")
    add_fact("fixture|qld|health|2024-25", qld_doc, qld_node, "2024-25", 500_000, "gfs_expense", "actual")

    # Local government actuals (no specific year required by the test).
    local_doc = add_doc("fixture_local_govt_actuals", "NSW", "local")
    local_node = add_node(local_doc, "fixture:local:roads", "Roads", "NSW", "local")
    add_fact("fixture|local|roads|2023-24", local_doc, local_node, "2023-24", 250_000, "actual_accrual_expense", "actual")

    # Federal debt/liability, FY2024-25 (feeds the always-on debt widget).
    debt_doc = add_doc("fixture_federal_debt", "Commonwealth", "federal")
    debt_node = add_node(debt_doc, "fixture:debt:securities", "Debt securities", "Commonwealth", "federal")
    add_fact(
        "fixture|debt|securities|2024-25", debt_doc, debt_node, "2024-25",
        2_000_000, "gfs_liability", "actual",
    )

    # Federal GDP/tax-to-GDP ratio, FY2024-25.
    gdp_doc = add_doc("fixture_federal_gdp", "Commonwealth", "federal")
    gdp_node = add_node(gdp_doc, "fixture:tax_gdp", "Tax to GDP", "Commonwealth", "federal")
    add_fact(
        "fixture|ratio|2024-25", gdp_doc, gdp_node, "2024-25", 0, "tax_to_gdp_ratio", "actual",
        accounting_basis="not_applicable", amount_value=24.5, quantity=24.5, unit="percent",
    )
    # amount_aud must be NULL for a pure ratio fact (schema CHECK requires
    # amount_aud OR quantity, and the API reads amount_value for ratios).
    conn.execute(
        "UPDATE facts SET amount_aud = NULL WHERE fact_key = 'fixture|ratio|2024-25'"
    )

    conn.commit()
    conn.close()
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
