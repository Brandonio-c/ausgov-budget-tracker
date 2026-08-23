import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const buildDir = mkdtempSync(path.join(tmpdir(), "ausgov-chart-semantics-"));
const require = createRequire(import.meta.url);

try {
  execFileSync(
    path.resolve("node_modules/.bin/tsc"),
    [
      "--outDir",
      buildDir,
      "--module",
      "commonjs",
      "--target",
      "ES2022",
      "--esModuleInterop",
      "--skipLibCheck",
      "lib/types.ts",
      "lib/colors.ts",
      "lib/sunburstTree.ts",
      "lib/chartSemantics.ts",
      "lib/availability.ts",
    ],
    { stdio: "inherit" },
  );

  const { foldToTopN, formatMeasureValue } = require(path.join(buildDir, "colors.js"));
  const { buildSunburst, perFunctionDepth } = require(path.join(buildDir, "sunburstTree.js"));
  const { formatApiAvailability } = require(path.join(buildDir, "availability.js"));
  const { additiveSiblingTotal, commonUnit, reportedAriaSummary, reportedTooltip } = require(
    path.join(buildDir, "chartSemantics.js"),
  );

  const relationship = (overrides = {}) => ({
    edge_kind: "same_group",
    branch_kind: "additive",
    presentation_role: "data",
    compatibility_group: "budget_expense",
    fact_financial_year: "2024-25",
    is_year_fallback: false,
    unit: "AUD",
    ...overrides,
  });

  assert.equal(
    formatApiAvailability([
      { financial_year: "2025-26", estimate_status: "revised_estimate" },
      { financial_year: "2024-25", estimate_status: "actual" },
      { financial_year: "2024-25", estimate_status: "actual" },
    ]),
    "API availability: FY2024-25 to FY2025-26; revised estimate, actual",
  );
  const node = (name, value, relation, children = null) => ({
    name,
    value,
    id: null,
    children,
    relationship: relation,
    unit: relation?.unit ?? null,
  });

  const parent = node("Parent", 100, relationship(), [
    node("Published 80", 80, relationship()),
    node("Published 40", 40, relationship()),
  ]);
  const sunburst = buildSunburst([parent], 2, false);
  const scaledChild = sunburst.data[0].children[0];
  assert.notEqual(scaledChild.value, scaledChild.reportedValue);
  assert.equal(scaledChild.reportedValue, 80);
  assert.equal(scaledChild.reportedUnit, "AUD");
  assert.match(
    reportedTooltip("Published 80", scaledChild, scaledChild.value, "AUD"),
    /\$80/,
  );
  assert.match(reportedAriaSummary(sunburst.data, "AUD"), /Published 80: \$80/);

  const fboLeaf = node(
    "Audited subfunction",
    60,
    relationship({
      branch_kind: "related",
      branch_family: "fbo",
      accounting_basis: "accrual",
      estimate_status: "audited_actual",
    }),
  );
  const fboFolder = node(
    "Historical FBO Appendix A (audited)",
    100,
    relationship({
      edge_kind: "related_breakdown",
      branch_kind: "related",
      branch_family: "fbo",
      presentation_role: "navigation",
    }),
    [node("Health", 60, relationship({ branch_kind: "related", branch_family: "fbo" }), [fboLeaf])],
  );
  const purpose = node("Health", 100, relationship(), [
    node("Canonical health", 100, relationship()),
    fboFolder,
  ]);
  const canonicalRings = buildSunburst([purpose], 3, false, "canonical");
  assert.equal(canonicalRings.data[0].children[0].name, "Canonical health");
  const fboRings = buildSunburst([purpose], 3, false, "fbo");
  assert.equal(fboRings.data[0].children[0].name, "Audited subfunction");

  // Regression: a P0 defect where additiveChildren() gated exclusion on
  // "is this a folder-shaped navigation node" instead of on branch_kind
  // alone, so bare (non-folder) related_breakdown children — the shape a
  // GFS purpose with NO native additive sub-breakdown gets when the backend
  // grafts a related family straight onto the leaf (e.g. real production
  // "Social protection", which has zero same_group children of its own and
  // only Statement 6 category estimates attached directly) — silently
  // rendered as if they partitioned the canonical additive total. Confirmed
  // live against the running production backend before the fix: Social
  // security and welfare showed 0 children under this exact shape until the
  // resolver bug was fixed, and even after that fix the sunburst itself
  // still needed this separate correction to stop treating those related
  // children as additive once they *were* reachable.
  const noNativeBreakdown = node("Social protection", 286_605, relationship(), [
    node(
      "Assistance to the aged",
      101_767,
      relationship({ branch_kind: "related", branch_family: "statement_6" }),
    ),
    node(
      "Assistance to people with disabilities",
      86_338,
      relationship({ branch_kind: "related", branch_family: "statement_6" }),
    ),
  ]);
  const canonicalNoBreakdown = buildSunburst([noNativeBreakdown], 3, false, "canonical");
  assert.equal(
    canonicalNoBreakdown.data[0].children,
    undefined,
    "a purpose with no native additive breakdown must render as a leaf in canonical mode, " +
      "never silently absorbing bare related siblings as if they partitioned it",
  );
  const statement6NoBreakdown = buildSunburst([noNativeBreakdown], 3, false, "statement_6");
  assert.equal(statement6NoBreakdown.data[0].children.length, 2);
  assert.equal(statement6NoBreakdown.data[0].children[0].name, "Assistance to the aged");
  assert.equal(
    statement6NoBreakdown.data[0].children[0].relationship.branch_kind,
    "related",
    "the related branch view must still correctly label this data as related, not additive",
  );

  // Regression: a P0 defect where the chart exposed a single aggregated
  // "of N" depth number (maxVisibleDepth over ALL top-level functions
  // combined) with no disclosure that most functions stop far shallower —
  // e.g. "6 reported rings" implying uniform depth when Social Security
  // stops at the first ring. perFunctionDepth() must report each top-level
  // function's own depth so a UI can disclose the true, uneven picture.
  const shallowFunction = node("Social security and welfare", 200, relationship());
  const deepFunction = node("Health", 100, relationship(), [
    node("Medical services", 100, relationship(), [
      node("MBS", 100, relationship()),
    ]),
  ]);
  const depths = perFunctionDepth([shallowFunction, deepFunction], "canonical");
  assert.deepEqual(depths, [
    { name: "Social security and welfare", depth: 1 },
    { name: "Health", depth: 3 },
  ]);

  // Regression: a P1 defect where the outermost ring of an undrilled
  // top-level view (the well-known, bounded federal/state function list)
  // folded into "Other" past 7 siblings just like any deeper, genuinely
  // unbounded tail — hiding real named categories at the single most
  // important level of the chart. foldFirstRing=false (undrilled) must keep
  // every top-level function visible; foldFirstRing=true (drilled, the
  // default) must fold exactly as before.
  const nineFunctions = Array.from({ length: 9 }, (_, i) =>
    node(`Function ${i}`, 100 - i, relationship()),
  );
  const undrilled = buildSunburst(nineFunctions, 1, false, "canonical", false);
  assert.equal(undrilled.data.length, 9, "undrilled top level must never fold into Other");
  assert.ok(undrilled.data.every((n) => !n.name.startsWith("Other")));
  const drilled = buildSunburst(nineFunctions, 1, false, "canonical", true);
  assert.equal(drilled.data.length, 8, "drilled/default view still folds past 7 siblings");
  assert.ok(drilled.data.some((n) => n.name.startsWith("Other")));

  const relatedTooltip = reportedTooltip(
    "Recipients",
    {
      reportedValue: 25,
      reportedUnit: "recipient_count",
      reportedParentValue: 100,
      relationship: relationship({
        branch_kind: "related",
        compatibility_group: "recipient_count",
        unit: "recipient_count",
      }),
    },
    10,
    "AUD",
  );
  assert.match(relatedTooltip, /25 recipient_count/);
  assert.match(relatedTooltip, /not a percent of parent/);
  assert.match(relatedTooltip, /Related · Data/);
  assert.match(relatedTooltip, /Source FY 2024-25/);
  assert.doesNotMatch(relatedTooltip, /% of parent/);

  const additiveTooltip = reportedTooltip(
    "Additive",
    {
      reportedValue: 40,
      reportedUnit: "percent",
      reportedParentValue: 80,
      relationship: relationship({ unit: "percent" }),
    },
    5,
    "AUD",
  );
  assert.match(additiveTooltip, /40%/);
  assert.match(additiveTooltip, /50\.0% of parent/);
  assert.equal(formatMeasureValue(12.5, "percent"), "12.5%");

  const audNode = node("AUD", 100, relationship());
  const percentNode = node(
    "Percent",
    12.5,
    relationship({ compatibility_group: "ratio", unit: "percent" }),
  );
  assert.equal(commonUnit([audNode, percentNode], null), "mixed_units");
  assert.equal(additiveSiblingTotal([audNode, percentNode], audNode), 100);
  assert.equal(additiveSiblingTotal([audNode, percentNode], percentNode), 12.5);

  const folded = foldToTopN(
    [
      node("Head", 100, relationship()),
      node("AUD current", 9, relationship()),
      node("AUD current 2", 8.5, relationship()),
      node("AUD prior", 8, relationship({ fact_financial_year: "2023-24" })),
      node("AUD prior 2", 7.5, relationship({ fact_financial_year: "2023-24" })),
      node(
        "Percent",
        7,
        relationship({ compatibility_group: "ratio", unit: "percent" }),
      ),
      node(
        "Percent 2",
        6.5,
        relationship({ compatibility_group: "ratio", unit: "percent" }),
      ),
      node(
        "Related recipients",
        6,
        relationship({
          branch_kind: "related",
          compatibility_group: "recipient_count",
          unit: "recipient_count",
        }),
      ),
      node(
        "Related recipients 2",
        5.5,
        relationship({
          branch_kind: "related",
          compatibility_group: "recipient_count",
          unit: "recipient_count",
        }),
      ),
    ],
    1,
  );
  const others = folded.filter((item) => item.name.startsWith("Other"));
  assert.equal(others.length, 4);
  for (const other of others) {
    const signatures = new Set(
      other.children.map((child) =>
        JSON.stringify([
          child.relationship.branch_kind,
          child.relationship.unit,
          child.relationship.fact_financial_year,
          child.relationship.compatibility_group,
        ]),
      ),
    );
    assert.equal(signatures.size, 1);
    assert.ok(other.relationship, "synthetic Other retains relationship metadata");
  }

  console.log("chart semantic unit tests passed");
} finally {
  rmSync(buildDir, { recursive: true, force: true });
}
