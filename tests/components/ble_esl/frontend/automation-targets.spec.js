import { test, expect } from "@playwright/test";

// The designer authors automations: a tag opens blank, a linked automation's
// design is loaded into it, and the design can be saved into any automation
// whose ble_esl.write action targets the tag.

const savedDocument = {
  version: 1,
  background: "white",
  elements: [
    {
      id: "server-saved",
      type: "text",
      x: 8,
      y: 8,
      width: 120,
      height: 32,
      text: "Stored on the server",
      font_size: 18,
      color: "black",
    },
  ],
};

const automation = async (request, id) =>
  (await request.get(`/api/config/automation/config/${id}`)).json();

const withoutWriteData = (config, index) => {
  const copy = structuredClone(config);
  const data = copy.actions[index].data;
  for (const key of ["payload", "design", "design_specs", "rotate"])
    delete data[key];
  return copy;
};

test.beforeEach(async ({ page, request }) => {
  await request.post("/reset");
  await page.goto("/?manager");
  await expect(page.locator(".card")).toHaveCount(2);
});

test("a tag opens blank even with a stored design; its browser draft survives a reload", async ({
  page,
  request,
}) => {
  await request.post("/api/designer", {
    data: {
      action: "save",
      entry_id: "demo-writable",
      document: savedDocument,
    },
  });
  // The list the editor boots from now carries the stored design.
  await page.reload();
  await expect(page.locator(".card")).toHaveCount(2);
  expect(
    await page.evaluate(
      () =>
        window.manager.tags.find((tag) => tag.entry_id === "demo-writable")
          .document?.elements?.length,
    ),
  ).toBe(1);
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator("ble-esl-designer .toolbar")).toBeVisible();
  await expect(page.locator(".el")).toHaveCount(0);
  expect(
    await page.evaluate(() => window.manager.editor.document.elements),
  ).toEqual([]);
  await expect(page.locator("#dirty-badge")).toBeHidden();

  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.locator(".el")).toHaveCount(1);
  // Navigating inside HA removes the panel without beforeunload.
  await page.evaluate(() => window.manager.remove());
  await page.reload();
  await expect(page).toHaveURL(/tag=demo-writable/);
  await expect(page.locator(".el")).toHaveCount(1);
  await expect(page.locator("#dirty-badge")).toBeVisible();
  expect(
    await page.evaluate(() =>
      window.manager.editor.document.elements.map((element) => element.id),
    ),
  ).not.toContain("server-saved");
});

test("a loaded automation's design saves into a different matching automation only", async ({
  page,
  request,
}) => {
  const morning = await automation(request, "morning");
  const temperature = await automation(request, "temperature");
  const night = await automation(request, "night");
  await page
    .locator('[data-action="automations"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("dialog", { name: "Connected automations" })
    .getByRole("button", { name: "Edit automation design", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save to automation", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => window.manager.automationEditSource.configId),
  ).toBe("morning");
  await expect(page.locator(".el")).toHaveCount(1);
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.locator(".el")).toHaveCount(2);

  await page
    .getByRole("button", { name: "Save to another automation…", exact: true })
    .click();
  const chooser = page.getByRole("dialog", {
    name: "Choose the automation to save to:",
  });
  await expect(chooser).toBeVisible();
  // The automation being edited is the plain Save's target, not offered here.
  await expect(chooser.getByRole("radio")).toHaveCount(2);
  await expect(
    chooser.getByRole("radio", { name: "Morning information" }),
  ).toHaveCount(0);
  await chooser.getByRole("radio", { name: "Temperature display" }).check();
  await chooser.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator(".message")).toContainText(
    "Saved to Temperature display.",
  );

  const saved = await automation(request, "temperature");
  const data = saved.actions[1].data;
  expect(data.payload).toHaveLength(2);
  expect(data.design).toEqual(expect.any(String));
  expect(data.background).toBe("white");
  expect(data.rotate).toBeUndefined();
  // Only the write action's design data changed.
  expect(withoutWriteData(saved, 1)).toEqual(withoutWriteData(temperature, 1));
  expect(await automation(request, "morning")).toEqual(morning);
  expect(await automation(request, "night")).toEqual(night);
  // Still editing the morning automation, whose changes are not saved yet.
  await expect(page.locator("#dirty-badge")).toBeVisible();
  await expect(page.locator(".editor-context")).toContainText(
    "Morning information",
  );
  await expect(
    page.getByRole("button", { name: "Save to automation", exact: true }),
  ).toBeVisible();

  // Loading the target shows the design that was saved into it.
  await page.evaluate(() => {
    window.confirm = () => true;
    window.manager.editAutomation("demo-writable", "automation.temperature");
  });
  await expect
    .poll(() =>
      page.evaluate(() => window.manager.automationEditSource?.configId),
    )
    .toBe("temperature");
  await expect(page.locator(".el")).toHaveCount(2);
});

