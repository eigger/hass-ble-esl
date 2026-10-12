import { t } from "./i18n.js";
import { clone, palette } from "./model.js";
// Keep the historical spec-editor export for callers outside the inspector.
export { applySpecInput } from "./editor/inspector/spec-input.js";

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const LONG = new Set(["value", "text", "data", "values", "items", "points"]);
const getPath = (spec, path) =>
  path.split(".").reduce((node, key) => node?.[key], spec);

// "x_start" reads as "X start"; a required field is starred.
const label = (field, hass) => {
  const name = field.name.replaceAll("_", " ");
  return `${esc(t(hass, name[0].toUpperCase() + name.slice(1)))}${field.required ? " *" : ""}`;
};
const hint = (field) => (field.doc ? ` title="${esc(field.doc)}"` : "");
const placeholder = (field) =>
  field.default === undefined ? "" : ` placeholder="${esc(field.default)}"`;

function control(field, value, path, colors, hass) {
  const attrs = `data-spec="${esc(path)}" data-kind="${field.kind}" data-required="${!!field.required}" aria-label="${esc(path.replaceAll("_", " "))}${field.required ? t(hass, " (required)") : ""}"`;
  if (field.kind === "boolean") {
    const state = typeof value === "boolean" ? String(value) : "";
    return `<select ${attrs}>${[
      [
        "",
        field.default === undefined
          ? "—"
          : t(hass, "default ({value})", { value: field.default }),
      ],
      ["true", "yes"],
      ["false", "no"],
    ]
      .map(
        ([key, text]) =>
          `<option value="${key}" ${state === key ? "selected" : ""}>${t(hass, text)}</option>`,
      )
      .join(
        "",
      )}${typeof value === "string" ? `<option selected value="__keep">${esc(value)}</option>` : ""}</select>`;
  }
  if (field.kind === "enum" || field.enum) {
    const options = [...(field.enum || [])].map(String);
    const extra =
      value !== undefined && !options.includes(String(value))
        ? [String(value)]
        : [];
    return `<select ${attrs}><option value="">${field.default === undefined ? "—" : esc(t(hass, "default ({value})", { value: field.default }))}</option>${[
      ...options,
      ...extra,
    ]
      .map(
        (option) =>
          `<option value="${esc(option)}" ${String(value) === option ? "selected" : ""}>${esc(option)}</option>`,
      )
      .join("")}</select>`;
  }
  if (field.kind === "color") {
    const options = [...palette(colors), "transparent"];
    const extra =
      typeof value === "string" && value && !options.includes(value)
        ? [value]
        : [];
    return `<select ${attrs}><option value="">${field.default === undefined ? t(hass, "none") : esc(t(hass, "default ({value})", { value: field.default }))}</option>${[
      ...options,
      ...extra,
    ]
      .map(
        (color) =>
          `<option value="${esc(color)}" ${value === color ? "selected" : ""}>${esc(t(hass, color))}</option>`,
      )
      .join("")}</select>`;
  }
  if (field.kind === "number")
    return `<input ${attrs} type="text" value="${esc(value ?? "")}"${placeholder(field)}>`;
  if (["array", "elements", "object"].includes(field.kind))
    return `<textarea ${attrs} data-json rows="3" spellcheck="false"${placeholder(field)}>${value === undefined ? "" : esc(JSON.stringify(value, null, 1))}</textarea>`;
  if (LONG.has(field.name))
    return `<textarea ${attrs} rows="2"${placeholder(field)}>${esc(value ?? "")}</textarea>`;
  return `<input ${attrs} type="text" value="${esc(value ?? "")}"${placeholder(field)}>`;
}

function fieldsHtml(fields, spec, colors, prefix = "", hass) {
  return fields
    .map((field) => {
      const path = prefix + field.name;
      if (field.kind === "object" && field.fields?.length)
        return `<fieldset class="wide spec-group"><legend${hint(field)}>${label(field, hass)}</legend><div class="props">${fieldsHtml(field.fields, spec, colors, `${path}.`, hass)}</div></fieldset>`;
      return `<label class="${["array", "elements", "object"].includes(field.kind) || LONG.has(field.name) ? "wide" : ""}"${hint(field)}>${label(field, hass)}${control(field, getPath(spec, path), path, colors, hass)}</label>`;
    })
    .join("");
}

// The inspector for an imagespec element: every field imagespec declares for
// its type, except the position keys the frame supplies.
export function specEditorHtml(definition, spec, colors, ditherMethods, hass) {
  if (!definition) return "";
  const dither = `<label>${t(hass, "Dither")}<select data-spec="dither" data-kind="enum" aria-label="dither"><option value="">${t(hass, "off (default)")}</option>${ditherMethods
    .filter((method) => method !== "none")
    .map(
      (method) =>
        `<option value="${esc(method)}" ${spec.dither === method || (spec.dither === true && method === "floyd") ? "selected" : ""}>${esc(method)}</option>`,
    )
    .join("")}</select></label>`;
  return `<div class="wide spec-doc"><strong>${esc(definition.type.replaceAll("_", " "))}</strong>${definition.doc ? `<span class="muted"> ${esc(definition.doc)}</span>` : ""}</div>${fieldsHtml(definition.fields, spec, colors, "", hass)}${dither}<p class="muted wide">${t(hass, "Text fields accept Jinja templates, e.g.")} <code>{{ states('sensor.x') }}</code>.</p>`;
}

export function newSpecElement(definition, newElement, tag) {
  const element = newElement("imagespec", tag);
  element.width = definition.width;
  element.height = definition.height;
  element.spec = clone(definition.example);
  return element;
}

export const specLabel = (element) => element.spec?.type || "element";
