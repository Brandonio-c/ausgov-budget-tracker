#!/usr/bin/env node
/**
 * Federal depth opportunity matrix: for every top-level Federal function in
 * a set of projections, compute the depth/coverage/terminal-leaf metrics the
 * data-depth mission uses to prioritize where to invest ingestion effort.
 *
 * Reuses the SHIPPED frontend depth logic (lib/sunburstTree.ts) rather than
 * a separate re-implementation, so the matrix reflects exactly what the live
 * UI does — the same discipline established in this session's earlier
 * remediation loops (see ops/reports/federal-depth-visualization-remediation-*.md).
 *
 * Requires a locally-running backend serving the real data/facts.db (see the
 * README's "fresh local backend" pattern — never the production container).
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const API_BASE = process.env.DEPTH_MATRIX_API_BASE ?? "http://127.0.0.1:8099";
const FRONTEND_DIR = path.resolve(process.argv[1], "../../../src/frontend");
const OUT_PREFIX =
  process.argv.find((a) => a.startsWith("--output-prefix="))?.split("=")[1] ??
  `ops/reports/federal-depth-opportunity-matrix-${new Date()
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\..+/, "")}Z`;

const PROJECTIONS = [
  { label: "federal_actuals_2024_25", mode: "actuals", level: "federal", year: "2024-25" },
  { label: "federal_actuals_2025_26", mode: "actuals", level: "federal", year: "2025-26" },
  { label: "federal_budget_2025_26", mode: "budget", level: "federal", year: "2025-26" },
];

const buildDir = mkdtempSync(path.join(tmpdir(), "ausgov-depth-matrix-"));
const require = createRequire(import.meta.url);

async function main() {
  execFileSync(
    path.join(FRONTEND_DIR, "node_modules/.bin/tsc"),
    [
      "--outDir",
      buildDir,
      "--module",
      "commonjs",
      "--target",
      "ES2022",
      "--esModuleInterop",
      "--skipLibCheck",
      path.join(FRONTEND_DIR, "lib/types.ts"),
      path.join(FRONTEND_DIR, "lib/colors.ts"),
      path.join(FRONTEND_DIR, "lib/sunburstTree.ts"),
      path.join(FRONTEND_DIR, "lib/chartSemantics.ts"),
    ],
    { stdio: "inherit" },
  );
  const { additiveChildren, nestableChildren, perFunctionDepth } = require(
    path.join(buildDir, "sunburstTree.js"),
  );

  const rows = [];

  for (const spec of PROJECTIONS) {
    const url = `${API_BASE}/v2/dashboard/tree?mode=${spec.mode}&level=${spec.level}&year=${spec.year}`;
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`FAILED ${spec.label}: ${res.status} ${await res.text()}`);
      continue;
    }
    const tree = await res.json();
    const rootNode =
      spec.level === "federal" && tree.children?.length === 1 ? tree.children[0] : tree;
    const rawChildren = rootNode?.children ?? [];
    const additive = additiveChildren(rawChildren);
    const grandTotal = additive.reduce((s, n) => s + n.value, 0);

    // Every branch_family reachable anywhere under this projection's root —
    // the set of related dimensions the depth calc must check per function.
    const branchFamilies = new Set();
    (function walkFamilies(nodes) {
      for (const n of nodes ?? []) {
        if (n.relationship?.branch_kind === "related" && n.relationship.branch_family) {
          branchFamilies.add(n.relationship.branch_family);
        }
        walkFamilies(n.children);
      }
    })(rawChildren);

    for (const fn of additive) {
      const canonicalNest = nestableChildren(fn, "canonical");
      const canonicalDepth = canonicalNest.length
        ? 1 + maxDepthOf(canonicalNest, "canonical", nestableChildren)
        : 1;

      const perFamilyDepth = {};
      let maxRelatedDepth = 0;
      for (const family of branchFamilies) {
        const nest = nestableChildren(fn, family);
        const depth = nest.length ? 1 + maxDepthOf(nest, family, nestableChildren) : 1;
        perFamilyDepth[family] = depth;
        if (depth > maxRelatedDepth) maxRelatedDepth = depth;
      }

      const leaves = collectCanonicalLeaves(fn, additiveChildren);
      const largestLeaf = leaves.reduce((m, l) => Math.max(m, l.value), 0);
      const sourceFamilies = new Set();
      (function walkSources(node) {
        const sf = node.relationship?.source_family ?? node.breakdown?.source_family;
        if (sf) sourceFamilies.add(sf);
        for (const c of node.children ?? []) walkSources(c);
      })(fn);

      rows.push({
        projection: spec.label,
        function: fn.name,
        value: fn.value,
        share_of_federal: grandTotal > 0 ? fn.value / grandTotal : null,
        canonical_additive_depth: canonicalDepth,
        max_related_depth: maxRelatedDepth,
        max_total_semantic_depth: Math.max(canonicalDepth, maxRelatedDepth),
        immediate_child_count: canonicalNest.length,
        canonical_terminal_leaf_count: leaves.length,
        largest_canonical_terminal_leaf: largestLeaf,
        leaves_over_1b: leaves.filter((l) => l.value >= 1e9).length,
        leaves_over_5b: leaves.filter((l) => l.value >= 5e9).length,
        leaves_over_10b: leaves.filter((l) => l.value >= 10e9).length,
        leaves_over_25b: leaves.filter((l) => l.value >= 25e9).length,
        leaves_over_50b: leaves.filter((l) => l.value >= 50e9).length,
        branch_families_with_depth: JSON.stringify(perFamilyDepth),
        source_families: [...sourceFamilies].join("|"),
      });
    }
  }

  const csvHeader = Object.keys(rows[0]).join(",");
  const csvBody = rows
    .map((r) =>
      Object.values(r)
        .map((v) => (typeof v === "string" && v.includes(",") ? `"${v}"` : v))
        .join(","),
    )
    .join("\n");
  writeFileSync(`${OUT_PREFIX}.csv`, `${csvHeader}\n${csvBody}\n`);
  writeFileSync(`${OUT_PREFIX}.json`, JSON.stringify(rows, null, 2) + "\n");
  console.log(`Wrote ${rows.length} rows to ${OUT_PREFIX}.csv / .json`);
}

function maxDepthOf(nodes, branchChoice, nestableChildren) {
  let deepest = 1;
  for (const n of nodes) {
    const nest = nestableChildren(n, branchChoice);
    const d = nest.length ? 1 + maxDepthOf(nest, branchChoice, nestableChildren) : 1;
    if (d > deepest) deepest = d;
  }
  return deepest;
}

function collectCanonicalLeaves(node, additiveChildren) {
  const kids = additiveChildren(node.children);
  if (kids.length === 0) return [{ name: node.name, value: node.value }];
  return kids.flatMap((k) => collectCanonicalLeaves(k, additiveChildren));
}

main()
  .catch((err) => {
    console.error(err);
    process.exitCode = 1;
  })
  .finally(() => {
    rmSync(buildDir, { recursive: true, force: true });
  });
