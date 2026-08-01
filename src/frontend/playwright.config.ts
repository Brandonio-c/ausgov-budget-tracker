import { defineConfig } from "@playwright/test";

// This app ships as a static export (next.config.ts: output "export",
// basePath "/ausgov-budget-tracker") deployed to Cloudflare Pages - `next
// dev` does not reliably hydrate this configuration (confirmed: JS bundle
// loads, DOM renders, but no event listeners attach and no data fetch ever
// fires). Tests must run against a real `next build` static export served
// under a path matching basePath, which is what actually ships to
// production and does hydrate correctly.
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3313";

export default defineConfig({
  testDir: "./tests-e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
  },
});
