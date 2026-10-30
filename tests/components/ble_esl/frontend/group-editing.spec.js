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
    .fill("90");
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => e.rotation || 0),
    ),
  ).toEqual([90, 90, 0]);
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
  // Field names are the YAML keys, capitalised like in the single-element panel.
  await expect(
    page.locator('label:has([data-property="spec.size"])'),
  ).toHaveText(/^Size/);
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

test("keyboard moves of a group stay on the label and repeated nudges are one undo step", async ({
  page,
}) => {
  const hit = page.locator(".el .hit-area");
  await hit.nth(0).click();
  await hit.nth(1).click({ modifiers: ["Shift"] });
  await page.getByRole("group", { name: "Display canvas" }).focus();
  const xs = () =>
    page.evaluate(() => window.panel.document.elements.map((e) => e.x));
  const undoDepth = () => page.evaluate(() => window.panel.undoStack.length);
  // Three quick nudges right: one undo step.
  const before = await undoDepth();
  for (let i = 0; i < 3; i++) await page.keyboard.press("ArrowRight");
  expect(await xs()).toEqual([13, 58, 150]);
  expect(await undoDepth()).toBe(before + 1);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  expect(await xs()).toEqual([10, 55, 150]);
  // Far past the left edge: the group stops with its leftmost frame at 0, and
  // a key that cannot move anything leaves no undo step.
  await page.getByRole("group", { name: "Display canvas" }).focus();
  for (let i = 0; i < 4; i++) await page.keyboard.press("Shift+ArrowLeft");
  expect(await xs()).toEqual([0, 45, 150]);
  const depth = await undoDepth();
  // Outside the merge window, so only the clamp can explain "no new step".
  await page.evaluate(() => (window.panel._nudgeAt = 0));
  await page.keyboard.press("ArrowLeft");
  expect(await xs()).toEqual([0, 45, 150]);
  expect(await undoDepth()).toBe(depth);
});

test("dragging a group far past the label edge stops it at the edge", async ({
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
    hit.x + hit.width / 2 - 300 * zoom,
    hit.y + hit.height / 2 - 200 * zoom,
    { steps: 8 },
  );
  await page.mouse.up();
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => [e.x, e.y]),
    ),
  ).toEqual([
    [0, 0],
    [45, 0],
    [150, 65],
  ]);
});

test("a nudge after an undo or on another selection starts its own undo step", async ({
  page,
}) => {
  const hit = page.locator(".el .hit-area");
  const ys = () =>
    page.evaluate(() => window.panel.document.elements.map((e) => e.y));
  const canvas = page.getByRole("group", { name: "Display canvas" });
  await hit.nth(0).click();
  await canvas.focus();
  await page.keyboard.press("ArrowDown");
  // Another element right away: not merged into the first one's step.
  await hit.nth(1).click();
  await canvas.focus();
  await page.keyboard.press("ArrowDown");
  expect(await ys()).toEqual([11, 11, 65]);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  expect(await ys()).toEqual([11, 10, 65]);
  // After nudge -> other edit -> undo, the nudge step is on top again and a
  // redo is pending: a new nudge must be a new step that clears the redo.
  await canvas.focus();
  await page.keyboard.press("ArrowDown");
  await page.evaluate(() => {
    window.panel.checkpoint();
    window.panel.element.width = 31;
    window.panel.edited();
  });
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  expect(await page.evaluate(() => window.panel.session.redoStack.length)).toBe(
    1,
  );
  const depth = await page.evaluate(() => window.panel.undoStack.length);
  await page.evaluate(() => (window.panel._nudgeAt = Date.now()));
  await canvas.focus();
  await page.keyboard.press("ArrowDown");
  expect(await page.evaluate(() => window.panel.session.redoStack.length)).toBe(
    0,
  );
  expect(await page.evaluate(() => window.panel.undoStack.length)).toBe(
    depth + 1,
  );
});
