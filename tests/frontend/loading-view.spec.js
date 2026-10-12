import { test, expect } from "@playwright/test";

test("loading view keeps step order, progress, translation, and safe errors", async ({
  page,
}) => {
  await page.goto("/");
  const view = await page.evaluate(async () => {
    const { createLoadingSteps, renderLoadingContent } =
      await import("/frontend/editor/loading-view.js");
    const translate = (key, values) =>
      values
        ? key
            .replace("{step}", values.step)
            .replace("{done}", values.done)
            .replace("{count}", values.count)
        : key;
    const escapeHtml = (value) =>
      String(value ?? "").replace(
        /[&<>"']/g,
        (char) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[char],
      );
    const loading = { error: null, steps: createLoadingSteps() };
    loading.steps[0].done = true;
    const progress = renderLoadingContent(loading, { translate, escapeHtml });
    loading.error = '<offline & "retry">';
    const error = renderLoadingContent(loading, { translate, escapeHtml });
    return { steps: loading.steps, progress, error };
  });

  expect(view.steps.map(({ key, label, done }) => [key, label, done])).toEqual([
    ["fonts", "fonts", true],
    ["icons", "icons", false],
    ["templates", "tile styles", false],
    ["specs", "component specs", false],
    ["tags", "devices", false],
  ]);
  expect(view.progress).toContain("Loading icons… (1/5)");
  expect(view.progress).toContain(
    'aria-label="Loading designer" max="5" value="1"',
  );
  expect(view.error).toContain("&lt;offline &amp; &quot;retry&quot;&gt;");
  expect(view.error).toContain('<button data-action="reload">Retry</button>');
});
