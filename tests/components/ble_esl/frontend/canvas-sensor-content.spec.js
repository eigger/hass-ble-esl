import { test, expect } from "@playwright/test";
import { renderSensorContent } from "../../../../custom_components/ble_esl/designer/frontend/editor/canvas/sensor-content.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const iconGlyph = (name, size) => `<icon name="${name}" size="${size}"></icon>`;
const element = {
  width: 20,
  height: 10,
  show_label: true,
};

test("sensor templates substitute escaped text, filter states, and scale icons", () => {
  const markup = renderSensorContent({
    element,
    stateValue: "on",
    template: {
      width: 10,
      height: 10,
      document: {
        elements: [
          {
            type: "text",
            x: 1,
            y: 2,
            width: 8,
            height: 3,
            color: "black",
            background: "white",
            font_size: 4,
            align: "left",
            text: "{{name}} {{state}} {{unit}} {{icon}}",
          },
          {
            type: "text",
            state: "off",
            text: "not this state",
          },
          {
            type: "icon",
            x: 0,
            y: 0,
            width: 6,
            height: 8,
            icon: "{{icon}}",
          },
        ],
      },
    },
    templateValues: {
      name: "<Office>",
      state: "21.5",
      unit: "°C",
      icon: "mdi:thermometer",
    },
    escapeHtml,
    iconGlyph,
  });
  expect(markup).toContain("&lt;Office&gt; 21.5 °C mdi:thermometer");
  expect(markup).not.toContain("not this state");
  expect(markup).toContain('<icon name="mdi:thermometer" size="8"></icon>');
  expect(markup).toContain("left:2px;top:2px;width:16px;height:3px");
});

test("weather numeric tile shows its precomputed value and unit", () => {
  const markup = renderSensorContent({
    element,
    label: "Outdoor",
    iconName: "mdi:thermometer",
    value: "18 °C",
    visual: false,
    escapeHtml,
    iconGlyph,
  });
  expect(markup).toContain('<icon name="mdi:thermometer" size="32"></icon>');
  expect(markup).toContain('<div class="label">Outdoor</div>');
  expect(markup).toContain('<div class="value">18 °C</div>');
});

test("binary sensor tiles use the visual icon without repeating state text", () => {
  const markup = renderSensorContent({
    element,
    label: "Window",
    iconName: "mdi:window-open",
    value: "on",
    visual: true,
    escapeHtml,
    iconGlyph,
  });
  expect(markup).toContain('<icon name="mdi:window-open" size="32"></icon>');
  expect(markup).toContain('<div class="label">Window</div>');
  expect(markup).toContain('<div class="value"></div>');
});

test("numeric sensor values remain visible and escaped", () => {
  const markup = renderSensorContent({
    element: { ...element, show_label: false },
    label: "unused",
    iconName: "mdi:gauge",
    value: "21 < 22",
    visual: false,
    escapeHtml,
    iconGlyph,
  });
  expect(markup).toContain('<div class="value">21 &lt; 22</div>');
  expect(markup).not.toContain("unused");
});
