import { test, expect } from "@playwright/test";

/**
 * Deterministic verification of Loop 11's second-level legend: hovering a
 * ring-1 wedge must show "Inside {name}:" with that node's own children.
 *
 * Blind pixel/angle guessing against the sunburst canvas proved unreliable
 * (percentages in sunburstLevelStyles() don't map to screen pixels the way
 * a naive fittedRadius calculation assumes). Instead this test reads the
 * real rendered layout from the ECharts instance itself — exposed on the
 * chart container as `__echartsInstance` specifically for this purpose
 * (see SpendingChart.tsx) — to compute the exact pixel position of a named
 * data item, then drives a genuine mouse hover there so the real
 * onEvents.mouseover code path fires, not a synthetic dispatch.
 */
test("Second-level legend updates correctly when hovering a specific ring-1 wedge", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("http://127.0.0.1:3313/ausgov-budget-tracker/");
  await page.waitForTimeout(3000);

  const yearSelect = page.locator("select").first();
  await expect
    .poll(async () => (await yearSelect.locator("option").count()) > 0, { timeout: 15000 })
    .toBeTruthy();
  const optionLabels = await yearSelect.locator("option").allTextContents();
  const target = optionLabels.find((t) => t.includes("2025-26"));
  if (target) await yearSelect.selectOption({ label: target });

  const spendingSection = page.getByLabel("Spending chart");
  await expect(spendingSection.getByText("Loading…")).toHaveCount(0, { timeout: 15000 });

  const ringsButtons = page.getByRole("button", { name: "rings", exact: true });
  const count = await ringsButtons.count();
  for (let i = 0; i < count; i++) {
    const btn = ringsButtons.nth(i);
    const insideDebtWidget = await btn.evaluate(
      (el) => el.closest('[aria-label="Government debt"]') !== null,
    );
    if (!insideDebtWidget) {
      await btn.click();
      break;
    }
  }
  await expect(spendingSection.getByText("Loading…")).toHaveCount(0, { timeout: 15000 });

  const branchGroup = page.getByRole("group", { name: "Ring branch" });
  await branchGroup.getByRole("button", { name: /Budget Statement 6/ }).click();
  await expect(spendingSection.getByText("Loading…")).toHaveCount(0, { timeout: 15000 });
  await page.waitForTimeout(500);

  const plusButton = page.getByRole("button", { name: "More rings" }).first();
  if (await plusButton.isEnabled()) {
    await plusButton.click();
    await page.waitForTimeout(500);
  }

  const targetName = "Social security and welfare";
  const canvas = spendingSection.locator("canvas").first();
  await canvas.scrollIntoViewIfNeeded();
  const canvasBox = await canvas.boundingBox();
  if (!canvasBox) throw new Error("chart canvas not found");

  const pixel = await canvas.evaluate((canvasEl, name) => {
    const container = canvasEl.closest("[data-chart-panel]") as
      | (HTMLElement & { __echartsInstance?: unknown })
      | null;
    const instance = container?.__echartsInstance as
      | {
          getModel: () => {
            getSeriesByIndex: (i: number) => {
              getData: () => {
                count: () => number;
                getName: (i: number) => string;
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                getItemLayout: (i: number) => any;
              };
            };
          };
        }
      | undefined;
    if (!instance) return { error: "no echarts instance exposed" };
    const data = instance.getModel().getSeriesByIndex(0).getData();
    for (let i = 0; i < data.count(); i += 1) {
      if (data.getName(i) === name) {
        const layout = data.getItemLayout(i);
        if (!layout) continue;
        const midAngle = (layout.startAngle + layout.endAngle) / 2;
        const midRadius = (layout.r0 + layout.r) / 2;
        return {
          x: layout.cx + midRadius * Math.cos(midAngle),
          y: layout.cy - midRadius * Math.sin(midAngle),
          layout,
        };
      }
    }
    return { error: `"${name}" not found among ${data.count()} data items` };
  }, targetName);

  console.log("resolved pixel for target node:", pixel);
  if ("error" in pixel) throw new Error(String(pixel.error));

  // ECharts computes layout in the canvas's internal bitmap pixel space,
  // which need not match the canvas element's CSS box 1:1 in either axis —
  // convert per-axis before adding the CSS-space canvasBox offset.
  const bitmap = await canvas.evaluate((el: HTMLCanvasElement) => ({
    width: el.width,
    height: el.height,
  }));
  const scaleX = bitmap.width / canvasBox.width;
  const scaleY = bitmap.height / canvasBox.height;
  console.log("canvas bitmap:", bitmap, "canvasBox:", canvasBox, "scaleX/Y:", scaleX, scaleY);

  const targetPageX = canvasBox.x + pixel.x / scaleX;
  const targetPageY = canvasBox.y + pixel.y / scaleY;
  const elementAtPoint = await page.evaluate(
    ([x, y]) => {
      const el = document.elementFromPoint(x, y);
      return el ? { tag: el.tagName, id: el.id, cls: el.className } : null;
    },
    [targetPageX, targetPageY] as const,
  );
  console.log("target page coords:", targetPageX, targetPageY, "element at point:", elementAtPoint);

  await page.mouse.move(targetPageX, targetPageY, { steps: 3 });
  await page.waitForTimeout(500);

  await page.screenshot({ path: "/tmp/verify_secondlevel_deterministic.png", fullPage: true });

  const insideHeading = page.locator(`text="Inside ${targetName}:"`);
  await expect(insideHeading).toBeVisible({ timeout: 5000 });

  const secondLegend = page.getByLabel("Chart legend").nth(1);
  const secondLegendText = await secondLegend.innerText();
  console.log("second-level legend content:", secondLegendText);
  expect(secondLegendText).toContain("Assistance to the aged");

  console.log("console errors:", consoleErrors);
  expect(consoleErrors).toEqual([]);
});
