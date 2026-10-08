import { test, expect } from "@playwright/test";
async function pickSensor(page, id) {
  await page
    .locator("#entity-picker")
    .getByRole("combobox", { name: "Search sensors", exact: true })
    .fill(id);
  await page.locator(`#entity-picker [data-entity="${id}"]`).click();
}
// One demo server serves every browser project; start each from a clean state.
test.beforeAll(async ({ request }) => {
  await request.post("/reset");
});
test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.waitForFunction(() => window.panel?.tag);
  await page.evaluate(() => {
    window.panel.document = {
      version: 1,
      elements: [],
      background: "white",
    };
    window.panel.render();
  });
});
test("sensor defaults, keyboard, dragging, resize, undo, save and preview", async ({
  page,
}) => {
  await expect(page.locator("#auto")).toHaveCount(0);
  await expect(page.locator("#interval")).toHaveCount(0);
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await pickSensor(page, "sensor.office_temperature");
  await expect(page.locator('[data-property="decimals"]')).toHaveValue("1");
  const element = page.locator(".el.selected");
  await element.focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Shift+ArrowDown");
  await expect(page.locator('[data-property="x"]')).toHaveValue("9");
  await expect(page.locator('[data-property="y"]')).toHaveValue("18");
  await page.keyboard.press("Control+d");
  await expect(page.locator(".el")).toHaveCount(2);
  await page.keyboard.press("Delete");
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  await expect(page.locator(".el")).toHaveCount(2);
  await page.locator(".layer").first().click();
  await expect(page.locator(".el")).toHaveCount(2);
  let box = await page.locator(".el").first().boundingBox();
  await page.mouse.move(box.x + 20, box.y + 20);
  await page.mouse.down();
  await page.mouse.move(box.x + 50, box.y + 26);
  await page.mouse.up();
  expect(
    Number(await page.locator('[data-property="x"]').inputValue()),
  ).toBeGreaterThan(8);
  box = await page.locator('.handle[data-corner="se"]').boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width / 2 - 60,
    box.y + box.height / 2 - 12,
  );
  await page.mouse.up();
  expect(
    Number(await page.locator('[data-property="width"]').inputValue()),
  ).toBeLessThan(140);
  await page.getByRole("button", { name: "Save", exact: false }).click();
  await expect(page.getByRole("status")).toContainText("Display saved");
  await expect(page.locator("img.exact")).toBeVisible();
  await page.screenshot({
    path: "artifacts/designer-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Send to tag", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("demo_only");
  expect(errors).toEqual([]);
});
test("entity drag and drop, discovery-only tag and narrow screen", async ({
  page,
}) => {
  await page.waitForFunction(() => window.panel?.tag);
  await page.evaluate(() => {
    window.panel.document = {
      version: 1,
      elements: [],
      background: "white",
    };
    window.panel.render();
  });
  await page
    .getByRole("combobox", { name: "Search sensors", exact: true })
    .fill("humidity");
  const source = page.locator(
    'ha-entity-picker [data-entity="sensor.office_humidity"]',
  );
  await source.dragTo(page.locator(".stage"), {
    targetPosition: { x: 35, y: 35 },
  });
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByLabel("Tag", { exact: true }).selectOption("demo-discovery");
  await expect(
    page.getByRole("button", { name: "Send to tag" }),
  ).toBeDisabled();
  await expect(page.getByRole("status")).toContainText("Discovery only");
  await pickSensor(page, "sensor.office_temperature");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "artifacts/designer-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});

test("preview fits its window by default and can zoom in and out", async ({
  page,
}) => {
  await page.setViewportSize({ width: 900, height: 900 });
  await expect(page.locator(".stage")).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => {
        const root = window.panel.shadowRoot;
        return (
          root.querySelector(".stage").getBoundingClientRect().width <=
          root.querySelector(".canvas-wrap").clientWidth
        );
      }),
    )
    .toBe(true);
  const before = await page.locator(".stage").boundingBox();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  expect((await page.locator(".stage").boundingBox()).width).toBeGreaterThan(
    before.width,
  );
  await page.getByRole("button", { name: "Zoom out", exact: true }).click();
  await page.getByRole("button", { name: "Fit preview", exact: true }).click();
  expect(
    Math.abs((await page.locator(".stage").boundingBox()).width - before.width),
  ).toBeLessThan(2);
});

test("sensor and text can be added when HA is served over plain HTTP", async ({
  page,
}) => {
  await page.addInitScript(() =>
    Object.defineProperty(crypto, "randomUUID", { value: undefined }),
  );
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.waitForFunction(() => window.panel?.tag);
  await page.evaluate(() => {
    window.panel.document = {
      version: 1,
      elements: [],
      background: "white",
    };
    window.panel.render();
  });
  await page.locator('[data-add="text"]').click();
  await expect(page.locator(".el")).toHaveCount(1);
  await pickSensor(page, "sensor.office_temperature");
  await expect(page.locator(".el")).toHaveCount(2);
  await page.locator(".el.selected").click({ button: "right" });
  await page.getByRole("menuitem", { name: "Duplicate" }).click();
  await expect(page.locator(".el")).toHaveCount(3);
  expect(errors).toEqual([]);
});

test("side panels collapse independently and expand the preview", async ({
  page,
}) => {
  await expect(page.locator(".stage")).toBeVisible();
  const before = (await page.locator(".canvas-wrap").boundingBox()).width;
  await page.getByRole("button", { name: "Toggle entities panel" }).click();
  await expect(page.locator(".library")).toBeHidden();
  await page.getByRole("button", { name: "Toggle properties panel" }).click();
  await expect(page.locator(".inspector")).toBeHidden();
  expect(
    (await page.locator(".canvas-wrap").boundingBox()).width,
  ).toBeGreaterThan(before);
  await page.getByRole("button", { name: "Toggle entities panel" }).click();
  await expect(page.locator(".library")).toBeVisible();
  await page.getByRole("button", { name: "Toggle properties panel" }).click();
  await expect(page.locator(".inspector")).toBeVisible();
});

test("unrelated HA state updates do not prevent a rendered preview", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await page.evaluate(() => {
    window.previewNoise = setInterval(() => {
      const panel = window.panel;
      panel.hass = {
        ...panel.hass,
        states: {
          ...panel.hass.states,
          "sensor.unrelated": {
            entity_id: "sensor.unrelated",
            state: String(Date.now()),
            attributes: { friendly_name: "Unrelated" },
          },
        },
      };
    }, 75);
  });
  await expect(page.locator("img.exact")).toBeVisible({ timeout: 2500 });
  await page.evaluate(() => clearInterval(window.previewNoise));
});

test("element actions are in the context menu; trash, Backspace and Delete work", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await expect(
    page.locator('.inspector [data-action="duplicate"]'),
  ).toHaveCount(0);
  await expect(page.locator("[data-preset]")).toHaveCount(0);
  await page.locator(".el.selected").click({ button: "right" });
  await expect(page.getByRole("menu")).toBeVisible();
  await page.getByRole("menuitem", { name: "Duplicate" }).click();
  await expect(page.locator(".el")).toHaveCount(2);
  await page.keyboard.press("Backspace");
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  await expect(page.locator(".el")).toHaveCount(2);
  await page.locator(".layer").first().click();
  await page
    .getByRole("button", { name: "Delete selected element", exact: true })
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Delete selected element", exact: true }),
  ).toHaveCount(0);
  await page.locator(".layer").first().click();
  await page.keyboard.press("Delete");
  await expect(page.locator(".el")).toHaveCount(0);
});

