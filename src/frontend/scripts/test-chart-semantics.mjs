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
    ],
    { stdio: "inherit" },
  );

  const { foldToTopN, formatMeasureValue } = require(path.join(buildDir, "colors.js"));
  const { buildSunburst } = require(path.join(buildDir, "sunburstTree.js"));
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
