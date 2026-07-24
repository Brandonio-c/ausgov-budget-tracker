import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const home = readFileSync(join(root, "src/frontend/app/page.tsx"), "utf8");
const legacy = readFileSync(join(root, "src/frontend/app/legacy/page.tsx"), "utf8");
const api = readFileSync(join(root, "src/frontend/lib/api.ts"), "utf8");

assert.match(home, /data-default-store=\"facts-dashboard\"/);
assert.match(home, /SpendingChart/);
assert.match(home, /apiDashboard/);
assert.match(home, /Actuals/);
assert.match(home, /Budget/);
assert.match(home, /FactCitationViewer/);
assert.doesNotMatch(home, /Citation-bearing facts store \(cutover\)/);

assert.match(legacy, /api\s*\.\s*levels\s*\(/);
assert.match(legacy, /SpendingChart/);
assert.doesNotMatch(legacy, /apiDashboard/);

assert.match(api, /\/v2\/dashboard\/levels/);
assert.match(api, /\/api\/spending\/levels/);

assert.match(
  readFileSync(join(root, "src/frontend/components/CitationPanel/CitationPanel.tsx"), "utf8"),
  /data-citation-link/,
);
console.log("default_view_regression_ok");
