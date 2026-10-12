import { test, expect } from "@playwright/test";
import { renderColorPicker } from "../../custom_components/ble_esl/designer/frontend/editor/color-picker.js";

test("color picker renders accessible swatches and the background transparency option", () => {
  const markup = renderColorPicker({
    key: "background",
    value: "red",
    label: "Background",
    colors: ["black", "red"],
    translate: (value) => `translated ${value}`,
  });

  expect(markup).toContain('role="group" aria-label="Background"');
  expect(markup).toContain('data-pick="background" data-value="red"');
  expect(markup).toContain('aria-label="Background: translated red"');
  expect(markup).toContain('aria-pressed="true"');
  expect(markup).toContain('data-value="transparent"');
  expect(markup).toContain("repeating-conic-gradient");
});

test("non-background color controls do not offer transparent", () => {
  const markup = renderColorPicker({
    key: "color",
    value: "black",
    label: "Color",
    colors: ["black", "red"],
    translate: (value) => value,
  });

  expect(markup).toContain('data-pick="color" data-value="black"');
  expect(markup).not.toContain("transparent");
});
