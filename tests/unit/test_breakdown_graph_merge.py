import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from backend.breakdown_graph import merge_projected_children  # noqa: E402


def test_augment_retains_path_only_and_edge_only_children() -> None:
    merged = merge_projected_children(
        {"Path only": {"node_id": 1, "amount": 10, "children": {}}},
        {"Edge only": {"node_id": 2, "amount": 20, "children": {}}},
    )
    assert list(merged) == ["Edge only", "Path only"]


def test_collision_prefers_edge_fact_and_retains_path_descendants() -> None:
    merged = merge_projected_children(
        {
            "Program": {
                "node_id": 7,
                "amount": 10,
                "fact_id": 100,
                "children": {"Path detail": {"amount": 3, "children": {}}},
            }
        },
        {
            "Program": {
                "node_id": 7,
                "amount": 11,
                "fact_id": 101,
                "relationship": {"edge_set_id": "declared"},
                "children": {"Edge detail": {"amount": 4, "children": {}}},
            }
        },
    )
    program = merged["Program"]
    assert program["amount"] == 11
    assert program["fact_id"] == 101
    assert set(program["children"]) == {"Edge detail", "Path detail"}


def test_canonical_key_deduplicates_differently_labelled_children() -> None:
    merged = merge_projected_children(
        {"Original label": {"_canonical_key": "purpose|health", "amount": 1}},
        {"Health": {"_canonical_key": "purpose|health", "amount": 2}},
    )
    assert list(merged) == ["Original label"]
    assert merged["Original label"]["amount"] == 2


def test_authoritative_policy_replaces_only_after_registry_validation() -> None:
    merged = merge_projected_children(
        {"Path": {"amount": 1}},
        {"Edge": {"amount": 2}},
        authoritative=True,
    )
    assert list(merged) == ["Edge"]
