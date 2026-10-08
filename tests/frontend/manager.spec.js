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
  await expect(
    card.getByRole("button", { name: "Battery 85%", exact: true }),
  ).toBeVisible();
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

test("automation preview seeds only safe sequential literal variables", async ({
  page,
}) => {
  const values = await page.evaluate(() =>
    window.manager.safeAutomationVariables(
      {
        variables: { root: "root literal", dynamic: "root fallback" },
        actions: [
          {
            enabled: false,
            variables: { disabled_value: "must not run" },
          },
          {
            variables: {
              root: "preceding literal",
              dynamic: "{{ states('sensor.example') }}",
            },
          },
          { action: "sensor.read", response_variable: "response_data" },
          {
            parallel: [
              { sequence: [{ variables: { parallel_value: "uncertain" } }] },
            ],
          },
          { action: "ble_esl.write" },
        ],
      },
      ["actions", 4],
    ),
  );
  expect(values).toMatchObject({ root: "preceding literal" });
  expect(values).not.toHaveProperty("dynamic");
  expect(values).not.toHaveProperty("disabled_value");
  expect(values).not.toHaveProperty("response_data");
  expect(values).not.toHaveProperty("parallel_value");
});

test("preview parameters remain outside the saved automation payload", async ({
  page,
  request,
}) => {
  await request.post("/api/config/automation/config/morning", {
    data: {
      id: "morning",
      alias: "Morning",
      variables: {},
      triggers: [{ trigger: "time", at: "07:00:00" }],
      conditions: [],
      actions: [
        {
          action: "ble_esl.write",
          target: { device_id: "demo-device-0" },
          data: {
            background: "white",
            payload: [
              {
                type: "text_fit",
                x: 8,
                y: 8,
                width: 220,
                height: 28,
                value: "{{ font_bold }}",
                color: "black",
              },
            ],
          },
        },
      ],
      mode: "single",
    },
  });
  await page.evaluate(() => {
    window.manager.editAutomation("demo-writable", "automation.morning");
  });
  const parameters = page.getByRole("dialog", { name: "Preview parameters" });
  await expect(parameters).toBeVisible();
  await parameters
    .getByLabel("font_bold", { exact: true })
    .fill("first-preview.ttf");
  await parameters
    .getByRole("button", { name: "Apply preview values" })
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Preview parameters" }).click();
  await parameters
    .getByLabel("font_bold", { exact: true })
    .fill("second-preview.ttf");
  await parameters
    .getByRole("button", { name: "Apply preview values" })
    .click();
  await expect
    .poll(() =>
      page.evaluate(
        () => window.manager.editor._automationPreviewVariables.font_bold,
      ),
    )
    .toBe("second-preview.ttf");
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.locator(".message")).toContainText("Automation saved.");
  const saved = await page.evaluate(() =>
    window.manager.hass.callApi("GET", "config/automation/config/morning"),
  );
  expect(saved.actions[0].data.payload[0].value).toBe("{{ font_bold }}");
  expect(JSON.stringify(saved)).not.toContain("second-preview.ttf");
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

test("automation editing restores the ordinary design, draft and undo history", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const savedState = await page.evaluate(() => {
    const editor = window.manager.editor;
    return {
      document: structuredClone(editor.document),
      undo: structuredClone(editor.undoStack),
      selected: editor.selected,
      dirty: editor.dirty,
    };
  });
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.locator(".message")).toContainText("Automation saved.");
  expect(
    await page.evaluate(() => {
      const event = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    }),
  ).toBe(true);
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  const restored = await page.evaluate(() => {
    const editor = window.manager.editor;
    return {
      document: editor.document,
      undo: editor.undoStack,
      selected: editor.selected,
      dirty: editor.dirty,
    };
  });
  expect(restored).toEqual(savedState);
  await expect(page.locator(".el")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toHaveCount(0);
});