test("a blank design saves into an existing automation and picks its write action", async ({
  page,
  request,
}) => {
  const original = await automation(request, "morning");
  const config = structuredClone(original);
  const write = config.actions[1];
  config.actions = [
    config.actions[0],
    { ...structuredClone(write), alias: "First screen" },
    { ...structuredClone(write), alias: "Second screen" },
  ];
  await request.post("/api/config/automation/config/morning", {
    data: config,
  });
  const temperature = await automation(request, "temperature");
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await expect(page.locator(".el")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Save to automation", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await expect(page.locator("#dirty-badge")).toBeVisible();

  const save = page.getByRole("button", {
    name: "Save to existing automation…",
    exact: true,
  });
  // Cancelling the choice writes nothing.
  await save.click();
  const chooser = page.getByRole("dialog", {
    name: "Choose the automation to save to:",
  });
  await expect(chooser.getByRole("radio")).toHaveCount(3);
  await chooser.getByRole("button", { name: "Cancel" }).click();
  await expect(chooser).toHaveCount(0);
  expect(await automation(request, "morning")).toEqual(config);

  await save.click();
  await chooser.getByRole("radio", { name: "Morning information" }).check();
  await chooser.getByRole("button", { name: "Continue" }).click();
  const actions = page.getByRole("dialog", {
    name: "Choose the write action to replace:",
  });
  await expect(actions.getByRole("radio")).toHaveCount(2);
  await actions.getByRole("radio", { name: "Second screen" }).check();
  await actions.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator(".message")).toContainText(
    "Saved to Morning information.",
  );

  const saved = await automation(request, "morning");
  expect(saved.actions[1]).toEqual(config.actions[1]);
  expect(saved.actions[2].data.payload).toHaveLength(1);
  expect(saved.actions[2].data.design).toEqual(expect.any(String));
  expect(withoutWriteData(saved, 2)).toEqual(withoutWriteData(config, 2));
  expect(await automation(request, "temperature")).toEqual(temperature);
  // The design now lives in that automation: nothing is left unsaved.
  await expect(page.locator("#dirty-badge")).toBeHidden();
});

test("saving into an automation keeps the design's orientation", async ({
  page,
  request,
}) => {
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.evaluate(() => window.manager.editor.setTagOrientation(90));
  await page
    .getByRole("button", { name: "Save to existing automation…", exact: true })
    .click();
  const chooser = page.getByRole("dialog", {
    name: "Choose the automation to save to:",
  });
  await chooser.getByRole("radio", { name: "Night screen" }).check();
  await chooser.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator(".message")).toContainText(
    "Saved to Night screen.",
  );
  expect((await automation(request, "night")).actions[1].data.rotate).toBe(90);
});

test("a restored draft saved into an automation is no longer unsaved after a reload", async ({
  page,
  request,
}) => {
  const card = page.locator('.card[data-entry="demo-writable"]');
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page.evaluate(() => window.manager.remove());
  await page.reload();
  await expect(page.locator(".el")).toHaveCount(1);
  await expect(page.locator("#dirty-badge")).toBeVisible();

  await page
    .getByRole("button", { name: "Save to existing automation…", exact: true })
    .click();
  const chooser = page.getByRole("dialog", {
    name: "Choose the automation to save to:",
  });
  await chooser.getByRole("radio", { name: "Night screen" }).check();
  await chooser.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator(".message")).toContainText(
    "Saved to Night screen.",
  );
  await expect(page.locator("#dirty-badge")).toBeHidden();
  expect(
    (await automation(request, "night")).actions[1].data.payload,
  ).toHaveLength(1);

  await page.evaluate(() => window.manager.remove());
  await page.reload();
  await expect(page).toHaveURL(/tag=demo-writable/);
  await expect(page.locator("ble-esl-designer .toolbar")).toBeVisible();
  await expect(page.locator(".el")).toHaveCount(0);
  await expect(page.locator("#dirty-badge")).toBeHidden();
  await page.locator('[data-action="dashboard"]').click();
  await expect(card).toBeVisible();
  await expect(card.locator(".badge.draft")).toHaveCount(0);
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("ble_esl_designer_drafts"),
    ),
  ).toBeNull();
});

test("no action of the automation being edited is offered as another automation", async ({
  page,
  request,
}) => {
  const original = await automation(request, "morning");
  const config = structuredClone(original);
  const write = config.actions[1];
  config.actions = [
    config.actions[0],
    { ...structuredClone(write), alias: "First screen" },
    { ...structuredClone(write), alias: "Second screen" },
  ];
  await request.post("/api/config/automation/config/morning", {
    data: config,
  });
  await page.evaluate(() => {
    window.manager.editAutomation("demo-writable", "automation.morning");
  });
  const actions = page.getByRole("dialog", {
    name: "Choose the write action to import:",
  });
  await actions.getByRole("radio", { name: "First screen" }).check();
  await actions.getByRole("button", { name: "Continue" }).click();
  await expect(
    page.getByRole("button", { name: "Save to automation", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page
    .getByRole("button", { name: "Save to another automation…", exact: true })
    .click();
  const chooser = page.getByRole("dialog", {
    name: "Choose the automation to save to:",
  });
  await expect(chooser.getByRole("radio")).toHaveCount(2);
  await expect(
    chooser.getByRole("radio", { name: "Morning information" }),
  ).toHaveCount(0);
  await expect(
    chooser.getByRole("radio", { name: "Night screen" }),
  ).toHaveCount(1);
  await chooser.getByRole("button", { name: "Cancel" }).click();
  expect(await automation(request, "morning")).toEqual(config);
});
