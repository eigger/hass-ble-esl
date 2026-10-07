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

test("multiple automations show count, state, editor links and manual association controls", async ({
  page,
}) => {
  const card = page.locator('[data-entry="demo-writable"]').first();
  await expect(card).toContainText("3 automations · 2 active");
  await card.locator('[data-action="automations"]').click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(".row")).toHaveCount(3);
  await expect(
    dialog.getByRole("link", { name: "Night screen" }),
  ).toHaveAttribute("href", "/config/automation/edit/night");
  await expect(dialog).toContainText("Inactive");
  const mutation = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request.postDataJSON()?.action === "link_automation",
  );
  await dialog
    .getByLabel("Existing automation")
    .selectOption("automation.weekly");
  await dialog
    .getByRole("button", { name: "Link automation", exact: true })
    .click();
  expect((await mutation).postDataJSON()).toEqual({
    type: "ble_esl/designer",
    action: "link_automation",
    entry_id: "demo-writable",
    entity_id: "automation.weekly",
  });
  await expect(dialog.locator(".row")).toHaveCount(4);
  await dialog
    .getByRole("button", { name: "Unlink Weekly summary", exact: true })
    .click();
  await expect(dialog.locator(".row")).toHaveCount(3);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(card).toContainText("3 automations · 2 active");
  await card.getByRole("button", { name: "Edit design" }).click();
  await page
    .getByRole("button", { name: "Connected automations", exact: true })
    .click();
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(".row")).toHaveCount(3);
});

test("zero and one automation summaries and mobile bottom sheet", async ({
  page,
}) => {
  const card = page.locator('[data-entry="demo-discovery"]').first();
  await expect(card).toContainText("Link automation");
  await page.setViewportSize({ width: 390, height: 844 });
  await card.locator('[data-action="automations"]').click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await expect(dialog).toContainText("No connected automations");
  await dialog.getByLabel("Search automations").fill("Night");
  await dialog
    .getByLabel("Existing automation")
    .selectOption("automation.night");
  await dialog
    .getByRole("button", { name: "Link automation", exact: true })
    .click();
  await expect(dialog.locator(".row")).toHaveCount(1);
  await page.screenshot({
    path: "artifacts/manager-automations-mobile.png",
  });
  const box = await dialog.boundingBox();
  expect(Math.abs(box.y + box.height - 844)).toBeLessThan(2);
  await dialog.getByRole("button", { name: "Close automations" }).click();
  await expect(card).toContainText("Night screen · Inactive");
});

