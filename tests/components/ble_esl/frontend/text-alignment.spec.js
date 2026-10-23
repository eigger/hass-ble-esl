import { expect, test } from "@playwright/test";
import { renderTextAlignmentControls } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/text-alignment.js";

test("text alignment controls preserve font size, accessible labels, and selection state", () => {
  const controls = renderTextAlignmentControls(
    { align: "center", font_size: 18 },
    {
      translate: (message) => message,
      escapeHtml: (value) => String(value).replaceAll("&", "&amp;"),
    },
  );

  expect(controls).toContain('data-property="font_size" type="number"');
  expect(controls).toContain('value="18" step="1"');
  expect(controls).toContain('role="group" aria-label="Text alignment"');
  expect(controls).toContain(
    'data-pick="align" data-value="left" aria-label="Align left" title="Align left" aria-pressed="false"',
  );
  expect(controls).toContain(
    'data-pick="align" data-value="center" aria-label="Align center" title="Align center" aria-pressed="true"',
  );
  expect(controls).toContain(
    'data-pick="align" data-value="right" aria-label="Align right" title="Align right" aria-pressed="false"',
  );
  expect(controls).toContain('icon="mdi:format-align-center"');
  expect(controls).not.toContain("<svg");
});

test("font size escapes authored values and unset alignment stays unselected", () => {
  const controls = renderTextAlignmentControls(
    { font_size: '"&' },
    {
      translate: (message) => message,
      escapeHtml: (value) =>
        String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;"),
    },
  );

  expect(controls).toContain('value="&quot;&amp;" step="1"');
  expect(controls).toContain(
    'data-value="left" aria-label="Align left" title="Align left" aria-pressed="false"',
  );
  expect(controls).toContain(
    'data-value="center" aria-label="Align center" title="Align center" aria-pressed="false"',
  );
  expect(controls).toContain(
    'data-value="right" aria-label="Align right" title="Align right" aria-pressed="false"',
  );
  const blank = renderTextAlignmentControls(
    {},
    {
      translate: (message) => message,
      escapeHtml: (value) => String(value),
    },
  );
  expect(blank).toContain('value="" step="1"');
});
