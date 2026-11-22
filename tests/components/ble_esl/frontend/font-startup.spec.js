import { test, expect } from "@playwright/test";

test("a stalled font download does not block the editor and is retried", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  let requests = 0;
  await page.route(
    "**/ble_esl_designer_fonts/NotoSansKR-Regular.ttf",
    async (route) => {
      requests++;
      if (requests === 1) {
        await gate;
        await route.abort().catch(() => {});
      } else {
        await route.continue();
      }
    },
  );
  try {
    await page.goto("/");
    await expect(page.locator(".workspace")).toBeVisible();
    await page.locator('[data-add="text"]').click();
    await expect(page.locator(".el.selected")).toBeVisible();
    await expect
      .poll(() => requests, { timeout: 15000 })
      .toBeGreaterThanOrEqual(2);
    await expect
      .poll(
        () =>
          page.evaluate(() =>
            [...document.fonts].some(
              (font) => font.family === "LabelText" && font.status === "loaded",
            ),
          ),
        { timeout: 15000 },
      )
      .toBe(true);
    await expect(page.locator(".el.selected")).toBeVisible();
  } finally {
    release();
  }
});

test("exhausted fonts can be retried without disturbing an edit", async ({
  page,
}) => {
  let fail = true;
  let requests = 0;
  await page.route(
    "**/ble_esl_designer_fonts/NotoSansKR-Regular.ttf",
    async (route) => {
      requests++;
      if (fail) await route.fulfill({ status: 503, body: "unavailable" });
      else await route.continue();
    },
  );
  await page.goto("/");
  await expect(page.locator(".workspace")).toBeVisible();
  const retry = page.getByRole("button", { name: "Retry fonts" });
  await expect(retry).toBeVisible();
  expect(requests).toBe(3);
  await page.locator('[data-add="text"]').click();
  const input = page.locator('[data-property="x"]');
  await input.fill("12");
  await input.press("Tab");
  const before = await page.evaluate(() =>
    JSON.stringify(window.panel.document),
  );
  fail = false;
  await retry.click();
  await input.focus();
  await expect.poll(() => requests).toBe(4);
  await expect(retry).toBeHidden();
  await expect(input).toBeFocused();
  expect(await page.evaluate(() => JSON.stringify(window.panel.document))).toBe(
    before,
  );
  expect(requests).toBe(4);
  await expect
    .poll(() =>
      page.evaluate(() =>
        [...document.fonts].some(
          (font) => font.family === "LabelText" && font.status === "loaded",
        ),
      ),
    )
    .toBe(true);
});
