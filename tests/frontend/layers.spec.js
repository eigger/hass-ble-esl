import { test, expect } from "@playwright/test";
import { renderLayerRows } from "../../custom_components/ble_esl/designer/frontend/editor/inspector/layers.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );

test("layer rows put the front item first and preserve safe selected and hidden states", () => {
  const rows = renderLayerRows({
    elements: [
      { id: "back", visible: true, name: "Back layer" },
      { id: "front", visible: false, name: "<Front & center>" },
    ],
    selected: "front",
    layerLabel: (item) => item.name,
    t: (message, values) =>
      message.replace(/\{(\w+)\}/g, (_, key) => values?.[key] ?? `{${key}}`),
    esc: escapeHtml,
    icon: (name) => `<svg data-icon="${name}"></svg>`,
    toolIcon: (name) => `<svg data-icon="${name}"></svg>`,
  });

  expect(rows.indexOf('data-select="front"')).toBeLessThan(
    rows.indexOf('data-select="back"'),
  );
  expect(rows).toContain('class="layer active" data-select="front"');
  expect(rows).toContain(
    'aria-pressed="true">&lt;Front &amp; center&gt;</button>',
  );
  expect(rows).toContain('class="layer-row hidden-layer"');
  expect(rows).toContain(
    'data-layer-action="visible" aria-label="Show &lt;Front &amp; center&gt;" aria-pressed="true"',
  );
  expect(rows).toContain('data-delete-layer="front"');
  expect(rows).not.toContain("<Front & center>");
});
