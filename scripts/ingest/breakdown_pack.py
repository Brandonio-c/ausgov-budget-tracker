#!/usr/bin/env python3
"""Run a breakdown pack: extract → publish → emit related/same_group edges."""

from __future__ import annotations

import argparse
import importlib.util
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

PACKS_DIR = REPO_ROOT / "config" / "breakdowns"
CROSSWALKS_DIR = PACKS_DIR / "crosswalks"
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_extractor(extractor_rel: str) -> dict[str, Any]:
    path = REPO_ROOT / extractor_rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        mod.main()
    return {"extractor": extractor_rel}


def ensure_node(conn: sqlite3.Connection, source_key: str, name: str, mapping_meta: dict) -> int:
    canonical = f"{source_key}|node|{name}"
    row = conn.execute(
        "SELECT id FROM nodes WHERE canonical_key = ?", (canonical,)
    ).fetchone()
    if row:
        return int(row[0])
    # Find source_document for this source_key
    doc = conn.execute(
        "SELECT id, jurisdiction, government_level FROM source_documents WHERE source_key = ?",
        (source_key,),
    ).fetchone()
    if not doc:
        raise RuntimeError(f"source_documents missing for {source_key}")
    cur = conn.execute(
        """
        INSERT INTO nodes (
            canonical_key, node_type, name, jurisdiction, government_level,
            source_document_id, source_locator_json
        ) VALUES (?, 'category', ?, ?, ?, ?, '{}')
        """,
        (
            canonical,
            name,
            doc[1] or mapping_meta.get("jurisdiction", "Commonwealth"),
            doc[2] or mapping_meta.get("government_level", "federal"),
            doc[0],
        ),
    )
    return int(cur.lastrowid)


def link_same_group_from_paths(
    conn: sqlite3.Connection,
    source_key: str,
    mapping_meta: dict,
) -> int:
    """Create same_group edges Parent←Child for hierarchical node names."""
    nodes = conn.execute(
        """
        SELECT n.id, n.name
        FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = ?
        """,
        (source_key,),
    ).fetchall()
    by_name = {r[1]: r[0] for r in nodes}
    inserted = 0
    doc_id = conn.execute(
        "SELECT id FROM source_documents WHERE source_key = ?", (source_key,)
    ).fetchone()
    doc_id = doc_id[0] if doc_id else None
    for name, child_id in list(by_name.items()):
        if " / " not in name:
            continue
        parent_name = name.rsplit(" / ", 1)[0]
        parent_id = by_name.get(parent_name)
        if parent_id is None:
            parent_id = ensure_node(conn, source_key, parent_name, mapping_meta)
            by_name[parent_name] = parent_id
        conn.execute(
            """
            INSERT OR IGNORE INTO breakdown_edges (
                parent_node_id, child_node_id, edge_kind, crosswalk_id,
                financial_year, priority, source_document_id, notes
            ) VALUES (?, ?, 'same_group', NULL, NULL, 100, ?, ?)
            """,
            (parent_id, child_id, doc_id, f"path:{parent_name}"),
        )
        inserted += conn.execute("SELECT changes()").fetchone()[0]
    return inserted


