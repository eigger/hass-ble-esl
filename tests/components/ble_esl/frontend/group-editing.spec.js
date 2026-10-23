import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.waitForFunction(() => window.panel?.tag);
  await page.evaluate(() => {
    const p = window.panel;
    p.document = { version: 1, elements: [], background: "white" };
    for (const [x, y] of [
      [10, 10],
      [55, 10],
      [150, 65],
    ]) {
      p.add("rectangle");
      Object.assign(p.element, { x, y, width: 25, height: 25, color: "black" });
    }
    p.selected = null;
    p.edited();
  });
  await expect(page.locator(".el")).toHaveCount(3);
});

test("shift selection shares properties and keyboard movement with one undo", async ({
  page,
}) => {
  const hit = page.locator(".el .hit-area");
  await hit.nth(0).click();
  await hit.nth(1).click({ modifiers: ["Shift"] });
  await expect(page.locator(".el.selected")).toHaveCount(2);
  await page.getByRole("spinbutton", { name: "Width", exact: true }).fill("35");
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => e.width),
    ),
  ).toEqual([35, 35, 25]);
  await page.locator("[data-pick=color][data-value=red]").click();
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => e.color),
    ),
  ).toEqual(["red", "red", "black"]);
  await page
    .getByRole("spinbutton", { name: "Rotation value (°)", exact: true })
    .fill("33.3");
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => e.rotation || 0),
    ),
  ).toEqual([33.3, 33.3, 0]);
  await page.getByRole("group", { name: "Display canvas" }).focus();
  await page.keyboard.press("ArrowDown");
  expect(
    await page.evaluate(() => window.panel.document.elements.map((e) => e.y)),
  ).toEqual([11, 11, 65]);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  expect(
    await page.evaluate(() => window.panel.document.elements.map((e) => e.y)),
  ).toEqual([10, 10, 65]);
});

test("marquee selection and drag move the selected components together", async ({
  page,
}) => {
  const stage = page.getByRole("group", { name: "Display canvas" });
  const b = await stage.boundingBox();
  const zoom = await page.evaluate(() => window.panel.zoom);
  await page.mouse.move(b.x + 2 * zoom, b.y + 2 * zoom);
  await page.mouse.down();
  await page.mouse.move(b.x + 100 * zoom, b.y + 45 * zoom, { steps: 8 });
  await page.mouse.up();
  await expect(page.locator(".el.selected")).toHaveCount(2);
  const hit = await page
    .locator(".el.selected .hit-area")
    .first()
    .boundingBox();
  await page.mouse.move(hit.x + hit.width / 2, hit.y + hit.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    hit.x + hit.width / 2 + 20 * zoom,
    hit.y + hit.height / 2 + 10 * zoom,
    { steps: 8 },
  );
  await page.mouse.up();
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => [e.x, e.y]),
    ),
  ).toEqual([
    [30, 20],
    [75, 20],
    [150, 65],
  ]);
});

test("group deletion and duplicate preserve undo and component configurations", async ({
  page,
}) => {
  await page.evaluate(() => {
    window.panel.selectIds(
      window.panel.document.elements.slice(0, 2).map((e) => e.id),
    );
    window.panel.render();
  });
  await page.getByRole("button", { name: "Duplicate", exact: true }).click();
  await expect(page.locator(".el")).toHaveCount(5);
  await expect(page.locator(".el.selected")).toHaveCount(2);
  await page.getByRole("group", { name: "Display canvas" }).focus();
  await page.keyboard.press("Backspace");
  await expect(page.locator(".el")).toHaveCount(3);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(page.locator(".el")).toHaveCount(5);
});

test("native elements share compatible spec properties", async ({ page }) => {
  await page.evaluate(() => {
    const p = window.panel;
    p.document = { version: 1, background: "white", elements: [] };
    p.addSpec("text");
    p.addSpec("text");
    p.selectIds(p.document.elements.map((e) => e.id));
    p.render();
  });
  await page.locator('[data-property="spec.size"]').fill("32");
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => e.spec.size),
    ),
  ).toEqual([32, 32]);
  await page.locator("[data-pick=color][data-value=red]").click();
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => e.spec.color),
    ),
  ).toEqual(["red", "red"]);
});
