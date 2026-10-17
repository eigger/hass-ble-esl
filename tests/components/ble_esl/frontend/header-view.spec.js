import { test, expect } from "@playwright/test";

test("header reflects mode, lock state, translations, and escaped version", async ({
  page,
}) => {
  await page.goto("/");
  const html = await page.evaluate(async () => {
    const { renderHeader } = await import("/frontend/editor/header-view.js");
    const translate = (key) => `translated ${key}`;
    const escapeHtml = (value) =>
      String(value ?? "").replace(
        /[&<>\"']/g,
        (char) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[char],
      );
    return renderHeader({
      mode: "template",
      loading: false,
      refreshing: false,
      sessionLocked: true,
      version: '1<&"',
      translate,
      escapeHtml,
    });
  });

  expect(html).toContain("translated ESL Designer");
  expect(html).toContain('aria-pressed="false" disabled>translated Display');
  expect(html).toContain(
    'aria-pressed="true" disabled>translated Sensor tile styles',
  );
  expect(html).toContain(
    'title="translated BLE ESL integration version">v1&lt;&amp;&quot;',
  );
});
