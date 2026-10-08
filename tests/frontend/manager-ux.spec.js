import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page, request }) => {
  await request.post("/reset");
  await page.goto("/?manager");
  await expect(page.locator(".card")).toHaveCount(2);
  await expect(
    page.locator(
      '[data-entry="demo-writable"] [data-action="edit-automation"]',
    ),
  ).toBeVisible();
});

test("cards label read-only devices and frame the complete last successful image", async ({
  page,
}) => {
  const card = page.locator('.card[data-entry="demo-discovery"]');
  await expect(card.getByText("Read only", { exact: true })).toBeVisible();
  await expect(card.locator(".image-caption")).toHaveText(
    "Last successful image",
  );
  await expect
    .poll(() => card.locator("img").evaluate((img) => img.naturalWidth))
    .toBeGreaterThan(0);
  const frame = await card.locator(".image").boundingBox();
  const image = await card.locator("img").boundingBox();
  expect(image.x - frame.x).toBeGreaterThanOrEqual(9);
  expect(image.y - frame.y).toBeGreaterThanOrEqual(9);
  expect(frame.x + frame.width - image.x - image.width).toBeGreaterThanOrEqual(
    9,
  );
  expect(
    frame.y + frame.height - image.y - image.height,
  ).toBeGreaterThanOrEqual(9);
  await page.screenshot({
    path: "artifacts/manager-ux-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "artifacts/manager-ux-mobile.png",
    fullPage: true,
  });
  await page.evaluate(() => {
    const manager = window.manager;
    const id = manager.tags[1].entities.last_updated_content;
    manager.hass = {
      ...manager.hass,
      states: {
        ...manager.hass.states,
        [id]: { ...manager.hass.states[id], state: "unavailable" },
      },
    };
  });
  await expect(card.locator(".image-caption")).toBeEmpty();
  await expect(
    card.getByText("No successful image", { exact: true }),
  ).toBeVisible();
});

test("one linked automation opens directly and names its save destination", async ({
  page,
}) => {
  await page.evaluate(() => {
    const manager = window.manager;
    const data = manager.automationCache.get("demo-writable");
    manager.automationCache.set("demo-writable", {
      ...data,
      linked: [data.linked[0]],
    });
    manager.renderCards();
  });
  await page
    .locator('.card[data-entry="demo-writable"]')
    .getByRole("button", { name: "Edit automation design", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".editor-context")).toHaveText(
    "Living room › Morning information › Automation design",
  );
  await expect(page.locator(".message")).toHaveClass(/info/);
  await expect(page.locator(".message")).toHaveAttribute("role", "status");
  expect(await page.evaluate(() => window.manager.editor.dirty)).toBe(false);
  await page.getByRole("button", { name: "← Dashboard", exact: true }).click();
  await page
    .locator('.card[data-entry="demo-writable"]')
    .getByRole("button", { name: "Edit design", exact: true })
    .click();
  await expect(page.locator(".editor-context")).toHaveText(
    "Living room › Local design",
  );
  await expect(
    page.getByRole("button", { name: "Save to automation", exact: true }),
  ).toHaveCount(0);
});

test("editor context follows template mode and the selected tag", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator(".editor-context")).toHaveText(
    "Living room › Local design",
  );
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  await expect(page.locator(".editor-context")).toHaveText(
    "Living room › Sensor templates",
  );
  await page.getByRole("button", { name: "Display", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Tag", exact: true })
    .selectOption("demo-discovery");
  await expect(page.locator(".editor-context")).toHaveText(
    "Desk display › Local design",
  );
});