test("imports and repeatedly saves only the selected automation payload", async ({
  page,
}) => {
  const posts = [];
  let savedConfig;
  let reads = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") {
      savedConfig = route.request().postDataJSON();
      posts.push(savedConfig);
      await route.fulfill({ json: { result: "ok" } });
      return;
    }
    if (savedConfig) {
      if (++reads === 2) {
        savedConfig.alias = "Schedule changed elsewhere";
        savedConfig.description = "Updated after import";
        savedConfig.triggers[0].at = "08:00:00";
        savedConfig.conditions[0].state = "on";
        savedConfig.actions[0].data.message = "Updated elsewhere";
      }
      await route.fulfill({ json: savedConfig });
      return;
    }
    const response = await route.fetch();
    savedConfig = await response.json();
    reads++;
    await route.fulfill({ response, json: savedConfig });
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await expect(page.getByLabel("Tag", { exact: true })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Sensor templates", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Send to tag", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.locator(".message")).toContainText("Automation saved.");
  await expect.poll(() => posts.length).toBe(1);
  expect(posts[0].alias).toBe("Schedule changed elsewhere");
  expect(posts[0].description).toBe("Updated after import");
  expect(posts[0].triggers).toEqual([{ trigger: "time", at: "08:00:00" }]);
  expect(posts[0].conditions).toEqual([
    {
      condition: "state",
      entity_id: "binary_sensor.window",
      state: "on",
    },
  ]);
  expect(posts[0].actions[0]).toEqual({
    action: "persistent_notification.create",
    data: { title: "Schedule", message: "Updated elsewhere" },
  });
  expect(posts[0].actions[1].target).toEqual({ device_id: "demo-device-0" });
  expect(posts[0].actions[1].data.background).toBe("white");
  expect(posts[0].actions[1].data.payload).toHaveLength(2);
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect.poll(() => posts.length).toBe(2);
  expect(posts[1].actions[0]).toEqual(posts[0].actions[0]);
  expect(posts[1].actions[1].data.payload).toHaveLength(3);
});

test("finds matching write actions inside nested saved automation sequences", async ({
  page,
}) => {
  const paths = await page.evaluate(() =>
    window.manager.findWriteActions(
      {
        actions: [
          {
            action: "ble_esl.write",
            alias: "Direct",
            target: { device_id: ["tag-device"] },
            data: { payload: [] },
          },
          {
            choose: [
              {
                sequence: [
                  {
                    action: "ble_esl.write",
                    alias: "Nested",
                    target: { entity_id: ["text.tag_alias"] },
                    data: { payload: [] },
                  },
                ],
              },
            ],
          },
          {
            action: "ble_esl.write",
            target: { device_id: "other-device" },
            data: { payload: [{ entity_id: "text.tag_alias" }] },
          },
          {
            service: "ble_esl.write",
            entity_id: "text.tag_alias",
            data: { payload: [] },
          },
          {
            action: "ble_esl.write",
            data: { device_id: "tag-device", payload: [] },
          },
          {
            action: "ble_esl.write",
            target: { device_id: "other-device" },
            data: { device_id: "tag-device", payload: [] },
          },
          {
            action: "ble_esl.write",
            target: { entity_id: "text.other" },
            entity_id: "text.tag_alias",
            data: { payload: [] },
          },
        ],
      },
      { device_id: "tag-device", entity_ids: ["text.tag_alias"] },
    ),
  );
  expect(paths.matches.map((item) => item.label)).toEqual([
    "Direct",
    "Nested",
    "ble_esl.write (3)",
    "ble_esl.write (4)",
    "ble_esl.write (5)",
  ]);
  expect(paths.matches.map((item) => item.path)).toEqual([
    ["actions", 0],
    ["actions", 1, "choose", 0, "sequence", 0],
    ["actions", 3],
    ["actions", 4],
    ["actions", 6],
  ]);
  expect(paths.unsupported).toEqual([]);
});

test("does not infer target identity from payload and reports unsupported target scopes", async ({
  page,
}) => {
  const result = await page.evaluate(() =>
    window.manager.findWriteActions(
      {
        actions: [
          {
            action: "ble_esl.write",
            target: { device_id: "other-device" },
            data: { payload: [{ device_id: "tag-device" }] },
          },
          {
            action: "ble_esl.write",
            target: { area_id: "office" },
            data: { payload: [] },
          },
          {
            action: "ble_esl.write",
            target: {
              device_id: ["tag-device", "{{ states('sensor.target') }}"],
            },
            data: { payload: [] },
          },
        ],
      },
      { device_id: "tag-device", entity_ids: ["text.tag_alias"] },
    ),
  );
  expect(result.matches).toEqual([]);
  expect(result.unsupported).toHaveLength(2);
});

