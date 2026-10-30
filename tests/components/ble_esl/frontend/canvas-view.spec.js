import { test, expect } from "@playwright/test";
import {
  renderAlignmentGuides,
  renderLayerImageMarkup,
  renderLayerMarkup,
  resolveLayerLabel,
  renderSelectionMarkup,
  renderStageMarkup,
} from "../../../../custom_components/ble_esl/designer/frontend/editor/canvas/view.js";
import { selectionOverlayGeometry } from "../../../../custom_components/ble_esl/designer/frontend/editor/canvas/geometry.js";

const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const translate = (key, values) =>
  values ? key.replace("{corner}", values.corner) : key;

test("layer labels preserve element-specific and Home Assistant fallbacks", () => {
  const format = {
    state: { entity_id: "sensor.room", state: "21" },
    entityName: (state) => `Name: ${state.entity_id}`,
    specLabel: (element) => `Spec: ${element.spec.type}`,
  };
  expect(
    resolveLayerLabel({ type: "imagespec", spec: { type: "text" } }, format),
  ).toBe("Spec: text");
  expect(resolveLayerLabel({ type: "text", text: "" }, format)).toBe("text");
  expect(resolveLayerLabel({ type: "icon", icon: "mdi:home" }, format)).toBe(
    "mdi:home",
  );
  expect(
    resolveLayerLabel(
      { type: "sensor", label: "Room", entity_id: "sensor.room" },
      format,
    ),
  ).toBe("Room");
  expect(
    resolveLayerLabel({ type: "sensor", entity_id: "sensor.room" }, format),
  ).toBe("Name: sensor.room");
  expect(
    resolveLayerLabel(
      { type: "input_boolean", entity_id: "input_boolean.lamp" },
      {
        ...format,
        state: null,
      },
    ),
  ).toBe("input_boolean.lamp");
});

test("layer image view aligns renderer ink with resized non-text frames", () => {
  const element = { type: "imagespec", width: 16, height: 12 };
  const cropped = renderLayerImageMarkup({
    element,
    src: "layer-data",
    offset: [-2, 1],
    bounds: [0, 0, 10, 8],
    record: { size: [10, 8] },
  });
  expect(cropped).toContain('src="layer-data" alt="" aria-hidden="true"');
  expect(cropped).toContain("left:-2px;top:1px;width:16px;height:12px");

  const text = renderLayerImageMarkup({
    element: { ...element, type: "text" },
    src: "text-layer",
    offset: [2, 3],
    bounds: [0, 0, 10, 8],
    record: { size: [10, 8] },
  });
  expect(text).toContain("left:2px;top:3px;width:10px;height:8px");
  expect(
    renderLayerImageMarkup({
      element,
      src: "fallback",
      offset: null,
      bounds: null,
    }),
  ).not.toContain("style=");
});

test("canvas view composes accessible layers and exact preview markup", () => {
  const element = {
    id: "sensor<&",
    type: "sensor",
    x: 2,
    y: 3,
    width: 12,
    height: 8,
    color: "#123456",
    font_size: 9,
    align: "center",
  };
  const layer = renderLayerMarkup({
    element,
    index: 1,
    selected: true,
    rendered: "layer-data",
    label: "Room <sensor>",
    content: "21°C",
    hitBounds: [1, 0, 11, 8],
    layerImage: '<img class="layer-preview" src="layer-data">',
    faded: true,
    escape,
  });
  expect(layer).toContain('data-id="sensor&lt;&amp;"');
  expect(layer).toContain('aria-label="Room &lt;sensor&gt;"');
  expect(layer).toContain('aria-pressed="true"');
  expect(layer).toContain("z-index:2");
  expect(layer).toContain("left:1px;top:0px;width:10px;height:8px");
  expect(layer).toContain('style="opacity:.2"');

  const stage = renderStageMarkup({
    preview: "preview-data",
    previewLabel: "Exact display",
    layers: [layer],
    guides: "<span>guide</span>",
    selection: "<div>selection</div>",
  });
  expect(stage).toMatch(
    /^<img class="exact" src="preview-data" alt="Exact display">/,
  );
  expect(stage).toContain(layer);
  expect(stage.endsWith("<span>guide</span><div>selection</div>")).toBe(true);
});

test("selection view scales handles with zoom and guides match their axis", () => {
  const markup = renderSelectionMarkup({
    element: { id: "active", x: 10, y: 20, width: 16, height: 12 },
    geometry: selectionOverlayGeometry({
      element: { id: "active", x: 10, y: 20, width: 16, height: 12 },
      visible: [2, 1, 14, 11],
      zoom: 2,
      coarsePointer: true,
    }),
    translate,
    escape,
    deleteIcon: "delete-icon",
  });
  expect(markup).toContain('data-id="active"');
  expect(markup).toContain("left:12px;top:21px;width:12px;height:10px");
  expect(markup).toContain("width:16px;height:16px");
  expect(markup).toContain('aria-label="Resize nw"');
  expect(markup).toContain("translateX(-50%) scale(0.5)");
  expect(markup).toContain("delete-icon");

  const guides = renderAlignmentGuides([
    { axis: "x", position: 8 },
    { axis: "y", position: 12 },
  ]);
  expect(guides).toContain("left:8px;top:0;height:100%;border-left");
  expect(guides).toContain("left:0;top:12px;width:100%;border-top");
  expect(renderAlignmentGuides([])).toBe("");
});
