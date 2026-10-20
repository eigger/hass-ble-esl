import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.waitForFunction(() => window.panel?.tag);
  await page.evaluate(() => {
    window.panel.document = { version: 1, elements: [], background: "white" };
    window.panel.add("icon");
    Object.assign(window.panel.element, {
      icon: "mdi:washing-machine",
      x: 50,
      y: 30,
      width: 50,
      height: 30,
    });
    window.panel.edited();
  });
});

test("element rotation requires no conversion and supports undo", async ({
  page,
}) => {
  const before = await page.evaluate(() => ({
    id: window.panel.element.id,
    type: window.panel.element.type,
  }));
  await page.getByLabel("Rotate (°)", { exact: true }).selectOption("90");
  await page.waitForFunction(
    () => !!window.panel.layerBounds?.[window.panel.selected],
  );
  expect(
    await page.evaluate(() => ({
      id: window.panel.element.id,
      type: window.panel.element.type,
      rotation: window.panel.element.rotation,
    })),
  ).toEqual({ ...before, rotation: 90 });
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  expect(
    await page.evaluate(() => window.panel.document.elements[0].rotation || 0),
  ).toBe(0);
});

test("show hidden icons reveals editable ghosts without changing the design or output", async ({
  page,
}) => {
  await page.evaluate(() => {
    const p = window.panel;
    p.element.visible = false;
    p.edited();
  });
  await page.waitForFunction(
    () => !!window.panel.layerPreviews._ghosts?.[window.panel.selected],
  );
  const before = await page.evaluate(() => {
    window.panel.dirty = false;
    window.panel.render();
    return {
      doc: JSON.stringify(window.panel.document),
      png: window.panel.preview,
    };
  });
  const toggle = page.getByRole("button", {
    name: "Show hidden icons",
    exact: true,
  });
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".el.ghost .layer-preview")).toBeVisible();
  await expect(page.locator(".el.ghost .hit-area")).toBeVisible();
  expect(
    await page.evaluate(() => ({
      doc: JSON.stringify(window.panel.document),
      png: window.panel.preview,
    })),
  ).toEqual(before);
  expect(await page.evaluate(() => window.panel.dirty)).toBe(false);
  await toggle.click();
  await expect(page.locator(".el.ghost")).toHaveCount(0);
});
