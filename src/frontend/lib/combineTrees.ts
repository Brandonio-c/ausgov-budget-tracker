import { TreeNode } from "./types";

export const LEVEL_LABELS: Record<string, string> = {
  federal: "Federal",
  state: "State",
  territory: "Territory",
  local: "Local",
};

export const INTEGRITY_BANNER =
  "Levels are shown side-by-side; totals are not consolidated whole-of-government.";

/** Build a synthetic root whose children are government-level trees (never summed). */
export function combineLevelTrees(
  entries: Array<{ level: string; tree: TreeNode }>,
  year: string,
): TreeNode {
  const children: TreeNode[] = entries.map(({ level, tree }) => {
    // Federal: unwrap single Commonwealth jurisdiction so drilling matches View 1.
    const body =
      level === "federal" && tree.children?.length === 1 ? tree.children[0] : tree;
    return {
      name: LEVEL_LABELS[level] ?? level,
      value: body.value,
      id: body.id ?? null,
      children: body.children,
      breakdown: body.breakdown ?? null,
    };
  });
  return {
    name: `Combined — FY ${year}`,
    value: 0, // intentionally not a cross-level sum
    id: null,
    children,
  };
}

/** Top semantic category names for a level tree (jurisdictions unwrapped for multi-jurisdiction). */
export function topCategoryNames(tree: TreeNode, level: string): string[] {
  if (level === "federal" && tree.children?.length === 1) {
    return (tree.children[0].children ?? []).map((c) => c.name);
  }
  if (level !== "federal" && tree.children?.length) {
    const names = new Set<string>();
    for (const jurisdiction of tree.children) {
      for (const child of jurisdiction.children ?? []) {
        names.add(child.name);
      }
    }
    return [...names];
  }
  return (tree.children ?? []).map((c) => c.name);
}

/** Intersection of category names across level trees (case-insensitive, prefer first spelling). */
export function commonCategoryNames(
  entries: Array<{ level: string; tree: TreeNode }>,
): string[] {
  if (entries.length === 0) return [];
  const lists = entries.map((e) => topCategoryNames(e.tree, e.level));
  const canon = new Map<string, string>();
  for (const name of lists[0]) {
    canon.set(name.toLowerCase(), name);
  }
  for (const list of lists.slice(1)) {
    const lower = new Set(list.map((n) => n.toLowerCase()));
    for (const key of [...canon.keys()]) {
      if (!lower.has(key)) canon.delete(key);
    }
  }
  return [...canon.values()].sort((a, b) => a.localeCompare(b));
}

/** Years present in every selected level (intersection). */
export function intersectYears(yearLists: string[][]): string[] {
  if (yearLists.length === 0) return [];
  const sets = yearLists.map((ys) => new Set(ys));
  return yearLists[0]
    .filter((y) => sets.every((s) => s.has(y)))
    .sort();
}

/** Union of years sorted. */
export function unionYears(yearLists: string[][]): string[] {
  const all = new Set<string>();
  for (const ys of yearLists) {
    for (const y of ys) all.add(y);
  }
  return [...all].sort();
}
