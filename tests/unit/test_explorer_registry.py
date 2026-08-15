import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from backend.explorer_registry import load_explorer_registry  # noqa: E402


def test_live_registry_loads_all_six_completed_families() -> None:
    registry = load_explorer_registry()
    ids = {family.id for family in registry.families}
    assert ids == {"contracts", "grants", "vic_output_performance", "act_invoices", "pbs", "qgip"}


def test_pbs_family_has_four_estimate_statuses_and_a_source_key() -> None:
    pbs = load_explorer_registry().family_by_id("pbs")
    assert pbs is not None
    assert pbs.compatibility_group == "budget_expense"
    assert pbs.accounting_basis == "accrual"
    assert pbs.estimate_statuses == ("budget", "forward_estimate", "estimated_actual", "actual")
    assert pbs.default_estimate_status == "budget"
    assert pbs.source_key == "federal_pbs_programs_all"


def test_qgip_family_has_two_estimate_statuses_and_a_source_key() -> None:
    qgip = load_explorer_registry().family_by_id("qgip")
    assert qgip is not None
    assert qgip.compatibility_group == "actual_expense"
    assert qgip.accounting_basis == "accrual"
    assert qgip.estimate_statuses == ("actual", "actual_cumulative_agreement_total")
    assert qgip.default_estimate_status == "actual"
    assert qgip.source_key == "qld_qgip_expenditure"


def test_contracts_family_has_no_source_key_and_an_additive_note() -> None:
    contracts = load_explorer_registry().family_by_id("contracts")
    assert contracts is not None
    assert contracts.source_key is None
    assert "jurisdiction" in contracts.additive_note or "source_breakdown" in contracts.additive_note


def test_unknown_family_returns_none() -> None:
    assert load_explorer_registry().family_by_id("does_not_exist") is None


def _write_config(path: Path, families: str) -> None:
    path.write_text(f"version: 1\nfamilies:\n{families}", encoding="utf-8")


def test_default_estimate_status_must_be_in_estimate_statuses(tmp_path: Path) -> None:
    path = tmp_path / "families.yaml"
    _write_config(
        path,
        "  - id: bad\n"
        "    label: Bad\n"
        "    compatibility_group: g\n"
        "    accounting_basis: a\n"
        "    estimate_statuses: [x]\n"
        "    default_estimate_status: y\n",
    )
    with pytest.raises(ValueError, match="not in estimate_statuses"):
        load_explorer_registry(str(path))


def test_empty_estimate_statuses_rejected(tmp_path: Path) -> None:
    path = tmp_path / "families.yaml"
    _write_config(
        path,
        "  - id: bad\n"
        "    label: Bad\n"
        "    compatibility_group: g\n"
        "    accounting_basis: a\n"
        "    estimate_statuses: []\n"
        "    default_estimate_status: x\n",
    )
    with pytest.raises(ValueError, match="must not be empty"):
        load_explorer_registry(str(path))


def test_duplicate_family_ids_rejected(tmp_path: Path) -> None:
    path = tmp_path / "families.yaml"
    _write_config(
        path,
        "  - id: dup\n"
        "    label: A\n"
        "    compatibility_group: g\n"
        "    accounting_basis: a\n"
        "    estimate_statuses: [x]\n"
        "    default_estimate_status: x\n"
        "  - id: dup\n"
        "    label: B\n"
        "    compatibility_group: g\n"
        "    accounting_basis: a\n"
        "    estimate_statuses: [x]\n"
        "    default_estimate_status: x\n",
    )
    with pytest.raises(ValueError, match="unique"):
        load_explorer_registry(str(path))


def test_missing_compatibility_group_rejected(tmp_path: Path) -> None:
    path = tmp_path / "families.yaml"
    _write_config(
        path,
        "  - id: bad\n"
        "    label: Bad\n"
        "    accounting_basis: a\n"
        "    estimate_statuses: [x]\n"
        "    default_estimate_status: x\n",
    )
    with pytest.raises(ValueError, match="compatibility_group is required"):
        load_explorer_registry(str(path))
