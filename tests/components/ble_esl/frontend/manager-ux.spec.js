import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page, request }) => {
  await request.post("/reset");
  await page.goto("/?manager");
  await expect(page.locator(".card")).toHaveCount(2);
  await expect(
    page.locator('[data-entry="demo-writable"] [data-action="automations"]'),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          window.manager.automationCache.get("demo-writable")?.linked.length,
      ),
    )
    .toBeGreaterThan(0);
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

test("one linked automation opens from the connected list and names its save destination", async ({
  page,
}) => {
  const card = page.locator('.card[data-entry="demo-writable"]');
  await page.evaluate(() => {
    const manager = window.manager;
    const data = manager.automationCache.get("demo-writable");
    const callWS = manager.hass.callWS;
    manager.hass = {
      ...manager.hass,
      callWS: async (message) =>
        message.action === "automations"
          ? { ...data, linked: [data.linked[0]] }
          : callWS(message),
    };
    manager.automationCache.set("demo-writable", {
      ...data,
      linked: [data.linked[0]],
    });
    manager.renderCards();
  });
  await card.locator('[data-action="automations"]').click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
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
    .getByRole("button", { name: "Edit ESL design", exact: true })
    .click();
  await expect(page.locator(".editor-context")).toHaveText(
    "Living room › ESL design",
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
    "Living room › ESL design",
  );
  await page
    .getByRole("button", { name: "Sensor tile styles", exact: true })
    .click();
  await expect(page.locator(".editor-context")).toHaveText(
    "Living room › Sensor tile styles",
  );
  await page.getByRole("button", { name: "Display", exact: true }).click();
  await page
    .getByRole("combobox", { name: "ESL", exact: true })
    .selectOption("demo-discovery");
  await expect(page.locator(".editor-context")).toHaveText(
    "Desk display › ESL design",
  );
});

test("multiple automations open as a list and stale cache errors never pick one", async ({
  page,
}) => {
  const card = page.locator('.card[data-entry="demo-writable"]');
  await card.locator('[data-action="automations"]').click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Edit automation design", exact: true }),
  ).toHaveCount(3);
  await dialog.getByRole("button", { name: "Close automations" }).click();
  await page.evaluate(() => {
    window.manager.automationErrors.add("demo-writable");
    window.manager.renderCards();
  });
  await expect(card.locator('[data-action="edit-automation"]')).toHaveCount(0);
  await expect(card.locator('[data-action="automations"]')).toBeVisible();
  await expect(
    card.getByRole("button", { name: "Edit ESL design", exact: true }),
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
    // A select is as wide as its longest option whatever is selected, so
    // nothing is cut off and nothing moves when the choice changes.
    const before = await page.evaluate(() =>
      ["#filter", "#sort"].map((selector) => {
        const select = window.manager.shadowRoot.querySelector(selector);
        const box = select.getBoundingClientRect();
        return [selector, Math.round(box.x), Math.round(box.width)];
      }),
    );
    for (const selector of ["#filter", "#sort"]) {
      const count = await page.locator(`${selector} option`).count();
      for (let index = 0; index < count; index += 1) {
        await page.locator(selector).selectOption({ index });
        const after = await page.evaluate(() =>
          ["#filter", "#sort"].map((name) => {
            const select = window.manager.shadowRoot.querySelector(name);
            const box = select.getBoundingClientRect();
            return [name, Math.round(box.x), Math.round(box.width)];
          }),
        );
        expect(after, `${lang} ${selector} ${index}`).toEqual(before);
      }
    }
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
      window.manager.editor.querySelector(".editor-nav"),
    );
    const height = await page.evaluate(() =>
      Math.round(
        window.manager.editor
          .querySelector(".editor-nav")
          .getBoundingClientRect().height,
      ),
    );
    expect(height, lang).toBeLessThan(150);
  }
});

