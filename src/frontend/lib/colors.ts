import { TreeNode } from "./types";

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

/** Sort children by value desc; fold anything past the token ceiling into a
 *  single "Other" node whose own children are the folded nodes, so drilling
 *  into "Other" is just another (honest) level of the same tree. */
export function foldToTopN(children: TreeNode[], n = TOP_N): TreeNode[] {
  const sorted = [...children].sort((a, b) => b.value - a.value);
  if (sorted.length <= n + 1) return sorted;
  const head = sorted.slice(0, n);
  const tail = sorted.slice(n);
  const otherValue = tail.reduce((sum, node) => sum + node.value, 0);
  const other: TreeNode = {
    name: `Other (${tail.length})`,
    value: otherValue,
    id: null,
    children: tail,
  };
  return [...head, other];
}

export function colorsFor(nodes: TreeNode[], dark: boolean): string[] {
  const palette = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
  return nodes.map((node, i) => (node.name.startsWith("Other (") ? MUTED : palette[i % palette.length]));
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
