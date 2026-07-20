"""Shared types/helpers for source parsers."""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SpendingRow:
    financial_year: str  # e.g. "2024-25"
    level_of_government: str  # federal | state | local
    jurisdiction: str  # e.g. "Commonwealth", "SA", "VIC — Banyule City Council"
    category: str
    amount_aud: float
    subcategory: Optional[str] = None
    department: Optional[str] = None
    source_document_name: str = ""
    source_url: str = ""
    retrieved_at: str = ""
    source_context: dict[str, Any] = field(default_factory=dict)