test("multiple automations open a choice and stale cache errors never pick one", async ({
  page,
}) => {
  const card = page.locator('.card[data-entry="demo-writable"]');
  await card
    .getByRole("button", { name: "Edit automation design", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Edit design", exact: true }),
  ).toHaveCount(3);
  await dialog.getByRole("button", { name: "Close automations" }).click();
  await page.evaluate(() => {
    window.manager.automationErrors.add("demo-writable");
    window.manager.renderCards();
  });
  await expect(card.locator('[data-action="edit-automation"]')).toHaveCount(0);
  await expect(
    card.getByRole("button", { name: "Edit design", exact: true }),
  ).toBeVisible();
});

test("battery warnings follow device sensors and sorting preserves search and filters", async ({
  page,
}) => {
  await page.evaluate(() => {
    const manager = window.manager;
    const tag = manager.tags[0];
    const id = tag.entities.battery_low;
    manager.hass = {
      ...manager.hass,
      states: {
        ...manager.hass.states,
        [id]: { ...manager.hass.states[id], state: "on" },
      },
    };
  });
  await page.getByLabel("Sort ESLs").selectOption("attention");
  await expect(page.locator(".card").first()).toHaveAttribute(
    "data-entry",
    "demo-discovery",
  );
  await page.getByLabel("Filter ESLs").selectOption("low-battery");
  await expect(page.locator(".card")).toHaveCount(1);
  await expect(page.locator(".card")).toContainText("Living room");
  await page.getByLabel("Search ESLs").fill("living");
  await page.getByLabel("Sort ESLs").selectOption("battery");
  await expect(page.getByLabel("Search ESLs")).toHaveValue("living");
  await expect(page.getByLabel("Filter ESLs")).toHaveValue("low-battery");
  for (const state of ["off", "unknown", null]) {
    await page.evaluate((value) => {
      const manager = window.manager;
      const tag = manager.tags[0];
      const id = tag.entities.battery_low;
      const batteryId = tag.entities.battery;
      const states = {
        ...manager.hass.states,
        [batteryId]: { ...manager.hass.states[batteryId], state: "15" },
      };
      if (value === null) tag.entities.battery_low = null;
      else states[id] = { ...states[id], state: value };
      manager.hass = { ...manager.hass, states };
      manager.renderCards();
    }, state);
    await expect(page.locator(".card")).toHaveCount(0);
  }
});

test("message severity survives language changes", async ({ page }) => {
  await page.evaluate(() => {
    const manager = window.manager;
    manager.message("Automation saved.", "success");
    manager.hass = {
      ...manager.hass,
      locale: { ...manager.hass.locale, language: "ko" },
    };
  });
  await expect(page.locator(".message")).toHaveClass(/success/);
  await expect(page.locator(".message")).not.toHaveClass(/error/);
  await expect(page.locator(".message")).toHaveAttribute("role", "status");
  await expect(page.locator(".message")).toContainText(
    "자동화를 저장했습니다.",
  );
});

test("the scrollbar gutter is reserved and the drop-downs keep a fixed width", async ({
  page,
}) => {
  // Headless Chromium hides scrollbars, so the cause is checked, not the shift.
  await page.goto("/?manager");
  const filter = page.locator("#filter");
  await expect(filter).toBeVisible();
  const gutter = await page.evaluate(
    () =>
      getComputedStyle(
        window.manager.shadowRoot.querySelector(".dashboard-content"),
      ).scrollbarGutter,
  );
  expect(gutter).toBe("stable");
  const before = [
    await filter.boundingBox(),
    await page.locator("#sort").boundingBox(),
  ];
  for (const value of ["error", "unsynced", "low-battery", "all"]) {
    await filter.selectOption(value);
    expect([
      await filter.boundingBox(),
      await page.locator("#sort").boundingBox(),
    ]).toEqual(before);
  }
});

test("search box and drop-downs share one height and long translations fit", async ({
  page,
}) => {
  for (const lang of [
    "en",
    "ko",
    "de",
    "es",
    "fr",
    "it",
    "ja",
    "nl",
    "pl",
    "pt-BR",
    "ru",
    "zh-Hans",
    "zh-Hant",
  ]) {
    await page.goto(`/?manager&lang=${lang}`);
    await page.waitForFunction(() =>
      window.manager?.shadowRoot?.querySelector("#sort"),
    );
    const heights = await page.evaluate(() => {
      const root = window.manager.shadowRoot;
      return ["#search", "#filter", "#sort"].map((selector) =>
        Math.round(root.querySelector(selector).getBoundingClientRect().height),
      );
    });
    expect(heights, lang).toEqual([40, 40, 40]);
    const cut = await page.evaluate(() => {
      const root = window.manager.shadowRoot;
      return ["#filter", "#sort"].flatMap((selector) => {
        const select = root.querySelector(selector);
        const probe = document.createElement("span");
        probe.style.cssText = `position:absolute;visibility:hidden;white-space:nowrap;font:${getComputedStyle(select).font}`;
        document.body.append(probe);
        const limit = select.clientWidth - 40;
        const wide = [...select.options]
          .filter((option) => {
            probe.textContent = option.textContent;
            // 20% spare: CI fonts are wider than a developer machine's.
            return probe.getBoundingClientRect().width * 1.2 > limit;
          })
          .map((option) => option.textContent);
        probe.remove();
        return wide;
      });
    });
    expect(cut, lang).toEqual([]);
  }
});

test("the editor bar stays compact on a phone in long translations", async ({
  page,
}) => {
  await page.setViewportSize({ width: 400, height: 800 });
  for (const lang of ["en", "es", "ru", "de", "pl", "nl"]) {
    await page.goto(`/?manager&lang=${lang}`);
    await page.waitForFunction(() =>
      window.manager?.shadowRoot?.querySelector("[data-action=edit]"),
    );
    await page
      .locator('[data-entry="demo-writable"] [data-action="edit"]')
      .click();
    await page.waitForFunction(() =>
      window.manager.shadowRoot.querySelector(".editor-nav"),
    );
    const height = await page.evaluate(() =>
      Math.round(
        window.manager.shadowRoot
          .querySelector(".editor-nav")
          .getBoundingClientRect().height,
      ),
    );
    expect(height, lang).toBeLessThan(150);
  }
});
