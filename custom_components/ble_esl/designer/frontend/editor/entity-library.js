import { materialIcon } from "./material-icons.js";
// Pure entity-library rules and markup. Home Assistant state and localization
// stay at the editor boundary and enter through explicit values.
const ENTITY_DOMAINS =
  /^(sensor|binary_sensor|weather|input_number|number|input_boolean|input_select|select|counter)\./;

export function entityName(state, hass) {
  return (
    hass?.formatEntityName?.(state) ||
    state.attributes.friendly_name ||
    state.entity_id
  );
}

export function entityValue(element, hass, unavailableLabel) {
  if (element.type === "text") return element.text;
  const state = hass.states[element.entity_id];
  if (!state) return unavailableLabel;
  if (
    element.decimals !== undefined &&
    !["unknown", "unavailable"].includes(state.state)
  )
    return (
      Number(state.state).toFixed(element.decimals) +
      (element.show_unit && state.attributes.unit_of_measurement
        ? " " + state.attributes.unit_of_measurement
        : "")
    );
  const formatted = hass.formatEntityState?.(state) || state.state;
  if (!element.show_unit && state.attributes.unit_of_measurement)
    return state.state;
  return formatted;
}

export function listSupportedEntities(states) {
  return Object.values(states || {}).filter((state) =>
    ENTITY_DOMAINS.test(state.entity_id),
  );
}

export function firstNumericSensorEntity(entities) {
  return entities.find(
    (state) =>
      state.entity_id.startsWith("sensor.") &&
      Number.isFinite(Number.parseFloat(state.state)),
  );
}

export function filterEntities(entities, query, entityName) {
  const normalizedQuery = String(query || "").toLowerCase();
  return entities.filter((state) =>
    (state.entity_id + " " + entityName(state))
      .toLowerCase()
      .includes(normalizedQuery),
  );
}

export function renderEntityPreview({
  state,
  name,
  value,
  addLabel,
  escapeHtml,
}) {
  if (!state) return "";
  const entityId = escapeHtml(state.entity_id);
  return `<div class="entity-state" data-entity="${entityId}" draggable="true"><ha-state-icon></ha-state-icon><div class="state-copy"><div class="state-name">${escapeHtml(name)}</div><div class="state-value">${escapeHtml(value)}</div></div><button class="icon-button" data-action="add-current-entity" aria-label="${escapeHtml(addLabel)}" title="${escapeHtml(addLabel)}">${materialIcon("plus")}</button></div>`;
}
