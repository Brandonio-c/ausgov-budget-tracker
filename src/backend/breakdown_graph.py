"""Breakdown edge helpers — same_group additive trees vs related_breakdown links."""

from __future__ import annotations

from typing import Any

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
    """Best fact for a node in a given FY (prefer budget_expense then any)."""
    row = conn.execute(
        """
        SELECT
            f.id AS fact_id,
            f.amount_aud,
            f.financial_year,
            d.source_key,
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
            "node_name": row["node_name"],
            "node_id": node_id,
            "fy_fallback": False,
        }
    if not allow_nearest:
        return None

    # Prefer same or later estimate years, then earlier.
    target = _fy_sort_key(financial_year)[0]
    candidates = conn.execute(
        """
        SELECT
            f.id AS fact_id,
            f.amount_aud,
            f.financial_year,
            d.source_key,
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
    if not candidates:
        return None

    def rank(r) -> tuple[int, int, int]:
        fy = str(r["financial_year"])
        start = _fy_sort_key(fy)[0]
        # 0 = exact (unreachable here), 1 = later, 2 = earlier
        bucket = 1 if start >= target else 2
        distance = abs(start - target)
        return (bucket, distance, start)

    best = min(candidates, key=rank)
    return {
        "fact_id": int(best["fact_id"]),
        "amount_aud": float(best["amount_aud"] or 0),
        "financial_year": best["financial_year"],
        "source_key": best["source_key"],
        "compatibility_group": best["compatibility_group"],
        "node_name": best["node_name"],
        "node_id": node_id,
        "fy_fallback": str(best["financial_year"]) != financial_year,
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
        out.append(
            {
                "child_node_id": cid,
                "child_name": r["child_name"],
                "child_source_key": r["child_source_key"],
                "notes": r["notes"],
                "crosswalk_id": r["crosswalk_id"],
                "priority": r["priority"],
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
        "banner": (
            f"{FY_MISMATCH_BANNER} Selected year {tree_year}; "
            f"showing {fact.get('financial_year')}."
        ),
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
        fact = fact_for_node_year(
            conn,
            edge["child_node_id"],
            financial_year,
            allow_nearest=allow_nearest_fy,
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
    carry its own explicit non-additive tag, regardless of depth. Returns
    the effective fact year shown at this node (its own, or the nearest
    mismatched year found among its descendants) so a parent with no year
    fallback of its own can still surface an accurate banner.

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
    own_fy = existing.get("fact_financial_year")

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

    effective_fy = own_fy or (sorted(child_fys)[0] if child_fys else None)
    if effective_fy:
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
        "fact_financial_year": effective_fy,
        "banner": banner,
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
    source_key_prefixes: tuple[str, ...] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Load related_breakdown children for a leaf; nest same_group under each.
    Uses nearest-FY fallback for deeper same_group nests when needed.
    Depth 8 leaves room for S6 → component → PBS → grant program → recipient.
    """
    if depth > max_depth:
        return [], None
    related = child_edges(conn, parent_node_id, "related_breakdown", financial_year)
    if source_key_prefixes:
        related = [
            e
            for e in related
            if any(
                str(e.get("child_source_key") or "").startswith(p)
                for p in source_key_prefixes
            )
        ]
    if not related:
        return [], None

    children: dict[str, Any] = {}
    meta_source = related[0].get("child_source_key")
    quality = match_quality_from_notes(related[0].get("notes"))
    mismatch_years: set[str] = set()
    for edge in related:
        fact = fact_for_node_year(
            conn, edge["child_node_id"], financial_year, allow_nearest=True
        )
        if fact is None:
            continue
        label = display_name(edge["child_name"], parent_name)
        edge_quality = match_quality_from_notes(edge.get("notes"))
        node: dict[str, Any] = {
            "children": {},
            "amount": fact["amount_aud"],
            "fact_id": fact["fact_id"],
            "node_id": edge["child_node_id"],
            "source_key": fact["source_key"],
            "compatibility_group": fact["compatibility_group"],
        }
        if fact.get("fy_fallback"):
            node["breakdown"] = {"fact_financial_year": fact["financial_year"]}
        sg_kids, _ = build_same_group_subtree(
            conn,
            edge["child_node_id"],
            financial_year,
            parent_name=edge["child_name"],
            depth=depth + 1,
            max_depth=max_depth,
            allow_nearest_fy=True,
        )
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
        quality = match_quality_from_notes(edge.get("notes"))

    if not children:
        return [], None

    mismatch_year = sorted(mismatch_years)[0] if mismatch_years else None
    compat = (
        "actual_expense"
        if meta_source and str(meta_source).startswith("federal_fbo_")
        else "budget_expense"
    )
    breakdown = {
        "kind": "related_breakdown",
        "source_key": meta_source,
        "compatibility_group": compat,
        "match_quality": quality,
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
    aliases = {
        "health": "Health",
        "education": "Education",
        "defence": "Defence",
        "general public services": "General public services",
    }
    purpose = aliases.get(lookup.lower(), lookup)

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


def _related_folder(
    *,
    related_list: list[dict[str, Any]],
    breakdown: dict[str, Any],
    parent_amount: float,
    parent_fact_id: int | None,
) -> dict[str, Any]:
    """Navigable related folder preserving parent amount (non-additive)."""
    return {
        "children": {item["name"]: item["node"] for item in related_list},
        "amount": float(parent_amount or 0),
        "fact_id": parent_fact_id,
        "breakdown": breakdown,
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

    def _attach(node: dict[str, Any], nid: int, *, as_folders: bool) -> None:
        kids = node.setdefault("children", {})
        parent_amount = float(node.get("amount") or 0)
        parent_fact = node.get("fact_id")
        s6_list, s6_bd = build_related_subtree(
            conn,
            nid,
            financial_year,
            parent_name=None,
            source_key_prefixes=("federal_budget_statement_6",),
        )
        fbo_list, fbo_bd = build_related_subtree(
            conn,
            nid,
            financial_year,
            parent_name=None,
            source_key_prefixes=("federal_fbo_",),
        )
        if as_folders:
            if s6_list and s6_bd and "Statement 6 (budget estimates)" not in kids:
                kids["Statement 6 (budget estimates)"] = _related_folder(
                    related_list=s6_list,
                    breakdown=s6_bd,
                    parent_amount=parent_amount,
                    parent_fact_id=parent_fact,
                )
            if fbo_list and fbo_bd and "FBO Appendix A (audited)" not in kids:
                kids["FBO Appendix A (audited)"] = _related_folder(
                    related_list=fbo_list,
                    breakdown=fbo_bd,
                    parent_amount=parent_amount,
                    parent_fact_id=parent_fact,
                )
            node["children"] = kids
            return
        # Leaf purpose: S6 children as primary related drill; FBO as folder.
        if s6_list and s6_bd:
            node["children"] = {item["name"]: item["node"] for item in s6_list}
            node["breakdown"] = s6_bd
            if fbo_list and fbo_bd:
                node["children"]["FBO Appendix A (audited)"] = _related_folder(
                    related_list=fbo_list,
                    breakdown=fbo_bd,
                    parent_amount=parent_amount,
                    parent_fact_id=parent_fact,
                )
        elif fbo_list and fbo_bd:
            node["children"] = {item["name"]: item["node"] for item in fbo_list}
            node["breakdown"] = fbo_bd

    def walk(node: dict[str, Any], path_name: str | None = None) -> None:
        kids = node.get("children") or {}
        for child_name, child in list(kids.items()):
            walk(child, child_name)

        if kids:
            purpose = path_name or ""
            if purpose in ABS_PURPOSE_RELATED_TARGETS:
                nid = resolve_related_parent_node_id(
                    conn, purpose, node.get("fact_id")
                )
                if nid is not None:
                    _attach(node, nid, as_folders=True)
            return

        fact_id = node.get("fact_id")
        if not fact_id and path_name not in ABS_PURPOSE_RELATED_TARGETS:
            return
        nid = resolve_related_parent_node_id(conn, path_name or "", fact_id)
        if nid is None:
            return
        _attach(node, nid, as_folders=False)

    walk(tree)


def apply_edge_cascade_to_budget_tree(
    conn,
    tree: dict[str, Any],
    financial_year: str,
) -> None:
    """
    For budget-mode federal trees: replace path-collision children with
    ordered same_group edge children when edges exist for the node's fact.
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
        # Prefer edge cascade when it has more depth than path kids, or when
        # path kids mix sources. Always prefer edges if any same_group exist.
        node["children"] = {item["name"]: item["node"] for item in sg_list}

    # Seed node_ids from facts on leaves first
    def seed(node: dict[str, Any]) -> None:
        for child in (node.get("children") or {}).values():
            seed(child)
        if node.get("fact_id") and not node.get("node_id"):
            nid = primary_node_id(conn, int(node["fact_id"]))
            if nid:
                node["node_id"] = nid

    seed(tree)
    walk(tree)
