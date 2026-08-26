import { expect, test } from "@playwright/test";

const BASE = "/ausgov-budget-tracker/";

test.describe("Queensland MYFER explorer", () => {
  test("shows revised-estimate vintages with a source citation", async ({ page }) => {
    await page.goto(`${BASE}explorers/gfs/?view=qld_myfer`);

    await expect(page.getByRole("button", { name: "QLD MYFER" })).toBeVisible();
    await expect(page.getByText(/API availability:.*revised estimate/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/2015-16 MYFER \(revised estimate\)/).first()).toBeVisible();
    await expect(page.getByText(/vintage 2015-16/).first()).toBeVisible();
    await expect(page.getByText("Source citation")).toBeVisible();
    await expect(page.getByText(/table:Table 3/).first()).toBeVisible();
  });
});
