import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page, request }) => {
  await request.post("/reset");
  await page.goto("/");
  await page.waitForFunction(() => window.panel?.tag);
  await page.evaluate(() => {
    const panel = window.panel;
    panel.beginAutomationSession("preview-parameters-test");
    panel._automationSessionPending = false;
    panel._automationSaveMode = true;
    panel.busy = false;
    panel.dirty = false;
    panel.render();
  });
});

async function openParameters(page, values, missingName = null) {
  await page.evaluate(
    ({ values, missingName }) => {
      window.parameterRequest = window.panel.requestPreviewVariables(
        values,
        missingName,
      );
    },
    { values, missingName },
  );
  return page.locator("ble-esl-preview-parameters-dialog");
}

test("typed values validate per field and remain separate from the design", async ({
  page,
}) => {
  const designBefore = await page.evaluate(() => {
    window.panel.document.elements = [
      { id: "source", type: "text", text: "{{ greeting }}", x: 1, y: 2 },
    ];
    window.panel._automationPreviewVariables = { original: "kept" };
    return structuredClone(window.panel.document);
  });
  const modal = await openParameters(
    page,
    {
      enabled: false,
      count: 4,
      settings: { contrast: 2 },
      labels: ["a", "b"],
      optional: null,
    },
    "greeting",
  );
  await expect(modal.getByRole("dialog")).toBeVisible();
  await expect(modal.getByRole("status")).toContainText("greeting");
  await modal
    .locator('[data-value][aria-label="enabled"]')
    .selectOption("true");
  await modal.locator('[data-value][aria-label="count"]').fill("Infinity");
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect(
    modal.locator('[data-value][aria-label="count"]'),
  ).toHaveAttribute("aria-invalid", "true");
  await expect(modal.getByRole("alert")).toContainText("finite number");
  await expect(modal.getByRole("dialog")).toBeVisible();

  await modal.locator('[data-value][aria-label="count"]').fill("12.5");
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect(modal.getByRole("alert")).toContainText("missing parameter");
  await expect(modal.getByRole("dialog")).toBeVisible();
  await modal.locator('[data-value][aria-label="greeting"]').fill("Hello");
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect(modal).toHaveCount(0);
  await expect
    .poll(() => page.evaluate(() => window.parameterRequest))
    .toEqual({
      enabled: true,
      count: 12.5,
      settings: { contrast: 2 },
      labels: ["a", "b"],
      optional: null,
      greeting: "Hello",
    });
  expect(
    await page.evaluate(() => window.panel._automationPreviewVariables),
  ).toEqual({
    original: "kept",
  });
  expect(await page.evaluate(() => window.panel.document)).toEqual(
    designBefore,
  );
});

test("cancel and stale session responses leave parameter state unchanged", async ({
  page,
}) => {
  await page.evaluate(() => {
    window.panel._automationPreviewVariables = { unchanged: true };
  });
  let modal = await openParameters(page, { unchanged: true }, "first_name");
  await modal.locator('[data-value][aria-label="first_name"]').fill("changed");
  await modal.getByRole("button", { name: "Cancel" }).click();
  await expect
    .poll(() => page.evaluate(() => window.parameterRequest))
    .toBeNull();
  expect(
    await page.evaluate(() => window.panel._automationPreviewVariables),
  ).toEqual({
    unchanged: true,
  });

  modal = await openParameters(page, { unchanged: true }, "second_name");
  await modal.locator('[data-value][aria-label="second_name"]').fill("stale");
  await page.evaluate(() => {
    window.panel._automationSessionToken = "newer-session";
  });
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect
    .poll(() => page.evaluate(() => window.parameterRequest))
    .toBeNull();
  expect(
    await page.evaluate(() => window.panel._automationPreviewVariables),
  ).toEqual({
    unchanged: true,
  });
});

test("language changes preserve an open advanced draft and its focus", async ({
  page,
}) => {
  const modal = await openParameters(page, { count: 3 });
  await modal.locator("details.advanced summary").click();
  const json = modal.getByLabel("Preview parameter object");
  await json.fill('{"unfinished":');
  await modal.evaluate((element) =>
    element.updateHass({ locale: { language: "ko" } }),
  );
  const translatedJson = modal.getByLabel("미리보기 변수 객체");
  await expect(translatedJson).toHaveValue('{"unfinished":');
  await expect(modal.locator("h2")).toHaveText("미리보기 변수");
  await expect(modal.locator("details.advanced")).toHaveAttribute("open", "");
  await expect(translatedJson).toBeFocused();
  await modal.getByRole("button", { name: "취소" }).click();
  await expect
    .poll(() => page.evaluate(() => window.parameterRequest))
    .toBeNull();
});

