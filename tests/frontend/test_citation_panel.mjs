/**
 * CitationPanel contract test (no React runtime required):
 * complete citation must expose three distinct link roles.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const src = readFileSync(
  join(root, "src/frontend/components/CitationPanel/CitationPanel.tsx"),
  "utf8",
);

assert.match(src, /data-citation-link=\{link\.key\}/);
assert.match(src, /Publisher landing page/);
assert.match(src, /Original resource/);
assert.match(src, /Cached copy/);
assert.match(src, /landing_url/);
assert.match(src, /original_resource_url/);
assert.match(src, /cached_copy_url/);
// Quarantined facts are never passed in — empty state only
assert.match(src, /No citation/);
console.log("citation_panel_ok");