test("edits a unique direct match while preserving unrelated unresolved targets", async ({
  page,
}) => {
  let savedConfig;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") {
      savedConfig = route.request().postDataJSON();
      await route.fulfill({ json: { result: "ok" } });
      return;
    }
    const response = await route.fetch();
    const config = await response.json();
    config.actions.push({
      action: "ble_esl.write",
      target: { area_id: "unrelated_area" },
      data: { payload: [{ type: "text", value: "Untouched" }] },
    });
    await route.fulfill({ response, json: config });
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.locator(".message")).toContainText("Automation saved.");
  expect(savedConfig.actions.at(-1)).toEqual({
    action: "ble_esl.write",
    target: { area_id: "unrelated_area" },
    data: { payload: [{ type: "text", value: "Untouched" }] },
  });
});

test("refuses to save when the automation changed after import", async ({
  page,
}) => {
  let reads = 0;
  let posts = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") {
      posts++;
      await route.fulfill({ json: { result: "ok" } });
      return;
    }
    const response = await route.fetch();
    const config = await response.json();
    if (++reads === 2)
      config.actions[1].data.payload[0].value = "Changed elsewhere";
    await route.fulfill({ response, json: config });
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "selected write action changed since import",
  );
  expect(posts).toBe(0);
});

test("keeps the current design when an automation payload has unsupported elements", async ({
  page,
}) => {
  await page.route("**/api/config/automation/config/*", async (route) => {
    const response = await route.fetch();
    const config = await response.json();
    config.actions[1].data.payload = [{ type: "future_unsupported_kind" }];
    await route.fulfill({ response, json: config });
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "cannot be represented exactly",
  );
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toHaveCount(0);
  await expect(page.locator(".el")).toHaveCount(0);
});

test("does not import an unsupported automation background", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") posts++;
    const response = await route.fetch();
    const config = await response.json();
    config.actions[1].data.background = "purple";
    await route.fulfill({ response, json: config });
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "background is not supported",
  );
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toHaveCount(0);
  expect(posts).toBe(0);
});

test("does not report a background-only edit as saved to an automation", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") posts++;
    await route.continue();
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.evaluate(() => {
    const editor = window.manager.editor;
    editor.document.background = "black";
    editor.edited(false);
  });
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Background is not part of the automation payload",
  );
  expect(posts).toBe(0);
});

test("does not import a delayed automation response after leaving its ESL", async ({
  page,
}) => {
  let started;
  const requestStarted = new Promise((resolve) => (started = resolve));
  let release;
  const delayed = new Promise((resolve) => (release = resolve));
  await page.route("**/api/config/automation/config/*", async (route) => {
    started();
    await delayed;
    await route.continue();
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await requestStarted;
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="edit"][data-entry="demo-discovery"]')
    .click();
  release();
  await expect(page.getByLabel("Tag", { exact: true })).toHaveValue(
    "demo-discovery",
  );
  await expect(page.locator(".el")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toHaveCount(0);
});

test("does not apply a delayed import after returning to the same ESL normally", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page.evaluate(() => {
    const editor = window.manager.editor;
    const prepare = editor.prepareAutomationPayload.bind(editor);
    window.pendingImports = [];
    editor.prepareAutomationPayload = (...args) =>
      new Promise((resolve, reject) =>
        window.pendingImports.push({ args, resolve, reject, prepare }),
      );
    window.manager.editAutomation("demo-writable", "automation.morning");
  });
  await expect
    .poll(() => page.evaluate(() => window.pendingImports.length))
    .toBe(1);
  await page.keyboard.press("Escape");
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  const before = await page.evaluate(() =>
    JSON.stringify(window.manager.editor.document),
  );
  await page.evaluate(() => {
    const pending = window.pendingImports[0];
    pending.prepare(...pending.args).then(pending.resolve, pending.reject);
  });
  await expect(page.getByLabel("Tag", { exact: true })).toHaveValue(
    "demo-writable",
  );
  await expect
    .poll(() => page.evaluate(() => window.manager.editor._automationSaveMode))
    .toBe(false);
  expect(
    await page.evaluate(() => JSON.stringify(window.manager.editor.document)),
  ).toBe(before);
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toHaveCount(0);
});

test("ignores a delayed YAML import after restoring the prior editor session", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const ordinary = await page.evaluate(() =>
    structuredClone(window.manager.editor.document),
  );
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Import YAML", exact: true }).click();
  const dialog = page.locator("ble-esl-import-dialog dialog");
  await dialog.getByLabel("YAML to import").fill("- type: text\n  value: Late");
  await page.evaluate(() => {
    const editor = window.manager.editor;
    const api = editor.api.bind(editor);
    editor.api = (action, args) =>
      action === "import_yaml"
        ? new Promise((resolve) => (window.resolveYamlImport = resolve))
        : api(action, args);
  });
  await dialog.getByRole("button", { name: "Add to display" }).click();
  await expect
    .poll(() => page.evaluate(() => Boolean(window.resolveYamlImport)))
    .toBe(true);
  await page.evaluate(() =>
    window.manager.shadowRoot
      .querySelector('[data-action="dashboard"]')
      .click(),
  );
  const restored = await page.evaluate(() =>
    structuredClone(window.manager.editor.document),
  );
  await page.evaluate(() =>
    window.resolveYamlImport({
      elements: [
        {
          id: "late-import",
          type: "text",
          x: 0,
          y: 0,
          width: 80,
          height: 24,
          text: "Late",
        },
      ],
      issues: [],
      background: "white",
    }),
  );
  await expect(page.locator("ble-esl-import-dialog")).toHaveCount(0);
  expect(restored).toEqual(ordinary);
  expect(await page.evaluate(() => window.manager.editor.document)).toEqual(
    ordinary,
  );
});

