// Mirror the server schema defaults for legacy imported elements, so preview,
// imported display, and the next save render minimal documents identically.
const importedElementDefaults = {
  spec: {},
  color: "black",
  background: "transparent",
  visible: true,
  font_size: 24,
  text: "Text",
  image: "",
  image_fit: "contain",
  icon: "{{icon}}",
  state: "",
  state_icons: {},
  template: "auto",
  weather_when: "now",
  weather_field: "condition",
  entity_id: "",
  field_templates: {},
  data_field: "",
  attribute: "",
  value: 0,
  min_value: 0,
  max_value: 100,
  icon_rules: [],
  label: "",
  show_label: true,
  show_unit: true,
  align: "left",
};

/**
 * Fill legacy imported documents with the editor's current defaults.
 * Dependencies that provide document defaults, copying, and IDs are explicit
 * so this operation stays independent of the panel, browser UI, and HA.
 */
export function normalizeImportedDocument(
  document,
  { emptyDocument, clone, createId },
) {
  const normalized = {
    ...emptyDocument(),
    ...document,
    elements: Array.isArray(document?.elements) ? document.elements : [],
  };
  normalized.elements = normalized.elements.map((element) => ({
    ...clone(importedElementDefaults),
    ...element,
    id: element.id || createId(),
  }));
  return normalized;
}
