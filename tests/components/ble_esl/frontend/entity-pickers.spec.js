import { test, expect } from "@playwright/test";
import {
  configureBoundEntityPicker,
  configureLibraryEntityPicker,
  replaceEntityPickerElements,
  SENSOR_PICKER_DOMAINS,
} from "../../../../custom_components/ble_esl/designer/frontend/editor/entity-pickers.js";

function picker() {
  const listeners = {};
  return {
    listeners,
    addEventListener(name, callback) {
      listeners[name] = callback;
    },
  };
}

test("picker upgrade replaces each legacy node with a fresh attribute copy", () => {
  const replaced = [];
  const oldPickers = [
    {
      attributes: [
        { name: "id", value: "entity-picker" },
        { name: "label", value: "Sensor" },
      ],
      replaceWith(node) {
        replaced.push(node);
      },
    },
    {
      attributes: [{ name: "id", value: "template-sample" }],
      replaceWith(node) {
        replaced.push(node);
      },
    },
  ];
  const root = {
    querySelectorAll(selector) {
      expect(selector).toBe("ha-entity-picker");
      return oldPickers;
    },
  };
  const replacements = replaceEntityPickerElements(root, () => ({
    attributes: {},
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
  }));

  expect(replacements).toHaveLength(2);
  expect(replaced).toEqual(replacements);
  expect(replacements.map((node) => node.attributes)).toEqual([
    { id: "entity-picker", label: "Sensor" },
    { id: "template-sample" },
  ]);
});

test("library picker configures supported domains and forwards selection", () => {
  const target = picker();
  const hass = { states: {} };
  const selected = [];
  configureLibraryEntityPicker(target, {
    hass,
    value: "sensor.office",
    label: "Sensor",
    searchLabel: "Search sensors",
    onValueChanged: (value) => selected.push(value),
  });

  expect(target.hass).toBe(hass);
  expect(target.includeDomains).toEqual(SENSOR_PICKER_DOMAINS);
  expect(target.includeDomains).not.toBe(SENSOR_PICKER_DOMAINS);
  expect(target).toMatchObject({
    label: "Sensor",
    searchLabel: "Search sensors",
    allowCustomEntity: false,
    value: "sensor.office",
  });
  target.listeners["value-changed"]({ detail: { value: "weather.home" } });
  expect(selected).toEqual(["weather.home"]);
});

test("bound picker stops propagation and ignores empty or unchanged values", () => {
  const target = picker();
  const selected = [];
  const includeDomains = ["sensor", "weather"];
  configureBoundEntityPicker(target, {
    hass: { states: {} },
    value: "sensor.office",
    label: "Bound entity",
    includeDomains,
    onValueChanged: (value) => selected.push(value),
  });

  expect(target).toMatchObject({
    label: "Bound entity",
    searchLabel: "Bound entity",
    allowCustomEntity: false,
    required: true,
    value: "sensor.office",
    includeDomains,
  });
  const emit = (value) => {
    let stopped = false;
    target.listeners["value-changed"]({
      detail: { value },
      stopPropagation: () => (stopped = true),
    });
    return stopped;
  };
  expect(emit("")).toBe(true);
  expect(emit("sensor.office")).toBe(true);
  expect(emit("sensor.kitchen")).toBe(true);
  expect(selected).toEqual(["sensor.kitchen"]);
});