def link_related_crosswalk(
    conn: sqlite3.Connection,
    crosswalk_id: str,
    child_source_key: str,
) -> int:
    """ABS COFOG leaf → Statement 6 function children via crosswalk."""
    cw = load_yaml(CROSSWALKS_DIR / f"{crosswalk_id}.yaml")
    mappings = cw.get("mappings") or []
    inserted = 0

    for m in mappings:
        abs_name = m["abs"]
        budget_fn = m["budget"]
        quality = m.get("quality", cw.get("match_quality_default", "approx"))

        abs_nodes = conn.execute(
            """
            SELECT n.id FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key LIKE 'abs_gfs_%'
              AND (
                n.name = ?
                OR lower(n.name) = lower(?)
                OR lower(n.name) = lower(?)
              )
            """,
            (abs_name, abs_name, f"Total {abs_name}"),
        ).fetchall()
        # Also match "Total health" style (lowercase purpose word)
        if abs_name:
            total_lc = f"Total {abs_name[0].lower() + abs_name[1:]}"
            extra = conn.execute(
                """
                SELECT n.id FROM nodes n
                JOIN source_documents d ON d.id = n.source_document_id
                WHERE d.source_key LIKE 'abs_gfs_%' AND n.name = ?
                """,
                (total_lc,),
            ).fetchall()
            abs_nodes = list({(r[0],) for r in list(abs_nodes) + list(extra)})
        if not abs_nodes:
            continue

        # Prefer A.6.1 immediate sub-functions; else component leaves; else function total.
        child_nodes = conn.execute(
            """
            SELECT n.id, n.name FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = ?
              AND (
                n.name = ?
                OR n.name LIKE ?
              )
            """,
            (child_source_key, budget_fn, f"{budget_fn} / %"),
        ).fetchall()
        immediate = [
            (nid, name)
            for nid, name in child_nodes
            if name == budget_fn or name.count(" / ") == 1
        ]
        subfunctions = [(nid, name) for nid, name in immediate if name.count(" / ") == 1]

        if not subfunctions:
            # Fall back to component pack leaves under this function
            comp_nodes = conn.execute(
                """
                SELECT n.id, n.name FROM nodes n
                JOIN source_documents d ON d.id = n.source_document_id
                WHERE d.source_key = 'federal_budget_statement_6_components'
                  AND n.name LIKE ?
                  AND n.name NOT LIKE ? || ' / % / % / %'
                """,
                (f"{budget_fn} / %", budget_fn),
            ).fetchall()
            # Prefer depth-2 (function / sub / component) as related children of ABS
            depth2 = [(nid, name) for nid, name in comp_nodes if name.count(" / ") == 2]
            depth1 = [(nid, name) for nid, name in comp_nodes if name.count(" / ") == 1]
            subfunctions = depth1 or depth2

        if not subfunctions:
            # Last resort: function total (documents coverage; single related child)
            totals = [(nid, name) for nid, name in immediate if name == budget_fn]
            subfunctions = totals

        if not subfunctions:
            continue

        for (parent_id,) in abs_nodes:
            for child_id, child_name in subfunctions:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO breakdown_edges (
                        parent_node_id, child_node_id, edge_kind, crosswalk_id,
                        financial_year, priority, source_document_id, notes
                    ) VALUES (?, ?, 'related_breakdown', ?, NULL, 50, NULL, ?)
                    """,
                    (
                        parent_id,
                        child_id,
                        crosswalk_id,
                        f"{abs_name}→{child_name}|{quality}",
                    ),
                )
                inserted += conn.execute("SELECT changes()").fetchone()[0]
    return inserted


def link_historical_fbo_related(
    conn: sqlite3.Connection,
    crosswalk_id: str = "cofog_to_budget_function",
    child_source_key: str = "federal_budget_archive_function_series",
) -> int:
    """Attach ABS Commonwealth purposes to historical FBO function routes."""
    cw = load_yaml(CROSSWALKS_DIR / f"{crosswalk_id}.yaml")
    inserted = 0
    for mapping in cw.get("mappings") or []:
        abs_name = str(mapping["abs"])
        budget_fn = str(mapping["budget"])
        quality = str(mapping.get("quality", cw.get("match_quality_default", "approx")))
        abs_nodes = conn.execute(
            """
            SELECT DISTINCT n.id
            FROM nodes n JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key LIKE 'abs_gfs_commonwealth%'
              AND lower(n.name) IN (lower(?), lower(?))
            """,
            (abs_name, f"Total {abs_name}"),
        ).fetchall()
        if budget_fn == "Defence":
            child = conn.execute(
                """
                SELECT n.id FROM nodes n
                JOIN source_documents d ON d.id = n.source_document_id
                WHERE d.source_key = ? AND n.name = 'General public services / Defence'
                """,
                (child_source_key,),
            ).fetchone()
        else:
            child = conn.execute(
                """
                SELECT n.id FROM nodes n
                JOIN source_documents d ON d.id = n.source_document_id
                WHERE d.source_key = ? AND n.name = ?
                """,
                (child_source_key, budget_fn),
            ).fetchone()
            if child is None:
                has_children = conn.execute(
                    """
                    SELECT 1 FROM nodes n
                    JOIN source_documents d ON d.id = n.source_document_id
                    WHERE d.source_key = ? AND n.name LIKE ? LIMIT 1
                    """,
                    (child_source_key, f"{budget_fn} / %"),
                ).fetchone()
                if has_children:
                    child = (ensure_node(conn, child_source_key, budget_fn, {}),)
        if child is None:
            continue
        for (parent_id,) in abs_nodes:
            conn.execute(
                """
                INSERT OR IGNORE INTO breakdown_edges (
                    parent_node_id, child_node_id, edge_kind, crosswalk_id,
                    financial_year, priority, source_document_id, notes
                ) VALUES (?, ?, 'related_breakdown', ?, NULL, 50, NULL, ?)
                """,
                (
                    int(parent_id),
                    int(child[0]),
                    crosswalk_id,
                    f"{abs_name}→{budget_fn}|{quality}|historical_fbo",
                ),
            )
            inserted += int(conn.execute("SELECT changes()").fetchone()[0])
    return inserted


def _norm_path(name: str) -> str:
    return " / ".join(p.strip().lower() for p in (name or "").split(" / ") if p.strip())


def _insert_same_group(
    conn: sqlite3.Connection,
    parent_id: int,
    child_id: int,
    crosswalk_id: str,
    priority: int,
    notes: str,
) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO breakdown_edges (
            parent_node_id, child_node_id, edge_kind, crosswalk_id,
            financial_year, priority, source_document_id, notes
        ) VALUES (?, ?, 'same_group', ?, NULL, ?, NULL, ?)
        """,
        (parent_id, child_id, crosswalk_id, priority, notes),
    )
    return int(conn.execute("SELECT changes()").fetchone()[0])


