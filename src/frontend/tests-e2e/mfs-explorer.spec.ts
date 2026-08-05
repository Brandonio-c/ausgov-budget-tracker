import { test, expect } from "@playwright/test";

/**
 * MFS-aggregates milestone (Task 10/11) UI regression suite. Runs against
 * the fixture backend (scripts/ingest/build_e2e_fixture_db.py, which seeds
 * a small mfs_ytd_revenue + mfs_stock_total_assets series) - no production
 * database or raw-data corpus needed, so this is safe to run in CI
 * alongside dashboard.spec.ts.
 */

const BASE = "/ausgov-budget-tracker/";

test.describe("MFS explorer", () => {
  test("loads with measure/year selectors and a flow disclosure badge", async ({ page }) => {
    await page.goto(`${BASE}explorers/mfs/`);
    await expect(page.getByRole("heading", { name: "Monthly Financial Statements (MFS) explorer" })).toBeVisible();
    await expect(page.getByText("Flow (year-to-date)")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Year-to-date flow through/)).toBeVisible();
    await expect(page.getByText("Source vintage: current")).toBeVisible();
  });

  test("switching to a stock measure flips the disclosure to point-in-time", async ({ page }) => {
    await page.goto(`${BASE}explorers/mfs/`);
    await expect(page.getByText("Flow (year-to-date)")).toBeVisible({ timeout: 15_000 });

    await page.locator("select").first().selectOption("mfs_stock_total_assets");
    await expect(page.getByText("Stock (point-in-time)")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Point-in-time stock at/)).toBeVisible();
  });

  test("renders the four required visualizations and never an expenditure pie", async ({ page }) => {
    await page.goto(`${BASE}explorers/mfs/`);
    await expect(page.getByText("Flow (year-to-date)")).toBeVisible({ timeout: 15_000 });

    await expect(page.getByRole("heading", { name: /YTD revenue vs YTD expenses/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Fiscal balance vs underlying cash balance/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Balance-sheet stocks/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: /vs.*same reporting month/ })).toBeVisible();

    // Never an annual expenditure pie/sunburst on this page.
    await expect(page.getByLabel("Spending chart")).toHaveCount(0);
  });

  test("citation panel shows a real source citation for the selected reporting month", async ({ page }) => {
    await page.goto(`${BASE}explorers/mfs/`);
    await expect(page.getByText("Flow (year-to-date)")).toBeVisible({ timeout: 15_000 });
    // The panel shows the current reporting month's citation immediately
    // (not only after a click) - confirm it is a real citation, not the
    // "no selection yet" placeholder.
    await expect(page.getByText("Source citation")).toBeVisible();
    await expect(page.getByText("Click a data point to see its source citation.")).toHaveCount(0);
  });
});