test("a missing parameter cannot silently default to an empty string", async ({
  page,
}) => {
  const modal = await openParameters(page, {}, "required_name");
  await modal.locator("details.advanced summary").click();
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect(modal.getByRole("alert")).toContainText("missing parameter");
  await expect(modal.getByRole("dialog")).toBeVisible();

  await modal
    .getByLabel("Preview parameter object")
    .fill('{"required_name":"","other":"changed"}');
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect(modal.getByRole("alert")).toContainText("missing parameter");
  await expect(modal.getByRole("dialog")).toBeVisible();
  await modal.getByLabel("Use an empty string for required_name").check();
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect
    .poll(() => page.evaluate(() => window.parameterRequest))
    .toEqual({ required_name: "", other: "changed" });
});

test("explicit empty-string choice persists through parameter row rerenders", async ({
  page,
}) => {
  const modal = await openParameters(page, {}, "required_name");
  const allowEmpty = modal.getByLabel("Use an empty string for required_name");
  await allowEmpty.check();
  await modal.getByRole("button", { name: "Add parameter" }).click();
  await expect(allowEmpty).toBeChecked();
  await modal.locator("[data-type]").last().selectOption("boolean");
  await expect(allowEmpty).toBeChecked();
  await modal.getByRole("button", { name: "Cancel" }).click();
});

test("removing or renaming a required parameter keeps the dialog recoverable", async ({
  page,
}) => {
  const modal = await openParameters(page, {}, "required_name");
  await modal
    .getByRole("button", { name: "Remove parameter required_name" })
    .click();
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect(modal.getByRole("alert")).toContainText("missing parameter");
  await expect(modal.getByRole("dialog")).toBeVisible();

  await modal.getByRole("button", { name: "Add parameter" }).click();
  const row = modal.locator("fieldset").last();
  await row.locator("[data-name]").fill("required_name");
  await row.locator("[data-value]").fill("ready");
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect
    .poll(() => page.evaluate(() => window.parameterRequest))
    .toEqual({ required_name: "ready" });
});

test("parameter actions preserve invalid drafts and use unique trimmed names", async ({
  page,
}) => {
  const modal = await openParameters(page, { parameter_2: 1 });
  const count = modal.locator('[data-value][aria-label="parameter_2"]');
  await count.fill("Infinity");
  await modal.getByRole("button", { name: "Add parameter" }).click();
  await expect(count).toHaveValue("Infinity");
  await expect(modal.getByRole("alert")).toContainText("finite number");

  const type = modal.locator("[data-type]").first();
  await type.selectOption("string");
  await expect(type).toHaveValue("number");
  await expect(count).toHaveValue("Infinity");

  await count.fill("1");
  await modal.getByRole("button", { name: "Add parameter" }).click();
  await expect(modal.locator("fieldset [data-name]").nth(1)).toHaveValue(
    "parameter_3",
  );
  const added = modal.locator("fieldset").nth(1);
  await added.locator("[data-name]").fill("  removable  ");
  await added.locator("[data-remove]").click();
  await expect(modal.locator("fieldset")).toHaveCount(1);
  await modal.getByRole("button", { name: "Cancel" }).click();
});

test("Remove can discard its invalid row while preserving other invalid drafts", async ({
  page,
}) => {
  const modal = await openParameters(page, { count: 1, settings: { a: 1 } });
  const number = modal.locator('[data-value][aria-label="count"]');
  const json = modal.locator('[data-value][aria-label="settings"]');
  await number.fill("Infinity");
  await json.fill("{");
  await modal.getByRole("button", { name: "Remove parameter count" }).click();
  await expect(number).toHaveValue("Infinity");
  await expect(json).toHaveValue("{");
  await expect(modal.getByRole("alert")).toContainText("valid JSON");

  await json.fill('{"a":1}');
  await modal.getByRole("button", { name: "Remove parameter count" }).click();
  await expect(modal.locator("fieldset")).toHaveCount(1);
  await json.fill("{");
  await modal
    .getByRole("button", { name: "Remove parameter settings" })
    .click();
  await expect(modal.locator("fieldset")).toHaveCount(0);
  await modal.getByRole("button", { name: "Cancel" }).click();
});

test("changing a type uses the trimmed parameter name without duplicating keys", async ({
  page,
}) => {
  const modal = await openParameters(page, { original: 2 });
  await modal.locator("[data-name]").fill("  renamed  ");
  await modal.locator("[data-type]").selectOption("string");
  await expect(modal.locator("[data-name]")).toHaveValue("renamed");
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect
    .poll(() => page.evaluate(() => window.parameterRequest))
    .toEqual({ renamed: "" });
});