def link_a61_to_components(conn: sqlite3.Connection) -> int:
    """A.6.1 Function/Sub → component nodes by path prefix or exact name.

    Three-level components (Function / Sub / Component) hang under the
    matching A.6.1 Function/Sub. Function- or subfunction-level lumps that
    share an exact name with A.6.1 (e.g. Defence, Education / Higher
    education) also hang under that A.6.1 node so PBS programs attached to
    the component lump remain reachable from related_breakdown.
    """
    inserted = 0
    comps = conn.execute(
        """
        SELECT n.id, n.name FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = 'federal_budget_statement_6_components'
          AND (
            n.name LIKE '% / % / %'
            OR EXISTS (
              SELECT 1 FROM nodes a
              JOIN source_documents ad ON ad.id = a.source_document_id
              WHERE ad.source_key = 'federal_budget_statement_6_a61'
                AND lower(a.name) = lower(n.name)
            )
          )
        """
    ).fetchall()
    for child_id, child_name in comps:
        # Exact A.6.1 match first (Defence, Education / Higher education, …)
        exact = conn.execute(
            """
            SELECT n.id FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = 'federal_budget_statement_6_a61'
              AND lower(n.name) = lower(?)
            """,
            (child_name,),
        ).fetchall()
        if exact:
            for (parent_id,) in exact:
                inserted += _insert_same_group(
                    conn,
                    parent_id,
                    child_id,
                    "a61_to_components",
                    90,
                    f"a61→comp-exact:{child_name}",
                )
            continue
        # Else 3-level: parent is Function / Sub
        if child_name.count(" / ") < 2:
            continue
        parent_path = child_name.rsplit(" / ", 1)[0]
        parents = conn.execute(
            """
            SELECT n.id FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = 'federal_budget_statement_6_a61'
              AND lower(n.name) = lower(?)
            """,
            (parent_path,),
        ).fetchall()
        for (parent_id,) in parents:
            inserted += _insert_same_group(
                conn,
                parent_id,
                child_id,
                "a61_to_components",
                90,
                f"a61→comp:{child_name}",
            )
    return inserted


