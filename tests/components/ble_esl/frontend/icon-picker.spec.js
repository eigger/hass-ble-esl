import { test, expect } from "@playwright/test";
import {
  renderIconChoices,
  renderIconGlyph,
} from "../../../../custom_components/ble_esl/designer/frontend/editor/icon-picker.js";

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

test("icon choices search case-insensitively and keep accessible button markup", () => {
  const markup = renderIconChoices(
    { "weather-sunny": "sun & rays", "weather-night": "moon", alarm: "clock" },
    "WEATHER-N",
    escapeHtml,
  );

  expect(markup).toContain('data-icon="weather-night"');
  expect(markup).toContain('aria-label="weather-night"');
  expect(markup).not.toContain("weather-sunny");
  expect(markup).not.toContain("alarm");
});

test("icon markup escapes catalog values and limits the chooser to 120 entries", () => {
  const icons = Object.fromEntries(
    Array.from({ length: 121 }, (_, index) => [`icon-${index}`, "glyph <&"]),
  );
  icons['unsafe"name'] = "glyph <&";

  const markup = renderIconChoices(icons, "unsafe", escapeHtml);
  expect(markup).toContain('data-icon="unsafe&quot;name"');
  expect(markup).toContain("glyph &lt;&amp;");

  const limited = renderIconChoices(icons, "", escapeHtml);
  expect((limited.match(/<button/g) || []).length).toBe(120);
  expect(limited).not.toContain('data-icon="icon-120"');
});

test("individual icon glyphs retain the requested size and escape font content", () => {
  expect(
    renderIconGlyph("mdi:test", 32, { "mdi:test": "<path>&" }, escapeHtml),
  ).toBe(
    '<span class="mdi" aria-hidden="true" style="font-size:32px">&lt;path&gt;&amp;</span>',
  );
});
