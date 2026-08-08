import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from backend.edge_set_policy import load_edge_set_registry  # noqa: E402


def test_shared_crosswalk_resolves_statement6_and_fbo_separately() -> None:
    registry = load_edge_set_registry()
    statement6 = registry.resolve(
        crosswalk_id="cofog_to_budget_function",
        edge_kind="related_breakdown",
        source_key="federal_budget_statement_6_a61_2025_26",
    )
    fbo = registry.resolve(
        crosswalk_id="cofog_to_budget_function",
        edge_kind="related_breakdown",
        source_key="federal_fbo_2024_25_function_subfunction",
    )

    assert statement6.id == "statement_6_under_abs"
    assert statement6.fallback_policy == "nearest_earlier"
    assert statement6.branch_family == "statement_6"
    assert statement6.branch_kind == "related"
    assert fbo.id == "fbo_2024_25_under_abs"
    assert fbo.fallback_policy == "exact_only"
    assert fbo.branch_family == "fbo"

    archive = registry.resolve(
        crosswalk_id="cofog_to_budget_function",
        edge_kind="related_breakdown",
        source_key="federal_budget_archive_function_series",
    )
    assert archive.id == "fbo_archive_under_abs"
    assert archive.fallback_policy == "exact_only"
    assert archive.projection_policy == "augment"
    assert archive.presentation_role == "navigation"


def test_cross_measure_drill_is_declared_related_even_on_physical_same_group_edge() -> None:
    policy = load_edge_set_registry().resolve(
        crosswalk_id="grantconnect_under_pbs",
        edge_kind="same_group",
        source_key="federal_grantconnect_awards_2024_25",
    )
    assert policy.id == "grants_under_pbs"
    assert policy.branch_kind == "related"


def test_unregistered_edges_default_to_augment_and_exact_only() -> None:
    policy = load_edge_set_registry().resolve(
        crosswalk_id="not_registered",
        edge_kind="same_group",
        source_key="unknown_source",
    )
    assert policy.projection_policy == "augment"
    assert policy.fallback_policy == "exact_only"


def _write_config(path: Path, edge_sets: str) -> None:
    path.write_text(
        "version: 1\n"
        "defaults:\n"
        "  projection_policy: augment\n"
        "  fallback_policy: exact_only\n"
        "  presentation_role: data\n"
        "edge_sets:\n"
        f"{edge_sets}",
        encoding="utf-8",
    )


def test_authoritative_policy_requires_completeness_manifest(tmp_path: Path) -> None:
    path = tmp_path / "edge_sets.yaml"
    _write_config(
        path,
        "  - id: incomplete\n"
        "    crosswalk_id: pack\n"
        "    edge_kind: same_group\n"
        "    projection_policy: authoritative\n",
    )
    with pytest.raises(ValueError, match="requires completeness_manifest"):
        load_edge_set_registry(str(path))


def test_overlapping_source_rules_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "edge_sets.yaml"
    _write_config(
        path,
        "  - id: broad\n"
        "    crosswalk_id: pack\n"
        "    edge_kind: same_group\n"
        "    source_key_prefixes: [federal_]\n"
        "  - id: narrow\n"
        "    crosswalk_id: pack\n"
        "    edge_kind: same_group\n"
        "    source_key_prefixes: [federal_budget_]\n",
    )
    with pytest.raises(ValueError, match="overlapping edge sets"):
        load_edge_set_registry(str(path))