test("cancelled YAML import does not mutate the design when its response arrives", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Import YAML", exact: true }).click();
  const dialog = page.locator("ble-esl-import-dialog dialog");
  await dialog.getByLabel("YAML to import").fill("- type: text\n  value: Late");
  await page.evaluate(() => {
    const editor = window.manager.editor;
    const api = editor.api.bind(editor);
    editor.api = (action, args) =>
      action === "import_yaml"
        ? new Promise((resolve) => (window.resolveYamlImport = resolve))
        : api(action, args);
  });
  const original = await page.evaluate(() =>
    structuredClone(window.manager.editor.document),
  );
  await dialog.getByRole("button", { name: "Add to display" }).click();
  await expect
    .poll(() => page.evaluate(() => Boolean(window.resolveYamlImport)))
    .toBe(true);
  await page.keyboard.press("Escape");
  await expect(page.locator("ble-esl-import-dialog")).toHaveCount(0);
  await page.evaluate(() =>
    window.resolveYamlImport({
      elements: [
        {
          id: "cancelled-import",
          type: "text",
          x: 0,
          y: 0,
          width: 80,
          height: 24,
          text: "Late",
        },
      ],
      issues: [],
      background: "white",
    }),
  );
  expect(await page.evaluate(() => window.manager.editor.document)).toEqual(
    original,
  );
});

test("ignores a delayed component conversion after restoring another session", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  const ordinary = await page.evaluate(() =>
    structuredClone(window.manager.editor.document),
  );
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page.evaluate(() => {
    const editor = window.manager.editor;
    const api = editor.api.bind(editor);
    window.pendingConversions = [];
    editor.api = (action, args) =>
      action === "convert"
        ? new Promise((resolve) => window.pendingConversions.push(resolve))
        : api(action, args);
    editor.convertSelected();
  });
  await expect
    .poll(() => page.evaluate(() => window.pendingConversions.length))
    .toBe(1);
  await page.evaluate(() =>
    window.manager.shadowRoot
      .querySelector('[data-action="dashboard"]')
      .click(),
  );
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  expect(await page.evaluate(() => window.manager.editor.document)).toEqual(
    ordinary,
  );
  await page.evaluate(() => {
    window.manager.editor.convertSelected();
  });
  await expect
    .poll(() => page.evaluate(() => window.pendingConversions.length))
    .toBe(2);
  await page.evaluate(() =>
    window.pendingConversions[0]({
      elements: [
        {
          id: "late-conversion",
          type: "text",
          x: 0,
          y: 0,
          width: 80,
          height: 24,
          text: "Late",
        },
      ],
      issues: [],
      different_pixels: 0,
    }),
  );
  await expect
    .poll(() => page.evaluate(() => window.manager.editor.converting))
    .toBe(true);
  expect(await page.evaluate(() => window.manager.editor.document)).toEqual(
    ordinary,
  );
  await page.evaluate(() =>
    window.pendingConversions[1]({
      elements: [
        {
          id: "current-conversion",
          type: "text",
          x: 0,
          y: 0,
          width: 80,
          height: 24,
          text: "Current",
        },
      ],
      issues: [],
      different_pixels: 0,
    }),
  );
  await expect
    .poll(() => page.evaluate(() => window.manager.editor.converting))
    .toBe(false);
});

