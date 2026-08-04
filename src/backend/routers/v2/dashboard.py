"""Dashboard-shaped read API over facts.db (Actuals | Budget modes)."""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ...abs_gfs_hierarchy import (
    abs_gfs_breakdown_note,
    abs_gfs_hierarchy_path,
    is_abs_gfs_source,
)
from ...abs_gfs_liability_hierarchy import (
    abs_gfs_liability_path,
    is_abs_gfs_liability_source,
)
from ...abs_gfs_revenue_hierarchy import (
    abs_gfs_revenue_path,
    is_abs_gfs_revenue_source,
)
from ...breakdown_graph import (
    apply_edge_cascade_to_budget_tree,
    attach_related_to_tree,
    build_related_subtree,
    build_same_group_subtree,
    primary_node_id,
)
from ...compatibility import (
    assert_compatible_or_raise,
    display_value,
    mode_to_view_family,
    validate_fact_set,
)
from ...evidence_locator import (
    build_reconstructed,
    media_type_for_path,
    parse_locator_string,
    parse_source_locator_json,
    resolve_fact_source_file,
)
from ...facts_db import get_facts_connection
from ...gdp_hierarchy import gdp_hierarchy_path
from ...schemas import BreakdownMeta, TreeNode
from .citation import build_citation

router = APIRouter(prefix="/dashboard", tags=["v2-dashboard"])

Mode = Literal[
    "actuals",
    "budget",
    "debt",
    "revenue",
    "gdp",  # legacy alias → gdp_current
    "gdp_current",
    "gdp_chain_volume",
    "gdp_expenditure",
    "gva_current",
    "gva_chain_volume",
    "gsp_current",
    "gsp_chain_volume",
    "ratios",
]
TOTAL_RE = re.compile(r"^total\b", re.IGNORECASE)

LEVEL_ORDER = ("federal", "state", "territory", "local")

_ECONOMY_MODES = frozenset(
    {
        "gdp",
        "gdp_current",
        "gdp_chain_volume",
        "gdp_expenditure",
        "gva_current",
        "gva_chain_volume",
        "gsp_current",
        "gsp_chain_volume",
        "ratios",
    }
)


def _facts_conn():
    try:
        return get_facts_connection()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _normalize_level(level: str) -> str:
    if level == "national":
        return "federal"
    return level


def _mode_filters(mode: Mode) -> dict[str, Any]:
    """Map API mode → legacy compatibility_group + estimate statuses + view_family."""
    try:
        view_family = mode_to_view_family("gdp_current" if mode == "gdp" else mode)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if mode == "actuals":
        return {
            "compatibility_group": "actual_expense",
            "estimate_statuses": ("actual", "audited_actual"),
            "view_family": view_family,
        }
    if mode == "budget":
        return {
            "compatibility_group": "budget_expense",
            "estimate_statuses": (
                "budget",
                "forward_estimate",
                "revised_estimate",
                "estimated_actual",
            ),
            "view_family": view_family,
        }
    if mode == "debt":
        return {
            "compatibility_group": "gfs_liability",
            "estimate_statuses": ("actual", "audited_actual"),
            "view_family": view_family,
        }
    if mode == "revenue":
        return {
            "compatibility_group": "gfs_revenue",
            "estimate_statuses": ("actual", "audited_actual"),
            "view_family": view_family,
        }
    if mode in _ECONOMY_MODES:
        return {
            "compatibility_group": "gdp",
            "estimate_statuses": ("actual", "audited_actual"),
            "view_family": view_family,
            "economy_mode": mode if mode != "gdp" else "gdp_current",
        }
    raise HTTPException(
        status_code=400,
        detail=(
            "mode must be actuals|budget|debt|revenue|gdp|gdp_current|"
            "gdp_chain_volume|gdp_expenditure|gva_current|gva_chain_volume|"
            "gsp_current|gsp_chain_volume|ratios"
        ),
    )


