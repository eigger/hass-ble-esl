import { test, expect } from "@playwright/test";

test("toolbar view preserves editor actions and accessible disabled hints", async ({
  page,
}) => {
  await page.goto("/");
  const result = await page.evaluate(async () => {
    const { renderToolbar, TOOLBAR_STYLE } =
      await import("/frontend/editor/toolbar-view.js");
    const markup = renderToolbar({
      tag: { writable: false },
      mode: "display",
      sessionLocked: false,
      refreshing: false,
      busy: false,
      status: "Ready",
      dirty: true,
      automationSessionPending: false,
      automationSaveMode: false,
      undoAvailable: true,
      redoAvailable: false,
      zoomMode: "manual",
      zoom: 1.25,
      tags: [{ name: "entry" }],
      translate: (key) => key,
      escapeHtml: (value) => String(value).replaceAll("&", "&amp;"),
      icon: (name) => `<svg data-icon="${name}"></svg>`,
      tagName: (item) => item.name,
      renderTagOptions: () => '<option value="entry">entry</option>',
      sendHint: () => "Read only & unavailable",
    });
    return { markup, style: TOOLBAR_STYLE };
  });

  expect(result.markup).toContain('aria-label="ESL"');
  expect(result.markup).toContain('data-action="save"');
  expect(result.markup).toContain('aria-label="Save (unsaved changes)"');
  // A tag design is saved into automations, not by a Save of its own.
  expect(result.markup).toContain('data-action="save" hidden');
  expect(result.markup).not.toContain('data-action="restore"');
  expect(result.markup).toContain(
    'aria-description="Read only &amp; unavailable"',
  );
  expect(result.markup).toContain('aria-label="Undo"');
  expect(result.markup).toContain('aria-label="Redo"');
  expect(result.markup).toContain(
    'data-action="redo" disabled class="icon-button" aria-label="Redo"',
  );
  expect(result.markup).toContain(
    '<option value="1.25" selected>125%</option>',
  );
  expect(result.style).toContain(".toolbar{position:sticky");
  expect(result.style).toContain(":host([managed]) .toolbar{position:sticky}");
});