test("a newer same-ESL import wins over an older delayed import", async ({
  page,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page.evaluate(() => {
    const editor = window.manager.editor;
    const prepare = editor.prepareAutomationPayload.bind(editor);
    window.pendingImports = [];
    editor.prepareAutomationPayload = (...args) =>
      new Promise((resolve, reject) =>
        window.pendingImports.push({ args, resolve, reject, prepare }),
      );
    window.manager.editAutomation("demo-writable", "automation.morning");
  });
  await expect
    .poll(() => page.evaluate(() => window.pendingImports.length))
    .toBe(1);
  await page.evaluate(() => {
    window.manager.editAutomation("demo-writable", "automation.temperature");
  });
  await expect
    .poll(() => page.evaluate(() => window.pendingImports.length))
    .toBe(2);
  await page.evaluate(() => {
    const pending = window.pendingImports[1];
    pending.prepare(...pending.args).then(pending.resolve, pending.reject);
  });
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.evaluate(() => {
    const pending = window.pendingImports[0];
    pending.prepare(...pending.args).then(pending.resolve, pending.reject);
  });
  await expect
    .poll(() =>
      page.evaluate(() => window.manager.automationEditSource?.entity_id),
    )
    .toBe("automation.temperature");
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
});

test("leaving automation edit before cold boot unlocks the editor", async ({
  page,
}) => {
  const savedDocument = {
    version: 1,
    background: "white",
    elements: [
      {
        id: "saved-before-boot",
        type: "text",
        x: 8,
        y: 8,
        width: 90,
        height: 32,
        text: "Saved before boot",
        font_size: 18,
        color: "black",
      },
    ],
  };
  await page.evaluate((document) => {
    window.manager.tags.find(
      (tag) => tag.entry_id === "demo-writable",
    ).document = document;
  }, savedDocument);
  await page.route("**/frontend/icons.json", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 500));
    await route.continue();
  });
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.evaluate((document) => {
    const editor = window.manager.editor;
    const load = editor.load.bind(editor);
    editor.load = (tag) => {
      if (tag.entry_id === "demo-writable") tag.document = document;
      return load(tag);
    };
    window.manager.editAutomation("demo-writable", "automation.morning");
  }, savedDocument);
  await page.locator('[data-action="dashboard"]').click();
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.getByLabel("Tag", { exact: true })).toHaveValue(
    "demo-writable",
  );
  expect(await page.evaluate(() => window.manager.editor.document)).toEqual(
    savedDocument,
  );
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toHaveCount(0);
});

test("keeps edits made while an automation save is in flight dirty", async ({
  page,
}) => {
  let started;
  const requestStarted = new Promise((resolve) => (started = resolve));
  let release;
  const delayed = new Promise((resolve) => (release = resolve));
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") {
      started();
      await delayed;
      await route.fulfill({ json: { result: "ok" } });
      return;
    }
    await route.continue();
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.getByRole("button", { name: "Save to automation" }).click();
  await requestStarted;
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  release();
  await expect(page.locator(".message")).toContainText("Automation saved.");
  await expect(page.locator("#dirty-badge")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
});

test("does not save a newer same-ESL import after an older save waited on uploads", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") posts++;
    await route.continue();
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await page.evaluate(() => {
    window.releaseUploadWait = null;
    window.manager.editor.pendingUploads.add(
      new Promise((resolve) => (window.releaseUploadWait = resolve)),
    );
  });
  await page.getByRole("button", { name: "Save to automation" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.evaluate(() => {
    window.manager.editAutomation("demo-writable", "automation.temperature");
  });
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => window.manager.automationEditSource?.entity_id),
    )
    .toBe("automation.temperature");
  await page.evaluate(() => window.releaseUploadWait());
  await page.waitForTimeout(100);
  expect(posts).toBe(0);
  await expect(
    page.getByRole("button", { name: "Save to automation" }),
  ).toBeVisible();
});