test("typing properties updates without blur and keeps text editing shortcuts", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  const label = page.locator('[data-property="label"]');
  await label.fill("Living room");
  await expect(label).toBeFocused();
  await expect(page.locator(".el.selected .label")).toHaveText("Living room");
  await page.keyboard.press("Backspace");
  await expect(page.locator(".el")).toHaveCount(1);
  await expect(label).toHaveValue("Living roo");
  await expect(page.locator("img.exact")).toBeVisible();
  await expect(label).toBeFocused();
  await page.getByRole("button", { name: "Colour: red", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Colour: red", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Align center", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Align center", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("sensor type template designer saves, previews and preserves the display draft", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.locator('[data-add="text"]').click();
  await page.locator('[data-property="text"]').fill("Keep my draft");
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  await expect(page.getByLabel("Template", { exact: true })).toHaveValue(
    "output:numeric",
  );
  await expect(page.locator(".el")).toHaveCount(3);
  await expect(page.locator("img.exact")).toBeVisible();
  await page.locator('[data-token="unit"]').click();
  await page.locator('[data-property="text"]').fill("{{state}} {{unit}}");
  await page.getByRole("button", { name: "Save", exact: false }).click();
  await expect(page.getByRole("status")).toContainText("Template saved");
  await page.getByRole("button", { name: "Display", exact: true }).click();
  await expect(page.locator(".el")).toHaveCount(1);
  await expect(page.locator('[data-property="text"]')).toHaveValue(
    "Keep my draft",
  );
  await pickSensor(page, "sensor.office_temperature");
  await expect(page.locator("img.exact")).toBeVisible();
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  await page
    .getByLabel("Template", { exact: true })
    .selectOption("output:binary");
  await expect(page.locator(".el")).toHaveCount(2);
  await page.locator(".layer").last().click();
  await expect(page.getByLabel("Icon name", { exact: true })).toHaveValue(
    "{{icon}}",
  );
  const configure = page.getByRole("button", {
    name: "Configure",
    exact: true,
  });
  await expect(configure).toHaveCSS("grid-column", "1 / -1");
  await configure.click();
  await page
    .getByRole("combobox", { name: "Icon (blank = HA)", exact: true })
    .fill("mdi:window-open");
  await page.getByRole("button", { name: "Apply", exact: true }).click();
  expect(await page.evaluate(() => window.panel.element.icon)).toBe(
    "mdi:window-open",
  );
  await page.getByRole("button", { name: "Save", exact: false }).click();
  await expect(page.getByRole("status")).toContainText("Template saved");
  await page.screenshot({
    path: "artifacts/template-designer.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("weather uses an icon and offers forecast time and value selectors", async ({
  page,
}) => {
  await pickSensor(page, "weather.home");
  await expect(page.locator(".el.selected .value")).toHaveText("");
  await page
    .getByLabel("Weather time", { exact: true })
    .selectOption("tomorrow");
  await page
    .getByLabel("Weather value", { exact: true })
    .selectOption("temperature");
  await expect(page.getByLabel("Weather time", { exact: true })).toHaveValue(
    "tomorrow",
  );
  await expect(page.locator("img.exact")).toBeVisible();
});

test("icon picker font is registered and loaded in the document", async ({
  page,
}) => {
  await expect
    .poll(() =>
      page.evaluate(() =>
        [...document.fonts].some(
          (font) => font.family === "LabelMDI" && font.status === "loaded",
        ),
      ),
    )
    .toBe(true);
});

test("elements stay on the display", async ({ page }) => {
  await page.locator('[data-add="text"]').click();
  await page.locator('[data-property="x"]').fill("-20");
  await page.locator('[data-property="x"]').press("Tab");
  await expect.poll(() => page.evaluate(() => window.panel.element.x)).toBe(0);
  await page.locator('[data-property="x"]').fill("9999");
  await page.locator('[data-property="x"]').press("Tab");
  await expect
    .poll(() =>
      page.evaluate(() => window.panel.element.x + window.panel.element.width),
    )
    .toBe(await page.evaluate(() => window.panel.tag.width));
  await expect(page.locator("img.exact")).toBeVisible();
});

test("text can be edited directly in the preview", async ({ page }) => {
  await page.locator('[data-add="text"]').click();
  await page.locator(".el.selected .content").click();
  const editor = page.getByRole("textbox", {
    name: "Edit display text",
    exact: true,
  });
  await expect(editor).toBeFocused();
  // Type like a user: the placeholder is selected and gets replaced. (fill()
  // selects through addRange, which WebKit ignores inside a shadow tree.)
  await page.keyboard.type("Inline °C");
  await expect(page.locator('[data-property="text"]')).toHaveValue("Inline °C");
  await page.keyboard.press("Backspace");
  await expect(page.locator(".el")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await page.keyboard.press("Delete");
  await expect(page.locator(".el")).toHaveCount(0);
});

test("sensor controls are conditional and canvas settings are independent", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  await expect(page.locator('[data-property="label"]')).toBeVisible();
  await page.locator('[data-property="show_label"]').uncheck();
  await expect(page.locator('[data-property="label"]')).toHaveCount(0);
  await page.locator('[data-property="show_unit"]').uncheck();
  await expect(page.locator('[data-property="decimals"]')).toHaveCount(0);
  await expect(page.locator(".layer-card .layers")).toBeVisible();
  expect(await page.evaluate(() => window.panel.element.background)).toBe(
    "transparent",
  );
  await pickSensor(page, "binary_sensor.window");
  await expect(page.locator('[data-property="decimals"]')).toHaveCount(0);
});

test("create template starts with the selected sensor and applies the saved style", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  const id = await page.evaluate(() => window.panel.selected);
  await page
    .getByLabel("Sensor template", { exact: true })
    .selectOption("__new__");
  await expect(page.getByLabel("Template name", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.panel.sampleEntity)).toBe(
    "sensor.office_temperature",
  );
  await page
    .getByLabel("Template name", { exact: true })
    .fill("My temperature");
  await page.getByRole("button", { name: /^Save/ }).click();
  await page.getByRole("button", { name: "Display", exact: true }).click();
  expect(
    await page.evaluate(
      (id) => window.panel.document.elements.find((e) => e.id === id).template,
      id,
    ),
  ).toContain(":custom:");
  await expect(
    page
      .getByLabel("Sensor template", { exact: true })
      .locator("option:checked"),
  ).toHaveText("My temperature");
});

test("shape dropdown renders each supported shape", async ({ page }) => {
  await page.getByRole("button", { name: "Add shape", exact: true }).click();
  for (const type of [
    "ellipse",
    "triangle",
    "rounded_rectangle",
    "line",
    "rectangle",
  ]) {
    await page.getByLabel("Shape", { exact: true }).selectOption(type);
    await expect
      .poll(() => page.evaluate(() => window.panel.element.type))
      .toBe(type);
    await expect(page.locator("img.exact")).toBeVisible();
  }
});

test("template mode has no send or preview button and offers every sensor", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Send to tag", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Preview", exact: true }),
  ).toHaveCount(0);
  await page.locator("#template-sample").evaluate((picker) =>
    picker.dispatchEvent(
      new CustomEvent("value-changed", {
        detail: { value: "binary_sensor.window" },
      }),
    ),
  );
  expect(await page.evaluate(() => window.panel.templateSensorType)).toBe(
    "output:binary",
  );
  expect(
    await page.locator("#template-sample").evaluate((picker) => picker.value),
  ).toBe("binary_sensor.window");
});

