import { test, expect } from "@playwright/test";

// Verifies item 7.2's QGIP explorer, added purely via a
// config/explorers/families.yaml registry entry (item 6.1/6.2's
// registry-driven shell) - no frontend code was written for this family.

test("QGIP explorer family page loads with truthful totals and both estimate_status bases selectable", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/ausgov-budget-tracker/explorers/family/qgip/");
  await page.waitForLoadState("networkidle");

  await expect(page.getByRole("heading", { name: "QLD QGIP expenditure" })).toBeVisible();
  await expect(page.getByText(/rows for .*\(actual\), total value \$/)).toBeVisible();

  const estimateStatus = page.getByLabel("Estimate status");
  await expect(estimateStatus).toBeVisible();
  const options = await estimateStatus.locator("option").allTextContents();
  expect(options).toContain("actual");
  expect(options).toContain("actual_cumulative_agreement_total");

  expect(errors, `console errors: ${JSON.stringify(errors)}`).toEqual([]);
});
