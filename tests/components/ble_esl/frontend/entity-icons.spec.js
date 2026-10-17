import { expect, test } from "@playwright/test";
import { defaultEntityIcon } from "../../../../custom_components/ble_esl/designer/frontend/editor/entity-icons.js";

const state = (entity_id, value, attributes = {}) => ({
  entity_id,
  state: value,
  attributes,
});

test("default entity icons preserve explicit icons and unknown fallbacks", () => {
  expect(defaultEntityIcon(null)).toBe("mdi:eye");
  expect(
    defaultEntityIcon(
      state("sensor.temperature", "20", { icon: "mdi:home-thermometer" }),
    ),
  ).toBe("mdi:home-thermometer");
  expect(defaultEntityIcon(state("sensor.mode", "heat"))).toBe("mdi:eye");
});

test("weather states map to their established icons", () => {
  expect(defaultEntityIcon(state("weather.home", "sunny"))).toBe(
    "mdi:weather-sunny",
  );
  expect(defaultEntityIcon(state("weather.home", "clear-night"))).toBe(
    "mdi:weather-night",
  );
  expect(defaultEntityIcon(state("weather.home", "unrecognized"))).toBe(
    "mdi:weather-cloudy",
  );
});

test("binary sensor icons reflect active state and device class", () => {
  expect(
    defaultEntityIcon(
      state("binary_sensor.window", "off", { device_class: "window" }),
    ),
  ).toBe("mdi:window-closed");
  expect(
    defaultEntityIcon(
      state("binary_sensor.window", "on", { device_class: "window" }),
    ),
  ).toBe("mdi:window-open");
  expect(defaultEntityIcon(state("binary_sensor.unknown", "on"))).toBe(
    "mdi:checkbox-marked-circle",
  );
});

test("common sensor device classes map to their established icons", () => {
  expect(
    defaultEntityIcon(
      state("sensor.temperature", "20", { device_class: "temperature" }),
    ),
  ).toBe("mdi:thermometer");
  expect(
    defaultEntityIcon(
      state("sensor.humidity", "40", { device_class: "humidity" }),
    ),
  ).toBe("mdi:water-percent");
  expect(
    defaultEntityIcon(
      state("sensor.timestamp", "now", { device_class: "timestamp" }),
    ),
  ).toBe("mdi:calendar-clock");
});
