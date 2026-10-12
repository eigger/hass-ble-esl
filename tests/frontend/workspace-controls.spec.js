import { test, expect } from "@playwright/test";
import { renderPanelToggle } from "../../custom_components/ble_esl/designer/frontend/editor/workspace-controls.js";

const translate = (key, values = {}) =>
  key.replace(/\{(\w+)\}/g, (_, name) => values[name] ?? `{${name}}`);

test("workspace panel toggle exposes its target, state, and accessible labels", () => {
  const closed = renderPanelToggle({
    action: "toggle-library",
    open: false,
    label: "entities",
    id: "library",
    translate,
    iconMarkup: "menu icon",
  });
  expect(closed).toContain('data-action="toggle-library"');
  expect(closed).toContain('aria-label="Toggle entities panel"');
  expect(closed).toContain('aria-controls="library"');
  expect(closed).toContain('title="Show entities"');
  expect(closed).toContain('aria-expanded="false"');
  expect(closed).toContain("menu icon");

  const open = renderPanelToggle({
    action: "toggle-inspector",
    open: true,
    label: "properties",
    id: "inspector",
    translate,
    iconMarkup: "menu icon",
  });
  expect(open).toContain('aria-label="Toggle properties panel"');
  expect(open).toContain('title="Hide properties"');
  expect(open).toContain('aria-expanded="true"');
});