test("detected associations have no unlink control and missing associations have no unsafe edit link", async ({
  page,
}) => {
  await page.evaluate(() => {
    const manager = window.manager;
    const callWS = manager.hass.callWS;
    manager.hass = {
      ...manager.hass,
      callWS: async (msg) =>
        msg.action === "automations"
          ? {
              linked: [
                {
                  entity_id: "automation.morning",
                  name: "Morning information",
                  state: "on",
                  id: "morning",
                  source: "detected",
                  missing: false,
                },
                {
                  entity_id: "automation.weekly",
                  name: "Deleted automation",
                  state: "unavailable",
                  id: "removed",
                  source: "manual",
                  missing: true,
                  link_id: "removed-registry-id",
                },
              ],
              available: [],
            }
          : callWS(msg),
    };
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await expect(dialog).toContainText("References this ESL");
  await expect(
    dialog.getByRole("button", { name: "Unlink Morning information" }),
  ).toHaveCount(0);
  await expect(
    dialog.getByRole("link", { name: "Deleted automation" }),
  ).toHaveCount(0);
  await expect(
    dialog.getByRole("button", { name: "Unlink Deleted automation" }),
  ).toBeEnabled();
});

test("automation dialog preserves keyboard focus across unrelated and relevant HA updates", async ({
  page,
}) => {
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  const unlink = dialog.getByRole("button", {
    name: "Unlink Night screen",
    exact: true,
  });
  await unlink.focus();
  await page.evaluate(() => {
    const manager = window.manager;
    manager.hass = { ...manager.hass, states: { ...manager.hass.states } };
  });
  await expect(unlink).toBeFocused();
  await page.evaluate(() => {
    const manager = window.manager;
    manager.hass = {
      ...manager.hass,
      states: {
        ...manager.hass.states,
        "automation.night": {
          ...manager.hass.states["automation.night"],
          state: "on",
        },
      },
    };
  });
  await expect(unlink).toBeFocused();
  await expect(
    dialog.locator(".row").filter({ hasText: "Night screen" }),
  ).toContainText("Active");
});

test("closing a pending link and opening another ESL keeps the result associated with original ESL", async ({
  page,
}) => {
  await page.evaluate(() => {
    const manager = window.manager;
    const callWS = manager.hass.callWS;
    manager.hass = {
      ...manager.hass,
      callWS: async (msg) => {
        if (msg.action !== "link_automation") return callWS(msg);
        const result = await callWS(msg);
        return new Promise(
          (resolve) => (window.releaseLink = () => resolve(result)),
        );
      },
    };
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByLabel("Existing automation")
    .selectOption("automation.weekly");
  await dialog
    .getByRole("button", { name: "Link automation", exact: true })
    .click();
  await page.waitForFunction(() => window.releaseLink);
  await dialog.getByRole("button", { name: "Close automations" }).click();
  await page
    .locator('[data-action="automations"][data-entry="demo-discovery"]')
    .click();
  await expect(dialog).toContainText("No connected automations");
  await page.evaluate(() => window.releaseLink());
  await expect(dialog.locator(".row")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Close automations" }).click();
  await expect(
    page.locator('[data-entry="demo-writable"]').first(),
  ).toContainText("4 automations · 2 active");
  await expect(
    page.locator('[data-entry="demo-discovery"]').first(),
  ).toContainText("Link automation");
});

test("successful image timestamp changes reload the thumbnail at the same proxy URL", async ({
  page,
}) => {
  const card = page.locator('[data-entry="demo-writable"]').first();
  const before = await card.locator("img").getAttribute("src");
  await page.evaluate(() => {
    const manager = window.manager;
    const image = manager.hass.states["image.demo_0_last_updated_content"];
    manager.hass = {
      ...manager.hass,
      states: {
        ...manager.hass.states,
        [image.entity_id]: { ...image, state: "2026-10-08T01:23:45+00:00" },
      },
    };
  });
  await expect(card.locator("img")).not.toHaveAttribute("src", before);
  await expect(card.locator("img")).toHaveAttribute(
    "src",
    /updated=2026-10-08T01%3A23%3A45%2B00%3A00/,
  );
});

test("manager headers and embedded designer toolbar remain visible in real scrolling containers", async ({
  page,
}) => {
  // Exercise navigation while list requests are slow: click() returns before
  // the async dashboard refresh has finished replacing the cards.
  await page.route("**/api/designer", async (route) => {
    if (route.request().postDataJSON()?.action === "list")
      await new Promise((resolve) => setTimeout(resolve, 150));
    await route.continue();
  });
  for (const [width, height] of [
    [1440, 477],
    [900, 477],
    [390, 844],
  ]) {
    await expect(
      page.getByRole("button", { name: "Refresh", exact: true }),
    ).toBeEnabled();
    await page.setViewportSize({ width, height });
    await page.evaluate(() => {
      const manager = window.manager;
      // Enough cards to overflow even in a wide, tall dashboard.
      manager.tags = Array.from({ length: 12 }, (_, index) => ({
        ...manager.tags[0],
        entry_id: `scroll-${index}`,
      }));
      manager.renderCards();
    });
    const before = await page
      .locator("ble-esl-manager")
      .evaluate(
        (host) =>
          host.shadowRoot.querySelector("header").getBoundingClientRect().top,
      );
    await page
      .locator(".dashboard-content")
      .evaluate((node) => (node.scrollTop = 500));
    expect(
      await page
        .locator(".dashboard-content")
        .evaluate((node) => node.scrollTop),
    ).toBeGreaterThan(0);
    expect(
      await page
        .locator("ble-esl-manager")
        .evaluate(
          (host) =>
            host.shadowRoot.querySelector("header").getBoundingClientRect().top,
        ),
    ).toBe(before);
    expect(await page.evaluate(() => document.scrollingElement.scrollTop)).toBe(
      0,
    );
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(page.locator("#dashboard .card")).toHaveCount(2);
    await page
      .locator('[data-action="edit"][data-entry="demo-writable"]')
      .click();
    await expect(
      page.getByRole("button", { name: "Send to tag", exact: true }),
    ).toBeVisible();
    await page
      .locator("ble-esl-designer")
      .evaluate((host) => (host.scrollTop = 500));
    await expect
      .poll(() =>
        page.locator("ble-esl-designer").evaluate((host) => {
          const root = host.shadowRoot;
          const header = root.querySelector("header").getBoundingClientRect();
          const toolbar = root
            .querySelector(".toolbar")
            .getBoundingClientRect();
          const nav = host
            .getRootNode()
            .querySelector(".editor-nav")
            .getBoundingClientRect();
          return [
            host.scrollTop > 0,
            Math.abs(header.top - nav.bottom) < 1,
            Math.abs(toolbar.top - header.bottom) < 1,
          ];
        }),
      )
      .toEqual([true, true, true]);
    expect(await page.evaluate(() => document.scrollingElement.scrollTop)).toBe(
      0,
    );
    if (width === 1440)
      await page.screenshot({ path: "artifacts/manager-fixed-header.png" });
    await page.locator('[data-action="dashboard"]').click();
    await expect(
      page.getByRole("button", { name: "Refresh", exact: true }),
    ).toBeEnabled();
    await expect(page.locator("#dashboard .card")).toHaveCount(2);
  }
});
