"""Pure helpers for explicit dashboard projection metadata.

This module does not select facts or mutate the graph.  It turns the current
tree projection into a typed semantic contract and computes depth metadata
without relying on source names in presentation code.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Iterable

from .schemas import ProjectionBranchSummary, ProjectionMeta, RelationshipMeta, TreeNode


def projection_v2_enabled() -> bool:
    """Temporary rollback flag; enabled by default for the additive API field."""
    return os.getenv("DASHBOARD_PROJECTION_V2", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _single(values: Iterable[Any]) -> str | None:
    normalized = sorted({str(value) for value in values if value not in (None, "")})
    return normalized[0] if len(normalized) == 1 else None


def relationship_from_node_dict(
    node: dict[str, Any],
    *,
    requested_financial_year: str,
    inherited_related: bool = False,
) -> RelationshipMeta:
    """Build one relationship object from graph metadata or path provenance."""
    explicit = dict(node.get("relationship") or {})
    legacy = dict(node.get("breakdown") or {})
    # The compatibility alias historically stamped a canonical leaf itself
    # as related when related children were attached.  An explicit additive
    # relationship on that leaf supersedes the alias provenance; otherwise
    # the canonical ABS node would falsely inherit the child budget source.
    if (
        explicit.get("branch_kind") == "additive"
        and legacy.get("kind") == "related_breakdown"
    ):
        legacy = {}
    values = node.get("_projection_values") or {}

    edge_kind = explicit.get("edge_kind") or legacy.get("kind") or "same_group"
    branch_kind = explicit.get("branch_kind") or (
        "related" if inherited_related or edge_kind == "related_breakdown" else "additive"
    )
    if inherited_related:
        branch_kind = "related"
    presentation_role = (
        explicit.get("presentation_role")
        or node.get("presentation_role")
        or "data"
    )
    fact_financial_year = (
        explicit.get("fact_financial_year")
        or legacy.get("fact_financial_year")
        or _single(values.get("financial_year") or [])
    )
    is_fallback = bool(
        explicit.get("is_year_fallback")
        if explicit.get("is_year_fallback") is not None
        else legacy.get("is_year_fallback")
    )
    return RelationshipMeta(
        edge_kind=edge_kind,
        branch_kind=branch_kind,
        presentation_role=presentation_role,
        edge_set_id=(
            explicit.get("edge_set_id")
            or explicit.get("crosswalk_id")
            or legacy.get("edge_set_id")
        ),
        branch_family=(
            explicit.get("branch_family")
            or legacy.get("source_family")
            or _single(values.get("source_family") or [])
        ),
        source_key=(
            explicit.get("source_key")
            or legacy.get("source_key")
            or _single(values.get("source_key") or [])
        ),
        source_family=(
            explicit.get("source_family")
            or legacy.get("source_family")
            or _single(values.get("source_family") or [])
        ),
        compatibility_group=(
            explicit.get("compatibility_group")
            or legacy.get("compatibility_group")
            or _single(values.get("compatibility_group") or [])
        ),
        accounting_basis=(
            explicit.get("accounting_basis")
            or legacy.get("accounting_basis")
            or _single(values.get("accounting_basis") or [])
        ),
        estimate_status=(
            explicit.get("estimate_status")
            or legacy.get("estimate_status")
            or _single(values.get("estimate_status") or [])
        ),
        requested_financial_year=(
            explicit.get("requested_financial_year")
            or legacy.get("requested_financial_year")
            or requested_financial_year
        ),
        fact_financial_year=fact_financial_year,
        is_year_fallback=is_fallback,
        fallback_reason=explicit.get("fallback_reason") or legacy.get("fallback_reason"),
        match_quality=explicit.get("match_quality") or legacy.get("match_quality"),
        unit=explicit.get("unit") or legacy.get("unit") or _single(values.get("unit") or []),
    )


def projection_metadata(
    children: list[TreeNode],
    *,
    requested_mode: str,
    requested_level: str,
    requested_financial_year: str,
    selected_accounting_basis: str | None,
) -> ProjectionMeta:
    """Summarize semantic depth; navigation wrappers do not add a level."""
    maximum_visible = 0
    maximum_additive = 0
    contains_related = False
    summaries: dict[tuple[str | None, str], dict[str, int]] = defaultdict(
        lambda: {"node_count": 0, "max_depth": 0}
    )

    def visit(node: TreeNode, semantic_depth: int) -> None:
        nonlocal maximum_visible, maximum_additive, contains_related
        relation = node.relationship
        if relation is None:
            return
        depth = semantic_depth + (0 if relation.presentation_role == "navigation" else 1)
        maximum_visible = max(maximum_visible, depth)
        if relation.branch_kind == "additive":
            maximum_additive = max(maximum_additive, depth)
        else:
            contains_related = True
        key = (relation.branch_family or relation.source_family, relation.branch_kind)
        summaries[key]["node_count"] += 1
        summaries[key]["max_depth"] = max(summaries[key]["max_depth"], depth)
        for child in node.children or []:
            visit(child, depth)

    for child in children:
        visit(child, 0)

    branch_summaries = [
        ProjectionBranchSummary(
            branch_family=family,
            branch_kind=kind,
            node_count=values["node_count"],
            max_depth=values["max_depth"],
        )
        for (family, kind), values in sorted(
            summaries.items(), key=lambda item: ((item[0][0] or ""), item[0][1])
        )
    ]
    return ProjectionMeta(
        requested_mode=requested_mode,
        requested_level=requested_level,
        requested_financial_year=requested_financial_year,
        selected_accounting_basis=selected_accounting_basis,
        max_visible_depth=maximum_visible,
        max_additive_depth=maximum_additive,
        contains_related_branches=contains_related,
        branch_summaries=branch_summaries,
    )
