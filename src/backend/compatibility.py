"""Semantic compatibility decisions for dashboard aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

_HERE = Path(__file__).resolve().parent


def _default_view_families_path() -> Path:
    """Resolve config in repo checkout or Docker (/app/config bind-mount)."""
    candidates: list[Path] = [
        Path("/app/config/compatibility/view_families.yaml"),
    ]
    # Repo checkout: …/ausgov-budget-tracker/src/backend → …/config/...
    if len(_HERE.parents) >= 3:
        candidates.append(
            _HERE.parents[2] / "config" / "compatibility" / "view_families.yaml"
        )
    if len(_HERE.parents) >= 2:
        candidates.append(
            _HERE.parents[1] / "config" / "compatibility" / "view_families.yaml"
        )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


@dataclass
class CompatibilityDecision:
    allowed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    view_family: str | None = None
    selected_measure_types: list[str] = field(default_factory=list)
    units: list[str] = field(default_factory=list)
    price_bases: list[str] = field(default_factory=list)
    valuation_bases: list[str] = field(default_factory=list)
    observation_dates: list[str] = field(default_factory=list)
    root_total_allowed: bool = True
    additive_across_nodes: bool = True
    mixed_valuation_bases: bool = False
    mixed_observation_dates: bool = False


@lru_cache(maxsize=4)
def load_view_families(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else _default_view_families_path()
    if not p.is_file():
        raise FileNotFoundError(
            f"view_families.yaml not found (tried {[str(_default_view_families_path())]}); "
            f"path={p}"
        )
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data


def mode_to_view_family(mode: str, spec: Mapping[str, Any] | None = None) -> str:
    data = spec or load_view_families()
    mapping = data.get("mode_to_family") or {}
    if mode not in mapping:
        raise KeyError(f"Unknown dashboard mode/view: {mode!r}")
    return str(mapping[mode])


def family_spec(family_id: str, spec: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = spec or load_view_families()
    families = data.get("families") or {}
    if family_id not in families:
        raise KeyError(f"Unknown view_family: {family_id!r}")
    return dict(families[family_id])


def display_value(row: Mapping[str, Any]) -> float | None:
    """Prefer amount_value; fall back to amount_aud for pre-migration rows."""
    if row.get("amount_value") is not None:
        return float(row["amount_value"])
    if row.get("amount_aud") is not None:
        return float(row["amount_aud"])
    return None


def _uniq(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        if v is None or v == "":
            continue
        s = str(v)
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def validate_fact_set(
    rows: Sequence[Mapping[str, Any]],
    *,
    view_family: str,
    valuation_filter: str | None = None,
    spec: Mapping[str, Any] | None = None,
) -> CompatibilityDecision:
    """
    Validate that rows may be shown together under view_family.

    Rejects mixing units (e.g. percent + AUD), price bases, or measure types
    outside the family allowlist. Debt mixed valuation bases warn / disable
    root total unless a single basis filter is applied.
    """
    fam = family_spec(view_family, spec)
    decision = CompatibilityDecision(
        allowed=True,
        view_family=view_family,
        root_total_allowed=bool(fam.get("root_total_allowed", True)),
        additive_across_nodes=bool(fam.get("additive_across_nodes", True)),
    )
    if not rows:
        decision.warnings.append("No facts matched the query filters.")
        return decision

    measures = _uniq(r.get("measure_type") for r in rows)
    units = _uniq(r.get("unit") or "AUD" for r in rows)
    # Treat NULL currency unit quirks: percent rows should have unit=percent
    price_bases = _uniq(
        (r.get("price_basis") or "unspecified") for r in rows
    )
    valuation_bases = _uniq(
        (r.get("valuation_basis") or "unspecified") for r in rows
    )
    obs_dates = _uniq(r.get("observation_date") for r in rows)

    decision.selected_measure_types = measures
    decision.units = units
    decision.price_bases = price_bases
    decision.valuation_bases = valuation_bases
    decision.observation_dates = obs_dates
    decision.mixed_valuation_bases = len(valuation_bases) > 1
    decision.mixed_observation_dates = len(obs_dates) > 1

    allowed_units = fam.get("compatible_units")
    if allowed_units:
        bad_u = [u for u in units if u not in allowed_units]
        if bad_u:
            decision.allowed = False
            decision.errors.append(
                f"Incompatible unit(s) {bad_u} for view_family={view_family}; "
                f"allowed={list(allowed_units)}"
            )

    if len(units) > 1:
        decision.allowed = False
        decision.errors.append(
            f"Cannot combine multiple units in one tree: {units}"
        )

    if "percent" in units and any(u == "AUD" for u in units):
        decision.allowed = False
        decision.errors.append("Cannot mix percent and AUD in one additive tree")

    allowed_pb = fam.get("compatible_price_bases")
    if allowed_pb:
        # unspecified often OK for legacy expense; still block current vs chain
        concrete = [p for p in price_bases if p not in ("unspecified", "not_applicable")]
        if len(set(concrete)) > 1:
            decision.allowed = False
            decision.errors.append(
                f"Cannot mix price bases {concrete} under {view_family}"
            )
        bad_pb = [p for p in concrete if p not in allowed_pb]
        if bad_pb:
            decision.allowed = False
            decision.errors.append(
                f"Price basis {bad_pb} not allowed for {view_family}"
            )

    allowed_mt = fam.get("compatible_measure_types")
    if allowed_mt:
        bad_m = [m for m in measures if m not in allowed_mt]
        if bad_m:
            decision.allowed = False
            decision.errors.append(
                f"Measure type(s) {bad_m} not allowed in view_family={view_family}"
            )

    # Legacy GDP bucket: if somehow still queried as mixed group without family filter
    if view_family == "gdp_current" and "gdp_chain_volume" in measures:
        decision.allowed = False
        decision.errors.append("gdp_current cannot include gdp_chain_volume facts")
    if view_family == "gdp_chain_volume" and "gdp_current" in measures:
        decision.allowed = False
        decision.errors.append("gdp_chain_volume cannot include gdp_current facts")
    if "tax_to_gdp_ratio" in measures and view_family != "ratios":
        decision.allowed = False
        decision.errors.append(
            "tax_to_gdp_ratio belongs only in view_family=ratios"
        )

    if fam.get("single_valuation_basis_for_total") and decision.mixed_valuation_bases:
        if valuation_filter and valuation_filter not in ("all", "comparison"):
            # filtered to one basis — OK
            pass
        elif valuation_filter in ("all", "comparison", None) and decision.mixed_valuation_bases:
            decision.root_total_allowed = False
            decision.additive_across_nodes = False
            decision.warnings.append(
                "Mixed valuation bases (face/fair/…) — comparison only; "
                "unqualified total disabled."
            )

    if not fam.get("can_mix_observation_dates", True) and decision.mixed_observation_dates:
        decision.root_total_allowed = False
        decision.warnings.append(
            "Mixed observation dates — do not treat as a single as-at stock."
        )

    if not fam.get("additive_across_nodes", True):
        decision.root_total_allowed = False
        decision.additive_across_nodes = False

    if not decision.root_total_allowed and not decision.errors:
        decision.warnings.append(
            f"Root total not allowed for view_family={view_family}"
        )

    return decision


def assert_compatible_or_raise(
    decision: CompatibilityDecision,
) -> CompatibilityDecision:
    """Raise ValueError with structured message for API 422 mapping."""
    if not decision.allowed:
        raise ValueError("; ".join(decision.errors) or "Incompatible fact set")
    return decision
