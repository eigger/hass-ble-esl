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
  await expect(
    card.getByRole("button", { name: "배터리 85%", exact: true }),
  ).toBeVisible();
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
  await setLanguage(page, "sv");
  await expect(
    page.getByRole("heading", { name: "ESL Manager" }),
  ).toBeVisible();
  await expect(
    card.getByRole("button", { name: "Battery 85%", exact: true }),
  ).toBeVisible();
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

// Keep Designer's language support in step with the integration's translations.
test("locale catalogs match component languages and preserve interpolation tokens", async () => {
  const { readdirSync } = await import("node:fs");
  const { messages } =
    await import("../../custom_components/ble_esl/designer/frontend/locales/index.js");
  const { language, supportedLanguages, t } =
    await import("../../custom_components/ble_esl/designer/frontend/i18n.js");
  const componentLanguages = readdirSync(
    new URL("../../custom_components/ble_esl/translations/", import.meta.url),
  )
    .filter((name) => name.endsWith(".json"))
    .map((name) => name.slice(0, -5))
    .sort();
  expect([...supportedLanguages].sort()).toEqual(componentLanguages);
  const tokens = (text) =>
    [...text.matchAll(/\{\w+\}/g)].map((match) => match[0]).sort();
  for (const code of supportedLanguages) {
    expect(Object.keys(messages[code]).sort()).toEqual(
      Object.keys(messages.en).sort(),
    );
    for (const [key, value] of Object.entries(messages[code])) {
      expect(value.trim(), `${code}: ${key}`).not.toBe("");
      expect(tokens(value), `${code}: ${key}`).toEqual(tokens(key));
      expect(value, `${code}: ${key}`).not.toMatch(
        /__ESL|\n|<script|\[\d{4}\]/,
      );
      if (key.includes("{{ template }}"))
        expect(value).toContain("{{ template }}");
      if (key.includes("value, entity, entity_id, attributes"))
        expect(value).toContain("value, entity, entity_id, attributes");
    }
  }
  for (const [requested, expected] of [
    ["de-DE", "de"],
    ["fr_CA", "fr"],
    ["pt-br", "pt-BR"],
    ["pt", "pt-BR"],
    ["zh-Hans", "zh-Hans"],
    ["zh_Hant", "zh-Hant"],
    ["zh-CN", "zh-Hans"],
    ["zh-SG", "zh-Hans"],
    ["zh-TW", "zh-Hant"],
    ["zh-HK", "zh-Hant"],
    ["zh-Hant-HK", "zh-Hant"],
    ["sv", "en"],
  ])
    expect(language({ locale: { language: requested } })).toBe(expected);
  expect(language({ language: "ja" })).toBe("ja");
  expect(language()).toBe("en");
  expect(t({ language: "ja" }, "Battery {value}", { value: "85%" })).toContain(
    "85%",
  );
});

const localizedControls = [
  ["de", "Speichern"],
  ["es", "Guardar"],
  ["fr", "Enregistrer"],
  ["it", "Salva"],
  ["ja", "保存"],
  ["nl", "Opslaan"],
  ["pl", "Zapisz"],
  ["pt-BR", "Salvar"],
  ["ru", "Сохранить"],
  ["zh-Hans", "保存"],
  ["zh-Hant", "保存"],
];
for (const [code, save] of localizedControls) {
  test(`dashboard, automation dialog and designer use ${code} UI copy`, async ({
    page,
  }) => {
    const { messages } =
      await import("../../custom_components/ble_esl/designer/frontend/locales/index.js");
    const copy = messages[code];
    await page.goto(`/?manager&lang=${code}`);
    await expect(
      page.getByRole("heading", { name: copy["ESL Manager"], exact: true }),
    ).toBeVisible();
    const card = page.locator('[data-entry="demo-writable"]').first();
    await expect(card).toContainText("Living room");
    await expect(card).toContainText(copy["Last successful send"]);
    await card.locator('[data-action="automations"]').click();
    const dialog = page.locator("ble-esl-automation-dialog");
    await expect(
      dialog.getByRole("heading", {
        name: copy["Connected automations"],
        exact: true,
      }),
    ).toBeVisible();
    await dialog.locator(".close").click();
    await card.locator('[data-action="edit"]').click();
    await expect(
      page
        .locator("ble-esl-designer")
        .getByRole("button", { name: save, exact: true }),
    ).toBeVisible();
    await page.locator('ble-esl-designer [data-add="text"]').click();
    await page
      .locator('[data-property="text"]')
      .fill('Save {{ states("sensor.demo_temperature") }}');
    await page.locator('[data-action="yaml"]').click();
    const yaml = page.locator("ble-esl-yaml-dialog");
    await expect(
      yaml.getByRole("heading", { name: copy["Payload YAML"], exact: true }),
    ).toBeVisible();
    expect(await yaml.locator("textarea").inputValue()).toContain(
      'Save {{ states("sensor.demo_temperature") }}',
    );
  });
}

test("automation creation preserves its name and device across locale changes", async ({
  page,
}) => {
  await page.goto("/?manager&lang=ko");
  await page
    .locator('[data-action="edit"][data-entry="demo-writable"]')
    .click();
  await page
    .getByRole("button", { name: "자동화 만들기", exact: true })
    .click();
  const dialog = page.locator("ble-esl-yaml-dialog");
  await expect(dialog).toContainText("실행 조건은 비어 있습니다");
  await dialog.getByLabel("이름", { exact: true }).fill("거실 화면 갱신");
  await page.screenshot({ path: "artifacts/create-automation-ko.png" });
  await setLanguage(page, "en");
  await expect(
    dialog.getByRole("heading", { name: "Create automation" }),
  ).toBeVisible();
  await expect(dialog.getByLabel("Name", { exact: true })).toHaveValue(
    "거실 화면 갱신",
  );
  await expect(dialog.locator("textarea")).toHaveValue(/demo-device-0/);
  await dialog.getByLabel("Name", { exact: true }).press("Enter");
  await expect(
    dialog.getByRole("button", { name: "Create automation", exact: true }),
  ).toBeVisible();
});
