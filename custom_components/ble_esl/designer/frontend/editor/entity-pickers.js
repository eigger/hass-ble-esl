// Home Assistant entity-picker setup and event adaptation. State resolution
// and editor actions stay with the panel and enter through callbacks.
export const SENSOR_PICKER_DOMAINS = Object.freeze([
  "sensor",
  "binary_sensor",
  "weather",
  "input_number",
  "number",
  "input_boolean",
  "input_select",
  "select",
  "counter",
]);

export function replaceEntityPickerElements(root, createPicker) {
  const replacements = [];
  for (const oldPicker of root.querySelectorAll("ha-entity-picker")) {
    const newPicker = createPicker();
    for (const { name, value } of oldPicker.attributes)
      newPicker.setAttribute(name, value);
    oldPicker.replaceWith(newPicker);
    replacements.push(newPicker);
  }
  return replacements;
}

export function configureLibraryEntityPicker(
  picker,
  { hass, value, label, searchLabel, onValueChanged },
) {
  picker.hass = hass;
  picker.includeDomains = [...SENSOR_PICKER_DOMAINS];
  picker.label = label;
  picker.searchLabel = searchLabel;
  picker.allowCustomEntity = false;
  picker.value = value;
  picker.addEventListener("value-changed", (event) =>
    onValueChanged(event.detail.value),
  );
}

export function configureBoundEntityPicker(
  picker,
  { hass, value, label, includeDomains, onValueChanged },
) {
  picker.label = label;
  picker.searchLabel = label;
  picker.allowCustomEntity = false;
  picker.required = true;
  picker.value = value;
  picker.hass = hass;
  picker.includeDomains = includeDomains;
  picker.addEventListener("value-changed", (event) => {
    event.stopPropagation();
    const next = event.detail.value;
    if (!next || next === value) return;
    onValueChanged(next);
  });
}
