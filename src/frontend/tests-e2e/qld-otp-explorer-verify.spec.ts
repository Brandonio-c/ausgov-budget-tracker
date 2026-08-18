import { test, expect } from "@playwright/test";

// Verifies item 7.5's dedicated QLD on-time-payments explorer (a bespoke
// multi-measure-type page, not the generic registry shell - see
// src/backend/routers/v2/qld_otp.py's module docstring for why this
// source doesn't fit the single-compatibility-group registry pattern).

test("QLD OTP explorer loads with a real agency breakdown and never reports a total for a percentage measure", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/ausgov-budget-tracker/explorers/qld-otp/");
  await page.waitForLoadState("networkidle");

  await expect(page.getByRole("heading", { name: /QLD on-time payments/ })).toBeVisible();
  await expect(page.getByText(/agencies reported for/)).toBeVisible();

  // Switch to a percentage measure and confirm no total is shown.
  await page.getByLabel("Measure").selectOption({ label: "QLD on-time payment: % late payments to small business" });
  await page.waitForTimeout(800);
  const summary = await page.getByText(/agencies reported for/).innerText();
  expect(summary).not.toMatch(/total/i);
  await expect(page.getByText(/no total is reported/i)).toBeVisible();

  expect(errors, `console errors: ${JSON.stringify(errors)}`).toEqual([]);
});

test("agency breakdown is truthful, sorted descending, and clicking a row shows a real citation", async ({ page }) => {
  await page.goto("/ausgov-budget-tracker/explorers/qld-otp/");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Financial year").selectOption("2020-21");
  await page.waitForTimeout(300);
  await page.getByLabel("Quarter").selectOption("1");
  await page.waitForTimeout(800);

  await expect(page.getByText(/12 agencies reported for 2020-21 Q1/)).toBeVisible();

  const rows = page.locator("li button");
  const count = await rows.count();
  expect(count).toBeGreaterThan(1);

  const values: number[] = [];
  for (let i = 0; i < count; i++) {
    const text = await rows.nth(i).innerText();
    const match = text.match(/(-?\d[\d,]*)\s*count/);
    if (match) values.push(Number(match[1].replace(/,/g, "")));
  }
  const sorted = [...values].sort((a, b) => b - a);
  expect(values).toEqual(sorted);

  await rows.first().click();
  await expect(page.getByText("Source citation")).toBeVisible();
  await expect(page.getByText(/qld_on_time_payment_reports/).first()).toBeVisible();
});
