import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page, request }) => {
  await request.post("/reset");
  await page.goto("/?manager");
  await expect(page.locator(".card")).toHaveCount(2);
});

test("dashboard shows registry entities, filters and opens entity details", async ({
  page,
}) => {
  await expect(
    page.getByRole("heading", { name: "ESL Manager" }),
  ).toBeVisible();
  const card = page.locator('[data-entry="demo-writable"]').first();
  await expect(card).toContainText("Living room");
  await expect(card).toContainText("250 × 122");
  await expect(card).toContainText("Battery 85%");
  await expect(card).toContainText("In sync");
  await expect(card).toContainText("3.2 s");
  await expect(card.locator("img")).toBeVisible();
  await expect
    .poll(() => card.locator("img").evaluate((img) => img.naturalWidth))
    .toBeGreaterThan(0);
  await page.evaluate(() =>
    window.manager.addEventListener(
      "hass-more-info",
      (event) => (window.lastEntity = event.detail.entityId),
    ),
  );
  await card.getByRole("button", { name: "Living room", exact: true }).click();
  expect(await page.evaluate(() => window.lastEntity)).toBe(
    "text.demo_0_alias",
  );
  await page.getByLabel("Search ESLs").fill("desk");
  await expect(page.locator(".card")).toHaveCount(1);
  await expect(page.locator(".card")).toContainText("Transmission error");
  await page.getByLabel("Search ESLs").fill("");
  await page.getByLabel("Filter ESLs").selectOption("error");
  await expect(page.locator(".card")).toHaveCount(1);
  await page.getByLabel("Filter ESLs").selectOption("unsynced");
  await expect(page.locator(".card")).toHaveCount(1);
});

test("live entity values preserve successful image time and clear resolved errors", async ({
  page,
}) => {
  const card = page.locator('[data-entry="demo-discovery"]').first();
  const time = await card
    .locator('[data-entity="image.demo_1_last_updated_content"][title]')
    .getAttribute("title");
  await page.evaluate(() => {
    const manager = window.manager;
    manager.hass = {
      ...manager.hass,
      states: {
        ...manager.hass.states,
        "text.demo_1_alias": {
          entity_id: "text.demo_1_alias",
          state: "Kitchen",
          attributes: {},
        },
        "sensor.demo_1_write_duration": {
          entity_id: "sensor.demo_1_write_duration",
          state: "1.9",
          attributes: { success: true },
        },
      },
    };
  });
  await expect(card).toContainText("Kitchen");
  await expect(card).toContainText("No error");
  await expect(card).not.toContainText("Transmission error");
  await expect(card).toContainText("1.9 s");
  expect(
    await card
      .locator('[data-entity="image.demo_1_last_updated_content"][title]')
      .getAttribute("title"),
  ).toBe(time);
});

test("dashboard navigation preserves unsaved design and undo history", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(
    page.getByRole("button", { name: "Add text", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Undo", exact: false }),
  ).toBeEnabled();
  await expect(page.locator("#auto")).toHaveCount(0);
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  await expect(page.locator(".el")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("dashboard is responsive and handles missing states", async ({ page }) => {
  await page.screenshot({
    path: "artifacts/manager-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "artifacts/manager-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.evaluate(() => {
    window.manager.hass = { ...window.manager.hass, states: {} };
  });
  await expect(page.locator(".card").first()).toContainText("Battery —");
  await expect(page.locator(".card").first()).toContainText("Sync unknown");
  await expect(page.locator(".card").first()).toContainText(
    "No successful image",
  );
});

test("card navigation leaves template mode and retains template drafts", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  await page.getByLabel("Template name").fill("My template draft");
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="edit"][data-entry="demo-discovery"]')
    .click();
  await expect(page.getByLabel("Tag", { exact: true })).toHaveValue(
    "demo-discovery",
  );
  await expect(
    page.getByRole("button", { name: "Display", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: "Send to tag", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  await expect(page.getByLabel("Template name")).toHaveValue(
    "My template draft",
  );
});

test("choosing another card during editor boot honors latest selection", async ({
  page,
}) => {
  await page.route("**/frontend/icons.json", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 800));
    await route.continue();
  });
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="edit"][data-entry="demo-discovery"]')
    .click();
  await expect(page.getByLabel("Tag", { exact: true })).toHaveValue(
    "demo-discovery",
  );
  await expect(
    page.getByRole("button", { name: "Send to tag", exact: true }),
  ).toBeDisabled();
});
