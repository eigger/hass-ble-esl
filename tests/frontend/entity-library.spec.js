import { test, expect } from "@playwright/test";
import {
  entityName,
  entityValue,
  firstNumericSensorEntity,
  filterEntities,
  listSupportedEntities,
  renderEntityPreview,
} from "../../custom_components/ble_esl/designer/frontend/editor/entity-library.js";

test("entity names prefer HA formatting, then friendly name, then entity ID", () => {
  const state = {
    entity_id: "sensor.office",
    attributes: { friendly_name: "Office temperature" },
  };
  expect(entityName(state, { formatEntityName: () => "HA name" })).toBe(
    "HA name",
  );
  expect(entityName(state, {})).toBe("Office temperature");
  expect(entityName({ entity_id: "sensor.office", attributes: {} }, {})).toBe(
    "sensor.office",
  );
});

test("entity values preserve text, unavailable, decimal, unit, and HA formatting rules", () => {
  const hass = {
    states: {
      "sensor.temp": {
        entity_id: "sensor.temp",
        state: "20.56",
        attributes: { unit_of_measurement: "°C" },
      },
      "sensor.unknown": {
        entity_id: "sensor.unknown",
        state: "unknown",
        attributes: { unit_of_measurement: "°C" },
      },
    },
    formatEntityState: (state) => `${state.state} formatted`,
  };
  expect(entityValue({ type: "text", text: "literal" }, hass, "N/A")).toBe(
    "literal",
  );
  expect(entityValue({ entity_id: "sensor.missing" }, hass, "N/A")).toBe("N/A");
  expect(
    entityValue(
      { entity_id: "sensor.temp", decimals: 1, show_unit: true },
      hass,
      "N/A",
    ),
  ).toBe("20.6 °C");
  expect(
    entityValue({ entity_id: "sensor.temp", show_unit: false }, hass, "N/A"),
  ).toBe("20.56");
  expect(
    entityValue({ entity_id: "sensor.temp", show_unit: true }, hass, "N/A"),
  ).toBe("20.56 formatted");
  expect(
    entityValue(
      { entity_id: "sensor.unknown", decimals: 1, show_unit: true },
      hass,
      "N/A",
    ),
  ).toBe("unknown formatted");
});

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

test("entity library includes supported domains and filters by ID or display name", () => {
  const states = {
    "sensor.office": {
      entity_id: "sensor.office",
      attributes: { friendly_name: "Office temperature" },
    },
    "weather.home": { entity_id: "weather.home", attributes: {} },
    "light.office": { entity_id: "light.office", attributes: {} },
  };
  const entities = listSupportedEntities(states);
  const entityName = (state) =>
    state.attributes.friendly_name || state.entity_id;

  expect(entities.map((state) => state.entity_id)).toEqual([
    "sensor.office",
    "weather.home",
  ]);
  expect(
    filterEntities(entities, "OFFICE", entityName).map(
      (state) => state.entity_id,
    ),
  ).toEqual(["sensor.office"]);
  expect(
    filterEntities(entities, "weather.", entityName).map(
      (state) => state.entity_id,
    ),
  ).toEqual(["weather.home"]);
});

test("plot default sensor picks the first sensor with a numeric prefix", () => {
  const states = [
    { entity_id: "weather.home", state: "sunny" },
    { entity_id: "sensor.mode", state: "warm" },
    { entity_id: "sensor.first", state: "12 °C" },
    { entity_id: "sensor.second", state: "21.5" },
  ];
  expect(firstNumericSensorEntity(states)).toBe(states[2]);
  expect(firstNumericSensorEntity(states.slice(0, 2))).toBeUndefined();
});

test("entity preview escapes HA-provided values and keeps the add action contract", () => {
  const state = { entity_id: "sensor.<office>" };
  const markup = renderEntityPreview({
    state,
    name: "Office & kitchen",
    value: "<21 °C>",
    addLabel: "Add selected sensor",
    escapeHtml,
  });

  expect(markup).toContain('data-entity="sensor.&lt;office&gt;"');
  expect(markup).toContain("Office &amp; kitchen");
  expect(markup).toContain("&lt;21 °C&gt;");
  expect(markup).toContain('data-action="add-current-entity"');
});

test("entity preview is empty when no entity is selected", () => {
  expect(
    renderEntityPreview({
      state: null,
      name: "",
      value: "",
      addLabel: "Add selected sensor",
      escapeHtml,
    }),
  ).toBe("");
});
