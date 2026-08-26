import type { RelationshipMeta, TreeNode } from "./types";
import { CATEGORICAL_DARK, CATEGORICAL_LIGHT, MUTED, colorsFor, foldToTopN } from "./colors";
import { additiveSiblingTotal } from "./chartSemantics";

export type SunburstDatum = {
  name: string;
  /** ECharts layout weight. It may be scaled to keep nested arcs aligned. */
  value: number;
  /** Exact published/aggregated amount shown to people and assistive tech. */
  reportedValue: number;
  reportedUnit: string | null;
  reportedParentValue: number | null;
  relationship: RelationshipMeta | null;
  isRelated: boolean;
  /** Stable key for click/hover → TreeNode lookup (survives ECharts events). */
  nodeKey: string;
  itemStyle?: { color?: string; borderColor?: string; borderWidth?: number };
  label?: {
    show?: boolean;
    color?: string;
    fontSize?: number;
    rotate?: "radial" | "tangential" | number;
    minAngle?: number;
  };
  children?: SunburstDatum[];
};

export type SunburstBuild = {
  data: SunburstDatum[];
  lookup: Map<string, TreeNode>;
  total: number;
};

export type BranchChoice = "canonical" | string;

function clampDepth(depth: number, maxDepth = 32): number {
  return Math.min(maxDepth, Math.max(1, Math.round(depth)));
}

/** Lighten a hex color toward white by `amount` (0–1). */
export function lightenHex(hex: string, amount: number): string {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return hex;
  const r = parseInt(raw.slice(0, 2), 16);
  const g = parseInt(raw.slice(2, 4), 16);
  const b = parseInt(raw.slice(4, 6), 16);
  const mix = (c: number) => Math.round(c + (255 - c) * amount);
  const toHex = (c: number) => c.toString(16).padStart(2, "0");
  return `#${toHex(mix(r))}${toHex(mix(g))}${toHex(mix(b))}`;
}

/**
 * A sunburst wedge encodes "this is part of my parent's total" — so only
 * genuinely additive (`branch_kind !== "related"`) children may ever appear
 * here. `related_breakdown` data (Statement 6 estimates, contracts, grants,
 * PBS programs, recipient counts — a different measure family, vintage, or
 * accounting basis) must never be scaled into the canonical partition
 * alongside true additive siblings, however small the resulting visual
 * distortion looks (see `relatedFolderChildren` for the deliberate,
 * separately-surfaced way to reach this data via a branch selector).
 *
 * A GFS purpose with no native sub-purpose breakdown at all (e.g. ABS
 * Table_4 "Social protection") may correctly have ZERO additive children
 * once related data is excluded here — that is the truthful outcome, not a
 * regression: the richer Statement 6/PBS detail still exists and remains
 * reachable through the branch selector, just never blended into canonical
 * as if it partitioned the GFS actual.
 */
export function additiveChildren(nodes: TreeNode[] | null | undefined): TreeNode[] {
  return (nodes ?? []).filter((n) => {
    if (!(n.value > 0)) return false;
    if (n.relationship?.branch_kind === "related") return false;
    if (!n.relationship && n.breakdown?.kind === "related_breakdown") return false;
    return true;
  });
}

export function nodeHasFamilyDescendant(
  node: TreeNode | null | undefined,
  targetFamily: string,
): boolean {
  if (!node) return false;
  if (targetFamily === "all") return true;
  const rel = node.relationship;
  if (rel?.branch_family === targetFamily) return true;
  const brk = node.breakdown;
  if (brk?.branch_family === targetFamily) return true;
  if (
    targetFamily === "statement_6" &&
    (node.name?.startsWith("Statement 6") || rel?.source_key?.includes("statement_6"))
  ) {
    return true;
  }
  if (
    targetFamily === "fbo" &&
    (node.name?.startsWith("FBO Appendix A") || rel?.source_key?.includes("fbo"))
  ) {
    return true;
  }
  for (const child of node.children ?? []) {
    if (nodeHasFamilyDescendant(child, targetFamily)) return true;
  }
  return false;
}

/**
 * Positive-value related children for `branchChoice`, wherever they live:
 * either nested inside declared navigation folders, or attached directly as bare siblings.
 * When `branchChoice === "all"`, unfolds all authentic related detail across all families.
 * When `branchChoice` is a specific family (e.g. "contracts", "pbs", "statement_6", "ndis_participants"),
 * filters/prioritizes paths matching or leading to that family.
 */
