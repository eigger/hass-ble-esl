import { expect, test } from "@playwright/test";
import {
  renderTemplateControls,
  renderTemplateParts,
} from "../../../../custom_components/ble_esl/designer/frontend/editor/template-controls.js";

const translate = (text, variables = {}) =>
  text.replace(/\{(\w+)\}/g, (_, key) => variables[key]);
const escapeHtml = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );

test("template controls preserve labels, selected style, and escaped values", () => {
  const markup = renderTemplateControls({
    mode: "template",
    translate,
    escapeHtml,
    sampleOutput: "numeric",
    templateTypes: ["output:numeric", "sensor:temperature"],
    templates: { "sensor:temperature": { name: "Temperature" } },
    templateDrafts: new Map(),
    templateKey: "output:numeric",
    templateName: 'My "style"',
    width: 140,
    height: 60,
  });

  expect(markup).toContain(
    'aria-label="Style name" value="My &quot;style&quot;"',
  );
  expect(markup).toContain(
    '<option value="output:numeric" selected>numeric style</option>',
  );
  expect(markup).toContain(
    '<option value="sensor:temperature" >Temperature</option>',
  );
  expect(markup).toContain(
    'aria-label="Style width" type="number" min="16" max="1000" value="140"',
  );
  expect(markup).toContain("numeric output");
});

test("template controls and token tools stay hidden outside template mode", () => {
  expect(renderTemplateControls({ mode: "display" })).toBe("");
  expect(renderTemplateParts({ mode: "display" })).toBe("");
});

test("template token tools keep their existing actions and translated labels", () => {
  expect(renderTemplateParts({ mode: "template", translate })).toBe(
    '<div class="tools"><button data-token="name">Name</button><button data-token="state">State</button><button data-token="unit">Unit</button><button data-action="add-state-icon">State icon</button></div>',
  );
});