test("leaving an automation design with unsaved changes asks first", async ({
  page,
}) => {
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit automation design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  // Nothing changed yet: leaving asks nothing.
  const seen = [];
  const spy = (dialog) => {
    seen.push(dialog.message());
    dialog.dismiss();
  };
  page.on("dialog", spy);
  await page.locator('[data-action="dashboard"]').click();
  await expect(page.locator("#dashboard")).toBeVisible();
  page.off("dialog", spy);
  expect(seen).toEqual([]);
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit automation design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const messages = [];
  page.once("dialog", (dialog) => {
    messages.push(dialog.message());
    dialog.dismiss();
  });
  await page.locator('[data-action="dashboard"]').click();
  expect(messages).toEqual([
    "Discard the unsaved changes to this automation design?",
  ]);
  await expect(page.locator("#editor")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator('[data-action="dashboard"]').click();
  await expect(page.locator("#dashboard")).toBeVisible();
});

test("importing JSON over unsaved work and unlinking an automation ask first", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  const clean = JSON.stringify(
    await page.evaluate(() => window.manager.editor.document),
  );
  const file = {
    name: "design.json",
    mimeType: "application/json",
    buffer: Buffer.from(clean),
  };
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const before = await page.evaluate(
    () => window.manager.editor.document.elements.length,
  );
  const messages = [];
  page.once("dialog", (dialog) => {
    messages.push(dialog.message());
    dialog.dismiss();
  });
  await page.locator("#file").setInputFiles(file);
  await expect.poll(() => messages.length).toBe(1);
  expect(messages[0]).toContain("Replace the current design");
  await expect
    .poll(() => page.evaluate(() => window.manager.editor.busy))
    .toBe(false);
  expect(
    await page.evaluate(() => window.manager.editor.document.elements.length),
  ).toBe(before);
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  const unlink = dialog.getByRole("button", { name: /^Unlink / }).first();
  await expect(unlink).toBeVisible();
  const count = await dialog.getByRole("button", { name: /^Unlink / }).count();
  page.once("dialog", (confirm) => {
    messages.push(confirm.message());
    confirm.dismiss();
  });
  await unlink.click();
  await expect.poll(() => messages.length).toBe(2);
  expect(messages[1]).toContain("Unlink");
  await expect(dialog.getByRole("button", { name: /^Unlink / })).toHaveCount(
    count,
  );
});

test("cards flag unsaved drafts and keep them across a panel reload", async ({
  page,
}) => {
  const card = page.locator('.card[data-entry="demo-writable"]');
  await expect(card.locator(".badge.draft")).toHaveCount(0);
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const elements = await page.evaluate(
    () => window.manager.editor.document.elements.length,
  );
  await page.locator('[data-action="dashboard"]').click();
  await expect(card.locator(".badge.draft")).toHaveText("Unsaved changes");
  await expect(
    page.locator('.card[data-entry="demo-discovery"] .badge.draft'),
  ).toHaveCount(0);
  // Navigating inside HA removes the panel without beforeunload.
  await page.evaluate(() => window.manager.remove());
  await page.reload();
  await expect(page.locator(".card")).toHaveCount(2);
  await expect(card.locator(".badge.draft")).toHaveText("Unsaved changes");
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator("#dirty-badge")).toBeVisible();
  expect(
    await page.evaluate(() => window.manager.editor.document.elements.length),
  ).toBe(elements);
});

test("a tag design left unsaved while in Sensor tile styles is still flagged and restored", async ({
  page,
}) => {
  const card = page.locator('.card[data-entry="demo-writable"]');
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const elements = await page.evaluate(
    () => window.manager.editor.document.elements.length,
  );
  await page
    .getByRole("button", { name: "Sensor tile styles", exact: true })
    .click();
  await page.locator('[data-action="dashboard"]').click();
  await expect(card.locator(".badge.draft")).toHaveText("Unsaved changes");
  await page.evaluate(() => window.manager.remove());
  await page.reload();
  await expect(card.locator(".badge.draft")).toHaveText("Unsaved changes");
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator("#dirty-badge")).toBeVisible();
  expect(
    await page.evaluate(() => window.manager.editor.document.elements.length),
  ).toBe(elements);
});

test("manager messages float in view, can be dismissed, and confirmations clear", async ({
  page,
}) => {
  const message = page.locator(".message");
  await page.evaluate(() => window.manager.message("Something broke"));
  await expect(message).toBeVisible();
  await expect(message).toHaveAttribute("role", "alert");
  await expect(message.getByRole("button")).toHaveCount(0);
  const box = await page.locator(".message-wrap").boundingBox();
  const viewport = page.viewportSize();
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
  await page.getByRole("button", { name: "Dismiss message" }).click();
  await expect(message).toBeHidden();
  await page.evaluate(() => window.manager.message("Saved.", "success"));
  await expect(message).toHaveAttribute("role", "status");
  await expect(message).toBeHidden({ timeout: 10000 });
});

test("choosing between several write actions uses an accessible radio list", async ({
  page,
}) => {
  const ask = () =>
    page.evaluate(async () => {
      const { chooseOne } = await import("/frontend/choice-dialog.js");
      window.choice = chooseOne(
        window.manager.hass,
        "Choose the write action to import:",
        ["Action one", "Action two"],
      );
    });
  await ask();
  const dialog = page.getByRole("dialog", {
    name: "Choose the write action to import:",
  });
  await expect(dialog.getByRole("radio")).toHaveCount(2);
  await expect(dialog.getByRole("radio", { name: "Action one" })).toBeChecked();
  await expect(dialog.getByRole("radio", { name: "Action one" })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await dialog.getByRole("button", { name: "Continue" }).click();
  expect(await page.evaluate(() => window.choice)).toBe(1);
  await expect(dialog).toHaveCount(0);
  await ask();
  await page.keyboard.press("Escape");
  expect(await page.evaluate(() => window.choice)).toBeNull();
  await ask();
  await page.getByRole("button", { name: "Cancel" }).click();
  expect(await page.evaluate(() => window.choice)).toBeNull();
});

test("manager and designer toasts stack without overlapping on a phone", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator("ble-esl-designer .status")).toBeAttached();
  await page.waitForFunction(() => window.manager.editor.ready);
  const long = "A long failure message that wraps. ".repeat(6);
  await page.evaluate((text) => {
    window.manager.message(text);
    window.manager.editor.report(new Error(text));
  }, long);
  const manager = await page.locator(".message-wrap").boundingBox();
  const designer = await page.locator(".toast").boundingBox();
  expect(manager.height).toBeGreaterThan(60);
  expect(manager.x).toBeGreaterThanOrEqual(11);
  expect(manager.x + manager.width).toBeLessThanOrEqual(364);
  expect(designer.y + designer.height).toBeLessThanOrEqual(manager.y);
  expect(designer.y).toBeGreaterThanOrEqual(0);
});