function relatedFolderChildren(
  nodes: TreeNode[] | null | undefined,
  branchChoice: BranchChoice,
): TreeNode[] | null {
  const list = nodes ?? [];
  if (branchChoice === "canonical") return null;

  const result: TreeNode[] = [];

  for (const n of list) {
    if (!(n.value > 0)) continue;
    const rel = n.relationship;
    const role = rel?.presentation_role;
    const bf = rel?.branch_family;

    const isFolder =
      role === "navigation" ||
      (!rel &&
        n.breakdown?.kind === "related_breakdown" &&
        (n.name.startsWith("Statement 6") ||
          n.name.startsWith("FBO Appendix A") ||
          n.name.startsWith("Related ")));

    if (isFolder && (n.children?.length ?? 0) > 0) {
      if (
        branchChoice === "all" ||
        bf === branchChoice ||
        nodeHasFamilyDescendant(n, branchChoice)
      ) {
        for (const sub of n.children ?? []) {
          if (
            sub.value > 0 &&
            (branchChoice === "all" ||
              sub.relationship?.branch_family === branchChoice ||
              nodeHasFamilyDescendant(sub, branchChoice))
          ) {
            result.push(sub);
          }
        }
      }
    } else {
      if (
        branchChoice === "all" ||
        bf === branchChoice ||
        nodeHasFamilyDescendant(n, branchChoice)
      ) {
        result.push(n);
      }
    }
  }

  return result.length ? result : null;
}

/**
 * Collapse Defence → Defence → Defence style chains so program rings appear sooner.
 * Keeps the outer node’s published amount; adopts the innermost children.
 */
export function collapseSameNameChain(node: TreeNode): TreeNode {
  let cur = node;
  while (
    cur.children?.length === 1 &&
    cur.children[0].name === cur.name &&
    cur.children[0].value > 0
  ) {
    const inner = cur.children[0];
    cur = {
      ...cur,
      id: inner.id ?? cur.id,
      breakdown: inner.breakdown ?? cur.breakdown,
      relationship: inner.relationship ?? cur.relationship,
      unit: inner.unit ?? cur.unit,
      children: inner.children,
    };
  }
  return cur;
}

function prepareRingNodes(nodes: TreeNode[]): TreeNode[] {
  return nodes.map(collapseSameNameChain);
}

/**
 * Top-level ring wedges for the current drill node.
 * When ABS GFS leaves sit beside a Statement 6 pack, expand the pack (deeper).
 */
export function ringRootChildren(
  nodes: TreeNode[] | null | undefined,
  branchChoice: BranchChoice = "canonical",
): TreeNode[] {
  if (branchChoice !== "canonical") {
    const related = relatedFolderChildren(nodes, branchChoice);
    if (related) return prepareRingNodes(related);
  }
  return prepareRingNodes(additiveChildren(nodes));
}

/** Deepest nestable path length under these nodes (1 = leaves only / single ring). */
export function maxVisibleDepth(
  nodes: TreeNode[] | null | undefined,
  branchChoice: BranchChoice = "canonical",
): number {
  const kids = ringRootChildren(nodes, branchChoice);
  if (kids.length === 0) return 0;
  let deepest = 1;
  for (const n of kids) {
    const nest = nestableChildren(n, branchChoice);
    const childDepth = nest.length ? maxVisibleDepth(nest, branchChoice) : 0;
    deepest = Math.max(deepest, 1 + childDepth);
  }
  return deepest;
}

export type FunctionDepth = { name: string; depth: number };

/**
 * Per-top-level-node depth under the current branch, so a single aggregated
 * "of N" number (see `maxVisibleDepth`) never gets read as "every wedge has
 * N levels." `maxVisibleDepth` reports the deepest path reachable *anywhere*
 * among these nodes — genuinely necessary as a rendering clamp, since an
 * ECharts sunburst nests all rings to one shared depth — but presenting that
 * single number as a standalone fact would misleadingly imply every
 * top-level function goes that deep. A function whose own cascade stops at
 * depth 1 is a truthful leaf even when a sibling reaches much deeper under
 * the same branch choice; callers should surface this breakdown alongside
 * (not instead of) the rendering-depth control.
 */
export function perFunctionDepth(
  nodes: TreeNode[] | null | undefined,
  branchChoice: BranchChoice = "canonical",
): FunctionDepth[] {
  return ringRootChildren(nodes, branchChoice).map((n) => {
    const nest = nestableChildren(n, branchChoice);
    const depth = nest.length ? 1 + maxVisibleDepth(nest, branchChoice) : 1;
    return { name: n.name, depth };
  });
}

export function pathKey(names: string[]): string {
  return names.join("\u0001");
}

