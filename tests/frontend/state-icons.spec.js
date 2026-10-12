import { test, expect } from "@playwright/test";
import { renderStateIconRows } from "../../custom_components/ble_esl/designer/frontend/editor/inspector/state-icons.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

const render = (element, sample, type = "numeric") =>
  renderStateIconRows({
    element,
    sample,
    outputType: () => type,
    defaultIcon: (state) => `mdi:${state?.state || "eye"}`,
    iconGlyph: (name) => `<ha-icon data-name="${escapeHtml(name)}"></ha-icon>`,
    translate: (key, values = {}) =>
      key.replace("{state}", values.state ?? "{state}"),
    escapeHtml,
  });

test("binary state icon controls preserve order, defaults, and accessible actions", () => {
  const html = render(
    { state_icons: { unknown: "mdi:help", on: "mdi:lightbulb" } },
    { entity_id: "binary_sensor.door", state: "off", attributes: {} },
    "binary",
  );

  expect(html.indexOf('data-icon-state="on"')).toBeLessThan(
    html.indexOf('data-icon-state="off"'),
  );
  expect(html).toContain('aria-label="Choose icon for on"');
  expect(html).toContain('data-name="mdi:lightbulb"');
  expect(html).toContain('data-name="mdi:off"');
  expect(html).toContain('data-icon-state="unknown"');
  expect(html).toContain('aria-label="Add state mapping"');
});

test("state icon rows escape authored values and keep empty-sample controls", () => {
  const html = render(
    { state_icons: { "<ready&": "mdi:weather-sunny" } },
    null,
  );

  expect(html).toContain('data-icon-state="&lt;ready&amp;"');
  expect(html).toContain("weather-sunny");
  expect(html).toContain('aria-label="Search icons"');
  expect(html).toContain('data-icon="{{icon}}"');
});
