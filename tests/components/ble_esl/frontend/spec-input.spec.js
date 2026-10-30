import { expect, test } from "@playwright/test";
import { applySpecInput } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/spec-input.js";
import { specEditorHtml } from "../../../../custom_components/ble_esl/designer/frontend/spec-editor.js";

function input(path, value, extra = {}) {
  const attributes = new Map(),
    holder = {
      note: null,
      querySelector: () => holder.note,
      append(note) {
        note.remove = () => {
          holder.note = null;
        };
        holder.note = note;
      },
    };
  return {
    dataset: { spec: path, ...extra },
    value,
    holder,
    closest: () => holder,
    parentElement: holder,
    setAttribute: (key, value) => attributes.set(key, value),
    removeAttribute: (key) => attributes.delete(key),
    attributes,
  };
}

const definition = {
  fields: [
    {
      name: "style",
      kind: "object",
      fields: [{ name: "size", kind: "number" }],
    },
    { name: "items", kind: "array" },
    { name: "enabled", kind: "boolean" },
  ],
};

test("applies nested numbers and removes empty parent objects", () => {
  const spec = { style: { size: 12 } };
  expect(applySpecInput(input("style.size", "18"), spec, definition)).toBe(
    true,
  );
  expect(spec).toEqual({ style: { size: 18 } });
  expect(applySpecInput(input("style.size", ""), spec, definition)).toBe(true);
  expect(spec).toEqual({});
});

test("keeps invalid JSON and numeric input with accessible error feedback", () => {
  const originalDocument = globalThis.document;
  globalThis.document = {
    createElement: () => ({
      attributes: {},
      setAttribute(key, value) {
        this.attributes[key] = value;
      },
    }),
  };
  try {
    const spec = { items: ["last good"] },
      json = input("items", "[", { json: "" });
    expect(applySpecInput(json, spec, definition, {})).toBe(false);
    expect(spec.items).toEqual(["last good"]);
    expect(json.attributes.get("aria-invalid")).toBe("true");
    expect(json.holder.note).toMatchObject({
      className: "field-error",
      attributes: { role: "alert" },
    });

    const number = input("style.size", "12x");
    expect(applySpecInput(number, spec, definition, {})).toBe(false);
    expect(spec.style).toBeUndefined();
    expect(number.holder.note.textContent).toContain("Enter a number");

    number.value = "24";
    expect(applySpecInput(number, spec, definition, {})).toBe(true);
    expect(spec.style.size).toBe(24);
    expect(number.attributes.has("aria-invalid")).toBe(false);
    expect(number.holder.note).toBeNull();
  } finally {
    if (originalDocument === undefined) delete globalThis.document;
    else globalThis.document = originalDocument;
  }
});

test("supports template-valued JSON fields and boolean controls", () => {
  const spec = {};
  expect(
    applySpecInput(
      input("items", "{{ states('sensor.x') }}", { json: "" }),
      spec,
      definition,
    ),
  ).toBe(true);
  expect(spec.items).toBe("{{ states('sensor.x') }}");
  expect(applySpecInput(input("enabled", "false"), spec, definition)).toBe(
    true,
  );
  expect(spec.enabled).toBe(false);
});

test("renders quarter-turn rotation as an enum and stores it as a number", () => {
  const rotation = {
      name: "rotate",
      kind: "number",
      required: false,
      default: 0,
      enum: [0, 90, 180, 270],
    },
    definition = { type: "battery", fields: [rotation] },
    html = specEditorHtml(definition, {}, [], [], {});
  expect(html).toContain('data-spec="rotate"');
  expect(html).toContain('<option value="90"');
  expect(html).toContain('<option value="270"');

  const spec = {};
  expect(applySpecInput(input("rotate", "90"), spec, definition)).toBe(true);
  expect(spec.rotate).toBe(90);
});

test("imagespec field names stay as the YAML keys in every language", () => {
  const definition = {
    type: "text",
    fields: [
      { name: "text", kind: "string", required: true },
      { name: "font_size", kind: "number" },
    ],
  };
  const html = specEditorHtml(definition, {}, "BW", ["none"], {
    language: "ko",
  });
  expect(html).toContain(">Text *<");
  expect(html).toContain(">Font size<");
  expect(html).not.toContain("텍스트 *");
});