def link_pbs_to_components(conn: sqlite3.Connection) -> int:
    """Prefer component parent; else A.6.1 sub-function for PBS program nodes."""
    inserted = 0
    pbs_keys = (
        "federal_dss_pbs_programs",
        "federal_health_pbs_programs",
        "federal_pbs_programs_s6_bridge",
    )
    placeholders = ", ".join("?" for _ in pbs_keys)
    pbs = conn.execute(
        f"""
        SELECT n.id, n.name, d.source_key FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key IN ({placeholders})
          AND (n.name LIKE '% / % / %' OR n.name LIKE 'Defence / %')
        """,
        pbs_keys,
    ).fetchall()
    for pbs_id, pbs_name, pbs_source in pbs:
        # 3-level PBS paths: Function / Sub / Program → parent Function / Sub
        # 2-level (Defence): Function / Program → parent Function
        parts = [p.strip() for p in pbs_name.split(" / ") if p.strip()]
        if len(parts) < 2:
            continue
        parent_path = " / ".join(parts[:-1])
        program_leaf = parts[-1]
        # Prefer exact component leaf match (program under same path as component name)
        # First: parent is component node whose name equals Function/Sub/Component
        # matching PBS path when PBS program name ≈ component leaf.
        component_parents = conn.execute(
            """
            SELECT n.id, n.name FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = 'federal_budget_statement_6_components'
              AND (
                lower(n.name) = lower(?)
                OR (
                  lower(n.name) LIKE lower(?) || ' / %'
                  AND lower(n.name) NOT LIKE lower(?) || ' / % / %'
                )
              )
            """,
            (parent_path + " / " + program_leaf, parent_path, parent_path),
        ).fetchall()
        # Prefer: PBS hangs under matching component leaf when names align;
        # else under Function/Sub parent (component intermediate or A.6.1).
        matched_component_leaf = [
            (nid, name)
            for nid, name in component_parents
            if _norm_path(name) == _norm_path(parent_path + " / " + program_leaf)
            or _norm_path(name.rsplit(" / ", 1)[-1]) == _norm_path(program_leaf)
        ]
        if matched_component_leaf:
            for parent_id, _ in matched_component_leaf:
                inserted += _insert_same_group(
                    conn,
                    parent_id,
                    pbs_id,
                    "pbs_under_component",
                    70,
                    f"pbs:{pbs_source}:{pbs_name}",
                )
            continue

        # Function/Sub parents: components intermediate nodes, then A.6.1
        parents = conn.execute(
            """
            SELECT n.id, d.source_key FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key IN (
                'federal_budget_statement_6_components',
                'federal_budget_statement_6_a61'
            )
              AND lower(n.name) = lower(?)
            ORDER BY CASE d.source_key
                WHEN 'federal_budget_statement_6_components' THEN 0
                ELSE 1
            END
            """,
            (parent_path,),
        ).fetchall()
        # Prefer component parent only; if none, use A.6.1
        comp_parents = [p for p in parents if p[1] == "federal_budget_statement_6_components"]
        a61_parents = [p for p in parents if p[1] == "federal_budget_statement_6_a61"]
        chosen = comp_parents or a61_parents
        for parent_id, _sk in chosen:
            inserted += _insert_same_group(
                conn,
                parent_id,
                pbs_id,
                "pbs_dss_bridge",
                80 if comp_parents else 75,
                f"pbs:{pbs_source}:{pbs_name}",
            )
    return inserted


