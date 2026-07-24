from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class BreakdownMeta(BaseModel):
    """Provenance for related_breakdown children (not additive with parent)."""

    kind: Literal["same_group", "related_breakdown"]
    source_key: Optional[str] = None
    compatibility_group: Optional[str] = None
    match_quality: Optional[str] = None
    banner: Optional[str] = None
    fact_financial_year: Optional[str] = None


class TreeNode(BaseModel):
    name: str
    value: float
    id: Optional[int] = None  # present on leaves; also on related parents for citation
    children: Optional[list["TreeNode"]] = None
    breakdown: Optional[BreakdownMeta] = None


TreeNode.model_rebuild()


class SpendingItem(BaseModel):
    id: int
    financial_year: str
    level_of_government: str
    jurisdiction: str
    category: str
    subcategory: Optional[str]
    department: Optional[str]
    amount_aud: float
    source_document_name: str
    source_url: str
    retrieved_at: str


class SourceHighlight(BaseModel):
    row_index: int
    column_index: int
    cell: str


class SourceContext(BaseModel):
    source_type: Literal["spreadsheet", "pdf", "unsupported"]
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    highlight: Optional[SourceHighlight] = None
    unit: Optional[str] = None
    note: Optional[str] = None
    # PDF documents must be captured and hosted by this backend (or another
    # same-app endpoint) before they can be embedded. Never point this at the
    # live government source URL.
    viewer_url: Optional[str] = None
    page_number: Optional[int] = None
    text_anchor: Optional[str] = None
