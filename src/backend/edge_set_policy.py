"""Declarative projection/fallback policy for ``breakdown_edges`` sets."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_HERE = Path(__file__).resolve().parent
_ALLOWED_EDGE_KINDS = {"same_group", "related_breakdown"}
_ALLOWED_PROJECTIONS = {"augment", "authoritative"}
_ALLOWED_FALLBACKS = {"exact_only", "nearest_earlier", "none"}
_ALLOWED_ROLES = {"data", "navigation"}
_ALLOWED_BRANCH_KINDS = {"additive", "related"}


def _default_path() -> Path:
    candidates = [
        Path("/app/config/breakdowns/edge_sets.yaml"),
        _HERE.parents[1] / "config" / "breakdowns" / "edge_sets.yaml",
        _HERE.parent / "config" / "breakdowns" / "edge_sets.yaml",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


@dataclass(frozen=True)
class EdgeSetPolicy:
    id: str
    crosswalk_id: str | None
    branch_family: str | None
    edge_kind: str
    branch_kind: str
    projection_policy: str
    fallback_policy: str
    presentation_role: str
    folder_label: str | None
    source_key_allowlist: tuple[str, ...]
    source_key_prefixes: tuple[str, ...]
    sort_order: int
    completeness_manifest: str | None = None

    def matches(self, crosswalk_id: str | None, edge_kind: str, source_key: str | None) -> bool:
        if self.crosswalk_id != crosswalk_id or self.edge_kind != edge_kind:
            return False
        source = source_key or ""
        if self.source_key_allowlist and source not in self.source_key_allowlist:
            return False
        if self.source_key_prefixes and not any(
            source.startswith(prefix) for prefix in self.source_key_prefixes
        ):
            return False
        return True


@dataclass(frozen=True)
class EdgeSetRegistry:
    policies: tuple[EdgeSetPolicy, ...]
    defaults: dict[str, Any]

    def policy_by_id(self, edge_set_id: str) -> EdgeSetPolicy:
        for policy in self.policies:
            if policy.id == edge_set_id:
                return policy
        raise KeyError(edge_set_id)

    def resolve(
        self,
        *,
        crosswalk_id: str | None,
        edge_kind: str,
        source_key: str | None,
    ) -> EdgeSetPolicy:
        matches = [
            policy
            for policy in self.policies
            if policy.matches(crosswalk_id, edge_kind, source_key)
        ]
        if len(matches) > 1:
            raise ValueError(
                "ambiguous edge-set policy for "
                f"crosswalk_id={crosswalk_id!r} edge_kind={edge_kind!r} "
                f"source_key={source_key!r}: {[policy.id for policy in matches]}"
            )
        if matches:
            return matches[0]
        return EdgeSetPolicy(
            id=(crosswalk_id or f"source_native_{edge_kind}"),
            crosswalk_id=crosswalk_id,
            branch_family=None,
            edge_kind=edge_kind,
            branch_kind="additive" if edge_kind == "same_group" else "related",
            projection_policy=str(self.defaults.get("projection_policy", "augment")),
            fallback_policy=str(self.defaults.get("fallback_policy", "exact_only")),
            presentation_role=str(self.defaults.get("presentation_role", "data")),
            folder_label=None,
            source_key_allowlist=(),
            source_key_prefixes=(),
            sort_order=int(self.defaults.get("sort_order", 100)),
        )


def _policy(raw: dict[str, Any], defaults: dict[str, Any]) -> EdgeSetPolicy:
    policy = EdgeSetPolicy(
        id=str(raw["id"]),
        crosswalk_id=raw.get("crosswalk_id"),
        branch_family=raw.get("branch_family"),
        edge_kind=str(raw["edge_kind"]),
        branch_kind=str(
            raw.get(
                "branch_kind",
                "additive" if raw["edge_kind"] == "same_group" else "related",
            )
        ),
        projection_policy=str(
            raw.get("projection_policy", defaults.get("projection_policy", "augment"))
        ),
        fallback_policy=str(
            raw.get("fallback_policy", defaults.get("fallback_policy", "exact_only"))
        ),
        presentation_role=str(
            raw.get("presentation_role", defaults.get("presentation_role", "data"))
        ),
        folder_label=raw.get("folder_label"),
        source_key_allowlist=tuple(raw.get("source_key_allowlist") or ()),
        source_key_prefixes=tuple(raw.get("source_key_prefixes") or ()),
        sort_order=int(raw.get("sort_order", defaults.get("sort_order", 100))),
        completeness_manifest=raw.get("completeness_manifest"),
    )
    if policy.edge_kind not in _ALLOWED_EDGE_KINDS:
        raise ValueError(f"edge set {policy.id}: invalid edge_kind={policy.edge_kind!r}")
    if policy.branch_kind not in _ALLOWED_BRANCH_KINDS:
        raise ValueError(
            f"edge set {policy.id}: invalid branch_kind={policy.branch_kind!r}"
        )
    if policy.projection_policy not in _ALLOWED_PROJECTIONS:
        raise ValueError(
            f"edge set {policy.id}: invalid projection_policy={policy.projection_policy!r}"
        )
    if policy.fallback_policy not in _ALLOWED_FALLBACKS:
        raise ValueError(
            f"edge set {policy.id}: invalid fallback_policy={policy.fallback_policy!r}"
        )
    if policy.presentation_role not in _ALLOWED_ROLES:
        raise ValueError(
            f"edge set {policy.id}: invalid presentation_role={policy.presentation_role!r}"
        )
    if policy.projection_policy == "authoritative" and not policy.completeness_manifest:
        raise ValueError(
            f"edge set {policy.id}: authoritative policy requires completeness_manifest"
        )
    return policy


@lru_cache(maxsize=4)
def load_edge_set_registry(path: str | None = None) -> EdgeSetRegistry:
    config_path = Path(path) if path else _default_path()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if int(data.get("version", 0)) != 1:
        raise ValueError(f"unsupported edge_sets version in {config_path}")
    defaults = dict(data.get("defaults") or {})
    if str(defaults.get("projection_policy", "augment")) not in _ALLOWED_PROJECTIONS:
        raise ValueError("invalid default projection_policy")
    if str(defaults.get("fallback_policy", "exact_only")) not in _ALLOWED_FALLBACKS:
        raise ValueError("invalid default fallback_policy")
    if str(defaults.get("presentation_role", "data")) not in _ALLOWED_ROLES:
        raise ValueError("invalid default presentation_role")
    policies = tuple(_policy(dict(raw), defaults) for raw in data.get("edge_sets") or [])
    ids = [policy.id for policy in policies]
    if len(ids) != len(set(ids)):
        raise ValueError("edge set IDs must be unique")

    # Detect overlapping rules eagerly with representative allowlist/prefix values.
    for index, left in enumerate(policies):
        for right in policies[index + 1 :]:
            if left.crosswalk_id != right.crosswalk_id or left.edge_kind != right.edge_kind:
                continue
            samples = set(left.source_key_allowlist) | set(right.source_key_allowlist)
            samples |= set(left.source_key_prefixes) | set(right.source_key_prefixes)
            if not samples:
                raise ValueError(f"ambiguous unscoped edge sets: {left.id}, {right.id}")
            if any(
                left.matches(left.crosswalk_id, left.edge_kind, sample)
                and right.matches(right.crosswalk_id, right.edge_kind, sample)
                for sample in samples
            ):
                raise ValueError(f"overlapping edge sets: {left.id}, {right.id}")
    return EdgeSetRegistry(policies=policies, defaults=defaults)
