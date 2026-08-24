"""Breakdown edge helpers — same_group additive trees vs related_breakdown links."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.edge_set_policy import EdgeSetPolicy, load_edge_set_registry

_HERE = Path(__file__).resolve().parent


def _cofog_crosswalk_path() -> Path:
    candidates = [
        Path("/app/config/breakdowns/crosswalks/cofog_to_budget_function.yaml"),
        _HERE.parents[1] / "config" / "breakdowns" / "crosswalks" / "cofog_to_budget_function.yaml",
        _HERE.parent / "config" / "breakdowns" / "crosswalks" / "cofog_to_budget_function.yaml",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


@lru_cache(maxsize=1)
def _budget_to_abs_purpose() -> dict[str, str]:
    """Reverse-index config/breakdowns/crosswalks/cofog_to_budget_function.yaml
    (budget-function name, lowercased) -> ABS COFOG purpose name - the name
    related_breakdown edges are actually attached under in the DB (e.g.
    "Social security and welfare" -> "Social protection"). Exact-quality
    mappings win over approx ones when more than one ABS purpose maps to the
    same budget function (e.g. "Environmental protection" also maps
    approximately onto "Housing and community amenities", which already has
    its own exact self-mapping)."""
    path = _cofog_crosswalk_path()
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    by_budget: dict[str, tuple[str, str]] = {}
    for mapping in data.get("mappings", []):
        abs_name = mapping.get("abs")
        budget_name = mapping.get("budget")
        quality = mapping.get("quality", "approx")
        if not abs_name or not budget_name:
            continue
        key = budget_name.lower()
        existing = by_budget.get(key)
        if existing is None or (existing[1] != "exact" and quality == "exact"):
            by_budget[key] = (abs_name, quality)
    return {key: abs_name for key, (abs_name, _quality) in by_budget.items()}

RELATED_BANNER = (
    "Related breakdown from a different measure family — amounts are shown for "
    "navigation and must not be summed into the parent pie slice."
)

FY_MISMATCH_BANNER = (
    "Child amounts use a nearby published financial year because this layer has "
    "no figures for the selected year — not additive with the parent measure."
)

# ABS purpose labels that nest same_group children in Table_4 but still need
# Statement 6 related attach at the purpose node.
ABS_PURPOSE_RELATED_TARGETS = frozenset(
    {
        "Health",
        "Education",
        "General public services",
        "Defence",
        "Social protection",
        "Public order and safety",
        "Housing and community amenities",
        "Recreation, culture and religion",
        "Economic affairs",
        "Environmental protection",
        "Transport",
    }
)


def match_quality_from_notes(notes: str | None) -> str:
    if not notes:
        return "approx"
    if "|exact" in notes:
        return "exact"
    if "|approx" in notes:
        return "approx"
    return "approx"


def banner_for_related(
    source_key: str | None,
    quality: str,
    *,
    tree_year: str | None = None,
    child_year: str | None = None,
) -> str:
    src = source_key or "related source"
    parts = [RELATED_BANNER, f"Source: {src}.", f"Crosswalk match: {quality}."]
    if tree_year and child_year and tree_year != child_year:
        parts.append(
            f"Deeper component/program rows use FY {child_year} where "
            f"{tree_year} is unpublished in those tables."
        )
    return " ".join(parts)


def primary_node_id(conn, fact_id: int) -> int | None:
    row = conn.execute(
        """
        SELECT node_id FROM fact_nodes
        WHERE fact_id = ? AND dimension_role = 'primary'
        LIMIT 1
        """,
        (fact_id,),
    ).fetchone()
    return int(row[0]) if row else None


def _fy_sort_key(fy: str) -> tuple[int, int]:
    try:
        start = int(str(fy).split("-", 1)[0])
        return (start, start)
    except (TypeError, ValueError):
        return (0, 0)


def fact_for_node_year(
    conn,
    node_id: int,
    financial_year: str,
    *,
    allow_nearest: bool = False,
) -> dict[str, Any] | None:
    """Best fact for a node in a given FY (prefer budget_expense then any).

    Fallback policy (Task 7 of the semantic-defect milestone): (1) exact
    requested year; (2) nearest EARLIER year - never later/future, since a
    later year is not a legitimate stand-in for an earlier parent's figure;
    (3) no result if no earlier year exists at all. Among earlier
    candidates, one corroborated by another fact from the same source
    edition is preferred over a lone fact from a different edition, and
    fallback_reason/is_year_fallback/source_budget_edition are always
    returned so the API and UI can disclose the actual source year rather
    than silently substituting it.
    """
    row = conn.execute(
        """
        SELECT
            f.id AS fact_id,
            f.amount_aud,
            f.financial_year,
            f.estimate_status,
            f.accounting_basis,
            f.unit,
            d.source_key,
            d.source_family,
            m.compatibility_group,
            n.name AS node_name
        FROM facts f
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        WHERE fn.node_id = ?
          AND f.financial_year = ?
        ORDER BY
            CASE m.compatibility_group
                WHEN 'budget_expense' THEN 0
                WHEN 'actual_expense' THEN 1
                ELSE 2
            END,
            CASE f.estimate_status
                WHEN 'budget' THEN 0
                WHEN 'estimated_actual' THEN 1
                WHEN 'revised_estimate' THEN 2
                WHEN 'forward_estimate' THEN 3
                WHEN 'actual' THEN 4
                ELSE 5
            END,
            f.id
        LIMIT 1
        """,
        (node_id, financial_year),
    ).fetchone()
    if row:
        return {
            "fact_id": int(row["fact_id"]),
            "amount_aud": float(row["amount_aud"] or 0),
            "financial_year": row["financial_year"],
            "source_key": row["source_key"],
            "compatibility_group": row["compatibility_group"],
            "estimate_status": row["estimate_status"],
            "accounting_basis": row["accounting_basis"],
            "unit": row["unit"],
            "node_name": row["node_name"],
            "source_family": row["source_family"],
            "node_id": node_id,
            "fy_fallback": False,
            "requested_financial_year": financial_year,
            "fallback_reason": "exact_year_match",
        }
    if not allow_nearest:
        return None

    target = _fy_sort_key(financial_year)[0]
    candidates = conn.execute(
        """
        SELECT
            f.id AS fact_id,
            f.amount_aud,
            f.financial_year,
            f.estimate_status,
            f.accounting_basis,
            f.unit,
            d.source_key,
            d.source_family,
            m.compatibility_group,
            n.name AS node_name
        FROM facts f
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        WHERE fn.node_id = ?
        ORDER BY
            CASE m.compatibility_group
                WHEN 'budget_expense' THEN 0
                WHEN 'actual_expense' THEN 1
                ELSE 2
            END,
            f.financial_year,
            f.id
        """,
        (node_id,),
    ).fetchall()
    earlier = [r for r in candidates if _fy_sort_key(str(r["financial_year"]))[0] < target]
    if not earlier:
        return None

    def _distance(r) -> int:
        return target - _fy_sort_key(str(r["financial_year"]))[0]

    min_distance = min(_distance(r) for r in earlier)
    nearest = [r for r in earlier if _distance(r) == min_distance]
    source_key_counts = Counter(str(r["source_key"]) for r in earlier)
    # Prefer a nearest candidate corroborated by another fact from the same
    # edition over a lone fact from a different edition; ties keep the
    # pre-sorted (compatibility_group priority, then id) order.
    best = min(
        nearest,
        key=lambda r: 0 if source_key_counts[str(r["source_key"])] > 1 else 1,
    )
    same_edition = source_key_counts[str(best["source_key"])] > 1
    return {
        "fact_id": int(best["fact_id"]),
        "amount_aud": float(best["amount_aud"] or 0),
        "financial_year": best["financial_year"],
        "source_key": best["source_key"],
        "compatibility_group": best["compatibility_group"],
        "estimate_status": best["estimate_status"],
        "accounting_basis": best["accounting_basis"],
        "unit": best["unit"],
        "node_name": best["node_name"],
        "source_family": best["source_family"],
        "node_id": node_id,
        "fy_fallback": True,
        "requested_financial_year": financial_year,
        "fallback_reason": (
            "nearest_earlier_year_same_edition"
            if same_edition
            else "nearest_earlier_year_other_edition"
        ),
    }


def child_edges(
    conn,
    parent_node_id: int,
    edge_kind: str,
    financial_year: str | None = None,
) -> list[dict[str, Any]]:
    """Distinct child edges for a parent (dedupe SQLite NULL uniqueness quirks)."""
    rows = conn.execute(
        """
        SELECT
            e.child_node_id,
            e.notes,
            e.crosswalk_id,
            e.priority,
            n.name AS child_name,
            d.source_key AS child_source_key
        FROM breakdown_edges e
        JOIN nodes n ON n.id = e.child_node_id
        LEFT JOIN source_documents d ON d.id = n.source_document_id
        WHERE e.parent_node_id = ?
          AND e.edge_kind = ?
          AND (e.financial_year IS NULL OR e.financial_year = ?)
        ORDER BY e.priority DESC, n.name, e.id
        """,
        (parent_node_id, edge_kind, financial_year),
    ).fetchall()
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        cid = int(r["child_node_id"])
        if cid in seen:
            continue
        seen.add(cid)
        policy = load_edge_set_registry().resolve(
            crosswalk_id=r["crosswalk_id"],
            edge_kind=edge_kind,
            source_key=r["child_source_key"],
        )
        out.append(
            {
                "child_node_id": cid,
                "child_name": r["child_name"],
                "child_source_key": r["child_source_key"],
                "notes": r["notes"],
                "crosswalk_id": r["crosswalk_id"],
                "priority": r["priority"],
                "policy": policy,
            }
        )
    return out


def display_name(full_name: str, parent_name: str | None = None) -> str:
    name = (full_name or "").strip()
    if parent_name and name.startswith(parent_name + " / "):
        return name[len(parent_name) + 3 :]
    if " / " in name:
        return name.rsplit(" / ", 1)[-1]
    return name


def _child_meta_from_fact(
    fact: dict[str, Any],
    *,
    tree_year: str,
    kind: str = "same_group",
) -> dict[str, Any] | None:
    if not fact.get("fy_fallback"):
        return None
    return {
        "kind": kind,
        "source_key": fact.get("source_key"),
        "compatibility_group": fact.get("compatibility_group"),
        "match_quality": None,
        "fact_financial_year": fact.get("financial_year"),
        "requested_financial_year": tree_year,
        "is_year_fallback": True,
        "fallback_reason": fact.get("fallback_reason"),
        "source_budget_edition": fact.get("source_key"),
        "estimate_status": fact.get("estimate_status"),
        "banner": (
            f"{FY_MISMATCH_BANNER} Selected year {tree_year}; "
            f"showing {fact.get('financial_year')}."
        ),
    }


def _relationship_from_fact(
    fact: dict[str, Any],
    *,
    tree_year: str,
    edge_kind: str,
    branch_kind: str,
    policy: EdgeSetPolicy,
    match_quality: str | None = None,
    presentation_role: str = "data",
) -> dict[str, Any]:
    return {
        "edge_kind": edge_kind,
        "branch_kind": (
            "related" if policy.branch_kind == "related" else branch_kind
        ),
        "presentation_role": presentation_role or policy.presentation_role,
        "edge_set_id": policy.id,
        "branch_family": policy.branch_family or fact.get("source_family"),
        "source_key": fact.get("source_key"),
        "source_family": fact.get("source_family"),
        "compatibility_group": fact.get("compatibility_group"),
        "accounting_basis": fact.get("accounting_basis"),
        "estimate_status": fact.get("estimate_status"),
        "requested_financial_year": tree_year,
        "fact_financial_year": fact.get("financial_year"),
        "is_year_fallback": bool(fact.get("fy_fallback")),
        "fallback_reason": fact.get("fallback_reason"),
        "match_quality": match_quality,
        "unit": fact.get("unit"),
    }


def build_same_group_subtree(
    conn,
    parent_node_id: int,
    financial_year: str,
    *,
    parent_name: str | None = None,
    depth: int = 0,
    max_depth: int = 8,
    allow_nearest_fy: bool = False,
) -> tuple[list[dict[str, Any]], None]:
    if depth > max_depth:
        return [], None
    edges = child_edges(conn, parent_node_id, "same_group", financial_year)
    out: list[dict[str, Any]] = []
    for edge in edges:
        policy: EdgeSetPolicy = edge["policy"]
        fact = fact_for_node_year(
            conn,
            edge["child_node_id"],
            financial_year,
            allow_nearest=(
                allow_nearest_fy and policy.fallback_policy == "nearest_earlier"
            ),
        )
        if fact is None:
            continue
        label = display_name(edge["child_name"], parent_name)
        node: dict[str, Any] = {
            "children": {},
            "amount": fact["amount_aud"],
            "fact_id": fact["fact_id"],
            "node_id": edge["child_node_id"],
            "source_key": fact["source_key"],
            "compatibility_group": fact["compatibility_group"],
            "relationship": _relationship_from_fact(
                fact,
                tree_year=financial_year,
                edge_kind="same_group",
                branch_kind="additive",
                policy=policy,
                match_quality=match_quality_from_notes(edge.get("notes")),
                presentation_role=policy.presentation_role,
            ),
            # This node's own published fact.amount_aud is always
            # authoritative - never silently replaced by sum(children) when
            # this dict is later serialized (_to_tree_node()'s default for
            # a node with children and no preserve_amount). Without this,
            # any node reached here that also has its own nested same_group
            # children reports whatever those children happen to sum to
            # instead of its real fact amount (found live: "Arts and
            # cultural heritage" via /item/{id}/children read $1.1996B -
            # the sum of 13 partial PBS program facts - instead of its
            # actual $2.329B Statement 6 A.6.1 figure). The main /tree
            # endpoint already gets this right via _build_tree_dict()'s own
            # preserve_amount marking (see dashboard.py); this is the same
            # fix for this second, independent tree-building path.
            "preserve_amount": True,
            "_edge_policy": policy,
        }
        meta = _child_meta_from_fact(fact, tree_year=financial_year)
        if meta:
            node["breakdown"] = meta
        nested, _ = build_same_group_subtree(
            conn,
            edge["child_node_id"],
            financial_year,
            parent_name=edge["child_name"],
            depth=depth + 1,
            max_depth=max_depth,
            allow_nearest_fy=allow_nearest_fy,
        )
        if nested:
            node["children"] = {c["name"]: c["node"] for c in nested}
        out.append({"name": label, "node": node})
    return out, None


def _mark_related_descendants(
    node: dict[str, Any],
    *,
    source_key: str | None,
    compat: str | None,
    quality: str,
    tree_year: str,
    mismatch_years: set[str],
) -> str | None:
    """Force every descendant beneath a related_breakdown attach point to
    carry its own explicit non-additive tag AND its own explicit year-
    fallback disclosure (Task 7: requested_financial_year, is_year_fallback,
    fallback_reason, source_budget_edition, estimate_status), regardless of
    depth. Returns the effective fact year shown at this node (its own, or
    the nearest mismatched year found among its descendants) so a parent
    with no year fallback of its own can still surface an accurate banner -
    never leaving a mixed-year subtree with only the topmost node
    disclosing the actual year.

    build_same_group_subtree() is the additive-tree builder; when its
    output is nested under a related_breakdown parent (Statement 6 →
    component → PBS program, or ABS purpose → Statement 6 subfunction),
    those nested nodes previously kept whatever `breakdown` same_group
    assigned them (None unless that specific node had its own year
    fallback) — the only thing marking the subtree non-additive was the
    immediate parent's own `breakdown`. Since each node is serialized
    independently (both within one /dashboard/tree walk and, separately,
    on every standalone /item/{fact_id}/children drill-down call, which
    has no parent context to inherit from), a descendant with
    breakdown=None is indistinguishable from a real additive fact —
    this is the concrete mechanism behind children reading >100% of an
    unrelated parent and cross-government facts reading as if additive.
    """
    existing = node.get("breakdown") or {}
    existing_relationship = node.get("relationship") or {}
    own_fy = existing_relationship.get("fact_financial_year") or existing.get(
        "fact_financial_year"
    )
    own_is_fallback = bool(
        existing_relationship.get("is_year_fallback")
        or existing.get("is_year_fallback")
    )
    own_reason = existing_relationship.get("fallback_reason") or existing.get(
        "fallback_reason"
    )
    own_edition = existing.get("source_budget_edition") or existing.get("source_key")
    own_estimate_status = existing_relationship.get("estimate_status") or existing.get(
        "estimate_status"
    )

    child_fys: list[str] = []
    for child in (node.get("children") or {}).values():
        child_fy = _mark_related_descendants(
            child,
            source_key=source_key,
            compat=compat,
            quality=quality,
            tree_year=tree_year,
            mismatch_years=mismatch_years,
        )
        if child_fy:
            child_fys.append(child_fy)

    mismatched_child_fys = sorted(fy for fy in child_fys if fy != tree_year)
    effective_fy = (
        own_fy
        if own_is_fallback
        else (mismatched_child_fys[0] if mismatched_child_fys else own_fy)
    )
    is_fallback = own_is_fallback or (
        effective_fy is not None and effective_fy != tree_year
    )
    if effective_fy and effective_fy != tree_year:
        mismatch_years.add(str(effective_fy))
        banner = (
            f"{FY_MISMATCH_BANNER} Selected year {tree_year}; showing {effective_fy}. "
            f"{RELATED_BANNER}"
        )
    else:
        banner = existing.get("banner") or RELATED_BANNER
    node["breakdown"] = {
        "kind": "related_breakdown",
        "source_key": existing.get("source_key") or source_key,
        "compatibility_group": existing.get("compatibility_group") or compat,
        "match_quality": existing.get("match_quality") or quality,
        # Compatibility alias keeps its historical convention: null means
        # exact-year.  The new relationship contract always carries the
        # actual fact year explicitly.
        "fact_financial_year": effective_fy if is_fallback else None,
        "requested_financial_year": tree_year,
        "is_year_fallback": is_fallback,
        # own_reason only genuinely describes a fallback when own_fy is set
        # (this node's own fact needed one) - a node with an exact match at
        # its own level (own_reason=="exact_year_match") must not report
        # that label for the whole subtree when a *descendant's* mismatch
        # bubbled up into effective_fy; that case is its own distinct
        # reason so the disclosure stays honest about where the mismatch
        # actually lives.
        "fallback_reason": (
            own_reason
            if own_is_fallback
            else ("nested_child_year_mismatch" if is_fallback else own_reason)
        ),
        "source_budget_edition": own_edition or existing.get("source_key") or source_key,
        "estimate_status": own_estimate_status,
        "banner": banner,
    }
    node["relationship"] = {
        **existing_relationship,
        "edge_kind": existing_relationship.get("edge_kind") or "same_group",
        "branch_kind": "related",
        "presentation_role": existing_relationship.get("presentation_role") or "data",
        "source_key": existing_relationship.get("source_key") or source_key,
        "compatibility_group": (
            existing_relationship.get("compatibility_group") or compat
        ),
        "requested_financial_year": tree_year,
        "fact_financial_year": effective_fy,
        "is_year_fallback": is_fallback,
        "fallback_reason": (
            own_reason
            if own_is_fallback
            else ("nested_child_year_mismatch" if is_fallback else own_reason)
        ),
        "match_quality": existing_relationship.get("match_quality") or quality,
    }
    node["preserve_amount"] = True
    return effective_fy


def build_related_subtree(
    conn,
    parent_node_id: int,
    financial_year: str,
    *,
    parent_name: str | None = None,
    depth: int = 0,
    max_depth: int = 8,
    edge_set_ids: tuple[str, ...] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Load related_breakdown children for a leaf; nest same_group under each.
    Uses each declared edge set's fallback policy.
    Depth 8 leaves room for S6 → component → PBS → grant program → recipient.
    """
    if depth > max_depth:
        return [], None
    related = child_edges(conn, parent_node_id, "related_breakdown", financial_year)
    if edge_set_ids:
        allowed = set(edge_set_ids)
        related = [e for e in related if e["policy"].id in allowed]
    if not related:
        return [], None

    children: dict[str, Any] = {}
    meta_source = related[0].get("child_source_key")
    meta_fact: dict[str, Any] | None = None
    quality = match_quality_from_notes(related[0].get("notes"))
    mismatch_years: set[str] = set()
    for edge in related:
        policy: EdgeSetPolicy = edge["policy"]
        fact = fact_for_node_year(
            conn,
            edge["child_node_id"],
            financial_year,
            allow_nearest=policy.fallback_policy == "nearest_earlier",
        )
        sg_kids, _ = build_same_group_subtree(
            conn,
            edge["child_node_id"],
            financial_year,
            parent_name=edge["child_name"],
            depth=depth + 1,
            max_depth=max_depth,
            allow_nearest_fy=True,
        )
        if fact is None:
            if policy.presentation_role != "navigation" or not sg_kids:
                continue
            first_relationship = sg_kids[0]["node"].get("relationship") or {}
            fact = {
                "fact_id": None,
                "amount_aud": sum(float(kid["node"].get("amount") or 0) for kid in sg_kids),
                "financial_year": financial_year,
                "source_key": edge.get("child_source_key"),
                "source_family": first_relationship.get("source_family"),
                "compatibility_group": first_relationship.get("compatibility_group"),
                "accounting_basis": first_relationship.get("accounting_basis"),
                "estimate_status": first_relationship.get("estimate_status"),
                "unit": first_relationship.get("unit"),
                "fy_fallback": False,
                "fallback_reason": "exact_year_descendants",
            }
        label = display_name(edge["child_name"], parent_name)
        edge_quality = match_quality_from_notes(edge.get("notes"))
        node: dict[str, Any] = {
            "children": {},
            "amount": fact["amount_aud"],
            "fact_id": fact["fact_id"],
            "node_id": edge["child_node_id"],
            "source_key": fact["source_key"],
            "compatibility_group": fact["compatibility_group"],
            "relationship": _relationship_from_fact(
                fact,
                tree_year=financial_year,
                edge_kind="related_breakdown",
                branch_kind="related",
                policy=policy,
                match_quality=edge_quality,
                presentation_role=policy.presentation_role,
            ),
            "_edge_policy": policy,
        }
        node["breakdown"] = {
            "fact_financial_year": fact["financial_year"] if fact.get("fy_fallback") else None,
            "is_year_fallback": bool(fact.get("fy_fallback")),
            "fallback_reason": fact.get("fallback_reason"),
            "source_budget_edition": fact.get("source_key"),
            "estimate_status": fact.get("estimate_status"),
            "source_key": fact.get("source_key"),
        }
        if sg_kids:
            node["children"] = {c["name"]: c["node"] for c in sg_kids}
        # Every node beneath (and including) this related attach point -
        # regardless of depth, and regardless of whether it has its own
        # year fallback - must self-declare non-additive. Stamping only the
        # immediate container left deeper same_group-shaped nodes (Statement
        # 6 component -> PBS program) indistinguishable from a real additive
        # fact once serialized on their own - the mechanism behind children
        # reading >100% of an unrelated parent and cross-government facts
        # appearing to be additive. A node with no year fallback of its own
        # still bubbles up its nested descendants' mismatch year so the
        # banner stays accurate at every level a consumer might render it.
        _mark_related_descendants(
            node,
            source_key=fact["source_key"],
            compat=fact["compatibility_group"],
            quality=edge_quality,
            tree_year=financial_year,
            mismatch_years=mismatch_years,
        )
        children[label] = node
        meta_source = fact["source_key"] or meta_source
        meta_fact = fact
        quality = match_quality_from_notes(edge.get("notes"))

    if not children:
        return [], None

    mismatch_year = sorted(mismatch_years)[0] if mismatch_years else None
    first_policy: EdgeSetPolicy = related[0]["policy"]
    compat = (meta_fact or {}).get("compatibility_group")
    breakdown = {
        "kind": "related_breakdown",
        "source_key": meta_source,
        "source_family": (meta_fact or {}).get("source_family"),
        "compatibility_group": compat,
        "accounting_basis": (meta_fact or {}).get("accounting_basis"),
        "estimate_status": (meta_fact or {}).get("estimate_status"),
        "requested_financial_year": financial_year,
        "is_year_fallback": bool(mismatch_year),
        "fallback_reason": "nested_child_year_mismatch" if mismatch_year else None,
        "unit": (meta_fact or {}).get("unit"),
        "match_quality": quality,
        "edge_set_id": first_policy.id,
        "branch_family": first_policy.branch_family,
        "folder_label": first_policy.folder_label,
        "fact_financial_year": mismatch_year,
        "banner": banner_for_related(
            meta_source,
            quality,
            tree_year=financial_year if mismatch_year else None,
            child_year=mismatch_year,
        ),
    }
    return [{"name": k, "node": v} for k, v in children.items()], breakdown


