import { t } from "../../i18n.js";

const TEMPLATE = /\{[{%#]/;

const find = (fields, path) => {
  const [head, ...rest] = path.split("."),
    field = fields.find((candidate) => candidate.name === head);
  return rest.length ? find(field?.fields || [], rest.join(".")) : field;
};

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
    if (!Object.keys(chain[index]).length)
      delete chain[index - 1][keys[index - 1]];
}

// A red border alone does not say what is wrong: say it under the field.
function flag(input, message) {
  const holder = input.closest("label") || input.parentElement;
  let note = holder.querySelector(".field-error");
  if (!message) {
    note?.remove();
    input.removeAttribute("aria-invalid");
    return;
  }
  input.setAttribute("aria-invalid", "true");
  if (!note) {
    note = document.createElement("span");
    note.className = "field-error";
    note.setAttribute("role", "alert");
    holder.append(note);
  }
  note.textContent = message;
}

// Apply one input to the spec. Invalid, incomplete values keep the last good
// value and expose the existing accessible inline error.
export function applySpecInput(input, spec, definition, hass) {
  const path = input.dataset.spec,
    field =
      path === "dither"
        ? { kind: "enum" }
        : find(definition?.fields || [], path);
  if (!field) return false;
  const raw = input.value;
  flag(input, "");
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
        flag(input, t(hass, "Not valid JSON: check the brackets and quotes"));
        return false;
      }
    }
  } else if (field.kind === "number") {
    if (TEMPLATE.test(raw)) value = raw;
    else if (raw.trim() !== "" && Number.isFinite(Number(raw)))
      value = Number(raw);
    else {
      flag(input, t(hass, "Enter a number, or a {{ template }}"));
      return false;
    }
  } else if (field.kind === "boolean") value = raw === "true";
  setPath(spec, path, value);
  return true;
}
