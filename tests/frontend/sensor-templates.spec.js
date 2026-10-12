import { expect, test } from "@playwright/test";
import {
  createDefaultSensorTemplate,
  outputType,
  sensorType,
  substituteTemplateTokens,
  templateCompatibility,
  templateTypes,
} from "../../custom_components/ble_esl/designer/frontend/editor/sensor-templates.js";
import {
  emptyDocument,
  newElement,
} from "../../custom_components/ble_esl/designer/frontend/model.js";

const state = (entity_id, value, attributes = {}) => ({
  entity_id,
  state: value,
  attributes,
});

test("sensor template rules classify outputs and retain legacy compatibility", () => {
  expect(outputType(null)).toBe("text");
  expect(outputType(state("weather.home", "sunny"))).toBe("weather");
  expect(outputType(state("binary_sensor.window", "off"))).toBe("binary");
  expect(
    outputType(
      state("sensor.temperature", "20.5", { unit_of_measurement: "°C" }),
    ),
  ).toBe("numeric");
  expect(outputType(state("sensor.mode", "heat"))).toBe("text");
  expect(
    sensorType(
      state("sensor.temperature", "20", { device_class: "temperature" }),
    ),
  ).toBe("sensor:temperature");
  expect(
    templateCompatibility({ sensor_type: "binary_sensor:door" }, "x"),
  ).toBe("binary");
  expect(templateCompatibility(null, "weather:default")).toBe("weather");
  expect(templateCompatibility(null, "sensor:temperature")).toBe("numeric");
});

test("template type list is unique and includes built-ins, saved styles, and drafts", () => {
  const templates = { "sensor:temperature": {}, "output:numeric": {} };
  const drafts = new Map([["output:text:custom:1", {}]]);
  expect(templateTypes(templates, drafts)).toEqual([
    "output:numeric",
    "output:binary",
    "output:text",
    "output:weather",
    "sensor:temperature",
    "output:text:custom:1",
  ]);
});

test("default sensor template preserves its established element layout", () => {
  const document = createDefaultSensorTemplate({ emptyDocument, newElement });
  expect(document.elements).toHaveLength(3);
  expect(
    document.elements.map(({ type, x, y, width, height }) => ({
      type,
      x,
      y,
      width,
      height,
    })),
  ).toEqual([
    { type: "icon", x: 4, y: 14, width: 32, height: 32 },
    { type: "text", x: 44, y: 4, width: 92, height: 18 },
    { type: "text", x: 44, y: 25, width: 92, height: 31 },
  ]);
  expect(
    document.elements.map((element) =>
      element.type === "icon" ? element.icon : element.text,
    ),
  ).toEqual(["{{icon}}", "{{name}}", "{{state}} {{unit}}"]);
});

test("template token substitution replaces supported tokens and leaves other text alone", () => {
  expect(
    substituteTemplateTokens(
      "{{name}}: {{state}} {{unit}} {{icon}} / {{unknown}}",
      {
        name: "Kitchen",
        state: "21.5",
        unit: "°C",
        icon: "mdi:home",
      },
    ),
  ).toBe("Kitchen: 21.5 °C mdi:home / {{unknown}}");
  expect(
    substituteTemplateTokens("{{state}} / {{state}}", { state: "on" }),
  ).toBe("on / on");
});