def link_path_children_under_cascade(
    conn: sqlite3.Connection,
    *,
    child_source_key: str,
    crosswalk_id: str,
    parent_sources: tuple[str, ...] = (
        "federal_dss_pbs_programs",
        "federal_health_pbs_programs",
        "federal_budget_statement_6_components",
        "federal_budget_statement_6_a61",
        "federal_pbs_programs_s6_bridge",
    ),
    priority: int = 55,
) -> int:
    """Attach ``{parent_path} / …`` children from *child_source_key* under cascade parents."""
    children = conn.execute(
        """
        SELECT n.id, n.name FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = ?
          AND n.name LIKE '% / %'
        """,
        (child_source_key,),
    ).fetchall()
    parents = conn.execute(
        f"""
        SELECT n.id, n.name, d.source_key FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key IN ({", ".join("?" for _ in parent_sources)})
        """,
        parent_sources,
    ).fetchall()
    # Prefer earlier parent_sources entries when names collide (e.g. bare "Defence")
    sk_rank = {sk: i for i, sk in enumerate(parent_sources)}
    by_lower: dict[str, int] = {}
    by_lower_rank: dict[str, int] = {}
    for nid, name, sk in parents:
        key = name.lower()
        rank = sk_rank.get(sk, 99)
        if key not in by_lower or rank < by_lower_rank[key]:
            by_lower[key] = int(nid)
            by_lower_rank[key] = rank

    inserted = 0
    seen: set[tuple[int, int]] = set()
    for child_id, child_name in children:
        parts = [p.strip() for p in child_name.split(" / ") if p.strip()]
        if len(parts) < 2:
            continue
        parent_id = None
        attach_id = int(child_id)
        for cut in range(len(parts) - 1, 0, -1):
            prefix = " / ".join(parts[:cut])
            pid = by_lower.get(prefix.lower())
            if pid is None:
                continue
            child_path = " / ".join(parts[: cut + 1])
            crow = conn.execute(
                """
                SELECT n.id FROM nodes n
                JOIN source_documents d ON d.id = n.source_document_id
                WHERE d.source_key = ? AND lower(n.name) = lower(?)
                """,
                (child_source_key, child_path),
            ).fetchone()
            if not crow:
                continue
            parent_id = pid
            attach_id = int(crow[0])
            break
        if parent_id is None:
            continue
        pair = (parent_id, attach_id)
        if pair in seen:
            continue
        seen.add(pair)
        inserted += _insert_same_group(
            conn,
            parent_id,
            attach_id,
            crosswalk_id,
            priority,
            f"{crosswalk_id}:{child_name}",
        )
    return inserted


def link_grants_under_pbs(conn: sqlite3.Connection) -> int:
    """Hang GrantConnect grant-program nodes under matched PBS / S6 parents."""
    return link_path_children_under_cascade(
        conn,
        child_source_key="federal_grantconnect_awards",
        crosswalk_id="grantconnect_under_pbs",
        priority=60,
    )


def link_dss_under_pbs(conn: sqlite3.Connection) -> int:
    """Hang DSS recipient demographics under Social protection PBS parents."""
    return link_path_children_under_cascade(
        conn,
        child_source_key="federal_dss_payment_demographics",
        crosswalk_id="dss_demo_under_pbs",
        parent_sources=(
            "federal_dss_pbs_programs",
            "federal_budget_statement_6_components",
        ),
        priority=58,
    )