def resolve_related_parent_node_id(
    conn, node_name: str, fact_id: int | None
) -> int | None:
    """Map ABS purpose / Total-* names to a node that has related_breakdown edges."""
    name = (node_name or "").strip()
    if fact_id:
        nid = primary_node_id(conn, int(fact_id))
        if nid is not None and child_edges(conn, nid, "related_breakdown"):
            return nid

    lookup = name
    if lookup.lower().startswith("total "):
        rest = lookup[6:].strip()
        lookup = rest[:1].upper() + rest[1:] if rest else lookup
    purpose = _budget_to_abs_purpose().get(lookup.lower(), lookup)

    candidates = [purpose, f"Total {purpose}", f"Total {purpose[0].lower() + purpose[1:]}"]
    for cand in candidates:
        row = conn.execute(
            """
            SELECT n.id FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            JOIN breakdown_edges e ON e.parent_node_id = n.id
              AND e.edge_kind = 'related_breakdown'
            WHERE d.source_key LIKE 'abs_gfs_commonwealth%'
              AND n.name = ?
            LIMIT 1
            """,
            (cand,),
        ).fetchone()
        if row:
            return int(row[0])

    # Any commonwealth node with related edges whose notes mention the purpose
    row = conn.execute(
        """
        SELECT n.id FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        JOIN breakdown_edges e ON e.parent_node_id = n.id
          AND e.edge_kind = 'related_breakdown'
        WHERE d.source_key LIKE 'abs_gfs_commonwealth%'
          AND (n.name = ? OR e.notes LIKE ?)
        LIMIT 1
        """,
        (purpose, f"{purpose}→%"),
    ).fetchone()
    if row:
        return int(row[0])
    if fact_id:
        return primary_node_id(conn, int(fact_id))
    return None


