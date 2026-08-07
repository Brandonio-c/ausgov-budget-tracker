from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class BreakdownMeta(BaseModel):
    """Provenance for related_breakdown children (not additive with parent)."""

    kind: Literal["same_group", "related_breakdown"]
    source_key: Optional[str] = None
    compatibility_group: Optional[str] = None
    match_quality: Optional[str] = None
    banner: Optional[str] = None
    # source_financial_year in mission terms - the actual year this node's
    # fact was published for, populated whenever it differs from the
    # requested year (None means "matches the requested year exactly").
    fact_financial_year: Optional[str] = None
    # Task 7 (semantic-defect milestone): explicit, per-node year-fallback
    # disclosure - never rely on a folder-level banner alone to convey a
    # child's actual year.
    requested_financial_year: Optional[str] = None
    is_year_fallback: Optional[bool] = None
    fallback_reason: Optional[str] = None
    source_budget_edition: Optional[str] = None
    estimate_status: Optional[str] = None


class RelationshipMeta(BaseModel):
    """Explicit projection semantics for every non-root dashboard node.

    ``breakdown`` remains as a deprecated compatibility alias while clients
    migrate.  Unlike that alias, edge kind and inherited branch semantics are
    separate: a same-group edge nested beneath a related attach point remains
    ``edge_kind=same_group`` but ``branch_kind=related``.
    """

    edge_kind: Literal["root", "same_group", "related_breakdown"]
    branch_kind: Literal["additive", "related"]
    presentation_role: Literal["data", "navigation"]
    edge_set_id: Optional[str] = None
    branch_family: Optional[str] = None
    source_key: Optional[str] = None
    source_family: Optional[str] = None
    compatibility_group: Optional[str] = None
    accounting_basis: Optional[str] = None
    estimate_status: Optional[str] = None
    requested_financial_year: Optional[str] = None
    fact_financial_year: Optional[str] = None
    is_year_fallback: bool = False
    fallback_reason: Optional[str] = None
    match_quality: Optional[str] = None
    unit: Optional[str] = None


class ProjectionBranchSummary(BaseModel):
    branch_family: Optional[str] = None
    branch_kind: Literal["additive", "related"]
    node_count: int
    max_depth: int


class ProjectionMeta(BaseModel):
    requested_mode: str
    requested_level: str
    requested_financial_year: str
    selected_accounting_basis: Optional[str] = None
    max_visible_depth: int
    max_additive_depth: int
    contains_related_branches: bool
    branch_summaries: list[ProjectionBranchSummary] = Field(default_factory=list)


class TreeNode(BaseModel):
    name: str
    value: float
    id: Optional[int] = None  # present on leaves; also on related parents for citation
    children: Optional[list["TreeNode"]] = None
    breakdown: Optional[BreakdownMeta] = None
    relationship: Optional[RelationshipMeta] = None
    projection: Optional[ProjectionMeta] = None
    # Dashboard warnings / debt semantics (optional; set on roots or debt leaves)
    mixed_observation_dates: Optional[bool] = None
    observation_dates: Optional[list[str]] = None
    valuation_basis: Optional[str] = None
    valuation_bases: Optional[list[str]] = None
    mixed_valuation_bases: Optional[bool] = None
    amount_granularity: Optional[str] = None
    warning: Optional[str] = None
    is_aggregate: Optional[bool] = None
    unit: Optional[str] = None
    view_family: Optional[str] = None
    root_total_allowed: Optional[bool] = None


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
