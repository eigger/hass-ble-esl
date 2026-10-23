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
  await page
    .getByRole("slider", { name: "Rotate (°)", exact: true })
    .fill("90");
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

test("rotation slider and numeric box update each other live at arbitrary angles", async ({
  page,
}) => {
  const slider = page.getByRole("slider", { name: "Rotate (°)", exact: true });
  const number = page.getByRole("spinbutton", {
    name: "Rotation value (°)",
    exact: true,
  });
  await expect(slider).toBeVisible();
  await slider.fill("37.5");
  await expect(number).toHaveValue("37.5");
  expect(await page.evaluate(() => window.panel.element.rotation)).toBe(37.5);
  await number.fill("123");
  await expect(slider).toHaveValue("123");
  expect(await page.evaluate(() => window.panel.element.rotation)).toBe(123);
});

test("editor toolbar uses HA material icons, including refresh", async ({
  page,
}) => {
  await expect(page.locator('[data-action="reload"] ha-icon')).toHaveAttribute(
    "icon",
    "mdi:refresh",
  );
  await expect(page.locator(".toolbar svg")).toHaveCount(0);
  await expect(page.locator('[data-action="show-hidden-icons"]')).toContainText(
    "Show hidden icons",
  );
});

test("configure modal keeps rotation slider and numeric value in sync", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Configure", exact: true }).click();
  const modal = page.locator("ble-esl-component-editor");
  await modal
    .getByRole("slider", { name: "Rotate (°)", exact: true })
    .fill("42.5");
  await expect(
    modal.getByRole("spinbutton", { name: "Rotation value (°)", exact: true }),
  ).toHaveValue("42.5");
  expect(await modal.evaluate((m) => m.draft.rotation)).toBe(42.5);
  await modal
    .getByRole("spinbutton", { name: "Rotation value (°)", exact: true })
    .fill("73");
  await expect(
    modal.getByRole("slider", { name: "Rotate (°)", exact: true }),
  ).toHaveValue("73");
});

test("tag orientation changes the canvas without discarding the current design", async ({
  page,
}) => {
  const before = await page.evaluate(() =>
    JSON.stringify(window.panel.document),
  );
  const dimensions = await page.evaluate(() => [
    window.panel.tag.width,
    window.panel.tag.height,
  ]);
  await page.route("**/api/designer", async (route) => {
    if (route.request().postDataJSON().action === "orientation")
      return route.fulfill({
        json: { rotation: 90, width: dimensions[1], height: dimensions[0] },
      });
    return route.continue();
  });
  await page.getByRole("button", { name: "Portrait", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Portrait", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    await page.evaluate(() => [
      window.panel.tag.width,
      window.panel.tag.height,
    ]),
  ).toEqual(dimensions.toReversed());
  expect(await page.evaluate(() => JSON.stringify(window.panel.document))).toBe(
    before,
  );
});

test("square tags have no portrait or landscape controls", async ({ page }) => {
  await page.evaluate(() => {
    window.panel.tag.width = 200;
    window.panel.tag.height = 200;
    window.panel.render();
  });
  await expect(
    page.getByRole("button", { name: "Portrait", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Landscape", exact: true }),
  ).toHaveCount(0);
});
