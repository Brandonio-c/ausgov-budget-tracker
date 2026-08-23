import type { RelationshipMeta, TreeNode } from "./types";

// Validated categorical palette (dataviz skill reference palette, unmodified —
// fixed hue order, validated with scripts/validate_palette.js for both modes).
export const CATEGORICAL_LIGHT = [
  "#2a78d6", // blue
  "#008300", // green
  "#e87ba4", // magenta
  "#eda100", // yellow
  "#1baf7a", // aqua
  "#eb6834", // orange
  "#4a3aa7", // violet
];

export const CATEGORICAL_DARK = [
  "#3987e5",
  "#008300",
  "#d55181",
  "#c98500",
  "#199e70",
  "#d95926",
  "#9085e9",
];

export const MUTED = "#898781"; // "Other" bucket — neutral, never a real category hue

const TOP_N = 7;

function semanticFoldKey(node: TreeNode): string {
  const relationship = node.relationship;
  return JSON.stringify({
    edgeKind:
      relationship?.edge_kind ??
      (node.breakdown?.kind === "related_breakdown"
        ? "related_breakdown"
        : "same_group"),
    branchKind: relationship?.branch_kind ?? "additive",
    presentationRole: relationship?.presentation_role ?? "data",
    unit: relationship?.unit ?? node.unit ?? "AUD",
    factYear:
      relationship?.fact_financial_year ?? node.breakdown?.fact_financial_year ?? null,
    compatibilityGroup:
      relationship?.compatibility_group ?? node.breakdown?.compatibility_group ?? null,
    accountingBasis: relationship?.accounting_basis ?? null,
  });
}

function commonValue<T>(values: T[]): T | null {
  return values.every((value) => value === values[0]) ? values[0] : null;
}

function aggregateRelationship(nodes: TreeNode[]): RelationshipMeta | null {
  const relationships = nodes.map((node): RelationshipMeta => {
    if (node.relationship) return node.relationship;
    const related = node.breakdown?.kind === "related_breakdown";
    return {
      edge_kind: related ? "related_breakdown" : "same_group",
      branch_kind: related ? "related" : "additive",
      presentation_role: "data",
      source_key: node.breakdown?.source_key,
      compatibility_group: node.breakdown?.compatibility_group,
      fact_financial_year: node.breakdown?.fact_financial_year,
      is_year_fallback: Boolean(node.breakdown?.is_year_fallback),
      fallback_reason: node.breakdown?.fallback_reason,
      match_quality: node.breakdown?.match_quality,
      unit: node.unit,
    };
  });
  if (relationships.length === 0) return null;
  const first = relationships[0];
  return {
    ...first,
    edge_set_id: commonValue(relationships.map((item) => item.edge_set_id)),
    branch_family: commonValue(relationships.map((item) => item.branch_family)),
    source_key: commonValue(relationships.map((item) => item.source_key)),
    source_family: commonValue(relationships.map((item) => item.source_family)),
    accounting_basis: commonValue(relationships.map((item) => item.accounting_basis)),
    estimate_status: commonValue(relationships.map((item) => item.estimate_status)),
    fallback_reason: commonValue(relationships.map((item) => item.fallback_reason)),
    match_quality: commonValue(relationships.map((item) => item.match_quality)),
    is_year_fallback: relationships.some((item) => item.is_year_fallback),
  };
}

/** Sort children by value desc and fold the tail without crossing semantic
 * boundaries. Each synthetic node is a drillable aggregate of one branch
 * kind/unit/source-year/compatibility group only. */
export function foldToTopN(children: TreeNode[], n = TOP_N): TreeNode[] {
  const sorted = [...children].sort((a, b) => b.value - a.value);
  if (sorted.length <= n + 1) return sorted;
  const head = sorted.slice(0, n);
  const tail = sorted.slice(n);
  const groups = new Map<string, TreeNode[]>();
  for (const node of tail) {
    const key = semanticFoldKey(node);
    groups.set(key, [...(groups.get(key) ?? []), node]);
  }
  const multipleSemanticGroups = groups.size > 1;
  const others = [...groups.values()].map((nodes) => {
    if (nodes.length === 1) return nodes[0];
    const first = nodes[0];
    const relationship = aggregateRelationship(nodes);
    const unit = relationship?.unit ?? first.unit ?? null;
    const qualifier = multipleSemanticGroups
      ? ` — ${relationship?.branch_kind ?? "additive"}, ${unit ?? "AUD"}`
      : "";
    const other: TreeNode = {
      name: `Other${qualifier} (${nodes.length})`,
      value: nodes.reduce((sum, node) => sum + node.value, 0),
      id: null,
      children: nodes,
      relationship,
      breakdown: first.breakdown ?? null,
      unit,
    };
    return other;
  });
  return [...head, ...others].sort((a, b) => b.value - a.value);
}

/**
 * Deterministic palette index from a name — stable across renders, sort
 * orders, and files, unlike an array-position index (`i % length`), which
 * silently reassigns every function's color whenever value-based sort order
 * changes (a different year, mode, or branch) and collides outright once
 * more categories are visible than palette hues (e.g. 17 federal functions
 * against a 7-color palette: positions 0/7/14 previously shared one hue).
 */
function stableColorIndex(name: string, paletteLength: number): number {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) % paletteLength;
}

export function colorsFor(nodes: TreeNode[], dark: boolean): string[] {
  const palette = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
  return nodes.map((node) =>
    node.name.startsWith("Other") ? MUTED : palette[stableColorIndex(node.name, palette.length)],
  );
}

export function formatAud(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(2)}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`;
  }
  return new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" }).format(value);
}

export function formatAudFull(value: number): string {
  return new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 }).format(
    value
  );
}

/** Format by semantic unit — never show `$` for percentages. */
export function formatMeasureValue(value: number, unit?: string | null): string {
  if (unit === "percent") {
    return `${value.toLocaleString("en-AU", { maximumFractionDigits: 2 })}%`;
  }
  if (unit && unit !== "AUD" && unit !== "aud") {
    return `${value.toLocaleString("en-AU", { maximumFractionDigits: 2 })} ${unit}`;
  }
  return formatAudFull(value);
}
