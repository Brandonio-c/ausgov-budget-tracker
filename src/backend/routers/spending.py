import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..db import get_connection
from ..schemas import SourceContext, SpendingItem, TreeNode
from ..source_files import resolve_source_file

router = APIRouter(prefix="/api/spending", tags=["spending"])


@router.get("/levels")
def list_levels() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT level_of_government, COUNT(*) AS n FROM spending GROUP BY level_of_government ORDER BY level_of_government"
    ).fetchall()
    conn.close()
    return [{"level": r["level_of_government"], "row_count": r["n"]} for r in rows]


@router.get("/years")
def list_years(level: str | None = Query(default=None)) -> list[str]:
    conn = get_connection()
    if level:
        rows = conn.execute(
            "SELECT DISTINCT financial_year FROM spending WHERE level_of_government = ? ORDER BY financial_year",
            (level,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT DISTINCT financial_year FROM spending ORDER BY financial_year").fetchall()
    conn.close()
    return [r["financial_year"] for r in rows]


@router.get("/tree", response_model=TreeNode)
def spending_tree(level: str = Query(...), year: str = Query(...)) -> TreeNode:
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, jurisdiction, category, subcategory, amount_aud
           FROM spending WHERE level_of_government = ? AND financial_year = ?""",
        (level, year),
    ).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for level={level!r} year={year!r}")

    # jurisdiction -> category -> subcategory(optional) -> row
    tree: dict = {}
    for r in rows:
        jurisdiction = r["jurisdiction"] or "Uncategorized"
        category = r["category"] or "Uncategorized"
        node = tree.setdefault(jurisdiction, {}).setdefault(category, {})
        if r["subcategory"]:
            node[r["subcategory"]] = {"__leaf__": (r["id"], r["amount_aud"])}
        else:
            node["__leaf__"] = (r["id"], r["amount_aud"])

    def build(name: str, subtree: dict) -> TreeNode:
        if "__leaf__" in subtree and len(subtree) == 1:
            row_id, amount = subtree["__leaf__"]
            return TreeNode(name=name, value=amount, id=row_id)

        leaf = subtree.pop("__leaf__", None)
        children = [build(child_name, child) for child_name, child in subtree.items()]
        if leaf is not None:
            row_id, amount = leaf
            children.append(TreeNode(name="(unclassified)", value=amount, id=row_id))
        total = sum(c.value for c in children)
        return TreeNode(name=name, value=total, children=children)

    top_children = [build(name, subtree) for name, subtree in tree.items()]
    total = sum(c.value for c in top_children)
    return TreeNode(name=f"{level} — {year}", value=total, children=top_children)


@router.get("/item/{item_id}", response_model=SpendingItem)
def spending_item(item_id: int) -> SpendingItem:
    conn = get_connection()
    row = conn.execute("SELECT * FROM spending WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No spending item with id={item_id}")
    return SpendingItem(**dict(row))


@router.get("/item/{item_id}/context", response_model=SourceContext)
def spending_item_context(item_id: int) -> SourceContext:
    conn = get_connection()
    row = conn.execute(
        "SELECT source_context_json FROM spending WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No spending item with id={item_id}")

    try:
        return SourceContext(**json.loads(row["source_context_json"]))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Stored source context is invalid") from exc


@router.get("/item/{item_id}/source-file", response_class=FileResponse)
def spending_item_source_file(item_id: int) -> FileResponse:
    conn = get_connection()
    row = conn.execute(
        "SELECT level_of_government, source_url FROM spending WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No spending item with id={item_id}")

    source_file = resolve_source_file(row["level_of_government"], row["source_url"])
    if source_file is None:
        raise HTTPException(status_code=404, detail="Cached source file is unavailable")

    return FileResponse(
        path=source_file.path,
        media_type=source_file.content_type,
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Disposition": f'inline; filename="{source_file.path.name}"',
            "X-Source-Id": source_file.source_id,
        },
    )
