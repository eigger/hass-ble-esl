const shapeTypes = [
  "rectangle",
  "rounded_rectangle",
  "ellipse",
  "triangle",
  "line",
];

export function renderOptionalProperties(
  element,
  { translate, escapeHtml, colorPicker, ditherMethods = [] },
) {
  const type = element.type;
  const text = ["sensor", "text"].includes(type);
  const shape = shapeTypes.includes(type) && type !== "line";
  const choice = (key, label, options, fallback = "default") =>
    `<label>${label}<select data-property="${key}" aria-label="${label}"><option value="">${translate(fallback)}</option>${options.map((value) => `<option value="${value}" ${element[key] === value ? "selected" : ""}>${translate(value.replaceAll("_", " "))}</option>`).join("")}</select></label>`;
  const number = (key, label, min, max, placeholder = "") =>
    `<label>${label}<input data-property="${key}" type="number" step="1" min="${min}" max="${max}" placeholder="${placeholder}" value="${escapeHtml(element[key] ?? "")}"></label>`;
  const flag = (key, label, fallback) =>
    `<label class="wide check"><input type="checkbox" data-property="${key}" ${(element[key] ?? fallback) ? "checked" : ""}>${label}</label>`;
  const methods = (
    ditherMethods?.length ? ditherMethods : ["none", "floyd"]
  ).filter((method) => method !== "none");
  const dither =
    element.dither === true
      ? "floyd"
      : element.dither === false
        ? "none"
        : (element.dither ?? "");
  let style = "";
  let advanced = "";

  if (text)
    advanced +=
      choice("valign", translate("Vertical align"), [
        "top",
        "middle",
        "bottom",
      ]) +
      choice(
        "fit",
        translate("Fit"),
        ["shrink", "ellipsis", "shrink_ellipsis"],
        "default (shrink ellipsis)",
      ) +
      number(
        "max_lines",
        translate("Max lines"),
        1,
        20,
        type === "text" ? "3" : "1",
      ) +
      number("min_font_size", translate("Min font size"), 1, 200, "8") +
      number("padding", translate("Padding"), 0, 100, "0") +
      number("line_spacing", translate("Line spacing"), 0, 100, "2") +
      `<label class="wide">${translate("Font file")}<input data-property="font" placeholder="${translate("Default font")}" value="${escapeHtml(element.font ?? "")}"></label>`;
  if (shape)
    style +=
      flag("filled", translate("Filled"), true) +
      number("line_width", translate("Outline width"), 1, 20, "1") +
      (type === "rounded_rectangle"
        ? number("radius", translate("Corner radius"), 0, 200, "auto")
        : "");
  if (type === "icon")
    advanced +=
      number("stroke_width", translate("Outline width"), 0, 20, "0") +
      colorPicker(
        "stroke_fill",
        element.stroke_fill ?? "white",
        translate("Outline colour"),
      );
  if (type === "image")
    style +=
      number("rotate", translate("Image rotation (°)"), -360, 360, "0") +
      flag("circle", translate("Crop to circle"), false);
  if (type === "progress_bar")
    style +=
      choice(
        "direction",
        translate("Direction"),
        ["right", "left", "up", "down"],
        "default (right)",
      ) +
      number("radius", translate("Corner radius"), 0, 200, "0") +
      number("line_width", translate("Outline width"), 1, 20, "1") +
      flag("show_percentage", translate("Show percentage"), false);
  if (type === "gauge")
    style +=
      number("thickness", translate("Arc thickness"), 1, 100, "8") +
      flag("show_value", translate("Show value"), true);
  if (["progress_bar", "gauge"].includes(type))
    advanced += `<label class="wide">${translate("Font file")}<input data-property="font" placeholder="${translate("Default font")}" value="${escapeHtml(element.font ?? "")}"></label>`;
  advanced += `<label class="wide">${translate("Dither")}<select data-property="dither" aria-label="${translate("Dither")}"><option value="">${type === "image" ? translate("default (floyd)") : translate("off (default)")}</option><option value="none" ${dither === "none" ? "selected" : ""}>${translate("none")}</option>${methods.map((method) => `<option value="${escapeHtml(method)}" ${dither === method ? "selected" : ""}>${escapeHtml(method)}</option>`).join("")}</select></label>`;

  return { style, advanced };
}