test("an uploaded photo is stored upright, with its EXIF orientation applied", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Add image", exact: true }).click();
  // 4×2 pixels with orientation 6: shown upright it is 2×4.
  await page
    .getByLabel("Upload image", { exact: true })
    .setInputFiles("tests/frontend/fixtures/exif-rotated.jpg");
  await expect
    .poll(() =>
      page.evaluate(() =>
        window.panel.element.image.startsWith("data:image/jpeg"),
      ),
    )
    .toBe(true);
  // What is stored is what the tag's renderer reads: the pixel size in the
  // JPEG's own header, which an <img> (it applies EXIF itself) would hide.
  const size = await page.evaluate(async () => {
    const bytes = new Uint8Array(
      await (await fetch(window.panel.element.image)).arrayBuffer(),
    );
    const view = new DataView(bytes.buffer);
    let offset = 2;
    while (offset + 9 < bytes.length) {
      const marker = view.getUint16(offset);
      if (marker === 0xffc0 || marker === 0xffc2)
        return [view.getUint16(offset + 7), view.getUint16(offset + 5)];
      offset += 2 + view.getUint16(offset + 2);
    }
    return null;
  });
  expect(size).toEqual([2, 4]);
});
test("the header and the toolbar stay in view while the panel scrolls", async ({
  page,
}) => {
  const bars = () =>
    page.evaluate(() => {
      const host = window.panel,
        root = host.shadowRoot,
        rect = (selector) => {
          const box = root.querySelector(selector).getBoundingClientRect(),
            origin = host.getBoundingClientRect().top;
          return { top: box.top - origin, bottom: box.bottom - origin };
        };
      return { header: rect("header"), toolbar: rect(".toolbar") };
    });
  // Cover wrapped toolbars and short desktop windows as well as tall ones.
  for (const [width, height] of [
    [1440, 1000],
    [900, 1000],
    [1440, 477],
    [900, 477],
  ]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => {
      window.panel.style.height = "450px";
      window.panel.scrollTop = 400;
    });
    // The panel measures the bars after the resize, not at once.
    await expect
      .poll(async () => {
        const { header, toolbar } = await bars();
        const padding = await page.evaluate(() =>
          parseFloat(window.panel.style.scrollPaddingTop),
        );
        return [
          header.top,
          toolbar.top === header.bottom,
          Math.abs(padding - toolbar.bottom) < 1,
        ];
      })
      .toEqual([0, true, true]);
    expect(await page.evaluate(() => window.panel.scrollTop)).toBeGreaterThan(
      0,
    );
  }
  // On a phone the bars scroll away with the page.
  await page.setViewportSize({ width: 600, height: 1000 });
  await page.evaluate(() => {
    window.panel.scrollTop = 400;
  });
  expect((await bars()).header.top).toBeLessThan(0);
});
test("images can be uploaded, resized and used as state-specific template parts", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Add image", exact: true }).click();
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDQAAAABJRU5ErkJggg==",
    "base64",
  );
  await page
    .getByLabel("Upload image", { exact: true })
    .setInputFiles({ name: "image.png", mimeType: "image/png", buffer: png });
  await expect
    .poll(() =>
      page.evaluate(() =>
        window.panel.element.image.startsWith("data:image/png"),
      ),
    )
    .toBe(true);
  await expect(page.locator("img.exact")).toBeVisible();
  await page.getByLabel("Image fit", { exact: true }).selectOption("fill");
  await expect(page.locator("img.exact")).toBeVisible();
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  await page.getByRole("button", { name: "Add image", exact: true }).click();
  await page.getByLabel("Visible state", { exact: true }).fill("on");
  expect(await page.evaluate(() => window.panel.element.state)).toBe("on");
});

test("slow previews never overlap and render the latest edit", async ({
  page,
}) => {
  await page.waitForTimeout(250);
  await page.evaluate(() => {
    window.activePreviews = window.peakPreviews = 0;
    window.panel.previewRequest = async () => {
      window.activePreviews++;
      window.peakPreviews = Math.max(
        window.peakPreviews,
        window.activePreviews,
      );
      await new Promise((resolve) => setTimeout(resolve, 650));
      window.activePreviews--;
      return {
        png: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDQAAAABJRU5ErkJggg==",
        layers: {},
      };
    };
  });
  for (let i = 0; i < 4; i++) {
    await page.evaluate(() => window.panel.queuePreview());
    await page.waitForTimeout(250);
  }
  await expect
    .poll(() => page.evaluate(() => window.activePreviews), { timeout: 4000 })
    .toBe(0);
  expect(await page.evaluate(() => window.peakPreviews)).toBe(1);
  await expect(page.locator("img.exact")).toBeVisible();
});

async function modalSource(page, id) {
  const modal = page.getByRole("dialog", { name: "Component editor" });
  await modal
    .getByRole("combobox", { name: "Search sensors", exact: true })
    .fill(id);
  await modal.locator(`ha-entity-picker [data-entity="${id}"]`).click();
}

test("components choose independent data in a modal and cancel leaves the display unchanged", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "＋ Add component", exact: true })
    .click();
  await modalSource(page, "sensor.office_temperature");
  await expect(
    page.getByRole("img", { name: "Component pixel preview" }),
  ).toHaveAttribute("src", /^data:image/);
  await page
    .getByRole("button", { name: "Add to display", exact: true })
    .click();
  expect(await page.evaluate(() => window.panel.element.entity_id)).toBe(
    "sensor.office_temperature",
  );
  await page
    .getByRole("button", { name: "＋ Add component", exact: true })
    .click();
  await modalSource(page, "sensor.office_humidity");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page
    .getByRole("button", { name: "＋ Add component", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Conditional icon", exact: true })
    .click();
  await modalSource(page, "binary_sensor.window");
  await page
    .getByRole("combobox", { name: "Rule icon", exact: true })
    .first()
    .fill("mdi:window-open");
  await page
    .getByRole("combobox", { name: "Rule icon", exact: true })
    .last()
    .fill("mdi:window-closed");
  await page
    .getByRole("button", { name: "Add to display", exact: true })
    .click();
  await expect(page.locator(".el")).toHaveCount(2);
  expect(
    await page.evaluate(() =>
      window.panel.document.elements.map((e) => e.entity_id),
    ),
  ).toEqual(["sensor.office_temperature", "binary_sensor.window"]);
  await expect(page.locator("img.exact")).toBeVisible();
});

test("numeric conditional icons have editable ranges and standard icon pickers", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "＋ Add component", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Conditional icon", exact: true })
    .click();
  await modalSource(page, "sensor.office_temperature");
  await page.getByRole("button", { name: "＋ Range", exact: true }).click();
  await page.getByLabel("Range 1 minimum", { exact: true }).fill("20");
  await page.getByLabel("Range 1 maximum", { exact: true }).fill("30");
  await page
    .getByRole("combobox", { name: "Rule icon", exact: true })
    .fill("mdi:thermometer");
  await expect(
    page.getByRole("img", { name: "Component pixel preview" }),
  ).toHaveAttribute("src", /^data:image/);
  await page.screenshot({
    path: "artifacts/component-modal.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Add to display", exact: true })
    .click();
  expect(await page.evaluate(() => window.panel.element.icon_rules[0])).toEqual(
    { kind: "range", min: 20, max: 30, icon: "mdi:thermometer" },
  );
});

test("four corner handles follow visible content and backgrounds have no controls", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  await page.locator('[data-property="show_label"]').uncheck();
  await expect(page.locator("img.exact")).toBeVisible();
  await expect(page.locator(".handle")).toHaveCount(4);
  await expect(
    page.getByRole("group", { name: "Background", exact: true }),
  ).toHaveCount(0);
  const element = await page.locator(".el.selected").boundingBox();
  const selection = await page.locator(".selection-box").boundingBox();
  expect(selection.height).toBeLessThan(element.height);
  // The longer properties panel can leave the page scrolled past the canvas.
  await page.locator(".stage").scrollIntoViewIfNeeded();
  const handle = await page.locator('.handle[data-corner="nw"]').boundingBox();
  const old = await page.evaluate(() => ({ ...window.panel.element }));
  await page.mouse.move(
    handle.x + handle.width / 2,
    handle.y + handle.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(handle.x - 20, handle.y - 20);
  await page.mouse.up();
  expect(await page.evaluate(() => window.panel.element.x)).toBeLessThan(old.x);
  expect(await page.evaluate(() => window.panel.element.width)).toBeGreaterThan(
    old.width,
  );
});

test("Bluetooth send persists the design before starting transfer", async ({
  page,
}) => {
  const actions = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/api/designer"))
      actions.push(request.postDataJSON().action);
  });
  await page.locator('[data-add="text"]').click();
  await page.getByRole("button", { name: "Send to tag", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("demo_only");
  const sent = actions.lastIndexOf("send");
  expect(sent).toBeGreaterThan(0);
  expect(actions[sent - 1]).toBe("save");
  expect(await page.evaluate(() => window.panel.dirty)).toBe(false);
});