def _insert_related_breakdown(
    conn: sqlite3.Connection,
    parent_id: int,
    child_id: int,
    crosswalk_id: str,
    priority: int,
    notes: str,
) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO breakdown_edges (
            parent_node_id, child_node_id, edge_kind, crosswalk_id,
            financial_year, priority, source_document_id, notes
        ) VALUES (?, ?, 'related_breakdown', ?, NULL, ?, NULL, ?)
        """,
        (parent_id, child_id, crosswalk_id, priority, notes),
    )
    return int(conn.execute("SELECT changes()").fetchone()[0])


NDIS_CANONICAL_PARENT_NAME = (
    "Social security and welfare / Assistance to people with disabilities / "
    "National Disability Insurance Scheme"
)
NDIS_CANONICAL_PARENT_SOURCE = "federal_budget_statement_6_components"

# (source_key, root node name, crosswalk_id). Root names are deliberately
# distinct per measure (not just distinct source_keys) - build_related_
# subtree() (breakdown_graph.py), when called without an edge_set_ids
# filter as dashboard_item_children() does, keys its result dict by child
# node NAME, so two measures sharing one root name would silently
# overwrite each other in that combined view (found live; see the
# extractor's ROOT_NODE comment and federal-deep-data-mission-*.md, Loop 8).
NDIS_STATS_ROOTS = (
    (
        "federal_ndis_participant_count",
        "NDIA Participant Statistics",
        "ndis_participants_under_statement6",
    ),
    (
        "federal_ndis_average_committed_plan_budget",
        "NDIA Average Committed Plan Budget",
        "ndis_average_budget_under_statement6",
    ),
)


def link_ndis_participant_statistics(conn: sqlite3.Connection) -> int:
    """One related_breakdown edge per NDIS statistics measure, from the
    canonical Statement 6 NDIS expenditure node to each measure's own
    source-native root node. Deliberately two separate edges/branch
    families (never merged): participant counts and average committed
    plan budget are distinct measures the source itself never sums into
    one another - see migrations/028_ndis_participant_plan_budgets_
    measures.sql. Uses related_breakdown (not same_group) since there is
    no existing consumer relying on same_group chain continuity through
    this brand-new attach point (unlike the pbs_dss_bridge/a61_to_
    components case investigated and reverted in Loop 7 of the Federal
    deep-data mission)."""
    parent = conn.execute(
        """
        SELECT n.id FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = ? AND n.name = ?
        """,
        (NDIS_CANONICAL_PARENT_SOURCE, NDIS_CANONICAL_PARENT_NAME),
    ).fetchone()
    if not parent:
        return 0
    parent_id = int(parent[0])

    inserted = 0
    for source_key, root_name, crosswalk_id in NDIS_STATS_ROOTS:
        root = conn.execute(
            """
            SELECT n.id FROM nodes n
            JOIN source_documents d ON d.id = n.source_document_id
            WHERE d.source_key = ? AND n.name = ?
            """,
            (source_key, root_name),
        ).fetchone()
        if not root:
            continue
        inserted += _insert_related_breakdown(
            conn,
            parent_id,
            int(root[0]),
            crosswalk_id,
            100,
            f"ndis:{source_key}:{root_name}",
        )
    return inserted


def link_austender_under_s6(conn: sqlite3.Connection) -> int:
    """Hang AusTender contract aggregates under Defence / Health / Transport A.6.1."""
    return link_path_children_under_cascade(
        conn,
        child_source_key="federal_austender_contracts",
        crosswalk_id="austender_under_s6",
        # Prefer A.6.1 / components only — s6_bridge also has a bare "Defence"
        # node that would steal the name index.
        parent_sources=(
            "federal_budget_statement_6_a61",
            "federal_budget_statement_6_components",
        ),
        priority=50,
    )


def link_ordered_cascade(conn: sqlite3.Connection) -> dict[str, int]:
    """Emit a61→components and components/a61→PBS same_group edges."""
    result = {
        "a61_to_components": link_a61_to_components(conn),
        "pbs_links": link_pbs_to_components(conn),
    }
    # Drop a61→PBS edges when the same PBS child already hangs under a component.
    conn.execute(
        """
        DELETE FROM breakdown_edges
        WHERE id IN (
            SELECT e.id
            FROM breakdown_edges e
            JOIN nodes pn ON pn.id = e.parent_node_id
            JOIN source_documents pd ON pd.id = pn.source_document_id
            JOIN nodes ch ON ch.id = e.child_node_id
            JOIN source_documents chd ON chd.id = ch.source_document_id
            WHERE e.edge_kind = 'same_group'
              AND pd.source_key = 'federal_budget_statement_6_a61'
              AND chd.source_key IN (
                  'federal_dss_pbs_programs',
                  'federal_health_pbs_programs',
                  'federal_pbs_programs_s6_bridge'
              )
              AND EXISTS (
                SELECT 1
                FROM breakdown_edges e2
                JOIN nodes cn ON cn.id = e2.parent_node_id
                JOIN source_documents cd ON cd.id = cn.source_document_id
                WHERE e2.child_node_id = e.child_node_id
                  AND e2.edge_kind = 'same_group'
                  AND cd.source_key = 'federal_budget_statement_6_components'
              )
        )
        """
    )
    result["pruned_a61_pbs_dupes"] = int(conn.execute("SELECT changes()").fetchone()[0])
    return result


def run_pack(pack_id: str, db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    pack_path = PACKS_DIR / f"{pack_id}.yaml"
    if not pack_path.is_file():
        # allow abs pack without extractor
        if pack_id == "abs_gfs_table4":
            migrate(db_path)
            return {"pack": pack_id, "status": "config_only"}
        raise FileNotFoundError(pack_path)
    pack = load_yaml(pack_path)
    migrate(db_path)
    summary: dict[str, Any] = {"pack": pack_id}

    if pack.get("extractor"):
        summary["extract"] = run_extractor(pack["extractor"])

    mapping_rel = pack.get("mapping")
    if mapping_rel:
        mapping_path = REPO_ROOT / mapping_rel
        summary["publish"] = run_mapping(mapping_path, db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        source_key = pack.get("source_key")
        if source_key and pack.get("edge_kind") == "same_group":
            mapping_meta = load_yaml(REPO_ROOT / mapping_rel) if mapping_rel else {}
            summary["same_group_edges"] = link_same_group_from_paths(
                conn, source_key, mapping_meta
            )
        if pack.get("related_crosswalk_id") and source_key:
            summary["related_edges"] = link_related_crosswalk(
                conn, pack["related_crosswalk_id"], source_key
            )
        if pack_id in (
            "bp1_s6_components",
            "pbs_programs_dss",
            "pbs_programs_health",
            "pbs_programs_s6_bridge",
        ):
            summary["cascade_edges"] = link_ordered_cascade(conn)
        if pack_id == "grantconnect_awards":
            summary["grant_links"] = link_grants_under_pbs(conn)
        if pack_id == "dss_payment_demographics":
            summary["dss_links"] = link_dss_under_pbs(conn)
        if pack_id == "austender_contracts":
            summary["austender_links"] = link_austender_under_s6(conn)
        conn.commit()
    finally:
        conn.close()
    return summary


ALL_PACKS = [
    "abs_gfs_table4",
    "bp1_s6_a61",
    "bp1_s6_components",
    "pbs_programs_dss",
    "pbs_programs_health",
    "pbs_programs_s6_bridge",
    "federal_fbo_function_subfunction",
    "grantconnect_awards",
    "dss_payment_demographics",
    "austender_contracts",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run breakdown pack")
    parser.add_argument("--pack", help="Pack id under config/breakdowns/")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run abs + a61 + components + PBS packs in order",
    )
    args = parser.parse_args(argv)
    if args.all:
        results = []
        for pid in ALL_PACKS:
            pack_file = PACKS_DIR / f"{pid}.yaml"
            if pid != "abs_gfs_table4" and not pack_file.is_file():
                results.append({"pack": pid, "status": "skipped_missing_config"})
                continue
            results.append(run_pack(pid, args.db))
        print(results)
        return 0
    if not args.pack:
        parser.error("--pack is required unless --all is set")
    print(run_pack(args.pack, args.db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
