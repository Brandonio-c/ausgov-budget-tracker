"""GDP / GSP hierarchy helpers for dashboard tree paths."""

from __future__ import annotations

import re


def is_gdp_hierarchy_label(name: str) -> bool:
    n = (name or "").strip().lower()
    return bool(
        re.search(
            r"\bgdp\b|\bgsp\b|gross state product|expenditure on gdp|gross value added|gva\b|"
            r"taxation revenue as % of gdp|final consumption|gross fixed capital",
            n,
        )
    )


def gdp_hierarchy_path(category: str) -> list[str] | None:
    """Nest GDP children under published totals when labels allow."""
    name = (category or "").strip()
    if not name:
        return None
    if re.search(r"^total\b", name, re.I):
        return None
    if " / " in name:
        parts = [p.strip() for p in name.split(" / ") if p.strip()]
        # e.g. Expenditure on GDP / Final consumption → under GDP total
        if parts and parts[0].lower().startswith("expenditure on gdp"):
            return ["GDP (current prices)", *parts]
        if len(parts) >= 2 and re.search(r"\bgsp\b|gross state product", parts[-1], re.I):
            return ["GSP (current prices)", *parts]
        return parts
    if re.search(r"gdp current|gross domestic product.*current", name, re.I):
        return ["GDP (current prices)", name]
    if re.search(r"chain.?volume|real gdp", name, re.I):
        return ["GDP (chain volume)", name]
    if re.search(r"\bgsp\b|gross state product", name, re.I):
        return ["GSP (current prices)", name]
    if re.search(r"tax.*gdp|% of gdp", name, re.I):
        return ["Derived ratios", name]
    if is_gdp_hierarchy_label(name):
        return ["GDP components", name]
    return [name]
