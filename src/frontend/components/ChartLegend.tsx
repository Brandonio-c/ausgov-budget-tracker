"use client";

import { TreeNode } from "@/lib/types";
import { colorsFor, formatMeasureValue } from "@/lib/colors";
import { commonUnit } from "@/lib/chartSemantics";

interface Props {
  nodes: TreeNode[];
  dark: boolean;
  onSelect?: (node: TreeNode) => void;
  highlightName?: string | null;
}

/**
 * A persistent, always-legible list of the current top-level categories —
 * ECharts sunburst/pie labels rely on wedge size and can overlap or get
 * truncated (confirmed live: FY2024-25's fewer, unevenly-sized GFS
 * categories produce colliding on-canvas labels). This renders as plain DOM
 * text next to the chart, using the same name-derived colors the chart
 * itself draws, so every category stays readable regardless of its wedge
 * angle.
 */
export default function ChartLegend({ nodes, dark, onSelect, highlightName }: Props) {
  if (nodes.length === 0) return null;
  const colors = colorsFor(nodes, dark);
  const unit = commonUnit(nodes, null);

  return (
    <ul
      className="mb-3 flex flex-wrap gap-x-3 gap-y-1.5 text-xs"
      aria-label="Chart legend"
    >
      {nodes.map((node, i) => {
        const isHighlighted =
          highlightName != null && node.name.toLowerCase() === highlightName.toLowerCase();
        const content = (
          <>
            <span
              aria-hidden="true"
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ backgroundColor: colors[i] }}
            />
            <span className={isHighlighted ? "font-semibold" : undefined}>{node.name}</span>
            <span className="text-zinc-500 dark:text-zinc-400">
              {formatMeasureValue(node.value, node.relationship?.unit ?? node.unit ?? unit)}
            </span>
          </>
        );
        return (
          <li key={node.name} className="flex items-center gap-1">
            {onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(node)}
                className="flex items-center gap-1 rounded hover:underline"
              >
                {content}
              </button>
            ) : (
              <span className="flex items-center gap-1">{content}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
