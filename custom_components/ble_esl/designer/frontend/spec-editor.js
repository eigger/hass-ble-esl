import { clone, palette } from "./model.js";

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const TEMPLATE = /\{[{%#]/;
const LONG = new Set(["value", "text", "data", "values", "items", "points"]);
const getPath = (spec, path) =>
  path.split(".").reduce((node, key) => node?.[key], spec);

// Set or clear one key, creating or dropping the objects around it.
function setPath(spec, path, value) {
  const keys = path.split("."),
    last = keys.pop(),
    chain = [spec];
  for (const key of keys) {
    let next = chain.at(-1)[key];
    if (next === null || typeof next !== "object" || Array.isArray(next)) {
      if (value === undefined) return;
      next = chain.at(-1)[key] = {};
    }
    chain.push(next);
  }
  if (value === undefined) delete chain.at(-1)[last];
  else chain.at(-1)[last] = value;
  for (let index = chain.length - 1; index > 0; index--)
    if (!Object.keys(chain[index]).length) delete chain[index - 1][keys[index - 1]];
}

const label = (field) =>
  `${esc(field.name.replaceAll("_", " "))}${field.required ? " *" : ""}`;
const hint = (field) => (field.doc ? ` title="${esc(field.doc)}"` : "");
const placeholder = (field) =>
  field.default === undefined ? "" : ` placeholder="${esc(field.default)}"`;

function control(field, value, path, colors) {
  const attrs = `data-spec="${esc(path)}" data-kind="${field.kind}" aria-label="${esc(path.replaceAll("_", " "))}${field.required ? " (required)" : ""}"`;
  if (field.kind === "boolean") {
    const state = typeof value === "boolean" ? String(value) : "";
    return `<select ${attrs}>${[
      ["", field.default === undefined ? "—" : `default (${field.default})`],
      ["true", "yes"],
      ["false", "no"],
    ]
      .map(
        ([key, text]) =>
          `<option value="${key}" ${state === key ? "selected" : ""}>${text}</option>`,
      )
      .join("")}${typeof value === "string" ? `<option selected value="__keep">${esc(value)}</option>` : ""}</select>`;
  }
  if (field.kind === "enum" || field.enum) {
    const options = [...(field.enum || [])].map(String);
    const extra =
      value !== undefined && !options.includes(String(value))
        ? [String(value)]
        : [];
    return `<select ${attrs}><option value="">${field.default === undefined ? "—" : `default (${esc(field.default)})`}</option>${[...options, ...extra]
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
    return `<select ${attrs}><option value="">${field.default === undefined ? "none" : `default (${esc(field.default)})`}</option>${[...options, ...extra]
      .map(
        (color) =>
          `<option value="${esc(color)}" ${value === color ? "selected" : ""}>${esc(color)}</option>`,
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

function fieldsHtml(fields, spec, colors, prefix = "") {
  return fields
    .map((field) => {
      const path = prefix + field.name;
      if (field.kind === "object" && field.fields?.length)
        return `<fieldset class="wide spec-group"><legend${hint(field)}>${label(field)}</legend><div class="props">${fieldsHtml(field.fields, spec, colors, `${path}.`)}</div></fieldset>`;
      return `<label class="${["array", "elements", "object"].includes(field.kind) || LONG.has(field.name) ? "wide" : ""}"${hint(field)}>${label(field)}${control(field, getPath(spec, path), path, colors)}</label>`;
    })
    .join("");
}

// The inspector for an imagespec element: every field imagespec declares for
// its type, except the position keys the frame supplies.
export function specEditorHtml(definition, spec, colors, ditherMethods) {
  if (!definition) return "";
  const dither = `<label>dither<select data-spec="dither" data-kind="enum" aria-label="dither"><option value="">none</option>${ditherMethods
    .filter((method) => method !== "none")
    .map(
      (method) =>
        `<option value="${esc(method)}" ${spec.dither === method || (spec.dither === true && method === "floyd") ? "selected" : ""}>${esc(method)}</option>`,
    )
    .join("")}</select></label>`;
  return `<div class="wide spec-doc"><strong>${esc(definition.type.replaceAll("_", " "))}</strong>${definition.doc ? `<span class="muted"> ${esc(definition.doc)}</span>` : ""}</div>${fieldsHtml(definition.fields, spec, colors)}${dither}<p class="muted wide">Text fields accept Jinja templates, e.g. <code>{{ states('sensor.x') }}</code>.</p>`;
}

const find = (fields, path) => {
  const [head, ...rest] = path.split(".");
  const field = fields.find((candidate) => candidate.name === head);
  return rest.length ? find(field?.fields || [], rest.join(".")) : field;
};

// Apply one input to the spec. Returns false when the input is not a value yet
// (half-typed JSON or a number), so the spec keeps its last good value.
export function applySpecInput(input, spec, definition) {
  const path = input.dataset.spec,
    field =
      path === "dither"
        ? { kind: "enum" }
        : find(definition?.fields || [], path);
  if (!field) return false;
  const raw = input.value;
  input.removeAttribute("aria-invalid");
  if (raw === "__keep") return true;
  if (raw === "") {
    setPath(spec, path, undefined);
    return true;
  }
  let value = raw;
  if ("json" in input.dataset) {
    try {
      value = JSON.parse(raw);
    } catch {
      // A template standing for the whole list is rendered when it is built.
      if (!TEMPLATE.test(raw)) {
        input.setAttribute("aria-invalid", "true");
        return false;
      }
    }
  } else if (field.kind === "number") {
    if (TEMPLATE.test(raw)) value = raw;
    else if (raw.trim() !== "" && Number.isFinite(Number(raw)))
      value = Number(raw);
    else {
      input.setAttribute("aria-invalid", "true");
      return false;
    }
  } else if (field.kind === "boolean") value = raw === "true";
  setPath(spec, path, value);
  return true;
}

export function newSpecElement(definition, newElement, tag) {
  const element = newElement("imagespec", tag);
  element.width = definition.width;
  element.height = definition.height;
  element.spec = clone(definition.example);
  return element;
}

export const specLabel = (element) => element.spec?.type || "element";
