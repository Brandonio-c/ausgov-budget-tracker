import { TreeNode } from "./types";

/** Find a path of TreeNodes from root children down to a fact id or name match. */
export function findDrillPath(
  root: TreeNode | null | undefined,
  opts: { factId?: number | null; highlight?: string | null },
): { path: TreeNode[]; leaf: TreeNode | null } {
  if (!root) return { path: [], leaf: null };
  const factId = opts.factId ?? null;
  const highlight = (opts.highlight || "").trim().toLowerCase();

  let best: TreeNode[] | null = null;
  let foundExact = false;

  function walk(node: TreeNode, path: TreeNode[]): boolean {
    const next = [...path, node];
    const nameLc = node.name.toLowerCase();
    const idMatch = factId != null && node.id === factId;
    const nameMatch =
      highlight.length > 0 &&
      (nameLc === highlight ||
        nameLc.includes(highlight) ||
        highlight.includes(nameLc) ||
        highlight.endsWith(nameLc));

    if (idMatch) {
      best = next;
      foundExact = true;
      return true;
    }
    if (nameMatch && (!best || next.length >= best.length)) {
      best = next;
    }
    for (const child of node.children || []) {
      if (walk(child, next)) return true;
    }
    return false;
  }

  walk(root, []);
  if (!best) return { path: [], leaf: null };

  const stack: TreeNode[] = best;
  const leaf = stack[stack.length - 1] ?? null;
  const path =
    stack.length > 0 && stack[0].name === root.name ? stack.slice(1) : stack;
  void foundExact;
  return { path, leaf };
}
