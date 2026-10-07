import { test, expect } from "@playwright/test";

const setLanguage = (page, language) =>
  page.evaluate((language) => {
    const panel = window.manager || window.panel;
    panel.hass = { ...panel.hass, locale: { language } };
  }, language);

test.beforeEach(async ({ request }) => {
  await request.post("/reset");
});

test("HA locale translates dashboard and automations while preserving authored names", async ({
  page,
}) => {
  await page.goto("/?manager&lang=ko-KR");
  await expect(page.getByRole("heading", { name: "ESL 매니저" })).toBeVisible();
  const card = page.locator('[data-entry="demo-writable"]').first();
  await expect(card).toContainText("Living room");
  await expect(card).toContainText("배터리 85%");
  await expect(card).toContainText("마지막 전송 성공");
  await expect(card).toContainText("자동화 3개");
  await expect(page.locator(".summary")).toContainText("ESL 2개");
  await expect(card.locator("img")).toHaveAttribute(
    "alt",
    "Living room의 마지막 전송 성공 이미지",
  );
  await page.screenshot({ path: "artifacts/esl-manager-ko.png" });
  await card.locator('[data-action="automations"]').click();
  await expect(
    page.getByRole("heading", { name: "연결된 자동화" }),
  ).toBeVisible();
  await expect(page.getByLabel("기존 자동화")).toBeVisible();
  await expect(page.locator(".row").first()).toContainText("활성");
  await expect(page.locator(".row").nth(2)).toContainText("비활성");
  const names = await page.locator(".row .name").allTextContents();
  await setLanguage(page, "en");
  await expect(
    page.getByRole("heading", { name: "Connected automations" }),
  ).toBeVisible();
  await expect(page.locator(".row .name")).toHaveText(names);
  await page.getByLabel("Close automations").click();
  await setLanguage(page, "fr");
  await expect(
    page.getByRole("heading", { name: "ESL Manager" }),
  ).toBeVisible();
  await expect(card).toContainText("Battery 85%");
});

test("locale switches retain designer history, nested modal drafts and templates", async ({
  page,
}) => {
  await page.goto("/?manager");
  await page
    .locator('[data-entry="demo-writable"] [data-action="edit"]')
    .click();
  await expect(page.locator("ble-esl-designer .stage")).toBeVisible();
  await page.getByRole("button", { name: "Add text", exact: true }).click();
  await page
    .locator('[data-property="text"]')
    .fill('Save {{ states("sensor.demo_temperature") }}');
  const before = await page.evaluate(() => ({
    document: window.manager.editor.document,
    undo: window.manager.editor.undoStack,
    dirty: window.manager.editor.dirty,
  }));
  await page
    .getByRole("button", { name: "＋ Add component", exact: true })
    .click();
  const component = page.locator("ble-esl-component-editor");
  await component.locator("#text").fill("Ready");
  await component.locator("#dynamic").click();
  const dynamic = page.locator("ble-esl-dynamic-fields");
  const template = "{{ 'red' if value | float(0) >= 20 else 'black' }}";
  await dynamic.locator("#template").fill(template);
  await setLanguage(page, "ko");
  await expect(
    dynamic.getByRole("heading", { name: "동적 필드" }),
  ).toBeVisible();
  await expect(dynamic.locator("#template")).toHaveValue(template);
  await expect(dynamic.locator("#template")).toBeFocused();
  await dynamic.locator("#apply").click();
  await expect(
    component.getByRole("heading", { name: "컴포넌트 추가" }),
  ).toBeVisible();
  await expect(component.locator("#text")).toHaveValue("Ready");
  await expect(component.locator('[data-type="progress_bar"]')).toContainText(
    "진행 막대",
  );
  await setLanguage(page, "en");
  await expect(
    component.getByRole("heading", { name: "Add component" }),
  ).toBeVisible();
  await expect(component.locator("#text")).toHaveValue("Ready");
  expect(await component.evaluate((el) => el.draft.field_templates.color)).toBe(
    template,
  );
  await component.locator("#close").click();
  expect(
    await page.evaluate(() => ({
      document: window.manager.editor.document,
      undo: window.manager.editor.undoStack,
      dirty: window.manager.editor.dirty,
    })),
  ).toEqual(before);
  await expect(page.locator('[data-property="text"]')).toHaveValue(
    'Save {{ states("sensor.demo_temperature") }}',
  );
});