test("rebases to a uniquely matched write action after its path shifts", async ({
  page,
}) => {
  let reads = 0;
  let savedConfig;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") {
      savedConfig = route.request().postDataJSON();
      await route.fulfill({ json: { result: "ok" } });
      return;
    }
    const response = await route.fetch();
    const config = await response.json();
    if (++reads === 2)
      config.actions.splice(1, 0, {
        action: "persistent_notification.create",
        data: { message: "Added elsewhere" },
      });
    await route.fulfill({ response, json: config });
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.locator(".message")).toContainText("Automation saved.");
  expect(savedConfig.actions[0].action).toBe("persistent_notification.create");
  expect(savedConfig.actions[1].data.message).toBe("Added elsewhere");
  expect(savedConfig.actions[2].action).toBe("ble_esl.write");
  expect(savedConfig.actions[2].data.payload).toHaveLength(2);
  expect(savedConfig.actions[2].data.payload[0].value).toBe(
    "Morning information",
  );
});

for (const [caseName, mutate] of [
  ["deleted", (config) => config.actions.splice(1, 1)],
  [
    "retargeted",
    (config) => (config.actions[1].target.device_id = "other-device"),
  ],
]) {
  test(`does not POST when the selected write action is ${caseName}`, async ({
    page,
  }) => {
    let reads = 0;
    let posts = 0;
    await page.route("**/api/config/automation/config/*", async (route) => {
      if (route.request().method() === "POST") {
        posts++;
        await route.fulfill({ json: { result: "ok" } });
        return;
      }
      const response = await route.fetch();
      const config = await response.json();
      if (++reads === 2) mutate(config);
      await route.fulfill({ response, json: config });
    });
    await page
      .locator('[data-action="automations"][data-entry="demo-writable"]')
      .click();
    const dialog = page.getByRole("dialog", { name: "Connected automations" });
    await dialog
      .getByRole("button", { name: "Edit design", exact: true })
      .first()
      .click();
    await expect(page.locator(".el")).toHaveCount(1);
    await page.getByRole("button", { name: "Save to automation" }).click();
    await expect(page.getByRole("alert")).toContainText(
      "selected write action changed since import",
    );
    expect(posts).toBe(0);
  });
}

test("does not POST when export reports a blocking validation error", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") posts++;
    await route.continue();
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page.evaluate(() => {
    window.manager.editor.api = async () => ({
      validation_errors: ["payload[0].width: invalid numeric value"],
      payload_data: [{ type: "text" }],
      writable: true,
    });
  });
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "cannot be saved as a payload",
  );
  expect(posts).toBe(0);
});

test("does not POST a malformed latest automation configuration", async ({
  page,
}) => {
  let reads = 0;
  let posts = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") {
      posts++;
      await route.fulfill({ json: { result: "ok" } });
      return;
    }
    if (++reads === 2) {
      await route.fulfill({ json: { id: "esl_schedule", actions: {} } });
      return;
    }
    await route.continue();
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "latest automation configuration is malformed",
  );
  expect(posts).toBe(0);
});

test("blocks saving when an unchanged selected action becomes ambiguous", async ({
  page,
}) => {
  let reads = 0;
  let posts = 0;
  await page.route("**/api/config/automation/config/*", async (route) => {
    if (route.request().method() === "POST") {
      posts++;
      await route.fulfill({ json: { result: "ok" } });
      return;
    }
    const response = await route.fetch();
    const config = await response.json();
    if (++reads === 2) config.actions.push(structuredClone(config.actions[1]));
    await route.fulfill({ response, json: config });
  });
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  const dialog = page.getByRole("dialog", { name: "Connected automations" });
  await dialog
    .getByRole("button", { name: "Edit design", exact: true })
    .first()
    .click();
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Save to automation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "selected write action changed since import",
  );
  expect(posts).toBe(0);
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
  await expect(
    page
      .locator(".card")
      .first()
      .getByRole("button", { name: "Battery —", exact: true }),
  ).toBeVisible();
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
  // Mimic HA's auto-height custom-panel wrapper, not just a flex container
  // that supplies a definite height to the manager in the demo.
  await page.evaluate(() => {
    document.body.style.cssText = "display:block;height:auto;overflow:visible";
    const wrapper = document.createElement("div");
    window.manager.before(wrapper);
    wrapper.append(window.manager);
  });
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
    [320, 640],
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
    const dashboardHeight = await page
      .locator("#dashboard header")
      .evaluate((node) => node.getBoundingClientRect().height);
    expect(dashboardHeight).toBe(56);
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
      .locator(".editor-content")
      .evaluate((node) => (node.scrollTop = 500));
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
            root.querySelector(".editor-content").scrollTop > 0,
            host.scrollTop === 0,
            nav.height >= 56 && nav.bottom < innerHeight,
            header.height === 56,
            Math.abs(header.top - nav.bottom) < 1,
            Math.abs(toolbar.top - header.bottom) < 1,
          ];
        }),
      )
      .toEqual([true, true, true, true, true, true]);
    expect(await page.evaluate(() => document.scrollingElement.scrollTop)).toBe(
      0,
    );
    await page
      .getByRole("button", { name: "Sensor templates", exact: true })
      .click();
    await page
      .locator(".editor-content")
      .evaluate((node) => (node.scrollTop = 500));
    expect(
      await page.locator(".template-controls").evaluate((node) => {
        const header = node.getRootNode().querySelector("header");
        return (
          node.getBoundingClientRect().top ===
          header.getBoundingClientRect().bottom
        );
      }),
    ).toBe(true);
    if (width === 1440)
      await page.screenshot({ path: "artifacts/manager-fixed-header.png" });
    await page.locator('[data-action="dashboard"]').click();
    await expect(
      page.getByRole("button", { name: "Refresh", exact: true }),
    ).toBeEnabled();
    await expect(page.locator("#dashboard .card")).toHaveCount(2);
  }
});

