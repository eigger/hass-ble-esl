import { test, expect } from "@playwright/test";
import { renderTagOptions } from "../../custom_components/ble_esl/designer/frontend/editor/tag-selector.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

test("tag selector options keep selected tag, dimensions, labels, and escaping", () => {
  const selected = {
    entry_id: 'device<&"',
    title: "Fallback",
    width: 296,
    height: 128,
  };
  const other = {
    entry_id: "other",
    title: "Other",
    width: 200,
    height: 100,
  };
  const html = renderTagOptions([selected, other], selected, {
    tagName: (tag) => (tag === selected ? 'Kitchen & "Hall"' : tag.title),
    escapeHtml,
  });

  expect(html).toContain(
    '<option value="device&lt;&amp;&quot;" selected>Kitchen &amp; &quot;Hall&quot; · 296×128</option>',
  );
  expect(html).toContain('<option value="other" >Other · 200×100</option>');
});
