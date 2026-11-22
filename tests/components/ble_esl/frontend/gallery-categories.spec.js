import { test, expect } from "@playwright/test";

test("filters real categories, retains browsing context and requests visible thumbnails only", async ({
  page,
}) => {
  const requests = [];
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  await page.route("**/api/designer", async (route) => {
    const data = route.request().postDataJSON();
    if (data.action === "preview_design_template") {
      requests.push(data.template_id);
      if (requests.length === 1) await gate;
    }
    await route.continue();
  });
  try {
    await page.request.post("/reset");
    await page.goto("/");
    await page.waitForFunction(() => window.panel?.tag);
    await page.getByRole("button", { name: "Browse design gallery" }).click();
    const gallery = page.locator("ble-esl-template-dialog");
    await expect(gallery.locator("[data-template]")).toHaveCount(19);
    await expect.poll(() => requests.length).toBe(1);
    await gallery.getByRole("button", { name: "Weather", exact: true }).click();
    await expect(
      gallery.locator('[data-template="calendar_weather"]'),
    ).toHaveCount(1);
    await expect(gallery.locator('[data-template="date_weather"]')).toHaveCount(
      1,
    );
    await expect(gallery.locator('[data-template="wifi"]')).toHaveCount(0);
    await gallery
      .getByRole("button", { name: "Schedule", exact: true })
      .click();
    await expect(
      gallery.locator('[data-template="calendar_weather"]'),
    ).toHaveCount(1);
    await expect(gallery.locator('[data-template="date_weather"]')).toHaveCount(
      1,
    );
    await gallery.locator('[data-template="date_weather"]').click();
    release();
    await expect(gallery.locator("[data-form-preview]")).toBeVisible();
    await gallery.getByRole("button", { name: "Back" }).click();
    await expect(
      gallery.getByRole("button", { name: "Schedule", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    await expect(
      gallery.locator('[data-template="date_weather"]'),
    ).toBeFocused();
    await gallery.getByRole("button", { name: "Cancel" }).click();
  } finally {
    release();
  }
});

test("scrolling requests only visible cards, and closing stops the queue", async ({
  page,
}) => {
  await page.request.post("/reset");
  const requests = [];
  let release;
  let hold = false;
  const gate = new Promise((resolve) => (release = resolve));
  await page.route("**/api/designer", async (route) => {
    const data = route.request().postDataJSON();
    if (data.action === "preview_design_template") {
      requests.push(data.template_id);
      if (hold) await gate;
    }
    await route.continue().catch(() => {});
  });
  try {
    await page.goto("/");
    await page.waitForFunction(() => window.panel?.tag);
    await page.getByRole("button", { name: "Browse design gallery" }).click();
    const gallery = page.locator("ble-esl-template-dialog");
    await expect(gallery.locator("[data-template]")).toHaveCount(19);
    await expect.poll(() => requests.length).toBeGreaterThan(0);
    const last = await gallery
      .locator("[data-template]")
      .last()
      .getAttribute("data-template");
    await expect(gallery.locator("[data-preview][src]").first()).toBeVisible();
    expect(requests).not.toContain(last);
    const beforeScroll = requests.length;
    hold = true;
    await gallery.locator(".list").evaluate((node) => {
      node.scrollTop = node.scrollHeight;
    });
    await expect.poll(() => requests.length).toBeGreaterThan(beforeScroll);
    const count = requests.length;
    await gallery.getByRole("button", { name: "Cancel" }).click();
    release();
    await expect(gallery).toHaveCount(0);
    await page.waitForTimeout(200);
    expect(requests.length).toBe(count);
  } finally {
    release();
  }
});

test("an empty template response has no filters to activate", async ({
  page,
}) => {
  await page.route("**/api/designer", async (route) => {
    if (route.request().postDataJSON().action === "design_templates")
      await route.fulfill({ json: [] });
    else await route.continue();
  });
  await page.goto("/");
  await page.waitForFunction(() => window.panel?.tag);
  await page.getByRole("button", { name: "Browse design gallery" }).click();
  const gallery = page.locator("ble-esl-template-dialog");
  await expect(
    gallery.getByText("No design templates fit this display."),
  ).toBeVisible();
  await expect(gallery.locator("[data-category]")).toHaveCount(0);
  await gallery.getByRole("button", { name: "Cancel" }).click();
});

for (const width of [320, 421, 500])
  test(`a ${width}px short gallery keeps cards usable with a design to save`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 350 });
    await page.goto("/");
    await page.waitForFunction(() => window.panel?.tag);
    await page.locator('[data-add="text"]').click();
    await page.getByRole("button", { name: "Browse design gallery" }).click();
    const gallery = page.locator("ble-esl-template-dialog");
    const viewport = gallery.locator(".gallery-content");
    const card = gallery.locator("[data-template]").first();
    await expect(card).toBeInViewport();
    expect(
      await viewport.evaluate((node) => node.clientHeight),
    ).toBeGreaterThan(100);
    await expect(gallery.locator("[data-preview][src]").first()).toBeVisible();
    await gallery.getByRole("button", { name: "Weather", exact: true }).click();
    await expect(gallery.locator('[data-template="date_weather"]')).toHaveCount(
      1,
    );
    await gallery.locator('[data-template="date_weather"]').click();
    await expect(gallery.getByRole("button", { name: "Back" })).toBeVisible();
  });