test("picking one of several write actions imports it; cancelling backs out", async ({
  page,
}) => {
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    const config = await response.json();
    const write = config.actions.find(
      (action) => (action.action || action.service) === "ble_esl.write",
    );
    config.actions.push(structuredClone(write));
    await route.fulfill({ response, json: config });
  });
  const openDesign = async () => {
    await page
      .locator('[data-action="automations"][data-entry="demo-writable"]')
      .click();
    await page
      .getByRole("dialog", { name: "Connected automations" })
      .getByRole("button", { name: "Edit automation design", exact: true })
      .first()
      .click();
  };
  await openDesign();
  const picker = page.getByRole("dialog", {
    name: "Choose the write action to import:",
  });
  await expect(picker.getByRole("radio")).toHaveCount(2);
  await page.keyboard.press("ArrowDown");
  await picker.getByRole("button", { name: "Continue" }).click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.locator('[data-action="dashboard"]').click();
  await openDesign();
  await expect(picker).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(picker).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toHaveCount(0);
  await expect(page.locator("#editor")).toBeVisible();
});

test("in the manager on a phone the designer drops its duplicate header", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.waitForFunction(() => window.manager.editor.ready);
  const designer = page.locator("ble-esl-designer");
  await expect(designer.locator("header h1")).toBeHidden();
  await expect(designer.locator("header ha-menu-button")).toBeHidden();
  const display = designer.getByRole("button", { name: "Display" });
  const tiles = designer.getByRole("button", {
    name: "Sensor tile styles",
    exact: true,
  });
  await expect(display).toBeVisible();
  await expect(tiles).toBeVisible();
  expect((await tiles.boundingBox()).height).toBeGreaterThanOrEqual(40);
  expect(
    await page.evaluate(
      () =>
        document.scrollingElement.scrollWidth -
        document.documentElement.clientWidth,
    ),
  ).toBeLessThanOrEqual(0);
  await page.screenshot({ path: "artifacts/manager-editor-phone.png" });
  await tiles.click();
  await expect(designer.locator(".template-controls")).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(designer.locator("header h1")).toBeVisible();
});

test("a card can discard its unsaved draft without opening the editor", async ({
  page,
}) => {
  const card = page.locator('.card[data-entry="demo-writable"]');
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.locator('[data-action="dashboard"]').click();
  await expect(card.locator(".badge.draft")).toHaveText("Unsaved changes");
  page.once("dialog", (dialog) => dialog.dismiss());
  await card.locator('[data-action="discard-draft"]').click();
  await expect(card.locator(".badge.draft")).toHaveText("Unsaved changes");
  page.once("dialog", (dialog) => dialog.accept());
  await card.locator('[data-action="discard-draft"]').click();
  await expect(card.locator(".badge.draft")).toHaveCount(0);
  await expect(card.locator('[data-action="discard-draft"]')).toHaveCount(0);
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator("#dirty-badge")).toBeHidden();
  expect(
    await page.evaluate(() => window.manager.editor.document.elements.length),
  ).toBe(0);
});

test("the editor can discard its unsaved design, and editing back to the start is not unsaved", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  const discard = page.locator('[data-action="discard"]');
  await expect(discard).toBeHidden();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.locator("#dirty-badge")).toBeVisible();
  await expect(discard).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await discard.click();
  await expect(page.locator("#dirty-badge")).toBeHidden();
  await expect(discard).toBeHidden();
  expect(
    await page.evaluate(() => window.manager.editor.document.elements.length),
  ).toBe(0);
  // Removing the element again by hand leaves nothing unsaved.
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.locator("#dirty-badge")).toBeVisible();
  await page.evaluate(() => {
    const editor = window.manager.editor;
    editor.checkpoint();
    editor.document.elements = [];
    editor.edited();
  });
  await expect(page.locator("#dirty-badge")).toBeHidden();
  await page.locator('[data-action="dashboard"]').click();
  await expect(
    page.locator('.card[data-entry="demo-writable"] .badge.draft'),
  ).toHaveCount(0);
});