test("general templates edit individual fields in a separate modal", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "＋ Add component", exact: true })
    .click();
  await modalSource(page, "sensor.office_temperature");
  await page
    .getByRole("button", { name: "ƒ Dynamic fields…", exact: true })
    .click();
  const modal = page.getByRole("dialog", {
    name: "Dynamic fields",
    exact: true,
  });
  await modal
    .getByLabel("Field template", { exact: true })
    .fill("{{ 'red' if value | float(0) > 20 else 'black' }}");
  await expect(modal.locator("#result")).toHaveText('"red"');
  await modal
    .getByRole("button", { name: "Apply templates", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Add to display", exact: true })
    .click();
  expect(
    await page.evaluate(() => window.panel.element.field_templates.color),
  ).toContain("value | float");
  await expect(page.locator("img.exact")).toBeVisible();
});

test("inspector and template sample use native HA entity pickers", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  const bound = page.locator('ha-entity-picker[data-property="entity_id"]');
  await expect(bound).toHaveCount(1);
  expect(
    await bound.evaluate((picker) => ({
      value: picker.value,
      hass: !!picker.hass,
      required: picker.required,
    })),
  ).toEqual({ value: "sensor.office_temperature", hass: true, required: true });
  await bound.getByRole("combobox").fill("temperature");
  await bound.getByRole("combobox").press("Backspace");
  await expect(page.locator(".el")).toHaveCount(1);
  await bound.evaluate((picker) =>
    picker.dispatchEvent(
      new CustomEvent("value-changed", {
        detail: { value: "binary_sensor.window" },
      }),
    ),
  );
  expect(await page.evaluate(() => window.panel.element.entity_id)).toBe(
    "binary_sensor.window",
  );
  await expect(page.locator('[data-property="decimals"]')).toHaveCount(0);
  await page
    .getByRole("button", { name: "Sensor templates", exact: true })
    .click();
  const sample = page.locator("ha-entity-picker#template-sample");
  await expect(sample).toHaveCount(1);
  await sample.evaluate((picker) =>
    picker.dispatchEvent(
      new CustomEvent("value-changed", {
        detail: { value: "binary_sensor.window" },
      }),
    ),
  );
  expect(
    await page.evaluate(() => ({
      entity: window.panel.sampleEntity,
      type: window.panel.templateSensorType,
    })),
  ).toEqual({ entity: "binary_sensor.window", type: "output:binary" });
});

test("clicking empty canvas and surrounding space deselects the component", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.locator(".el.selected")).toHaveCount(1);
  const stage = await page.locator(".stage").boundingBox();
  await page.mouse.click(stage.x + stage.width - 5, stage.y + stage.height - 5);
  await expect(page.locator(".el.selected")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Configure", exact: true }),
  ).toHaveCount(0);
  await page.locator(".el").click();
  await expect(page.locator(".el.selected")).toHaveCount(1);
  await page.locator(".canvas-wrap").click({ position: { x: 5, y: 5 } });
  await expect(page.locator(".el.selected")).toHaveCount(0);
  await expect(page.locator(".el")).toHaveCount(1);
});

test("transparent component padding does not capture hover or clicks above another layer", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  await page.evaluate(() => {
    window.panel.element.template = "default";
    window.panel.edited();
  });
  await page.locator('[data-property="show_label"]').uncheck();
  await page.waitForFunction(() => {
    const p = window.panel,
      e = p.element,
      b = p.layerBounds?.[e?.id];
    return b && b[3] < e.height - 12;
  });
  const fixture = await page.evaluate(() => {
    const p = window.panel,
      sensor = p.element;
    p.add("rectangle");
    const shape = p.element;
    Object.assign(shape, {
      x: sensor.x + sensor.width - 12,
      y: sensor.y + sensor.height - 12,
      width: 10,
      height: 10,
    });
    p.document.elements = [shape, sensor];
    p.selected = null;
    p.edited();
    return {
      sensor: sensor.id,
      shape: shape.id,
      x: shape.x + 5,
      y: shape.y + 5,
    };
  });
  await page.waitForFunction(
    (id) => !!window.panel.layerBounds?.[id],
    fixture.shape,
  );
  const stage = await page.locator(".stage").boundingBox();
  const zoom = await page.evaluate(() => window.panel.zoom);
  const point = {
    x: stage.x + fixture.x * zoom,
    y: stage.y + fixture.y * zoom,
  };
  await page.mouse.move(point.x, point.y);
  expect(
    await page.evaluate(
      ({ x, y }) =>
        window.panel.shadowRoot.elementFromPoint(x, y)?.closest("[data-id]")
          ?.dataset.id,
      point,
    ),
  ).toBe(fixture.shape);
  await page.mouse.click(point.x, point.y);
  expect(await page.evaluate(() => window.panel.selected)).toBe(fixture.shape);
  const empty = await page.evaluate(() => {
    const e = window.panel.document.elements.find((e) => e.type === "sensor");
    return { x: e.x + 5, y: e.y + e.height - 5 };
  });
  await page.mouse.click(stage.x + empty.x * zoom, stage.y + empty.y * zoom);
  expect(await page.evaluate(() => window.panel.selected)).toBeNull();
});

test("sensor components inside templates can open Configure and render", async ({
  page,
}) => {
  const id = await page.evaluate(() => {
    const p = window.panel;
    p.switchMode("template");
    p.add("sensor", p.hass.states["binary_sensor.window"]);
    return p.element.id;
  });
  await page.waitForFunction((id) => !!window.panel.layerBounds?.[id], id);
  await page.getByRole("button", { name: "Configure", exact: true }).click();
  const modal = page.getByRole("dialog", {
    name: "Component editor",
    exact: true,
  });
  await expect(modal.locator(".pixels img")).toBeVisible();
  await expect(modal.locator(".pixels img")).toHaveAttribute(
    "src",
    /^data:image\/png/,
  );
  await expect(modal.getByRole("status")).toBeEmpty();
  await modal.getByRole("button", { name: "Cancel", exact: true }).click();
});

test("tags load while HA has not defined the entity picker yet", async ({
  page,
}) => {
  await page.goto("/?lazy-picker");
  await page.waitForFunction(() => window.panel?.tag, null, { timeout: 3000 });
  await expect(page.locator("#tag option")).not.toHaveCount(0);
  // Once HA defines the picker, the panel upgrades to a working one.
  const before = await page.locator(".el").count();
  await pickSensor(page, "sensor.office_temperature");
  await expect(page.locator(".el")).toHaveCount(before + 1);
});

test("inline editing still gets a caret when the click resets the selection", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  // Safari clears the selection after the gesture, once the panel already
  // selected the placeholder on pointerup. Emulate that: this listener runs
  // first, so its task lands between the panel's two selections.
  await page.evaluate(() =>
    window.addEventListener(
      "pointerup",
      () => setTimeout(() => window.getSelection().removeAllRanges()),
      { once: true },
    ),
  );
  await page.locator(".el.selected .content").click();
  // Let the emulated reset and the panel's second selection happen, as they
  // do before a person's first key: typing into the middle of them is a race
  // of the test, not of the panel.
  await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 100)));
  await page.keyboard.type("Caret");
  await expect(page.locator('[data-property="text"]')).toHaveValue("Caret");
});

// The demo defines the picker 2.5 s after load; the interaction under test
// must happen before that, or the test proves nothing.
const pickerDefined = async (page) => {
  expect(
    await page.evaluate(() => !customElements.get("ha-entity-picker")),
  ).toBe(true);
  await page.waitForFunction(
    () => customElements.get("ha-entity-picker"),
    null,
    {
      timeout: 6000,
    },
  );
};

test("the picker arriving late keeps inline editing going", async ({
  page,
}) => {
  await page.goto("/?lazy-picker");
  await page.waitForFunction(() => window.panel?.tag);
  await page.locator('[data-add="text"]').click();
  await page.locator(".el.selected .content").click();
  await page.keyboard.type("Hello");
  await pickerDefined(page);
  await page.keyboard.type(" world");
  await expect(page.locator('[data-property="text"]')).toHaveValue(
    "Hello world",
  );
});

