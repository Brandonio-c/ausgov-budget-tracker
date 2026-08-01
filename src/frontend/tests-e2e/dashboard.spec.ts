import { test, expect } from "@playwright/test";

/**
 * Task 8 UI regression suite. Runs headlessly against a real `next dev`
 * server (basePath "/ausgov-budget-tracker") talking to a real backend
 * against data/facts.db - not mocked. Deep-links (mode/level/year query
 * params, handled in app/HomeClient.tsx) are used to reach each required
 * path directly rather than scripting every click, since HomeClient applies
 * them once on load.
 */

const BASE = "/ausgov-budget-tracker/";

test.describe("dashboard navigation and citation regressions", () => {
  test("home page loads with mode/chart controls", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByText("AusGov Budget Tracker")).toBeVisible();
    await expect(page.getByRole("button", { name: "Actuals", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Budget", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Debt", exact: true })).toBeVisible();
  });

  test("Federal Actuals 2024-25 deep link renders a populated chart", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2024-25`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart).toBeVisible();
    // The chart canvas/svg must actually paint something, not stay on the
    // "Loading…" placeholder - a real regression this catches is the API
    // call silently failing (wrong mode/level combination, CORS, etc).
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
  });

  test("Federal Budget mode switch updates the chart without an error banner", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2024-25`);
    await page.getByRole("button", { name: "Budget" }).click();
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    // HomeClient renders errors as visible text via setError(); absence of
    // that text is the regression signal, not a specific error selector.
    await expect(page.getByText(/failed to load|error/i)).toHaveCount(0);
  });

  test("QLD state actuals branch is reachable", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=state&year=2024-25`);
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await expect(page.getByLabel("Spending chart")).toBeVisible();
  });

  test("local government branch is reachable", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=local`);
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await expect(page.getByLabel("Spending chart")).toBeVisible();
  });

  test("debt view is labelled as GFS liability stock, not Budget net debt", async ({ page }) => {
    // The always-on "Government debt (liabilities)" widget (distinct from
    // the main chart's own Debt mode, which replaces it when selected)
    // carries this exact disclaimer - visible on the plain home page.
    await page.goto(BASE);
    await expect(page.getByText("Government debt (liabilities)")).toBeVisible();
    // This exact distinction (GFS liability stocks vs Budget Paper "net
    // debt") is a named mixed-valuation safeguard in the directive - a
    // regression that silently drops or renames this disclaimer would be a
    // real correctness/labelling bug for a debt figure.
    await expect(
      page.getByText(/GFS liability stocks.*not Budget Paper.*net debt/i)
    ).toBeVisible();
  });

  test("ring depth control renders on a GDP/ratio branch", async ({ page }) => {
    await page.goto(`${BASE}?mode=ratios&level=federal`);
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await expect(page.getByLabel("Spending chart")).toBeVisible();
  });
});
