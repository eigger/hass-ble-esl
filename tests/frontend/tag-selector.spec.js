import { test, expect } from "@playwright/test";
import {
  renderTagOptions,
  resolveTagName,
} from "../../custom_components/ble_esl/designer/frontend/editor/tag-selector.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

test("tag alias display falls back for unavailable or blank states", () => {
  const tag = { title: "Bedroom", entities: { alias: "input_text.tag_name" } };
  expect(resolveTagName(tag, { state: "Kitchen" })).toBe("Kitchen");
  expect(resolveTagName(tag, { state: "unknown" })).toBe("Bedroom");
  expect(resolveTagName(tag, { state: "unavailable" })).toBe("Bedroom");
  expect(resolveTagName(tag, { state: "  " })).toBe("Bedroom");
  expect(resolveTagName(tag, null)).toBe("Bedroom");
});

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
