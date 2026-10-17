import { test, expect } from "@playwright/test";
import { renderSpecPalette } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/spec-palette.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

test("imagespec palette groups and escapes renderer types", () => {
  const html = renderSpecPalette({
    specs: {
      types: [
        { category: 'Shapes & "lines"', type: "rounded_rect" },
        { category: 'Shapes & "lines"', type: "circle" },
      ],
    },
    mode: "display",
    translate: (key) => `t:${key}`,
    escapeHtml,
  });

  expect(html).toContain('<optgroup label="Shapes &amp; &quot;lines&quot;">');
  expect(html).toContain('<option value="rounded_rect">rounded rect</option>');
  expect(html).toContain('aria-label="t:Add element"');
  expect(html).toContain('data-action="add-spec"');
});

test("imagespec palette is absent without renderer specs or in template mode", () => {
  const render = (specs, mode) =>
    renderSpecPalette({ specs, mode, translate: (key) => key, escapeHtml });
  expect(render(null, "display")).toBe("");
  expect(
    render({ types: [{ category: "Shapes", type: "circle" }] }, "template"),
  ).toBe("");
});
