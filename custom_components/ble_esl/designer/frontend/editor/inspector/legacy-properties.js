import { renderElementRotation } from "../rotation-control.js";
export function renderLegacyElementProperties(element, dependencies) {
  const {
    translate,
    escapeHtml,
    colorPicker,
    iconGlyph,
    tokenText,
    stateIconRows,
    extraProperties,
    textAlignmentControls,
    weatherControls,
    shapeTypes,
    mode,
    advancedOpen,
    sensorOptions,
  } = dependencies;
  const field = (key, label, type = "text", wide = false) =>
    '<label class="' +
    (wide ? "wide" : "") +
    '">' +
    label +
    '<input data-property="' +
    key +
    '" type="' +
    type +
    '" value="' +
    escapeHtml(element[key] ?? "") +
    '"' +
    (type === "number" ? ' step="1"' : "") +
    "></label>";
  const group = (title, body) =>
    body ? '<h3 class="wide group-title">' + title + "</h3>" + body : "";
  const position = group(
    translate("Position & size (px)"),
    ["x", "y", "width", "height"]
      .map((key) => field(key, key[0].toUpperCase() + key.slice(1), "number"))
      .join("") + renderElementRotation(element, translate),
  );
  let html = "";
  let style = "";
  let picker = "";

  if (["progress_bar", "gauge"].includes(element.type))
    html +=
      field("min_value", translate("Minimum"), "number") +
      field("max_value", translate("Maximum"), "number") +
      field("value", translate("Value"), "number", true);
  if (element.type === "gauge")
    style += field("font_size", translate("Font size"), "number");
  if (["sensor", "text"].includes(element.type))
    style += textAlignmentControls(element);
  style += colorPicker("color", element.color, translate("Colour"));
  if (shapeTypes.includes(element.type))
    style +=
      '<label class="wide">' +
      translate("Shape") +
      '<select data-property="type" aria-label="' +
      translate("Shape") +
      '">' +
      shapeTypes
        .map(
          (type) =>
            '<option value="' +
            type +
            '" ' +
            (element.type === type ? "selected" : "") +
            ">" +
            type.replace("_", " ") +
            "</option>",
        )
        .join("") +
      "</select></label>";

  if (element.type === "image")
    html +=
      '<label class="wide">' +
      translate("Image URL") +
      '<input data-property="image" aria-label="' +
      translate("Image URL") +
      '" placeholder="' +
      translate("Paste a URL, or upload below") +
      '" value="' +
      escapeHtml(
        element.image?.startsWith("data:") ? "" : (element.image ?? ""),
      ) +
      '"></label><label class="wide">' +
      translate("Image") +
      '<input id="image-file" aria-label="' +
      translate("Upload image") +
      '" type="file" accept="image/*"></label><label class="wide">' +
      translate("Fit") +
      '<select data-property="image_fit" aria-label="' +
      translate("Image fit") +
      '">' +
      ["contain", "fill", "stretch"]
        .map(
          (value) =>
            '<option value="' +
            value +
            '" ' +
            (element.image_fit === value ? "selected" : "") +
            ">" +
            translate(value) +
            "</option>",
        )
        .join("") +
      "</select></label>";
  if (element.type === "icon")
    html +=
      '<label class="wide">' +
      translate("Icon") +
      '<button class="icon-choice" data-action="pick-icon" aria-label="' +
      translate("Choose icon") +
      '">' +
      iconGlyph(tokenText(element.icon), 24) +
      "<span>" +
      (element.icon === "{{icon}}"
        ? translate("HA state icon")
        : escapeHtml(element.icon.replace("mdi:", ""))) +
      '</span></button><input data-property="icon" aria-label="' +
      translate("Icon name") +
      '" value="' +
      escapeHtml(element.icon) +
      '" hidden></label>';

  const extra = extraProperties(element);
  style += extra.style;
  style +=
    '<label class="wide check"><input type="checkbox" data-property="visible" ' +
    (element.visible === false ? "" : "checked") +
    ">" +
    translate("Visible") +
    "</label>";
  if (mode === "template" && element.type === "icon")
    html += stateIconRows(element);
  if (mode === "template" && element.type !== "icon")
    html +=
      '<label class="wide">' +
      translate("Show for state") +
      '<input data-property="state" aria-label="' +
      translate("Visible state") +
      '" placeholder="' +
      translate("All states") +
      '" list="template-states" value="' +
      escapeHtml(element.state || "") +
      '"><datalist id="template-states">' +
      sensorOptions.templateStates
        .map((state) => '<option value="' + escapeHtml(state) + '"></option>')
        .join("") +
      "</datalist></label>";
  if (element.type === "text")
    html +=
      '<label class="wide">' +
      translate("Text") +
      '<textarea data-property="text" rows="3">' +
      escapeHtml(element.text) +
      "</textarea></label>";
  if (element.type === "sensor") {
    if (sensorOptions.isWeather) html += weatherControls(element);
    html +=
      '<label class="wide">' +
      translate("Tile style") +
      '<select data-property="template" aria-label="' +
      translate("Sensor tile style") +
      '"><option value="auto">' +
      translate("By sensor type") +
      '</option><option value="default" ' +
      (element.template === "default" ? "selected" : "") +
      ">" +
      translate("HA tile") +
      "</option>" +
      sensorOptions.templateStyles
        .map(
          ({ value, label, selected }) =>
            '<option value="' +
            escapeHtml(value) +
            '" ' +
            (selected ? "selected" : "") +
            ">" +
            escapeHtml(label) +
            "</option>",
        )
        .join("") +
      '<option value="__new__">' +
      translate("＋ Create tile style…") +
      "</option></select></label>";
    picker =
      '<ha-entity-picker class="wide" data-property="entity_id"></ha-entity-picker>';
    html +=
      '<label class="wide check"><input type="checkbox" data-property="show_label" ' +
      (element.show_label ? "checked" : "") +
      ">" +
      translate("Show label") +
      "</label>";
    if (element.show_label)
      html += field("label", translate("Label override"), "text", true);
    if (sensorOptions.numeric) {
      html +=
        '<label class="wide check"><input type="checkbox" data-property="show_unit" ' +
        (element.show_unit ? "checked" : "") +
        ">" +
        translate("Show unit") +
        "</label>";
      if (element.show_unit)
        html += field(
          "decimals",
          translate("Decimals (auto when blank)"),
          "number",
          true,
        );
    }
  }

  return (
    group(translate("Content"), picker + html) +
    position +
    group(translate("Style"), style) +
    (extra.advanced
      ? '<details class="wide advanced" ' +
        (advancedOpen ? "open" : "") +
        "><summary>" +
        translate("Advanced") +
        '</summary><div class="props">' +
        extra.advanced +
        "</div></details>"
      : "")
  );
}