def _relationship_from_breakdown(
    breakdown: dict[str, Any], *, presentation_role: str
) -> dict[str, Any]:
    return {
        "edge_kind": "related_breakdown",
        "branch_kind": "related",
        "presentation_role": presentation_role,
        "edge_set_id": breakdown.get("edge_set_id"),
        "branch_family": breakdown.get("branch_family")
        or breakdown.get("source_family"),
        "source_key": breakdown.get("source_key"),
        "source_family": breakdown.get("source_family"),
        "compatibility_group": breakdown.get("compatibility_group"),
        "accounting_basis": breakdown.get("accounting_basis"),
        "estimate_status": breakdown.get("estimate_status"),
        "requested_financial_year": breakdown.get("requested_financial_year"),
        "fact_financial_year": breakdown.get("fact_financial_year"),
        "is_year_fallback": bool(breakdown.get("is_year_fallback")),
        "fallback_reason": breakdown.get("fallback_reason"),
        "match_quality": breakdown.get("match_quality"),
        "unit": breakdown.get("unit"),
    }


def _related_folder(
    *,
    related_list: list[dict[str, Any]],
    breakdown: dict[str, Any],
    parent_amount: float,
    parent_fact_id: int | None,
) -> dict[str, Any]:
    """Navigable related folder preserving parent amount (non-additive)."""
    relationship = _relationship_from_breakdown(
        breakdown, presentation_role="navigation"
    )
    return {
        "children": {item["name"]: item["node"] for item in related_list},
        "amount": float(parent_amount or 0),
        "fact_id": parent_fact_id,
        "breakdown": breakdown,
        "relationship": relationship,
        "presentation_role": "navigation",
        "preserve_amount": True,
    }