test("editing preview parameters only updates the session map and clears preview caches", async ({
  page,
}) => {
  const before = await page.evaluate(() => {
    const panel = window.panel;
    panel._automationPreviewVariables = { count: 3 };
    panel.layerPreviews = { previous: "image" };
    panel.layerBounds = { previous: [1, 2] };
    panel.layerOffsets = { previous: [3, 4] };
    panel.layerRecords = [{ id: "previous" }];
    panel.templateEntities = ["sensor.example"];
    panel.preview = { previous: true };
    return structuredClone(panel.document);
  });
  await page.getByRole("button", { name: "Preview parameters" }).click();
  const modal = page.locator("ble-esl-preview-parameters-dialog");
  await modal.locator('[data-value][aria-label="count"]').fill("5");
  await modal.getByRole("button", { name: "Apply preview values" }).click();
  await expect
    .poll(() => page.evaluate(() => window.panel._automationPreviewVariables))
    .toEqual({ count: 5 });
  expect(await page.evaluate(() => window.panel.document)).toEqual(before);
  expect(await page.evaluate(() => window.panel.dirty)).toBe(false);
  expect(await page.evaluate(() => window.panel.layerPreviews)).toEqual({});
  expect(await page.evaluate(() => window.panel.layerBounds)).toEqual({});
  expect(await page.evaluate(() => window.panel.layerOffsets)).toEqual({});
  expect(await page.evaluate(() => window.panel.layerRecords)).toEqual([]);
  expect(await page.evaluate(() => window.panel.templateEntities)).toEqual([]);
});

test("automation save stays a visible text action on mobile and normal save remains unchanged", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const save = page.locator('[data-action="save"]');
  await expect(save).toHaveText("Save to automation");
  await expect(save).toHaveAttribute("aria-label", "Save to automation");
  await expect(save.locator("svg")).toHaveCount(0);
  await page.evaluate(() => window.panel.markDirty());
  await expect(save).toHaveText("Save to automation");
  await expect(save).toHaveAttribute("aria-label", "Save to automation");

  await page.evaluate(() => {
    window.panel.restoreEditorSession(
      null,
      window.panel._automationSessionToken,
    );
    window.panel.render();
  });
  await expect(save).not.toContainText("Save to automation");
  await expect(save.locator("svg")).toHaveCount(1);
});

test("imagespec common fields come first and advanced settings stay open after render", async ({
  page,
}) => {
  await page.evaluate(() => {
    window.panel._automationSessionPending = false;
    window.panel._automationSaveMode = false;
    window.panel.beginAutomationSession("spec-order-test");
    window.panel._automationSessionPending = false;
    window.panel._automationSaveMode = false;
    window.panel.busy = false;
    window.panel.addSpec("text");
  });
  await expect(page.locator('[data-spec="value"]')).toBeVisible();
  await expect(page.locator('[data-spec="size"]')).toBeVisible();
  const layout = await page.evaluate(() => {
    const props = window.panel.shadowRoot.querySelector(".props");
    const value = props.querySelector('[data-spec="value"]').closest("label");
    const size = props.querySelector('[data-spec="size"]').closest("label");
    const position = [...props.querySelectorAll("h3")].find((item) =>
      item.textContent.includes("Position & size"),
    );
    return {
      value: [...props.children].indexOf(value),
      size: [...props.children].indexOf(size),
      position: [...props.children].indexOf(position),
    };
  });
  expect(layout.value).toBeLessThan(layout.position);
  expect(layout.size).toBeLessThan(layout.position);
  const advanced = page.locator("details.spec-advanced");
  await expect(advanced).not.toHaveAttribute("open", "");
  await advanced.locator("summary").click();
  await expect(advanced).toHaveAttribute("open", "");
  await page.waitForFunction(() => window.panel.specAdvancedOpen);
  await page.evaluate(() => window.panel.render());
  await expect(page.locator("details.spec-advanced")).toHaveAttribute(
    "open",
    "",
  );
});

test("nested required diagram and plot fields remain visible before Advanced", async ({
  page,
}) => {
  for (const type of ["diagram", "plot"]) {
    await page.evaluate((specType) => {
      const panel = window.panel;
      panel.document.elements = [];
      panel.selected = null;
      panel.addSpec(specType);
    }, type);
    const required = page.locator('.props [data-spec][data-required="true"]');
    await expect(required.first()).toBeVisible();
    const count = await required.count();
    expect(count).toBeGreaterThan(0);
    for (let index = 0; index < count; index += 1)
      await expect(required.nth(index)).toBeVisible();
    await expect(page.locator("details.spec-advanced")).not.toHaveAttribute(
      "open",
      "",
    );
  }
});