test("the picker arriving late keeps an open component dialog", async ({
  page,
}) => {
  await page.goto("/?lazy-picker");
  await page.waitForFunction(() => window.panel?.tag);
  await page.locator('[data-action="add-component"]').click();
  await expect(page.locator("ble-esl-component-editor dialog")).toBeVisible();
  const text = page.getByLabel("Component text", { exact: true });
  await text.fill("abc");
  await page.getByRole("button", { name: /Dynamic fields/ }).click();
  const dynamic = page.getByRole("dialog", { name: "Dynamic fields" });
  await expect(dynamic).toBeVisible();
  await pickerDefined(page);
  await expect(
    page.locator("ble-esl-component-editor dialog").first(),
  ).toBeVisible();
  await expect(dynamic).toBeVisible();
  // The data source picker was swapped for a working one.
  await expect(
    page.locator("ble-esl-component-editor #source"),
  ).toHaveJSProperty("label", "Data source");
});

test("the display exports as the payload and a ready write action", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  await page.getByRole("button", { name: "Payload YAML" }).click();
  const dialog = page.locator("ble-esl-yaml-dialog dialog");
  await expect(dialog).toBeVisible();
  const yaml = dialog.getByLabel("YAML", { exact: true });
  await expect(yaml).toHaveValue(/- type: icon/);
  await expect(yaml).toHaveValue(/office_temperature|°C/);
  await dialog.getByRole("tab", { name: "Automation action" }).click();
  await expect(yaml).toHaveValue(/action: ble_esl\.write/);
  await expect(yaml).toHaveValue(/device_id: <your device>/);
  await dialog.getByRole("button", { name: "Close" }).click();
  await expect(page.locator("ble-esl-yaml-dialog")).toHaveCount(0);
});

const rendered = (page) =>
  // The box comes from the last render, so wait for one to exist.
  page.waitForFunction(
    () => !!window.panel.layerRecords?.[window.panel.element.id],
  );
const selectionBox = (page) =>
  page.locator(".selection-box").evaluate((node) => ({
    width: Number.parseFloat(node.style.width),
    height: Number.parseFloat(node.style.height),
  }));
const elementSize = (page) =>
  // The inspector is only refreshed when a drag ends; the element is current.
  page.evaluate(() => ({
    width: window.panel.element.width,
    height: window.panel.element.height,
  }));

for (const type of ["rectangle", "text"]) {
  test(`the selection box follows a ${type} while it is resized`, async ({
    page,
  }) => {
    await page.locator(`[data-add="${type}"]`).click();
    await rendered(page);
    const box = await selectionBox(page);
    const size = await elementSize(page);
    const handle = await page
      .locator('.handle[data-corner="se"]')
      .boundingBox();
    const [x, y] = [handle.x + handle.width / 2, handle.y + handle.height / 2];
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 80, y + 30);
    // Still dragging: no new render has arrived to refresh the content bounds,
    // so the box grows by what the frame grew.
    const during = await elementSize(page);
    expect(during.width).toBeGreaterThan(size.width);
    const grown = await selectionBox(page);
    expect(grown.width - box.width).toBe(during.width - size.width);
    expect(grown.height - box.height).toBe(during.height - size.height);
    await page.mouse.up();
    // Dropping schedules a new render; read the box before it can arrive.
    const dropped = await page.evaluate(() => {
      clearTimeout(window.panel.previewTimer);
      const box = window.panel.shadowRoot.querySelector(".selection-box");
      return {
        width: Number.parseFloat(box.style.width),
        height: Number.parseFloat(box.style.height),
      };
    });
    expect(dropped).toEqual(grown);
  });
}

test("a text box keeps its frame after a font size change and a render", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await rendered(page);
  await page.evaluate(() => {
    const input = window.panel.shadowRoot.querySelector(
      '[data-property="font_size"]',
    );
    input.value = "12";
    input.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
  });
  await page.waitForFunction(() =>
    window.panel.layerRecords[window.panel.element.id].shape.includes(
      '"font_size":12',
    ),
  );
  const frame = await elementSize(page);
  expect(await selectionBox(page)).toEqual(frame);
});

test("saving keeps the selection box on the content", async ({ page }) => {
  await page.locator('[data-add="rectangle"]').click();
  await rendered(page);
  const before = await selectionBox(page);
  // The server hands the document back with its defaults filled in.
  await page.getByRole("button", { name: /^Save/ }).click();
  await expect(page.locator(".status")).toContainText("Display saved");
  expect(await selectionBox(page)).toEqual(before);
});

test("keys typed in the YAML dialog do not edit the design behind it", async ({
  page,
}) => {
  await page.locator('[data-add="rectangle"]').click();
  const before = await page.evaluate(() => ({
    count: window.panel.document.elements.length,
    x: window.panel.element.x,
  }));
  await page.getByRole("button", { name: "Payload YAML" }).click();
  const yaml = page
    .locator("ble-esl-yaml-dialog dialog")
    .getByLabel("YAML", { exact: true });
  await expect(yaml).toBeVisible();
  await yaml.focus();
  for (const key of ["ArrowRight", "Backspace", "Delete", "Control+z"])
    await page.keyboard.press(key);
  await expect(page.locator("ble-esl-yaml-dialog dialog")).toBeVisible();
  expect(
    await page.evaluate(() => ({
      count: window.panel.document.elements.length,
      x: window.panel.element?.x,
    })),
  ).toEqual(before);
  await page.keyboard.press("Escape");
  await expect(page.locator("ble-esl-yaml-dialog")).toHaveCount(0);
  await expect(page.locator('[data-action="yaml"]')).toBeFocused();
});

test("an imagespec element is added from the list, edited by its fields and exported", async ({
  page,
}) => {
  await page.getByLabel("Add element").selectOption("pie");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.locator(".layer.active")).toHaveText("pie");
  await page.locator('[data-spec="values"]').fill("A,1;B,3");
  await page.locator('[data-spec="inner_radius"]').fill("20");
  await page.locator('[data-spec="outline"]').selectOption("red");
  // A half-typed number is flagged and the last good value is kept.
  await page.locator('[data-spec="inner_radius"]').fill("2x");
  await expect(page.locator('[data-spec="inner_radius"]')).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  expect(
    await page.evaluate(() => window.panel.element.spec.inner_radius),
  ).toBe(20);
  await page.getByRole("button", { name: "Payload YAML" }).click();
  const yaml = page
    .locator("ble-esl-yaml-dialog dialog")
    .getByLabel("YAML", { exact: true });
  await expect(yaml).toHaveValue(
    /- type: pie\n {2}values: A,1;B,3\n {2}inner_radius: 20/,
  );
  // Position keys come from the frame, in display coordinates.
  await expect(yaml).toHaveValue(/ {2}x: 48\n {2}y: 48\n {2}radius: 39/);
});

test("every imagespec element can be added and rendered", async ({ page }) => {
  // Each preview renders every element added so far.
  test.setTimeout(120_000);
  const types = await page.evaluate(() =>
    window.panel.specs.types.map((type) => type.type),
  );
  expect(types.length).toBeGreaterThan(25);
  // plot reads the recorder, which the demo server does not have.
  for (const type of types.filter((type) => type !== "plot")) {
    await page.evaluate((type) => window.panel.addSpec(type), type);
    await page.waitForFunction(
      () => window.panel.preview && !window.panel.error,
    );
  }
  expect(await page.evaluate(() => window.panel.document.elements.length)).toBe(
    types.length - 1,
  );
});

test("a click on an element keeps the exact preview and a drag swaps in the layers", async ({
  page,
}) => {
  await page.getByLabel("Add element").selectOption("pie");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.locator("img.exact")).toBeVisible();
  const hit = page.locator(".el.selected .hit-area");
  const box = await hit.boundingBox();
  const [x, y] = [box.x + box.width / 2, box.y + box.height / 2];
  await page.mouse.click(x, y);
  await expect(page.locator("img.exact")).toBeVisible();
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 30, y + 10);
  await expect(page.locator("img.exact")).toHaveCount(0);
  await page.mouse.up();
  await expect(page.locator("img.exact")).toBeVisible();
});