/** Children safe to draw as an outer ring under `parent` (must roughly partition it). */
export function nestableChildren(
  parent: TreeNode,
  branchChoice: BranchChoice = "canonical",
): TreeNode[] {
  if (branchChoice !== "canonical") {
    const related = relatedFolderChildren(parent.children, branchChoice);
    if (related) return unwrapSameName(parent.name, prepareRingNodes(related), positiveChildren);
  }

  let kids = prepareRingNodes(additiveChildren(parent.children));
  if (kids.length === 0) {
    return [];
  }
  kids = unwrapSameName(parent.name, kids);

  const parentValue = parent.value;
  if (!(parentValue > 0)) return kids;

  const sum = kids.reduce((s, c) => s + c.value, 0);
  // Block nesting only when a child *dominates* the parent (e.g. federal Social
  // protection pack hanging under a small state wedge in Combined). Statement 6 /
  // PBS estimate children often overshoot the GFS parent slightly — allow those
  // and let scaleToSum keep the published parent amount authoritative.
  if (sum > parentValue * 1.25) {
    const dominant = kids.some((k) => k.value > parentValue * 1.25);
    if (!dominant) return kids;

    // Drop children that alone exceed the parent; keep the rest and scale.
    const partition = kids.filter((k) => k.value <= parentValue * 1.01);
    if (partition.length > 0) return partition;

    return [];
  }
  return kids;
}

/**
 * Skip Defence → Defence → Defence wrapper levels when nesting rings.
 * `childrenOf` selects which projection continues the unwrap: `additiveChildren`
 * on the canonical path (never let a same-name wrapper smuggle related data
 * back in), or a plain positive-value filter on an already-related path (once
 * inside a related family's own cascade — e.g. Statement 6 → component → PBS
 * program — its internal nesting should render as-is, not be re-excluded for
 * carrying `branch_kind: "related"` a second time).
 */
function unwrapSameName(
  parentName: string,
  kids: TreeNode[],
  childrenOf: (nodes: TreeNode[] | null | undefined) => TreeNode[] = additiveChildren,
): TreeNode[] {
  let cur = kids;
  while (
    cur.length === 1 &&
    cur[0].name === parentName &&
    (cur[0].children?.length ?? 0) > 0
  ) {
    const next = prepareRingNodes(childrenOf(cur[0].children));
    if (next.length === 0) break;
    cur = next;
  }
  return cur;
}

/** Positive-value children, for continuing an unwrap already inside a related cascade. */
function positiveChildren(nodes: TreeNode[] | null | undefined): TreeNode[] {
  return (nodes ?? []).filter((n) => n.value > 0);
}

/** Scale a sunburst subtree so values sum to `target` (keeps ECharts arcs aligned). */
function scaleToSum(nodes: SunburstDatum[], target: number): SunburstDatum[] {
  const sum = nodes.reduce((s, n) => s + n.value, 0);
  if (!(sum > 0) || !(target > 0)) return nodes;
  if (Math.abs(sum - target) < 0.5) return nodes;
  const scale = target / sum;
  return nodes.map((n) => {
    const value = n.value * scale;
    return {
      ...n,
      value,
      children: n.children?.length ? scaleToSum(n.children, value) : n.children,
    };
  });
}

function buildLevel(
  nodes: TreeNode[],
  depthRemaining: number,
  pathNames: string[],
  lookup: Map<string, TreeNode>,
  parentColor: string | null,
  dark: boolean,
  labelDepth: number,
  currentDepth: number,
  reportedParentValue: number | null,
  branchChoice: BranchChoice,
  foldFirstRing: boolean,
): SunburstDatum[] {
  if (depthRemaining <= 0 || nodes.length === 0) return [];

  // `nodes` are already ring-prepared (additive or Statement 6 cascade).
  // The outermost ring of an undrilled view is the well-known, bounded
  // federal/state top-level function list — folding it into "Other" hides
  // real named categories behind an opaque bucket at the single most
  // important level of the chart. Folding remains appropriate once drilled
  // deeper, where tails can be long and genuinely unbounded (e.g. hundreds
  // of contract line items).
  const positive = nodes.filter((n) => n.value > 0);
  const folded = currentDepth === 1 && !foldFirstRing
    ? positive.sort((a, b) => b.value - a.value)
    : foldToTopN(positive);
  const topColors = parentColor
    ? folded.map((n) =>
        n.name.startsWith("Other") ? MUTED : lightenHex(parentColor, Math.min(0.55, 0.15 + currentDepth * 0.08)),
      )
    : colorsFor(folded, dark);

  return folded.map((node, i) => {
    const prepared = collapseSameNameChain(node);
    const names = [...pathNames, prepared.name];
    const nodeKey = pathKey(names);
    lookup.set(nodeKey, prepared);
    lookup.set(`${pathKey(pathNames)}\u0001#${i}`, prepared);

    const color = topColors[i];
    const nest = depthRemaining > 1 ? nestableChildren(prepared, branchChoice) : [];
    const rawChildren =
      nest.length > 0
        ? buildLevel(
            nest,
            depthRemaining - 1,
            names,
            lookup,
            color,
            dark,
            labelDepth,
            currentDepth + 1,
            prepared.value,
            branchChoice,
            foldFirstRing,
          )
        : undefined;

    // Published amount is authoritative — never replace it with sum(children),
    // which inflates Combined rings when related packs are attached.
    const value = prepared.value;
    const children =
      rawChildren && rawChildren.length > 0
        ? scaleToSum(rawChildren, value)
        : undefined;

    return {
      name: prepared.name,
      value,
      reportedValue: prepared.value,
      reportedUnit: prepared.relationship?.unit ?? prepared.unit ?? null,
      reportedParentValue:
        prepared.relationship?.branch_kind === "related" ||
        prepared.breakdown?.kind === "related_breakdown"
          ? null
          : currentDepth === 1
            ? additiveSiblingTotal(folded, prepared)
            : reportedParentValue,
      relationship: prepared.relationship ?? null,
      isRelated:
        prepared.relationship?.branch_kind === "related" ||
        prepared.breakdown?.kind === "related_breakdown",
      nodeKey,
      itemStyle: {
        color,
        borderColor: dark ? "#1a1a19" : "#fcfcfb",
        borderWidth: 1.5,
      },
      label: {
        show: currentDepth === labelDepth,
        color: dark ? "#ffffff" : "#0b0b0b",
        fontSize: 11,
        rotate: "radial" as const,
        minAngle: 8,
      },
      children: children && children.length > 0 ? children : undefined,
    };
  });
}