test("card information aligns and battery stays at the right edge", async ({
  page,
}) => {
  await page.evaluate(() => {
    window.manager.tags[0].title = 'Poshiji 37391810BD4D (PSJ-290 2.9" BWRY)';
    window.manager.tags[1].title = "Short model";
    window.manager.renderCards();
  });
  const metrics = await page.locator("#dashboard .card").evaluateAll((cards) =>
    cards.map((card) => {
      const box = (selector) =>
        card.querySelector(selector).getBoundingClientRect();
      return {
        image: box(".image").top,
        dimensions: box(".dimensions").top,
        right: box(".battery").right - box(".top").right,
        productRight: box(".product").right - box(".top").right,
        aligned:
          (box(".battery").top + box(".battery").bottom) / 2 ===
          (box("h2").top + box("h2").bottom) / 2,
        border: getComputedStyle(card.querySelector(".battery button"))
          .borderTopWidth,
      };
    }),
  );
  expect(metrics[0].image).toBe(metrics[1].image);
  expect(metrics[0].dimensions).toBe(metrics[1].dimensions);
  expect(metrics.map((metric) => metric.right)).toEqual([0, 0]);
  expect(metrics.map((metric) => metric.productRight)).toEqual([0, 0]);
  expect(metrics.map((metric) => metric.aligned)).toEqual([true, true]);
  expect(metrics.map((metric) => metric.border)).toEqual(["0px", "0px"]);
  await expect(page.locator(".battery svg")).toHaveCount(2);
});

test("thumbnail survives rerenders and waits for the next bitmap to load", async ({
  page,
}) => {
  const img = page.locator('[data-entry="demo-writable"] .image img');
  await expect
    .poll(() => img.evaluate((node) => node.naturalWidth))
    .toBeGreaterThan(0);
  await page.evaluate(() => {
    window.originalThumbnail =
      window.manager.shadowRoot.querySelector(".image img");
    window.manager.renderCards();
  });
  expect(await img.evaluate((node) => node === window.originalThumbnail)).toBe(
    true,
  );
  const before = await img.getAttribute("src");
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  let requested = false;
  await page.route("**/*updated=*", async (route) => {
    requested = true;
    await gate;
    await route.continue();
  });
  await page.evaluate(() => {
    const manager = window.manager;
    const image = manager.hass.states["image.demo_0_last_updated_content"];
    manager.hass = {
      ...manager.hass,
      states: {
        ...manager.hass.states,
        [image.entity_id]: { ...image, state: "2026-10-08T02:00:00+00:00" },
      },
    };
  });
  await expect.poll(() => requested).toBe(true);
  await expect(img).toHaveAttribute("src", before);
  expect(
    await img.evaluate(
      (node) => node === window.originalThumbnail && node.naturalWidth > 0,
    ),
  ).toBe(true);
  release();
  await expect(img).not.toHaveAttribute("src", before);
  expect(
    await img.evaluate((node) => node.complete && node.naturalWidth > 0),
  ).toBe(true);
});