test("choosing in the element list adds nothing until Add is pressed", async ({
  page,
}) => {
  const list = page.getByLabel("Add element");
  await list.focus();
  for (const key of ["ArrowDown", "ArrowDown", "ArrowDown"])
    await page.keyboard.press(key);
  expect(await page.evaluate(() => window.panel.document.elements.length)).toBe(
    0,
  );
  // Native select keyboard behavior differs between macOS and Linux.
  // Explicitly select a value before testing the Add button on both platforms.
  await list.selectOption("text");
  expect(await page.evaluate(() => window.panel.document.elements.length)).toBe(
    0,
  );
  await page.getByRole("button", { name: "Add", exact: true }).click();
  expect(await page.evaluate(() => window.panel.document.elements.length)).toBe(
    1,
  );
});

test("an error shown for a broken value is cleared once the value is fixed", async ({
  page,
}) => {
  await page.getByLabel("Add element").selectOption("text");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.locator("img.exact")).toBeVisible();
  const value = page.locator('[data-spec="value"]');
  await value.fill("{{ 1 / 0 }}");
  await expect(page.locator(".status")).toHaveClass(/error/);
  await value.fill("fixed");
  await expect(page.locator(".status")).not.toHaveClass(/error/);
  await expect(page.locator("img.exact")).toBeVisible();
});

test("a polygon's corners and a whole-list template can be typed", async ({
  page,
}) => {
  await page.getByLabel("Add element").selectOption("polygon");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.locator('[data-spec="points"]').fill("0,0;100,0;50,100");
  expect(await page.evaluate(() => window.panel.element.spec.points)).toBe(
    "0,0;100,0;50,100",
  );
  await page.getByLabel("Add element").selectOption("sparkline");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.locator('[data-spec="values"]').fill("{{ [1, 2, 3] }}");
  await expect(page.locator('[data-spec="values"]')).not.toHaveAttribute(
    "aria-invalid",
    "true",
  );
  expect(await page.evaluate(() => window.panel.element.spec.values)).toBe(
    "{{ [1, 2, 3] }}",
  );
});

test("clicking a text to edit it leaves no rendered copy of the old text under it", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await expect(page.locator("img.exact")).toBeVisible();
  // Deselect by clicking the empty canvas, then click the text itself: a
  // click starts editing it.
  await page.locator(".canvas-wrap").click({ position: { x: 5, y: 5 } });
  await expect(page.locator(".el.selected")).toHaveCount(0);
  const hit = page.locator(".el .hit-area");
  const box = await hit.boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page.locator(".el.editing")).toHaveCount(1);
  await expect(page.locator("img.exact")).toHaveCount(0);
});

test("the YAML keeps a template as written, or shows today's value", async ({
  page,
}) => {
  await page.getByLabel("Add element").selectOption("text");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page
    .locator('[data-spec="value"]')
    .fill("{{ states('sensor.office_temperature') }} °C");
  await page.getByRole("button", { name: "Payload YAML" }).click();
  const dialog = page.locator("ble-esl-yaml-dialog dialog");
  const yaml = dialog.getByLabel("YAML", { exact: true });
  // An automation should keep the template, so that is what is offered first.
  await expect(yaml).toHaveValue(
    /value: '\{\{ states\(''sensor.office_temperature''\) \}\} °C'/,
  );
  await dialog.getByLabel(/Keep templates/).uncheck();
  await expect(dialog.getByLabel(/Keep templates/)).toBeFocused();
  await expect(yaml).toHaveValue(/value: 21\.3 °C/);
  await dialog.getByLabel(/Keep templates/).check();
  await dialog.getByRole("tab", { name: "Automation action" }).click();
  await expect(yaml).toHaveValue(/action: ble_esl\.write/);
  await expect(yaml).toHaveValue(/\{\{ states/);
});

test("a pasted payload becomes elements and what cannot be placed is listed", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Import YAML" }).click();
  const dialog = page.locator("ble-esl-import-dialog dialog");
  await dialog
    .getByLabel("YAML to import")
    .fill(
      "[{type: circle, x: 40, y: 40, radius: 12}, {type: text, value: no y, x: 4}, {type: rectangle, x_start: 90, y_start: 80, x_end: 120, y_end: 100}]",
    );
  await dialog.getByRole("button", { name: "Add to display" }).click();
  await expect(dialog.getByRole("status")).toHaveText("2 placed, 1 skipped.");
  await expect(dialog.locator(".issues li")).toContainText("#2 text");
  await expect(page.locator(".layer")).toHaveCount(2);
  await expect(page.locator("img.exact")).toBeVisible();
  // The elements are there already: only closing is left.
  await expect(
    dialog.getByRole("button", { name: "Add to display" }),
  ).toHaveCount(0);
  await dialog.getByRole("button", { name: "Close" }).click();
  await expect(page.locator("ble-esl-import-dialog")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Import YAML" })).toBeFocused();
});

test("a payload that is not YAML says so and changes nothing", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Import YAML" }).click();
  const dialog = page.locator("ble-esl-import-dialog dialog");
  await dialog.getByLabel("YAML to import").fill("just some words");
  await dialog.getByRole("button", { name: "Add to display" }).click();
  await expect(dialog.getByRole("status")).toContainText("Paste a payload");
  await expect(page.locator(".layer")).toHaveCount(0);
});

test("pressing Add twice adds the payload once", async ({ page }) => {
  await page.getByRole("button", { name: "Import YAML" }).click();
  const dialog = page.locator("ble-esl-import-dialog dialog");
  await dialog
    .getByLabel("YAML to import")
    .fill("[{type: circle, x: 40, y: 40, radius: 12}]");
  await dialog.getByRole("button", { name: "Add to display" }).dblclick();
  await expect(page.locator(".layer")).toHaveCount(1);
});

test("a sensor converts to elements whose value is a template", async ({
  page,
  request,
}) => {
  // A sensor template saved by an earlier test would expand the sensor into
  // more elements than the plain one converted here.
  await request.post("/reset");
  await pickSensor(page, "sensor.office_temperature");
  await expect(page.locator("img.exact")).toBeVisible();
  await page.getByRole("button", { name: "Convert to elements" }).click();
  await expect(page.locator(".status")).toContainText(
    "drawn exactly as before",
  );
  await expect(page.locator(".layer")).toHaveCount(3);
  await page.getByRole("button", { name: "Payload YAML" }).click();
  const yaml = page
    .locator("ble-esl-yaml-dialog dialog")
    .getByLabel("YAML", { exact: true });
  await expect(yaml).toHaveValue(/states\(''sensor\.office_temperature''\)/);
  // Undo brings the sensor back as one element.
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  await expect(page.locator(".layer")).toHaveCount(1);
});

test("pressing Convert twice converts once", async ({ page, request }) => {
  await request.post("/reset");
  await pickSensor(page, "sensor.office_temperature");
  await expect(page.locator("img.exact")).toBeVisible();
  await page.getByRole("button", { name: "Convert to elements" }).dblclick();
  await expect(page.locator(".layer")).toHaveCount(3);
});

test("a layer can be deleted from the layer list", async ({ page }) => {
  await page.locator('[data-add="text"]').click();
  await page.locator('[data-add="rectangle"]').click();
  await expect(page.locator(".layer")).toHaveCount(2);
  await page
    .locator(".layer-row")
    .first()
    .getByRole("button", { name: /Delete/ })
    .click();
  await expect(page.locator(".layer")).toHaveCount(1);
  expect(await page.evaluate(() => window.panel.document.elements.length)).toBe(
    1,
  );
});

test("deleting another layer keeps the selection", async ({ page }) => {
  await page.locator('[data-add="text"]').click();
  await page.locator('[data-add="rectangle"]').click();
  const kept = await page.evaluate(() => window.panel.selected);
  await page
    .locator(".layer-row")
    .last()
    .getByRole("button", { name: /Delete/ })
    .click();
  expect(await page.evaluate(() => window.panel.selected)).toBe(kept);
  await expect(page.locator(".layer")).toHaveCount(1);
});

test("new elements do not land exactly on top of each other", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await page.locator('[data-add="text"]').click();
  const positions = await page.evaluate(() =>
    window.panel.document.elements.map((el) => `${el.x},${el.y}`),
  );
  expect(new Set(positions).size).toBe(2);
});

