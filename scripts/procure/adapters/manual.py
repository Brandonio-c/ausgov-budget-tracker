"""Manual and interactive portal classification."""

from __future__ import annotations

from ..models import Asset, Source
from .base import AdapterContext, BaseAdapter


class ManualAdapter(BaseAdapter):
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]:
        return [], {
            "official_url": source.landing_url,
            "attempted": ["registry-classified manual/web portal; public static discovery handled before final classification"],
            "reason": source.manual.get("notes") or source.research.get("parser_strategy") or "interactive/manual source",
            "candidates": [],
            "rejected": [],
        }