def attach_related_to_tree(
    conn,
    tree: dict[str, Any],
    financial_year: str,
) -> None:
    """
    Mutate tree-dict: attach related_breakdown on leaves, and on ABS purpose
    parents so Statement 6 / FBO cascades are reachable without double-counting.
    """

    def _attach(
        node: dict[str, Any],
        nid: int,
        *,
        as_folders: bool,
        parent_name: str,
    ) -> None:
        kids = node.setdefault("children", {})
        parent_amount = float(node.get("amount") or 0)
        parent_fact = node.get("fact_id")
        policies = {
            edge["policy"].id: edge["policy"]
            for edge in child_edges(
                conn, nid, "related_breakdown", financial_year
            )
        }
        groups: list[
            tuple[EdgeSetPolicy, list[dict[str, Any]], dict[str, Any]]
        ] = []
        for policy in sorted(
            policies.values(), key=lambda item: (item.sort_order, item.id)
        ):
            related_list, breakdown = build_related_subtree(
                conn,
                nid,
                financial_year,
                parent_name=None,
                edge_set_ids=(policy.id,),
            )
            if related_list and breakdown:
                groups.append((policy, related_list, breakdown))

        # A related source often repeats the canonical function at its own
        # root (Defence -> Defence).  That attach node is a navigation bridge,
        # not another semantic level; descendants retain their source-native
        # data roles.
        for _policy, related_list, _breakdown in groups:
            for item in related_list:
                if item["name"] != parent_name:
                    continue
                item["node"].setdefault("relationship", {})[
                    "presentation_role"
                ] = "navigation"
        if as_folders:
            for policy, related_list, breakdown in groups:
                label = policy.folder_label or f"Related {policy.branch_family or 'detail'}"
                if label in kids:
                    continue
                kids[label] = _related_folder(
                    related_list=related_list,
                    breakdown=breakdown,
                    parent_amount=parent_amount,
                    parent_fact_id=parent_fact,
                )
            node["children"] = kids
            return
        if groups and groups[0][0].presentation_role == "navigation":
            for policy, related_list, breakdown in groups:
                label = policy.folder_label or f"Related {policy.branch_family or 'detail'}"
                if label in kids:
                    continue
                kids[label] = _related_folder(
                    related_list=related_list,
                    breakdown=breakdown,
                    parent_amount=parent_amount,
                    parent_fact_id=parent_fact,
                )
            node["children"] = kids
            return
        # A leaf exposes the first declared related family directly and keeps
        # additional families in declared navigation folders.
        if groups:
            _primary_policy, primary_list, primary_bd = groups[0]
            node["children"] = {
                item["name"]: item["node"] for item in primary_list
            }
            node["breakdown"] = primary_bd
            node["relationship"] = {
                "edge_kind": "same_group",
                "branch_kind": "additive",
                "presentation_role": "data",
                "requested_financial_year": financial_year,
                "fact_financial_year": financial_year,
                "is_year_fallback": False,
            }
            for policy, related_list, breakdown in groups[1:]:
                label = policy.folder_label or f"Related {policy.branch_family or 'detail'}"
                if label in node["children"]:
                    continue
                node["children"][label] = _related_folder(
                    related_list=related_list,
                    breakdown=breakdown,
                    parent_amount=parent_amount,
                    parent_fact_id=parent_fact,
                )

    def walk(node: dict[str, Any], path_name: str | None = None) -> None:
        kids = node.get("children") or {}
        for child_name, child in list(kids.items()):
            walk(child, child_name)

        if kids:
            purpose = path_name or ""
            if not purpose and not node.get("fact_id"):
                return
            nid = resolve_related_parent_node_id(conn, purpose, node.get("fact_id"))
            if nid is not None and child_edges(
                conn, nid, "related_breakdown", financial_year
            ):
                _attach(node, nid, as_folders=True, parent_name=purpose)
            return

        fact_id = node.get("fact_id")
        if not fact_id and path_name not in ABS_PURPOSE_RELATED_TARGETS:
            return
        nid = resolve_related_parent_node_id(conn, path_name or "", fact_id)
        if nid is None:
            return
        _attach(node, nid, as_folders=False, parent_name=path_name or "")

    walk(tree)