test("undo keeps the selection when the element still exists", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await page.locator(".el.selected").focus();
  await page.keyboard.press("ArrowRight");
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  expect(await page.evaluate(() => window.panel.element?.x)).toBe(8);
});

test("a number outside its range is corrected in the field", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await page.locator("details.advanced summary").click();
  const field = page.locator('[data-property="max_lines"]');
  await field.fill("50");
  await field.press("Tab");
  await expect(field).toHaveValue("20");
  expect(await page.evaluate(() => window.panel.element.max_lines)).toBe(20);
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  expect(
    await page.evaluate(() => window.panel.element.max_lines),
  ).toBeUndefined();
  const size = page.locator('[data-property="font_size"]');
  await size.fill("4");
  await size.press("Tab");
  await expect(size).toHaveValue("8");
});

test("Ctrl+S inside a field saves instead of opening the browser dialog", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await page.locator('[data-property="x"]').focus();
  await page.keyboard.press("Control+s");
  await expect
    .poll(() => page.evaluate(() => window.panel.status))
    .toBe("Display saved");
});

test("Refresh tags keeps the tag being edited and its unsaved design", async ({
  page,
}) => {
  await page.locator("#tag").selectOption("demo-discovery");
  await page.locator('[data-add="text"]').click();
  await page.evaluate(() => (window.__oldTags = window.panel.tags));
  await page.locator('[data-action="reload"]').click();
  await page.waitForFunction(() => window.panel.tags !== window.__oldTags);
  expect(await page.evaluate(() => window.panel.document.elements.length)).toBe(
    1,
  );
  expect(await page.evaluate(() => window.panel.tag.entry_id)).toBe(
    "demo-discovery",
  );
});

test("entering the designer shows loading progress under the header until the tags are in", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  await page.route("**/api/designer", async (route) => {
    if (route.request().postDataJSON().action === "list") await gate;
    await route.continue();
  });
  await page.goto("/");
  await expect(page.locator("header h1")).toBeVisible();
  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(page.locator(".loading")).toContainText("devices");
  await expect(page.locator(".toolbar")).toHaveCount(0);
  await expect(page.locator(".workspace")).toHaveCount(0);
  await expect(page.locator('[data-action="template-mode"]')).toBeDisabled();
  release();
  await expect(page.locator(".workspace")).toBeVisible();
  await expect(page.locator(".loading")).toHaveCount(0);
  await expect(page.locator('[data-action="template-mode"]')).toBeEnabled();
});

test("a failed first load shows the error and Retry recovers", async ({
  page,
}) => {
  let fail = true;
  await page.route("**/api/designer", async (route) => {
    if (fail && route.request().postDataJSON().action === "specs")
      await route.fulfill({ status: 500, body: "boom" });
    else await route.continue();
  });
  await page.goto("/");
  await expect(page.locator(".loading .error")).toContainText("boom");
  await expect(page.locator(".workspace")).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".workspace")).toBeVisible();
  await expect(page.locator(".loading")).toHaveCount(0);
});

test("Refresh tags keeps the editor on screen while it reloads", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  let hold = false;
  await page.route("**/api/designer", async (route) => {
    if (hold && route.request().postDataJSON().action === "list") await gate;
    await route.continue();
  });
  await page.locator('[data-add="text"]').click();
  hold = true;
  await page.locator('[data-action="reload"]').click();
  await expect(page.locator('[data-action="reload"]')).toBeDisabled();
  await expect(page.locator(".workspace")).toBeVisible();
  await expect(page.locator('[data-action="template-mode"]')).toBeDisabled();
  await expect(page.locator(".loading")).toHaveCount(0);
  release();
  await expect(page.locator('[data-action="reload"]')).toBeEnabled();
  expect(await page.evaluate(() => window.panel.document.elements.length)).toBe(
    1,
  );
});

test("layers can be hidden and reordered, and the display background is set from the properties", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  await page.locator('[data-add="rectangle"]').click();
  const order = () =>
    page.evaluate(() => window.panel.document.elements.map((el) => el.type));
  expect(await order()).toEqual(["text", "rectangle"]);
  // The list shows the front element first; "Move forward" on the text lifts it.
  await page
    .getByRole("button", { name: /^Move .* forward$/ })
    .last()
    .click();
  expect(await order()).toEqual(["rectangle", "text"]);
  await page
    .getByRole("button", { name: /^Hide / })
    .first()
    .click();
  expect(
    await page.evaluate(() => window.panel.document.elements.at(-1).visible),
  ).toBe(false);
  await expect(page.locator(".el.hidden-el")).toHaveCount(1);
  await page.getByRole("button", { name: /^Show / }).click();
  await page.locator(".canvas-wrap").click({ position: { x: 4, y: 4 } });
  expect(await page.evaluate(() => window.panel.selected)).toBeNull();
  await expect(page.locator(".inspector .group-title")).toHaveText("Display");
  await page
    .getByRole("button", { name: "Background: black", exact: true })
    .click();
  expect(await page.evaluate(() => window.panel.document.background)).toBe(
    "black",
  );
  await expect(page.locator(".stage")).toHaveCSS(
    "background-color",
    "rgb(0, 0, 0)",
  );
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  expect(await page.evaluate(() => window.panel.document.background)).toBe(
    "white",
  );
});

test("the inspector groups its fields and an error message can be dismissed", async ({
  page,
}) => {
  await page.locator('[data-add="text"]').click();
  const titles = await page
    .locator(".inspector .group-title")
    .allTextContents();
  expect(titles).toEqual(["Content", "Position & size (px)", "Style"]);
  await expect(page.locator("details.advanced")).toBeVisible();
  await page.evaluate(() => window.panel.report(new Error("Broken")));
  await expect(page.locator(".status")).toContainText("Broken");
  await page.getByRole("button", { name: "Dismiss message" }).click();
  await expect(page.locator(".status.error")).toHaveCount(0);
  await page.locator('[data-property="x"]').fill("12");
  await expect(page.locator("#dirty-badge")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save (unsaved changes)" }),
  ).toBeVisible();
});

test("the add-element hints show for a display and not for sensor templates", async ({
  page,
}) => {
  await expect(page.locator("#library .hint")).toHaveCount(2);
  await page.getByRole("button", { name: "Sensor templates" }).click();
  await expect(page.locator("#library .hint")).toHaveCount(1);
});

test("new automation uses the unsaved design and current ESL with no triggers", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const requests = [];
  await page.route("**/api/config/automation/config/*", async (route) => {
    requests.push({
      path: route.request().url(),
      config: route.request().postDataJSON(),
    });
    await route.fulfill({ json: { result: "ok" } });
  });
  await page
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  const dialog = page.locator("ble-esl-yaml-dialog");
  await expect(dialog).toContainText("No triggers are configured");
  await expect(dialog.locator("textarea")).toHaveValue(/demo-device-0/);
  await dialog.getByLabel("Name", { exact: true }).fill("Room update");
  await dialog
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  await expect(
    dialog.getByRole("link", { name: "Edit automation" }),
  ).toBeVisible();
  expect(requests).toHaveLength(1);
  const { path, config } = requests[0];
  expect(path.endsWith(config.id)).toBe(true);
  expect(config.alias).toBe("Room update");
  expect(config.triggers).toEqual([]);
  expect(config.conditions).toEqual([]);
  expect(config.actions[0].action).toBe("ble_esl.write");
  expect(config.actions[0].target).toEqual({ device_id: "demo-device-0" });
  expect(config.actions[0].data.payload).toHaveLength(1);
  expect(config.actions[0].data.payload[0].value).toBe("Your text");
  await expect(page.locator(".el")).toHaveCount(1);
});

