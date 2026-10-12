import { test, expect } from "@playwright/test";
import {
  filterEntities,
  listSupportedEntities,
  renderEntityPreview,
} from "../../custom_components/ble_esl/designer/frontend/editor/entity-library.js";

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