def _economy_measure_clause(economy_mode: str | None) -> tuple[str, tuple[str, ...]]:
    """SQL fragment restricting GDP-bucket facts to one view family."""
    if not economy_mode:
        return "", ()
    if economy_mode == "gdp_current":
        return "AND f.measure_type = ?", ("gdp_current",)
    if economy_mode == "gdp_chain_volume":
        return "AND f.measure_type = ?", ("gdp_chain_volume",)
    if economy_mode == "gdp_expenditure":
        return "AND f.measure_type = ?", ("gdp_current",)
    if economy_mode == "gva_current":
        return "AND f.measure_type IN (?, ?)", ("gdp_current", "gva_current")
    if economy_mode == "gva_chain_volume":
        return "AND f.measure_type IN (?, ?)", ("gdp_chain_volume", "gva_chain_volume")
    if economy_mode == "gsp_current":
        return "AND f.measure_type = ?", ("gsp_current",)
    if economy_mode == "gsp_chain_volume":
        return "AND f.measure_type = ?", ("gsp_chain_volume",)
    if economy_mode == "ratios":
        return "AND f.measure_type = ?", ("tax_to_gdp_ratio",)
    return "", ()


def _estatus_clause(statuses: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    placeholders = ", ".join("?" for _ in statuses)
    return f"IN ({placeholders})", statuses


def _preferred_basis(
    conn, mode: Mode, level: str, year: str | None
) -> str | None:
    """Prefer GFS for actuals when both GFS and accrual exist for level/year."""
    if mode != "actuals":
        return None
    filt = _mode_filters(mode)
    est_sql, est_params = _estatus_clause(filt["estimate_statuses"])
    params: list[Any] = [
        filt["compatibility_group"],
        level,
        *est_params,
    ]
    sql = f"""
        SELECT DISTINCT f.accounting_basis
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        WHERE m.compatibility_group = ?
          AND CASE d.government_level WHEN 'national' THEN 'federal'
              ELSE d.government_level END = ?
          AND f.estimate_status {est_sql}
    """
    if year:
        sql += " AND f.financial_year = ?"
        params.append(year)
    bases = {r[0] for r in conn.execute(sql, params).fetchall()}
    if "gfs" in bases:
        return "gfs"
    if "accrual" in bases:
        return "accrual"
    return None


def _fact_rows(
    conn,
    mode: Mode,
    level: str,
    year: str,
    *,
    valuation_basis: str | None = None,
) -> list[dict[str, Any]]:
    filt = _mode_filters(mode)
    preferred = _preferred_basis(conn, mode, level, year)
    est_sql, est_params = _estatus_clause(filt["estimate_statuses"])
    eco_sql, eco_params = _economy_measure_clause(filt.get("economy_mode"))
    params: list[Any] = [
        filt["compatibility_group"],
        level,
        year,
        *est_params,
        *eco_params,
    ]
    sql = f"""
        SELECT
            f.id AS fact_id,
            f.amount_aud,
            f.amount_value,
            f.quantity,
            f.unit,
            f.currency,
            f.price_basis,
            f.view_family,
            d.jurisdiction,
            n.name AS node_name,
            f.accounting_basis,
            d.source_key,
            f.observation_date,
            f.valuation_basis,
            f.amount_granularity,
            f.source_locator_json,
            f.measure_type,
            f.quality_status
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        WHERE m.compatibility_group = ?
          AND CASE d.government_level WHEN 'national' THEN 'federal'
              ELSE d.government_level END = ?
          AND f.financial_year = ?
          AND f.estimate_status {est_sql}
          {eco_sql}
          AND COALESCE(f.quality_status, 'ok') NOT IN ('quarantined', 'rejected')
    """
    if preferred:
        sql += " AND f.accounting_basis = ?"
        params.append(preferred)
    if valuation_basis and valuation_basis not in ("all", "comparison"):
        sql += " AND COALESCE(f.valuation_basis, 'unspecified') = ?"
        params.append(valuation_basis)
    sql += " ORDER BY d.jurisdiction, n.name"
    rows = []
    for r in conn.execute(sql, params).fetchall():
        locator = r["source_locator_json"] or ""
        if "roll_up:sum_instruments" in locator:
            continue
        if (r["amount_granularity"] or "") == "instrument_type_aggregate" and "roll_up:" in locator:
            continue
        row = {
            "fact_id": int(r["fact_id"]),
            "amount_aud": r["amount_aud"],
            "amount_value": r["amount_value"],
            "quantity": r["quantity"],
            "unit": r["unit"] or "AUD",
            "currency": r["currency"],
            "price_basis": r["price_basis"] or "unspecified",
            "view_family": r["view_family"],
            "jurisdiction": r["jurisdiction"] or "Uncategorized",
            "node_name": (r["node_name"] or "Uncategorized").strip(),
            "accounting_basis": r["accounting_basis"],
            "source_key": r["source_key"],
            "observation_date": r["observation_date"],
            "valuation_basis": r["valuation_basis"],
            "amount_granularity": r["amount_granularity"],
            "measure_type": r["measure_type"],
        }
        val = display_value(row)
        if val is None:
            continue
        row["amount_aud"] = float(val)  # tree builder uses amount_aud as display magnitude
        eco = filt.get("economy_mode")
        name = row["node_name"]
        anzsic = bool(re.search(r"\([A-S]\)\s*$", name)) or bool(
            re.search(r"\([A-S]\)\s*/", name)
        )
        if eco == "gdp_current":
            # National GDP / expenditure aggregates only — not industry GVA lines.
            if anzsic:
                continue
            if re.search(r"tax.*%|% of gdp|derived ratio", name, re.I):
                continue
        elif eco == "gdp_chain_volume":
            if anzsic:
                continue
        elif eco == "gdp_expenditure":
            if anzsic:
                continue
            if not re.search(
                r"expenditure on gdp|gdp \(current|final consumption|gross fixed|"
                r"changes in inventories|exports of goods|imports of goods|less imports",
                name,
                re.I,
            ):
                continue
        elif eco in ("gva_current", "gva_chain_volume"):
            if not anzsic and not re.search(r"\bgva\b|gross value added|industry", name, re.I):
                continue
        elif eco in ("gsp_current", "gsp_chain_volume"):
            if not re.search(r"\bgsp\b|gross state", name, re.I) and row["measure_type"] not in (
                "gsp_current",
                "gsp_chain_volume",
            ):
                # measure filter already applied; keep all gsp_* rows
                pass
        rows.append(row)
    return rows


def _path_parts(node_name: str, source_key: str | None = None, mode: Mode | None = None) -> list[str] | None:
    """Split a node into tree path parts. None means omit the fact from the tree."""
    name = (node_name or "Uncategorized").strip()
    if source_key and source_key.startswith("aofm_"):
        # "Treasury Bonds / 21 Nov 2035" → Debt securities → Treasury Bonds → detail
        bits = [p.strip() for p in name.split(" / ") if p.strip()]
        if not bits:
            return ["Debt securities"]
        if bits[0].startswith("Debt securities"):
            return bits
        return ["Debt securities", *bits]
    if name.startswith("Provisions for defined-benefit superannuation"):
        bits = [p.strip() for p in name.split(" / ") if p.strip()]
        return bits or [name]
    if is_abs_gfs_liability_source(source_key):
        return abs_gfs_liability_path(name)
    if is_abs_gfs_revenue_source(source_key):
        return abs_gfs_revenue_path(name)
    if is_abs_gfs_source(source_key):
        return abs_gfs_hierarchy_path(name)
    if mode in _ECONOMY_MODES or mode == "gdp":
        return gdp_hierarchy_path(name)
    parts = [p.strip() for p in name.split(" / ") if p.strip()]
    return parts or [name or "Uncategorized"]


def _is_total_name(name: str) -> bool:
    return bool(TOTAL_RE.match(name.strip()))


def _prune_totals(node: dict[str, Any]) -> None:
    children = node.get("children") or {}
    if not children:
        return
    names = list(children.keys())
    non_totals = [n for n in names if not _is_total_name(n)]
    if non_totals:
        for n in names:
            if _is_total_name(n):
                del children[n]
    for child in children.values():
        _prune_totals(child)


def _build_tree_dict(rows: list[dict[str, Any]], mode: Mode | None = None) -> dict[str, Any]:
    root: dict[str, Any] = {
        "children": {},
        "amount": 0.0,
        "fact_id": None,
        "observation_dates": set(),
        "valuation_bases": set(),
    }
    for row in rows:
        nested = _path_parts(row["node_name"], row.get("source_key"), mode=mode)
        if nested is None:
            continue
        parts = [row["jurisdiction"], *nested]
        cursor = root
        for part in parts:
            kids = cursor.setdefault("children", {})
            if part not in kids:
                kids[part] = {
                    "children": {},
                    "amount": 0.0,
                    "fact_id": None,
                    "observation_dates": set(),
                    "valuation_bases": set(),
                }
            cursor = kids[part]
        # Leaf-only: accumulate amount only on the leaf node; parents roll up from children.
        cursor["amount"] = float(cursor.get("amount") or 0) + row["amount_aud"]
        cursor["fact_id"] = row["fact_id"]
        if row.get("observation_date"):
            cursor.setdefault("observation_dates", set()).add(str(row["observation_date"]))
            root.setdefault("observation_dates", set()).add(str(row["observation_date"]))
        if row.get("valuation_basis"):
            cursor["valuation_basis"] = row["valuation_basis"]
            cursor.setdefault("valuation_bases", set()).add(str(row["valuation_basis"]))
            root.setdefault("valuation_bases", set()).add(str(row["valuation_basis"]))
        if row.get("amount_granularity"):
            cursor["amount_granularity"] = row["amount_granularity"]
            cursor["is_aggregate"] = row["amount_granularity"] in {
                "instrument_type_aggregate",
                "scheme_aggregate",
                "council_aggregate",
            }
        if row.get("unit"):
            cursor["unit"] = row["unit"]
        if mode in _ECONOMY_MODES and re.search(
            r"gdp \(current|gsp \(current|gdp \(chain", parts[-1], re.I
        ):
            cursor["preserve_amount"] = True
    _prune_totals(root)
    return root


def _breakdown_meta(node: dict[str, Any]) -> BreakdownMeta | None:
    raw = node.get("breakdown")
    if not raw:
        return None
    return BreakdownMeta(**raw)


def _to_tree_node(name: str, node: dict[str, Any]) -> TreeNode:
    children_map = node.get("children") or {}
    breakdown = _breakdown_meta(node)
    obs_dates = sorted(node.get("observation_dates") or [])
    mixed = len(obs_dates) > 1
    val_bases = sorted(node.get("valuation_bases") or [])
    mixed_val = len(val_bases) > 1
    warnings: list[str] = []
    if mixed:
        warnings.append(
            "Mixed observation dates across nested liabilities — do not treat as a single as-at stock."
        )
    if mixed_val:
        warnings.append(
            "Mixed valuation bases — comparison only; do not treat as an unqualified total."
        )
    extra = {
        "valuation_basis": node.get("valuation_basis"),
        "valuation_bases": val_bases or None,
        "mixed_valuation_bases": mixed_val if val_bases else None,
        "amount_granularity": node.get("amount_granularity"),
        "is_aggregate": node.get("is_aggregate"),
        "observation_dates": obs_dates or None,
        "mixed_observation_dates": mixed if obs_dates else None,
        "unit": node.get("unit"),
        "warning": "; ".join(warnings) if warnings else None,
    }
    if children_map:
        children = [_to_tree_node(k, v) for k, v in children_map.items()]
        # Related children must not re-total the parent pie slice.
        if breakdown and breakdown.kind == "related_breakdown":
            return TreeNode(
                name=name,
                value=float(node.get("amount") or 0),
                id=node.get("fact_id"),
                children=children,
                breakdown=breakdown,
                **extra,
            )
        # Keep published fact amount when cascading deeper packs under a slice
        # (e.g. A.6.1 sub-function → components → PBS).
        if node.get("preserve_amount") and node.get("amount") is not None:
            return TreeNode(
                name=name,
                value=float(node.get("amount") or 0),
                id=node.get("fact_id"),
                children=children,
                breakdown=breakdown,
                **extra,
            )
        # Exclude synthetic related folders (Statement 6 …) from same_group rollup.
        # Purpose nodes that themselves carry related_breakdown keep their GFS value
        # and must still count in the parent pie.
        # Exclude related navigation folders (Statement 6 / FBO) from GFS pie rollup.
        # Purpose nodes that themselves carry related_breakdown (e.g. Social protection
        # leaf replace) still contribute their preserved ABS amount to the parent pie.
        additive = [
            c
            for c in children
            if not (
                c.breakdown
                and c.breakdown.kind == "related_breakdown"
                and (
                    c.value == 0
                    or c.name.startswith("Statement 6")
                    or c.name.startswith("FBO Appendix A")
                )
            )
        ]
        if additive:
            total = sum(c.value for c in additive)
        else:
            total = float(node.get("amount") or 0)
        return TreeNode(
            name=name,
            value=total,
            id=None if additive else node.get("fact_id"),
            children=children,
            breakdown=breakdown,
            **extra,
        )
    return TreeNode(
        name=name,
        value=float(node.get("amount") or 0),
        id=node.get("fact_id"),
        children=None,
        breakdown=breakdown,
        **extra,
    )


@router.get("/levels")
def dashboard_levels(mode: Mode = Query(...)) -> list[dict]:
    filt = _mode_filters(mode)
    est_sql, est_params = _estatus_clause(filt["estimate_statuses"])
    conn = _facts_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT
                CASE d.government_level WHEN 'national' THEN 'federal'
                    ELSE d.government_level END AS level,
                COUNT(*) AS n
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            WHERE m.compatibility_group = ?
              AND f.estimate_status {est_sql}
            GROUP BY 1
            """,
            (filt["compatibility_group"], *est_params),
        ).fetchall()
    finally:
        conn.close()
    by_level = {_normalize_level(r["level"]): int(r["n"]) for r in rows}
    return [
        {"level": lvl, "row_count": by_level[lvl]}
        for lvl in LEVEL_ORDER
        if lvl in by_level
    ]


@router.get("/years")
def dashboard_years(mode: Mode = Query(...), level: str = Query(...)) -> list[str]:
    filt = _mode_filters(mode)
    level = _normalize_level(level)
    est_sql, est_params = _estatus_clause(filt["estimate_statuses"])
    conn = _facts_conn()
    try:
        preferred = _preferred_basis(conn, mode, level, None)
        params: list[Any] = [
            filt["compatibility_group"],
            level,
            *est_params,
        ]
        sql = f"""
            SELECT DISTINCT f.financial_year
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            WHERE m.compatibility_group = ?
              AND CASE d.government_level WHEN 'national' THEN 'federal'
                  ELSE d.government_level END = ?
              AND f.estimate_status {est_sql}
        """
        if preferred:
            sql += " AND f.accounting_basis = ?"
            params.append(preferred)
        sql += " ORDER BY f.financial_year"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


@router.get("/tree", response_model=TreeNode)
def dashboard_tree(
    mode: Mode = Query(...),
    level: str = Query(...),
    year: str = Query(...),
    valuation_basis: str | None = Query(
        None,
        description="Debt filter: face_value|fair_value|… or all/comparison",
    ),
) -> TreeNode:
    level = _normalize_level(level)
    filt = _mode_filters(mode)
    conn = _facts_conn()
    try:
        rows = _fact_rows(conn, mode, level, year, valuation_basis=valuation_basis)
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No {mode} data for level={level!r} year={year!r}",
            )
        try:
            decision = assert_compatible_or_raise(
                validate_fact_set(
                    rows,
                    view_family=filt["view_family"],
                    valuation_filter=valuation_basis,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        tree_dict = _build_tree_dict(rows, mode=mode)
        if mode == "actuals":
            attach_related_to_tree(conn, tree_dict, year)
        elif mode == "budget" and level == "federal":
            apply_edge_cascade_to_budget_tree(conn, tree_dict, year)
    finally:
        conn.close()
    children = [
        _to_tree_node(name, child)
        for name, child in (tree_dict.get("children") or {}).items()
    ]
    obs_dates = sorted(tree_dict.get("observation_dates") or [])
    mixed = len(obs_dates) > 1
    val_bases = sorted(tree_dict.get("valuation_bases") or [])
    mixed_val = len(val_bases) > 1
    warnings = list(decision.warnings)
    if mixed and mode == "debt":
        warnings.append(
            "Mixed observation dates across authorities — figures are not a single as-at stock."
        )
    if mixed_val:
        warnings.append(
            "Mixed valuation bases — comparison only; unqualified total disabled."
        )
        decision.root_total_allowed = False

    if decision.root_total_allowed and decision.additive_across_nodes:
        total = sum(c.value for c in children)
    else:
        total = 0.0
        if not decision.root_total_allowed:
            warnings.append("Root total suppressed (non-additive or incompatible set).")

    unit = decision.units[0] if len(decision.units) == 1 else None
    return TreeNode(
        name=f"{level} — {year}",
        value=total,
        id=None,
        children=children,
        mixed_observation_dates=mixed if mode == "debt" and obs_dates else None,
        observation_dates=obs_dates if mode == "debt" and obs_dates else None,
        valuation_bases=val_bases or None,
        mixed_valuation_bases=mixed_val if val_bases else None,
        unit=unit,
        view_family=decision.view_family,
        root_total_allowed=decision.root_total_allowed,
        warning="; ".join(warnings) if warnings else None,
    )


def _parse_levels_param(levels: str) -> list[str]:
    raw = [_normalize_level(part.strip()) for part in levels.split(",") if part.strip()]
    if not raw:
        raise HTTPException(status_code=400, detail="levels must list at least one government level")
    unknown = [lvl for lvl in raw if lvl not in LEVEL_ORDER]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown level(s): {unknown!r}; expected one of {list(LEVEL_ORDER)}",
        )
    # Preserve LEVEL_ORDER, drop duplicates
    ordered = [lvl for lvl in LEVEL_ORDER if lvl in set(raw)]
    return ordered


def _years_for_level(conn, mode: Mode, level: str) -> list[str]:
    filt = _mode_filters(mode)
    preferred = _preferred_basis(conn, mode, level, None)
    est_sql, est_params = _estatus_clause(filt["estimate_statuses"])
    params: list[Any] = [filt["compatibility_group"], level, *est_params]
    sql = f"""
        SELECT DISTINCT f.financial_year
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        WHERE m.compatibility_group = ?
          AND CASE d.government_level WHEN 'national' THEN 'federal'
              ELSE d.government_level END = ?
          AND f.estimate_status {est_sql}
    """
    if preferred:
        sql += " AND f.accounting_basis = ?"
        params.append(preferred)
    sql += " ORDER BY f.financial_year"
    return [r[0] for r in conn.execute(sql, params).fetchall()]


def _first_fact_id(node: TreeNode) -> int | None:
    if node.id is not None:
        return int(node.id)
    for child in node.children or []:
        found = _first_fact_id(child)
        if found is not None:
            return found
    return None


def _sum_named_nodes(
    node: dict[str, Any], name_lower: str
) -> tuple[float, int | None]:
    """Sum tree values for nodes whose name matches (no double-count of descendants)."""
    total = 0.0
    fact_id: int | None = None
    children = node.get("children") or {}
    for child_name, child in children.items():
        if child_name.strip().lower() == name_lower:
            tree_node = _to_tree_node(child_name, child)
            total += float(tree_node.value or 0)
            sample = _first_fact_id(tree_node)
            if sample is not None:
                fact_id = sample
            continue
        sub_total, sub_id = _sum_named_nodes(child, name_lower)
        total += sub_total
        if sub_id is not None:
            fact_id = sub_id
    return total, fact_id


def _level_point(
    conn, mode: Mode, level: str, year: str, category: str | None
) -> dict[str, Any] | None:
    rows = _fact_rows(conn, mode, level, year)
    if not rows:
        return None
    tree_dict = _build_tree_dict(rows, mode=mode)
    children = [
        _to_tree_node(name, child)
        for name, child in (tree_dict.get("children") or {}).items()
    ]
    if category and category.strip():
        amount, fact_id = _sum_named_nodes(tree_dict, category.strip().lower())
        if amount == 0 and fact_id is None:
            return None
        return {
            "financial_year": year,
            "total_aud": amount,
            "fact_id": fact_id,
        }
    total = sum(c.value for c in children)
    sample_id = None
    for c in children:
        sample_id = _first_fact_id(c)
        if sample_id is not None:
            break
    return {
        "financial_year": year,
        "total_aud": float(total),
        "fact_id": sample_id,
    }


@router.get("/series")
def dashboard_series(
    mode: Mode = Query(...),
    levels: str = Query(..., description="Comma-separated government levels"),
    category: str | None = Query(
        default=None,
        description="Optional category/purpose name; empty = per-level totals",
    ),
) -> dict:
    """Per-level time series for timeline comparison (never cross-level summed)."""
    level_list = _parse_levels_param(levels)
    cat = category.strip() if category and category.strip() else None
    conn = _facts_conn()
    try:
        series_out: list[dict[str, Any]] = []
        year_set: set[str] = set()
        for level in level_list:
            years = _years_for_level(conn, mode, level)
            points: list[dict[str, Any]] = []
            for year in years:
                point = _level_point(conn, mode, level, year, cat)
                if point is None:
                    continue
                points.append(point)
                year_set.add(year)
            series_out.append({"level": level, "points": points})
    finally:
        conn.close()
    return {
        "mode": mode,
        "category": cat,
        "years": sorted(year_set),
        "series": series_out,
        "note": "Per-level series; not a consolidated Australia total.",
        "warning": (
            "Debt timeline may mix face-value and fair-value stocks across years/authorities; "
            "do not treat as continuous same-definition series."
            if mode == "debt"
            else None
        ),
    }


def _fact_locator_row(fact_id: int):
    conn = _facts_conn()
    try:
        return conn.execute(
            """
            SELECT
                f.id,
                f.financial_year,
                f.amount_aud,
                f.measure_type,
                f.accounting_basis,
                f.estimate_status,
                f.source_locator_json,
                d.jurisdiction,
                d.source_key,
                CASE d.government_level WHEN 'national' THEN 'federal'
                    ELSE d.government_level END AS level,
                d.title AS source_document_name,
                n.name AS node_name,
                r.local_path
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            LEFT JOIN fact_nodes fn
                ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            LEFT JOIN nodes n ON n.id = fn.node_id
            LEFT JOIN source_retrievals r ON r.id = f.source_retrieval_id
            WHERE f.id = ?
            """,
            (fact_id,),
        ).fetchone()
    finally:
        conn.close()


def _cached_path_for_fact(row) -> str | None:
    _, cached_from_locator, _ = parse_source_locator_json(row["source_locator_json"])
    return cached_from_locator or row["local_path"]


@router.get("/item/{fact_id}")
def dashboard_item(fact_id: int) -> dict:
    citation = build_citation(fact_id)
    row = _fact_locator_row(fact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    return {
        "id": row["id"],
        "financial_year": row["financial_year"],
        "level_of_government": row["level"],
        "jurisdiction": row["jurisdiction"],
        "category": row["node_name"],
        "amount_aud": row["amount_aud"],
        "measure_type": row["measure_type"],
        "accounting_basis": row["accounting_basis"],
        "estimate_status": row["estimate_status"],
        "source_document_name": row["source_document_name"],
        "breakdown_note": abs_gfs_breakdown_note(row["source_key"], row["node_name"]),
        "citation": citation,
    }


@router.get("/item/{fact_id}/children")
def dashboard_item_children(
    fact_id: int,
    year: str | None = Query(default=None),
) -> dict:
    """Primary same_group children, else related_breakdown children for FY."""
    row = _fact_locator_row(fact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    fy = year or row["financial_year"]
    conn = _facts_conn()
    try:
        nid = primary_node_id(conn, fact_id)
        if nid is None:
            return {
                "fact_id": fact_id,
                "financial_year": fy,
                "kind": "empty",
                "children": [],
                "breakdown": None,
            }
        same_list, _ = build_same_group_subtree(
            conn, nid, fy, parent_name=row["node_name"]
        )
        if same_list:
            # A node can have BOTH same_group children (Statement 6's own
            # further additive breakdown - functions/subfunctions almost
            # always do, via the a61_to_components/pbs_under_component
            # cascades) AND related_breakdown children (e.g. this
            # crosswalk's PBS program detail). Surfacing only same_group
            # here would make every related_breakdown edge on a
            # non-leaf Statement 6 node permanently unreachable - append a
            # clearly non-additive folder rather than dropping it.
            related_list, related_bd = build_related_subtree(
                conn, nid, fy, parent_name=row["node_name"]
            )
            if related_list and related_bd:
                same_list = list(same_list) + [
                    {
                        "name": "Related PBS program detail",
                        "node": {
                            "children": {item["name"]: item["node"] for item in related_list},
                            "amount": float(row["amount_aud"] or 0),
                            "fact_id": None,
                            "node_id": None,
                            "source_key": related_bd.get("source_key"),
                            "compatibility_group": related_bd.get("compatibility_group"),
                            "breakdown": related_bd,
                            "preserve_amount": True,
                        },
                    }
                ]
            children = [
                _to_tree_node(item["name"], item["node"]) for item in same_list
            ]
            return {
                "fact_id": fact_id,
                "financial_year": fy,
                "kind": "same_group",
                "children": [c.model_dump() for c in children],
                "breakdown": {
                    "kind": "same_group",
                    "source_key": row["source_key"],
                    "compatibility_group": None,
                    "banner": None,
                },
            }
        related_list, breakdown = build_related_subtree(
            conn, nid, fy, parent_name=row["node_name"]
        )
        if related_list and breakdown:
            children = [
                _to_tree_node(item["name"], item["node"]) for item in related_list
            ]
            return {
                "fact_id": fact_id,
                "financial_year": fy,
                "kind": "related_breakdown",
                "children": [c.model_dump() for c in children],
                "breakdown": breakdown,
                "parent_amount_aud": row["amount_aud"],
            }
        return {
            "fact_id": fact_id,
            "financial_year": fy,
            "kind": "empty",
            "children": [],
            "breakdown": None,
            "breakdown_note": abs_gfs_breakdown_note(
                row["source_key"], row["node_name"]
            ),
        }
    finally:
        conn.close()


@router.get("/item/{fact_id}/evidence")
def dashboard_item_evidence(fact_id: int) -> dict:
    citation = build_citation(fact_id)
    row = _fact_locator_row(fact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")

    _, _, locator_str = parse_source_locator_json(row["source_locator_json"])
    parsed = parse_locator_string(locator_str or citation.get("locator") or "")
    cached_path = _cached_path_for_fact(row)
    source = resolve_fact_source_file(cached_path)
    path = source.path if source else None
    media = media_type_for_path(path, parsed)
    reconstructed = build_reconstructed(path, media, parsed)

    # Prefer reconstructed CSV highlight when present
    highlight = parsed.get("highlight")
    if reconstructed and reconstructed.get("highlight"):
        highlight = reconstructed["highlight"]

    columns: list[str] = []
    rows: list[list[Any]] = []
    if reconstructed:
        columns = list(reconstructed.get("columns") or [])
        rows = list(reconstructed.get("rows") or [])

    return {
        "fact_id": fact_id,
        "media_type": media,
        "file_name": source.file_name if source else None,
        "content_type": source.content_type if source else None,
        "has_source_file": source is not None,
        "sheet_name": parsed.get("sheet_name"),
        "cell": parsed.get("cell"),
        "cell_range": parsed.get("cell_range"),
        "page_number": parsed.get("page_number"),
        "row_number": parsed.get("row_number"),
        "text_anchor": parsed.get("text_anchor"),
        "purpose": parsed.get("purpose"),
        "financial_year_label": parsed.get("financial_year_label"),
        "unit": parsed.get("unit"),
        "amount_aud": row["amount_aud"],
        "highlight": highlight,
        "columns": columns,
        "rows": rows,
        "note": (reconstructed or {}).get("note") or parsed.get("note"),
        "locator": locator_str or citation.get("locator"),
        "breakdown_note": abs_gfs_breakdown_note(row["source_key"], row["node_name"]),
        "citation": citation,
        "item": {
            "id": row["id"],
            "financial_year": row["financial_year"],
            "level_of_government": row["level"],
            "jurisdiction": row["jurisdiction"],
            "category": row["node_name"],
            "amount_aud": row["amount_aud"],
            "measure_type": row["measure_type"],
            "accounting_basis": row["accounting_basis"],
            "estimate_status": row["estimate_status"],
            "source_document_name": row["source_document_name"],
        },
    }


@router.get("/item/{fact_id}/source-file", response_class=FileResponse)
def dashboard_item_source_file(fact_id: int) -> FileResponse:
    row = _fact_locator_row(fact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    source = resolve_fact_source_file(_cached_path_for_fact(row))
    if source is None:
        raise HTTPException(status_code=404, detail="Cached source file is unavailable")
    return FileResponse(
        path=source.path,
        media_type=source.content_type,
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Disposition": f'inline; filename="{source.file_name}"',
            "X-Fact-Id": str(fact_id),
        },
    )
