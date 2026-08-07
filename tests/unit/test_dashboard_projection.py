from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from backend.dashboard_projection import (  # noqa: E402
    projection_metadata,
    relationship_from_node_dict,
)
from backend.schemas import RelationshipMeta, TreeNode  # noqa: E402


def test_same_group_descendant_can_inherit_related_branch_without_losing_edge_kind() -> None:
    relationship = relationship_from_node_dict(
        {
            "relationship": {
                "edge_kind": "same_group",
                "branch_kind": "additive",
                "presentation_role": "data",
                "edge_set_id": "fbo-pack",
                "fact_financial_year": "2023-24",
            }
        },
        requested_financial_year="2023-24",
        inherited_related=True,
    )
    assert relationship.edge_kind == "same_group"
    assert relationship.branch_kind == "related"
    assert relationship.fact_financial_year == "2023-24"


def test_projection_depth_ignores_navigation_wrappers() -> None:
    additive = RelationshipMeta(
        edge_kind="same_group",
        branch_kind="additive",
        presentation_role="data",
    )
    navigation = RelationshipMeta(
        edge_kind="related_breakdown",
        branch_kind="related",
        presentation_role="navigation",
        branch_family="fbo",
    )
    related = RelationshipMeta(
        edge_kind="same_group",
        branch_kind="related",
        presentation_role="data",
        branch_family="fbo",
    )
    tree = [
        TreeNode(
            name="Commonwealth",
            value=100,
            relationship=RelationshipMeta(
                edge_kind="same_group",
                branch_kind="additive",
                presentation_role="navigation",
            ),
            children=[
                TreeNode(
                    name="Defence",
                    value=100,
                    relationship=additive,
                    children=[
                        TreeNode(
                            name="FBO",
                            value=100,
                            relationship=navigation,
                            children=[
                                TreeNode(name="Subfunction", value=90, relationship=related)
                            ],
                        )
                    ],
                )
            ],
        )
    ]
    projection = projection_metadata(
        tree,
        requested_mode="actuals",
        requested_level="federal",
        requested_financial_year="2023-24",
        selected_accounting_basis="gfs",
    )
    assert projection.max_visible_depth == 2
    assert projection.max_additive_depth == 1
    assert projection.contains_related_branches is True
    fbo = next(summary for summary in projection.branch_summaries if summary.branch_family == "fbo")
    assert fbo.node_count == 2
    assert fbo.max_depth == 2