test("failed automation creation can retry the same ID without losing the name", async ({
  page,
}) => {
  const configs = [];
  await page.route("**/api/config/automation/config/*", async (route) => {
    configs.push(route.request().postDataJSON());
    await route.fulfill(
      configs.length === 1
        ? { status: 500, body: "Cannot save" }
        : { json: { result: "ok" } },
    );
  });
  await page
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  const dialog = page.locator("ble-esl-yaml-dialog");
  await dialog.getByLabel("Name", { exact: true }).fill("My ESL");
  await dialog
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  await expect(dialog.getByRole("status")).toContainText("Cannot save");
  await expect(dialog.getByLabel("Name", { exact: true })).toHaveValue(
    "My ESL",
  );
  await dialog
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  await expect(
    dialog.getByRole("link", { name: "Edit automation" }),
  ).toBeVisible();
  expect(configs).toHaveLength(2);
  expect(configs[0].id).toBe(configs[1].id);
});

test("design template: gallery applies elements and prefills the automation", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await expect(gallery).toContainText("Date label");
  await gallery.getByRole("button", { name: /Date label/ }).click();
  await gallery.getByLabel("Update time").fill("18:30:15");
  await gallery.getByRole("button", { name: "Add to display" }).click();
  await expect(gallery).toHaveCount(0);
  await expect(page.locator(".el")).toHaveCount(2);

  const configs = [];
  await page.route("**/api/config/automation/config/*", async (route) => {
    configs.push(route.request().postDataJSON());
    await route.fulfill({ json: { result: "ok" } });
  });
  await page
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  const dialog = page.locator("ble-esl-yaml-dialog");
  await expect(dialog).not.toContainText("No triggers are configured");
  await dialog
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  await expect(
    dialog.getByRole("link", { name: "Edit automation" }),
  ).toBeVisible();
  expect(configs[0].triggers).toEqual([{ trigger: "time", at: "18:30:15" }]);
  expect(configs[0].actions[0].data.payload[0].value).toContain("now()");
  expect(errors).toEqual([]);
});

test("design template: replace and create automation in one step", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByRole("button", { name: /Date label/ }).click();
  await gallery
    .getByRole("button", { name: "Replace and create automation" })
    .click();
  await expect(page.locator("ble-esl-yaml-dialog")).toContainText(
    "The template's triggers are included",
  );
});

test("design template: a missing font reports the error and keeps the display", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByRole("button", { name: /Date label/ }).click();
  await gallery.getByLabel("Font").fill("Missing.ttf");
  await gallery.getByRole("button", { name: "Add to display" }).click();
  await expect(gallery).toContainText("Font not found");
  await expect(page.locator(".el")).toHaveCount(0);
});

test("design template triggers are dropped once the template's elements are gone", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByRole("button", { name: /Date label/ }).click();
  await gallery.getByRole("button", { name: "Add to display" }).click();
  await page.getByRole("button", { name: "Undo", exact: false }).click();
  await page.getByRole("button", { name: "Redo", exact: false }).click();
  await page.evaluate(() => {
    window.panel.document.elements = [];
    window.panel.render();
  });
  await page
    .getByRole("button", { name: "Create automation", exact: true })
    .click();
  await expect(page.locator("ble-esl-yaml-dialog")).toContainText(
    "No triggers are configured",
  );
});

test("design template: the current design can be saved and applied again", async ({
  page,
}) => {
  await pickSensor(page, "sensor.office_temperature");
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByLabel("Design template name").fill("Office temperature");
  await gallery.getByRole("button", { name: "Save as template" }).click();
  await expect(gallery).toContainText("Saved template office_temperature");
  await expect(gallery).toContainText("My template");
  await expect(
    gallery.locator('img[data-preview="office_temperature"]'),
  ).toHaveAttribute("src", /^data:image\/png/);
  await expect(gallery.getByLabel("Design template name")).toHaveValue("");
  await gallery.getByRole("button", { name: /Office temperature/ }).click();
  await gallery.getByRole("button", { name: "Replace display" }).click();
  await expect(gallery).toHaveCount(0);
  await expect(page.locator(".el").first()).toBeVisible();
});

test("design template: an entity parameter offers matching entities and checks the choice", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByRole("button", { name: /Weather now/ }).click();
  const input = gallery.getByLabel("Weather entity");
  await expect(input).toHaveValue("weather.home");
  await expect(gallery.locator("datalist option")).toHaveCount(1);
  await input.fill("weather.nowhere");
  await gallery.getByRole("button", { name: "Add to display" }).click();
  await expect(gallery).toContainText("Entity not found: weather.nowhere");
  await expect(page.locator(".el")).toHaveCount(0);
  await input.fill("weather.home");
  await gallery.getByLabel("Update every (minutes)").selectOption("10");
  await gallery.getByRole("button", { name: "Add to display" }).click();
  await expect(gallery).toHaveCount(0);
  await expect(page.locator(".el").first()).toBeVisible();
});

test("design template: an entity default that does not exist gives way to one that does", async ({
  page,
}) => {
  await page.evaluate(() => {
    const states = { ...window.panel.hass.states };
    delete states["weather.home"];
    states["weather.forecast_home"] = {
      entity_id: "weather.forecast_home",
      state: "sunny",
      attributes: { friendly_name: "Forecast" },
    };
    window.panel.hass = { ...window.panel.hass, states };
  });
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByRole("button", { name: /Weather now/ }).click();
  await expect(gallery.getByLabel("Weather entity")).toHaveValue(
    "weather.forecast_home",
  );
  await gallery.getByLabel("Weather entity").fill("weather.mine");
  await gallery.getByLabel("Font").fill("CookieRunBold.ttf");
  await expect(gallery.getByLabel("Weather entity")).toHaveValue(
    "weather.mine",
  );
});

test("design template: thumbnails load in the gallery and the form preview follows the parameters", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  const thumbs = gallery.locator("img[data-preview]");
  await expect(thumbs.first()).toHaveAttribute("src", /^data:image\/png/);
  expect(await thumbs.count()).toBeGreaterThan(3);
  await gallery.getByRole("button", { name: /Message/ }).click();
  const preview = gallery.locator("img[data-form-preview]");
  await expect(preview).toHaveAttribute("src", /^data:image\/png/);
  const before = await preview.getAttribute("src");
  await gallery.getByLabel("Text", { exact: true }).fill("A different message");
  await expect
    .poll(async () => await preview.getAttribute("src"))
    .not.toBe(before);
});

test("design template: an invalid parameter hides the stale preview and says why", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByRole("button", { name: /Wi-Fi QR/ }).click();
  const preview = gallery.locator("img[data-form-preview]");
  await expect(preview).toHaveAttribute("src", /^data:image\/png/);
  await gallery.getByLabel("Network name (SSID)").fill("bad;name");
  await expect(gallery.locator("[data-form-preview-note]")).toContainText(
    "ssid",
  );
  await expect(preview).toBeHidden();
  await gallery.getByLabel("Network name (SSID)").fill("good");
  await expect(preview).toHaveAttribute("src", /^data:image\/png/);
});

test("design template: the preview error stays visible after a re-render", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Browse templates", exact: true })
    .click();
  const gallery = page.locator("ble-esl-template-dialog");
  await gallery.getByRole("button", { name: /Wi-Fi QR/ }).click();
  await gallery.getByLabel("Network name (SSID)").fill("bad;name");
  await expect(gallery.locator("[data-form-preview-note]")).toContainText(
    "ssid",
  );
  await page.evaluate(() => {
    window.panel.hass = { ...window.panel.hass, locale: { language: "ko" } };
  });
  await expect(gallery.locator("[data-form-preview-note]")).toContainText(
    "ssid",
  );
});
