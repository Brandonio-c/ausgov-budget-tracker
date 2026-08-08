"""Historical Statement 6/PBS acquisition identities must remain edition-safe."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from procure.registry import load_registry  # noqa: E402, I001


EXPECTED = {
    "federal_budget_statement_6_2022_23_march": (
        "2022-23 March Budget",
        "2022-03",
        "https://archive.budget.gov.au/2022-23/bp1/download/bp1_2022-23.pdf",
    ),
    "federal_budget_statement_6_2022_23_october": (
        "2022-23 October Budget",
        "2022-10",
        "https://archive.budget.gov.au/2022-23-october/bp1/download/bp1_2022-23.pdf",
    ),
    "federal_budget_statement_6_2023_24": (
        "2023-24 Budget",
        "2023-05",
        "https://archive.budget.gov.au/2023-24/bp1/download/bp1_2023-24.pdf",
    ),
    "federal_pbs_2022_23_march_treasury": (
        "2022-23 March Budget",
        "2022-03",
        "https://treasury.gov.au/sites/default/files/2022-03/tsy_pbs_2022-23.pdf",
    ),
    "federal_pbs_2022_23_october_treasury": (
        "2022-23 October Budget",
        "2022-10",
        "https://treasury.gov.au/sites/default/files/2022-10/tsy_pbs_october-2022-23.pdf",
    ),
    "federal_pbs_2023_24_treasury": (
        "2023-24 Budget",
        "2023-05",
        "https://treasury.gov.au/sites/default/files/2023-07/tsy_pbs_2023-24_230727.pdf",
    ),
}


def test_required_historical_budget_editions_have_distinct_source_identities():
    _, sources = load_registry()
    by_id = {source.id: source for source in sources}

    for source_id, (edition, vintage, resource_url) in EXPECTED.items():
        source = by_id[source_id]
        assert source.resource_url == resource_url
        assert source.access_method.value == "direct_file"
        assert source.formats == ["pdf"]
        assert source.research["publication_edition"] == edition
        assert source.research["publication_vintage"] == vintage

    assert len({by_id[source_id].resource_url for source_id in EXPECTED}) == len(EXPECTED)


def test_march_and_october_2022_23_are_not_collapsed_to_one_vintage():
    _, sources = load_registry()
    by_id = {source.id: source for source in sources}

    for family_prefix in ("federal_budget_statement_6", "federal_pbs"):
        march = by_id[f"{family_prefix}_2022_23_march" + ("_treasury" if family_prefix == "federal_pbs" else "")]
        october = by_id[f"{family_prefix}_2022_23_october" + ("_treasury" if family_prefix == "federal_pbs" else "")]
        assert march.research["publication_vintage"] == "2022-03"
        assert october.research["publication_vintage"] == "2022-10"
        assert march.id != october.id
        assert march.resource_url != october.resource_url
