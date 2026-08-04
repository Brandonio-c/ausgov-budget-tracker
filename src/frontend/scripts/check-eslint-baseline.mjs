#!/usr/bin/env node
/**
 * CI-enforced ESLint gate (Task 7 of the database-hygiene-and-CI-hardening
 * milestone). Runs ESLint, sums error/warning counts, and fails only if
 * either count exceeds the committed baseline in .eslint-baseline.json -
 * not a blanket `|| true` that hides everything, and not a hard "must be
 * zero" gate that would require fixing pre-existing, out-of-scope React-
 * hooks/rendering issues as a side effect of a database-hygiene milestone.
 * Read-only: never rewrites the baseline file itself (no CI job should
 * silently commit changes) - if the live count drops below the committed
 * baseline, this only prints a suggestion to lower it by hand, so the
 * ceiling can shrink over time but never creep back up unnoticed.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(DIR, "..");
const BASELINE_PATH = path.join(ROOT, ".eslint-baseline.json");

function runEslint() {
  try {
    const out = execFileSync("npx", ["eslint", ".", "--format", "json"], {
      cwd: ROOT,
      encoding: "utf-8",
      maxBuffer: 1024 * 1024 * 32,
    });
    return JSON.parse(out);
  } catch (err) {
    // ESLint exits non-zero whenever it finds any error - stdout still has
    // the JSON report we need.
    if (err.stdout) return JSON.parse(err.stdout);
    throw err;
  }
}

const results = runEslint();
const errorCount = results.reduce((sum, f) => sum + f.errorCount, 0);
const warningCount = results.reduce((sum, f) => sum + f.warningCount, 0);

const baseline = JSON.parse(readFileSync(BASELINE_PATH, "utf-8"));

console.log(
  `ESLint: ${errorCount} error(s), ${warningCount} warning(s) ` +
    `(baseline: ${baseline.max_errors} error(s), ${baseline.max_warnings} warning(s))`,
);

if (errorCount > baseline.max_errors || warningCount > baseline.max_warnings) {
  console.error(
    "ESLint regression: live problem count exceeds the committed baseline " +
      `(errors ${errorCount} > ${baseline.max_errors} or warnings ${warningCount} > ${baseline.max_warnings}). ` +
      "Fix the new issue(s), or if you deliberately paid down existing debt, " +
      "lower src/frontend/.eslint-baseline.json to match.",
  );
  process.exit(1);
}

if (errorCount < baseline.max_errors || warningCount < baseline.max_warnings) {
  console.log(
    "Live count is below the committed baseline - consider lowering " +
      `src/frontend/.eslint-baseline.json to {"max_errors": ${errorCount}, "max_warnings": ${warningCount}} ` +
      "so this improvement isn't allowed to silently regress.",
  );
}