def apply_edge_cascade_to_budget_tree(
    conn,
    tree: dict[str, Any],
    financial_year: str,
) -> None:
    """
    Augment path-derived children with declared same-group edge children.

    Replacement is permitted only when every projected edge belongs to an
    authoritative edge set. Registry validation requires those sets to name
    a completeness manifest. Existing projected parent totals are preserved
    while incomplete path-only rows remain navigable.
    """

    def walk(node: dict[str, Any]) -> None:
        kids = node.get("children") or {}
        for child in list(kids.values()):
            walk(child)
        fact_id = node.get("fact_id")
        node_id = node.get("node_id")
        if not node_id and fact_id:
            node_id = primary_node_id(conn, int(fact_id))
            if node_id:
                node["node_id"] = node_id
        if not node_id:
            return
        sg_list, _ = build_same_group_subtree(
            conn,
            int(node_id),
            financial_year,
            allow_nearest_fy=False,
        )
        if not sg_list:
            return
        projected = {item["name"]: item["node"] for item in sg_list}
        policies = {
            child["_edge_policy"]
            for child in projected.values()
            if child.get("_edge_policy") is not None
        }
        authoritative = bool(policies) and all(
            policy.projection_policy == "authoritative" for policy in policies
        )
        projected_total = sum(_projection_amount(child) for child in projected.values())
        node["children"] = merge_projected_children(
            kids,
            projected,
            authoritative=authoritative,
            parent_compatibility_group=_node_compatibility_group(node),
        )
        # This is the value emitted by the pre-change edge-only cascade. The
        # additional path rows are visible evidence, not a newly asserted
        # complete additive partition of the edge-derived parent.
        node["amount"] = projected_total
        node["preserve_amount"] = True
        node.setdefault(
            "breakdown",
            {
                "kind": "same_group",
                "source_key": node.get("source_key"),
                "compatibility_group": node.get("compatibility_group"),
                "banner": (
                    "Edge-derived partition total preserved; additional path-derived "
                    "rows remain visible because this edge set is not authoritative."
                ),
            },
        )

    # Seed node_ids from facts on leaves first
    def seed(node: dict[str, Any]) -> None:
        for child in (node.get("children") or {}).values():
            seed(child)
        if node.get("fact_id") and not node.get("node_id"):
            nid = primary_node_id(conn, int(node["fact_id"]))
            if nid:
                node["node_id"] = nid
        if node.get("node_id") and not node.get("_canonical_key"):
            row = conn.execute(
                "SELECT canonical_key FROM nodes WHERE id = ?",
                (int(node["node_id"]),),
            ).fetchone()
            if row and row[0]:
                node["_canonical_key"] = str(row[0])

    seed(tree)
    walk(tree)