/**
 * Build a sunburst tree from the current drill node's children.
 * `ringDepth` 1 = one ring (like pie); 2–3 expand nested breakdowns outward.
 * `foldFirstRing` controls whether the outermost ring may fold into "Other" —
 * pass `false` for an undrilled top-level view (federal/state function list)
 * so every named function stays visible; leave `true` once drilled deeper.
 */
export function buildSunburst(
  children: TreeNode[],
  ringDepth: number,
  dark: boolean,
  branchChoice: BranchChoice = "canonical",
  foldFirstRing = true,
): SunburstBuild {
  const available = Math.max(1, maxVisibleDepth(children, branchChoice));
  const depth = clampDepth(ringDepth, available);
  const lookup = new Map<string, TreeNode>();
  const roots = ringRootChildren(children, branchChoice);
  const rootReportedTotal = roots
    .filter(
      (node) =>
        node.relationship?.branch_kind !== "related" &&
        node.breakdown?.kind !== "related_breakdown",
    )
    .reduce((sum, node) => sum + node.value, 0);
  const data = buildLevel(
    roots,
    depth,
    [],
    lookup,
    null,
    dark,
    depth,
    1,
    rootReportedTotal,
    branchChoice,
    foldFirstRing,
  );
  const total = data.reduce((s, n) => s + n.value, 0);
  return { data, lookup, total };
}

export function sunburstLevelStyles(dark: boolean, depth: number) {
  const border = dark ? "#1a1a19" : "#fcfcfb";
  // Leave a small hollow center for the focus label; use almost full radius.
  const inner = 10;
  const outer = 98;
  const span = (outer - inner) / depth;
  return Array.from({ length: depth }, (_, i) => ({
    r0: `${inner + i * span}%`,
    r: `${inner + (i + 1) * span}%`,
    itemStyle: { borderWidth: 1.5, borderColor: border },
    label: {
      show: i === depth - 1,
      fontSize: i === depth - 1 ? 11 : 10,
      minAngle: 8,
      overflow: "truncate" as const,
    },
  }));
}

/** Resolve a TreeNode from an ECharts sunburst event via path names or nodeKey. */
export function resolveSunburstNode(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  params: any,
  lookup: Map<string, TreeNode> | undefined,
): TreeNode | null {
  if (!lookup) return null;
  const key = params?.data?.nodeKey;
  if (typeof key === "string" && lookup.has(key)) {
    return lookup.get(key) ?? null;
  }
  const names = (params?.treePathInfo || [])
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .map((x: any) => x?.name)
    .filter((n: unknown): n is string => typeof n === "string" && n.length > 0);
  // treePathInfo often includes a synthetic root name — drop leading empties / root
  const trimmed =
    names.length > 0 && !lookup.has(pathKey(names))
      ? names.slice(1)
      : names;
  for (const candidate of [names, trimmed]) {
    if (candidate.length === 0) continue;
    const hit = lookup.get(pathKey(candidate));
    if (hit) return hit;
  }
  return null;
}

export const SUNBURST_PALETTE = { light: CATEGORICAL_LIGHT, dark: CATEGORICAL_DARK, muted: MUTED };
