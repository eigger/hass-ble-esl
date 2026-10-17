import { expect, test } from "@playwright/test";
import { renderLegacyElementProperties } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/legacy-properties.js";

const dependencies = (overrides = {}) => ({
  translate: (message) => message,
  escapeHtml: (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll('"', "&quot;"),
  colorPicker: () => "<div data-color-control></div>",
  iconGlyph: () => "<span data-icon-glyph></span>",
  tokenText: (value) => value,
  stateIconRows: () => "<div data-state-icons></div>",
  extraProperties: () => ({
    style: "<input data-optional-style>",
    advanced: "<input data-optional-advanced>",
  }),
  textAlignmentControls: () => "<div data-text-alignment></div>",
  weatherControls: () => "<div data-weather-controls></div>",
  shapeTypes: ["rectangle", "rounded_rectangle", "ellipse", "triangle", "line"],
  mode: "display",
  advancedOpen: true,
  sensorOptions: {
    isWeather: false,
    templateStyles: [],
    templateStates: [],
    numeric: false,
  },
  ...overrides,
});

test("legacy inspector composes content, position, style, and advanced sections", () => {
  const markup = renderLegacyElementProperties(
    {
      type: "progress_bar",
      min_value: 0,
      max_value: 100,
      value: 24,
      visible: false,
    },
    dependencies(),
  );

  const content = markup.indexOf("Content");
  const value = markup.indexOf('data-property="value"');
  const position = markup.indexOf("Position & size");
  const style = markup.indexOf("Style");
  const optionalStyle = markup.indexOf("data-optional-style");
  const advanced = markup.indexOf("data-optional-advanced");
  expect(content).toBeLessThan(value);
  expect(value).toBeLessThan(position);
  expect(position).toBeLessThan(style);
  expect(style).toBeLessThan(optionalStyle);
  expect(optionalStyle).toBeLessThan(advanced);
  expect(markup).toContain('data-property="visible" >Visible</label>');
  expect(markup).toContain('<details class="wide advanced" open>');
});

test("sensor inspector composes weather controls, state choices, and HA tile styles", () => {
  const markup = renderLegacyElementProperties(
    {
      type: "sensor",
      entity_id: "weather.home",
      state: "sunny",
      template: "output:weather",
      show_label: true,
      show_unit: true,
    },
    dependencies({
      mode: "template",
      sensorOptions: {
        isWeather: true,
        templateStyles: [
          {
            value: "output:weather",
            label: "Weather & forecast",
            selected: true,
          },
        ],
        templateStates: ["on", "off", "sunny"],
        numeric: true,
      },
    }),
  );

  expect(markup).toContain("<div data-weather-controls></div>");
  expect(markup).toContain('<option value="sunny"></option>');
  expect(markup).toContain(
    '<option value="output:weather" selected>Weather &amp; forecast</option>',
  );
  expect(markup).toContain(
    '<ha-entity-picker class="wide" data-property="entity_id"></ha-entity-picker>',
  );
  expect(markup).toContain('data-property="show_label" checked');
  expect(markup).toContain('data-property="show_unit" checked');
  expect(markup).toContain('data-property="decimals"');
});
