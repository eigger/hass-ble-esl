import { test, expect } from "@playwright/test";
import {
  clone,
  emptyDocument,
} from "../../custom_components/ble_esl/designer/frontend/model.js";
import { normalizeImportedDocument } from "../../custom_components/ble_esl/designer/frontend/editor/document-operations.js";

const dependencies = {
  clone,
  emptyDocument,
  createId: (() => {
    let next = 0;
    return () => `generated-${++next}`;
  })(),
};

test("normalizes imported document defaults without losing document settings", () => {
  const result = normalizeImportedDocument(
    {
      version: 3,
      background: "red",
      custom_document_field: "kept",
      elements: [
        { id: "existing", type: "text", text: "Welcome", spec: { text: 12 } },
        { id: "", type: "sensor", visible: false },
        { type: "icon", value: null },
      ],
    },
    dependencies,
  );

  expect(result).toMatchObject({
    version: 3,
    background: "red",
    custom_document_field: "kept",
    elements: [
      {
        id: "existing",
        type: "text",
        text: "Welcome",
        color: "black",
        background: "transparent",
        visible: true,
        value: 0,
        spec: { text: 12 },
      },
      {
        id: "generated-1",
        type: "sensor",
        visible: false,
        entity_id: "",
        icon_rules: [],
      },
      {
        id: "generated-2",
        type: "icon",
        value: null,
        icon: "{{icon}}",
      },
    ],
  });
  expect(result.elements[0].spec).not.toBe(result.elements[1].spec);
  expect(result.elements[0].icon_rules).not.toBe(result.elements[1].icon_rules);
});

test("uses empty document defaults and an empty element list for invalid input", () => {
  expect(normalizeImportedDocument(undefined, dependencies)).toEqual({
    version: 1,
    background: "white",
    elements: [],
  });
  expect(
    normalizeImportedDocument(
      { version: 7, background: null, elements: {} },
      dependencies,
    ),
  ).toEqual({ version: 7, background: null, elements: [] });
});