def _normal_child_name(name: str) -> str:
    return " / ".join(
        part.strip().casefold() for part in str(name).split(" / ") if part.strip()
    )


def _node_compatibility_group(node: dict[str, Any]) -> str | None:
    explicit = (node.get("relationship") or {}).get("compatibility_group")
    if explicit:
        return str(explicit)
    direct = node.get("compatibility_group")
    if direct:
        return str(direct)
    values = sorted(
        str(value)
        for value in (node.get("_projection_values") or {}).get(
            "compatibility_group", set()
        )
        if value
    )
    return values[0] if len(set(values)) == 1 else None


def _mark_cross_compatibility_path(
    node: dict[str, Any], parent_compatibility_group: str | None
) -> None:
    child_compatibility_group = _node_compatibility_group(node)
    if (
        not parent_compatibility_group
        or not child_compatibility_group
        or parent_compatibility_group == child_compatibility_group
    ):
        return
    values = node.get("_projection_values") or {}

    def one(field: str) -> str | None:
        candidates = sorted(str(value) for value in values.get(field, set()) if value)
        return candidates[0] if len(set(candidates)) == 1 else None

    role = "data" if node.get("fact_id") or node.get("amount") else "navigation"
    node["relationship"] = {
        "edge_kind": "related_breakdown",
        "branch_kind": "related",
        "presentation_role": role,
        "edge_set_id": "path_augmentation",
        "branch_family": one("source_family"),
        "source_key": one("source_key"),
        "source_family": one("source_family"),
        "compatibility_group": child_compatibility_group,
        "accounting_basis": one("accounting_basis"),
        "estimate_status": one("estimate_status"),
        "fact_financial_year": one("financial_year"),
        "is_year_fallback": False,
        "unit": one("unit"),
    }
    node["breakdown"] = {
        "kind": "related_breakdown",
        "source_key": one("source_key"),
        "compatibility_group": child_compatibility_group,
        "banner": (
            "Path-derived row from a different measure family; retained for "
            "navigation and excluded from the budget partition total."
        ),
    }
    node["preserve_amount"] = True


