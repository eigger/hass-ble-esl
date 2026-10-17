import { expect, test } from "@playwright/test";
import { renderOptionalProperties } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/optional-properties.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );

const render = (element, options = {}) =>
  renderOptionalProperties(element, {
    translate: (message) => message,
    escapeHtml,
    colorPicker: (key, value, label) =>
      `<color-picker data-pick="${key}" data-value="${value}">${label}</color-picker>`,
    ...options,
  });

test("optional text controls retain defaults and escape authored font paths", () => {
  const { style, advanced } = render({
    type: "text",
    font: 'custom"font.ttf',
  });

  expect(style).toBe("");
  expect(advanced).toContain('data-property="max_lines"');
  expect(advanced).toContain('placeholder="3"');
  expect(advanced).toContain('data-property="fit"');
  expect(advanced).toContain('value="custom&quot;font.ttf"');
  expect(advanced).toContain('data-property="dither"');
});

test("shape and image controls keep their type-specific defaults", () => {
  const shape = render({ type: "rounded_rectangle" });
  expect(shape.style).toContain('data-property="filled" checked');
  expect(shape.style).toContain('data-property="line_width"');
  expect(shape.style).toContain('data-property="radius"');

  const image = render({ type: "image", dither: true });
  expect(image.style).toContain('data-property="rotate"');
  expect(image.style).toContain('data-property="circle"');
  expect(image.advanced).toContain('data-property="dither"');
  expect(image.advanced).toContain(
    '<option value="floyd" selected>floyd</option>',
  );
});

test("icon and progress controls receive palette and supported dither choices", () => {
  let pickerArgs;
  const icon = render(
    { type: "icon", stroke_fill: "red" },
    {
      colorPicker: (...args) => {
        pickerArgs = args;
        return "<div data-icon-palette></div>";
      },
    },
  );
  expect(pickerArgs).toEqual(["stroke_fill", "red", "Outline colour"]);
  expect(icon.advanced).toContain("data-icon-palette");
  expect(icon.advanced).toContain('data-property="stroke_width"');

  const progress = render(
    { type: "progress_bar", dither: false },
    { ditherMethods: ["none", "floyd", "ordered_4x4", 'custom_<x>&"'] },
  );
  expect(progress.style).toContain('data-property="direction"');
  expect(progress.style).toContain('data-property="show_percentage"');
  expect(progress.advanced).toContain('value="none" selected');
  expect(progress.advanced).toContain('value="ordered_4x4"');
  expect(progress.advanced).toContain('value="custom_&lt;x&gt;&amp;&quot;"');
  expect(progress.advanced).toContain(">custom_&lt;x&gt;&amp;&quot;</option>");
  expect(progress.advanced).toContain('value="floyd"');
});
