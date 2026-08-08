import { formatMeasureValue } from "./colors";
import type { TreeNode } from "./types";

export type ReportedChartDatum = {
  name?: string;
  reportedValue?: number;
  reportedUnit?: string | null;
  reportedParentValue?: number | null;
  relationship?: TreeNode["relationship"];
  isRelated?: boolean;
  children?: unknown[];
};

export function reportedAriaSummary(
  data: ReportedChartDatum[],
  fallbackUnit: string | null,
): string {
  const parts: string[] = [];
  const visit = (datum: ReportedChartDatum, path: string[]) => {
    const name = datum.name ?? "Unnamed item";
    const names = [...path, name];
    parts.push(
      `${names.join(" › ")}: ${formatMeasureValue(
        datum.reportedValue ?? 0,
        datum.reportedUnit ?? datum.relationship?.unit ?? fallbackUnit,
      )}`,
    );
    for (const child of (datum.children ?? []) as ReportedChartDatum[]) {
      visit(child, names);
    }
  };
  for (const datum of data) visit(datum, []);
  return parts.join("; ");
}

export function reportedTooltip(
  name: string,
  datum: ReportedChartDatum,
  fallbackValue: number,
  fallbackUnit: string | null,
): string {
  const reportedValue = datum.reportedValue ?? fallbackValue;
  const unit = datum.reportedUnit ?? datum.relationship?.unit ?? fallbackUnit;
  const related = datum.isRelated || datum.relationship?.branch_kind === "related";
  const parentValue = datum.reportedParentValue;
  const percentage =
    !related && parentValue != null && parentValue > 0
      ? ` (${((reportedValue / parentValue) * 100).toFixed(1)}% of parent)`
      : "";
  const relationshipNote = related
    ? "<br/><span style='opacity:.75'>Related breakdown — not a percent of parent</span>"
    : "";
  const hint = datum.children?.length
    ? "<br/><span style='opacity:.75'>Click to expand</span>"
    : "";
  return `${name}<br/>${formatMeasureValue(reportedValue, unit)}${percentage}${relationshipNote}${hint}`;
}

export function commonUnit(nodes: TreeNode[], fallback: string | null): string | null {
  const units = new Set(
    nodes
      .map((node) => node.relationship?.unit ?? node.unit)
      .filter((unit): unit is string => Boolean(unit)),
  );
  if (units.size === 1) return [...units][0];
  return units.size > 1 ? "mixed_units" : fallback;
}

export function additiveSiblingTotal(nodes: TreeNode[], target: TreeNode): number | null {
  const targetRelationship = target.relationship;
  const targetRelated =
    targetRelationship?.branch_kind === "related" ||
    target.breakdown?.kind === "related_breakdown";
  if (targetRelated) return null;
  const targetUnit = targetRelationship?.unit ?? target.unit ?? "AUD";
  const targetCompatibility =
    targetRelationship?.compatibility_group ?? target.breakdown?.compatibility_group ?? null;
  const targetYear =
    targetRelationship?.fact_financial_year ?? target.breakdown?.fact_financial_year ?? null;
  return nodes
    .filter((node) => {
      const relationship = node.relationship;
      const related =
        relationship?.branch_kind === "related" ||
        node.breakdown?.kind === "related_breakdown";
      return (
        !related &&
        (relationship?.unit ?? node.unit ?? "AUD") === targetUnit &&
        (relationship?.compatibility_group ??
          node.breakdown?.compatibility_group ??
          null) === targetCompatibility &&
        (relationship?.fact_financial_year ??
          node.breakdown?.fact_financial_year ??
          null) === targetYear
      );
    })
    .reduce((sum, node) => sum + node.value, 0);
}