def _projection_amount(node: dict[str, Any]) -> float:
    children = node.get("children") or {}
    if children and not node.get("preserve_amount"):
        return sum(_projection_amount(child) for child in children.values())
    return float(node.get("amount") or 0)


def _merge_node(
    path_node: dict[str, Any], projected_node: dict[str, Any]
) -> dict[str, Any]:
    """Prefer the explicit edge fact while retaining unique path descendants."""
    merged = {**path_node, **projected_node}
    merged["children"] = merge_projected_children(
        path_node.get("children") or {},
        projected_node.get("children") or {},
        authoritative=False,
        parent_compatibility_group=_node_compatibility_group(merged),
    )
    return merged


def merge_projected_children(
    path_children: dict[str, dict[str, Any]],
    projected_children: dict[str, dict[str, Any]],
    *,
    authoritative: bool = False,
    parent_compatibility_group: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Deterministically merge children by node ID, canonical key, then label."""
    if authoritative:
        return dict(
            sorted(projected_children.items(), key=lambda item: _normal_child_name(item[0]))
        )

    items: list[tuple[str, dict[str, Any]]] = []
    for name, path_node in path_children.items():
        _mark_cross_compatibility_path(path_node, parent_compatibility_group)
        items.append((name, path_node))
    for projected_name, projected_node in projected_children.items():
        projected_id = projected_node.get("node_id")
        projected_key = projected_node.get("_canonical_key")
        match_index: int | None = None
        for index, (path_name, path_node) in enumerate(items):
            same_id = projected_id is not None and projected_id == path_node.get("node_id")
            same_key = projected_key is not None and projected_key == path_node.get(
                "_canonical_key"
            )
            same_name = _normal_child_name(projected_name) == _normal_child_name(path_name)
            if same_id or same_key or same_name:
                match_index = index
                break
        if match_index is None:
            items.append((projected_name, projected_node))
        else:
            path_name, path_node = items[match_index]
            items[match_index] = (
                path_name,
                _merge_node(path_node, projected_node),
            )
    return dict(sorted(items, key=lambda item: _normal_child_name(item[0])))
