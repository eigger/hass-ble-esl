import { expect, test } from "@playwright/test";
import { buildSensorOptions } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/sensor-options.js";

const build = (element, overrides = {}) =>
  buildSensorOptions(element, {
    mode: "display",
    templateKey: "weather:default",
    templates: {},
    templateDrafts: new Map(),
    templateSensorType: "numeric",
    state: null,
    entities: [],
    outputType: () => "text",
    templateCompatibility: () => "text",
    sensorType: () => "numeric",
    outputStyleLabel: (type) => `${type} style`,
    ...overrides,
  });

test("sensor options preserve weather style labels, compatibility, and numeric rules", () => {
  const element = {
    type: "sensor",
    entity_id: "weather.home",
    weather_field: "temperature",
    template: "output:numeric",
  };
  const options = build(element, {
    templates: {
      "output:numeric": {},
      "output:text": { name: "Text override" },
    },
    templateDrafts: new Map([["output:numeric", { name: "Draft label" }]]),
    state: { entity_id: "weather.home", state: "sunny" },
    outputType: () => "numeric",
    templateCompatibility: (_template, key) =>
      key === "output:numeric" ? "numeric" : "text",
  });

  expect(options.isWeather).toBe(true);
  expect(options.numeric).toBe(true);
  expect(options.templateStyles).toEqual([
    {
      value: "output:numeric",
      label: "Draft label",
      selected: true,
    },
  ]);
});

test("weather template states are unique and only added outside icon editing", () => {
  const options = build(
    { type: "sensor", entity_id: "sensor.temp" },
    {
      mode: "template",
      entities: [{ state: "sunny" }, { state: "21", entity_id: "sensor.temp" }],
      sensorType: (state) => (state.state === "21" ? "numeric" : "weather"),
    },
  );

  expect(options.templateStates).toContain("on");
  expect(options.templateStates).toContain("sunny");
  expect(options.templateStates).toContain("21");
  expect(new Set(options.templateStates).size).toBe(
    options.templateStates.length,
  );
  expect(build({ type: "icon" }, { mode: "template" }).templateStates).toEqual(
    [],
  );
});