test("YAML and import text survive locale switches without translating payload values", async ({
  page,
}) => {
  await page.goto("/?lang=ko");
  await expect(page.locator(".stage")).toBeVisible();
  await page.getByRole("button", { name: "텍스트 추가", exact: true }).click();
  await page.locator('[data-property="text"]').fill("Ready");
  await page.locator('[data-action="yaml"]').click();
  const yaml = page.locator("ble-esl-yaml-dialog");
  await expect(
    yaml.getByRole("heading", { name: "페이로드 YAML" }),
  ).toBeVisible();
  const payload = await yaml.locator("textarea").inputValue();
  expect(payload).toContain("Ready");
  await setLanguage(page, "en");
  await expect(
    yaml.getByRole("heading", { name: "Payload YAML" }),
  ).toBeVisible();
  await expect(yaml.locator("textarea")).toHaveValue(payload);
  await yaml.locator("[data-close]").click();
  await page.locator('[data-action="import-yaml"]').click();
  const importer = page.locator("ble-esl-import-dialog");
  const input = "- type: text\n  value: Save\n  x: 10\n  y: 10";
  await importer.locator("textarea").fill(input);
  await setLanguage(page, "ko");
  await expect(
    importer.getByRole("heading", { name: "YAML 가져오기" }),
  ).toBeVisible();
  await expect(importer.locator("textarea")).toHaveValue(input);
});

test("automation validation and designer statuses follow locale switches", async ({
  page,
}) => {
  await page.goto("/?manager&lang=ko");
  await page
    .locator('[data-entry="demo-discovery"] [data-action="automations"]')
    .click();
  const modal = page.locator("ble-esl-automation-dialog");
  await expect(modal.locator('[data-action="link"]')).toBeEnabled();
  await modal.locator('[data-action="link"]').click();
  await expect(modal.locator(".result")).toHaveText(
    "기존 자동화를 선택하세요.",
  );
  await setLanguage(page, "en");
  await expect(modal.locator(".result")).toHaveText(
    "Choose an existing automation.",
  );
  await modal.locator(".close").click();
  await page
    .locator('[data-entry="demo-writable"] [data-action="edit"]')
    .click();
  await expect(page.locator("ble-esl-designer .status")).toHaveText("Ready");
  await setLanguage(page, "ko");
  await expect(page.locator("ble-esl-designer .status")).toHaveText("준비됨");
  await setLanguage(page, "en");
  await expect(page.locator("ble-esl-designer .status")).toHaveText("Ready");
});

test("locale switches preserve invalid spec drafts and translate validation without changing the document", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".stage")).toBeVisible();
  await page.locator("#add-spec").selectOption("pie");
  await page.locator('[data-action="add-spec"]').click();
  const input = page.locator('[data-spec="inner_radius"]');
  await input.fill("2x");
  await expect(input).toHaveAttribute("aria-invalid", "true");
  const document = await page.evaluate(() => window.panel.document);
  await setLanguage(page, "ko");
  await expect(input).toHaveValue("2x");
  await expect(input).toBeFocused();
  await expect(page.locator(".field-error")).toHaveText(
    "숫자 또는 {{ template }}을 입력하세요",
  );
  expect(await page.evaluate(() => window.panel.document)).toEqual(document);
  await setLanguage(page, "en");
  await expect(input).toHaveValue("2x");
  await expect(page.locator(".field-error")).toHaveText(
    "Enter a number, or a {{ template }}",
  );
  await page.locator("#add-spec").selectOption("sparkline");
  await page.locator('[data-action="add-spec"]').click();
  const arrayDraft = await page.evaluate(() => window.panel.document);
  const json = page.locator('[data-spec="values"]');
  await json.fill("[1,");
  await setLanguage(page, "ko");
  await expect(json).toHaveValue("[1,");
  expect(await page.evaluate(() => window.panel.document)).toEqual(arrayDraft);
});
