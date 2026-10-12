import { test, expect } from "@playwright/test";
import {
  alignmentGuides,
  clampMoved,
  clampResized,
  elementShape,
  fitZoom,
  moveBound,
  staggerElement,
  visibleBounds,
} from "../../custom_components/ble_esl/designer/frontend/editor/canvas/geometry.js";

const tag = { width: 32, height: 24 };
const element = (overrides = {}) => ({
  id: "active",
  type: "rectangle",
  x: 4,
  y: 3,
  width: 10,
  height: 8,
  ...overrides,
});

test("fit zoom keeps the preview margin, precision, and zoom bounds", () => {
  expect(
    fitZoom({
      viewportWidth: 360,
      viewportHeight: 260,
      tagWidth: 200,
      tagHeight: 100,
    }),
  ).toBe(1.5);
  expect(
    fitZoom({
      viewportWidth: 393,
      viewportHeight: 393,
      tagWidth: 100,
      tagHeight: 100,
    }),
  ).toBe(3.33);
  expect(
    fitZoom({
      viewportWidth: 20,
      viewportHeight: 20,
      tagWidth: 100,
      tagHeight: 100,
    }),
  ).toBe(0.1);
  expect(
    fitZoom({
      viewportWidth: 10000,
      viewportHeight: 10000,
      tagWidth: 100,
      tagHeight: 100,
    }),
  ).toBe(8);
});

test("new element staggering skips occupied positions and stops at tag bounds", () => {
  const initial = element({ x: 4, y: 3 });
  const existing = [initial, element({ id: "next", x: 12, y: 11 })];
  const added = element({ id: "added", x: 4, y: 3, width: 8, height: 4 });

  expect(staggerElement(added, existing, tag)).toMatchObject({ x: 20, y: 19 });
  expect(added).toMatchObject({ x: 4, y: 3 });
  expect(existing).toHaveLength(2);
  expect(
    staggerElement(
      element({ x: 24, y: 16, width: 8, height: 8 }),
      [element({ x: 24, y: 16, width: 8, height: 8 })],
      tag,
    ),
  ).toMatchObject({ x: 24, y: 16 });
});

test("render shape ignores frame changes and summarizes uploaded image data", () => {
  const original = element({
    image: `data:image/png;base64,${"a".repeat(100)}`,
  });
  const movedAndResized = {
    ...original,
    x: 20,
    y: 10,
    width: 18,
    height: 12,
  };
  expect(elementShape(original)).toBe(elementShape(movedAndResized));
  expect(
    elementShape({
      ...original,
      image: `data:image/png;base64,${"b".repeat(100)}`,
    }),
  ).not.toBe(elementShape(original));
});

test("visible bounds distinguish unknown, empty, and renderer measured content", () => {
  const item = element();
  const record = { shape: elementShape(item), size: [10, 8] };
  expect(visibleBounds(item, { record: undefined, layerBounds: {} })).toBe(
    undefined,
  );
  expect(
    visibleBounds(item, { record, layerBounds: { active: null } }),
  ).toBeNull();
  expect(
    visibleBounds(item, {
      record,
      layerBounds: { active: [2, 1, 8, 6] },
    }),
  ).toEqual([2, 1, 8, 6]);
  expect(
    visibleBounds(
      { ...item, width: 14 },
      {
        record,
        layerBounds: { active: [2, 1, 8, 6] },
      },
    ),
  ).toEqual([2, 1, 12, 6]);
  expect(
    visibleBounds({ ...item, type: "text" }, { record, layerBounds: {} }),
  ).toBeUndefined();
});

test("alignment guides use renderer bounds and six screen pixels at current zoom", () => {
  const active = element({ x: 10, y: 8, width: 10, height: 8 });
  const peer = element({ id: "peer", x: 24, y: 18, width: 10, height: 8 });
  const layerRecords = Object.fromEntries(
    [active, peer].map((item) => [
      item.id,
      { shape: elementShape(item), size: [item.width, item.height] },
    ]),
  );
  const guideTag = { width: 100, height: 100 };
  const guides = alignmentGuides({
    element: active,
    elements: [active, peer],
    tag: guideTag,
    layerRecords,
    layerBounds: {
      active: [0, 0, 12, 8],
      peer: [0, 0, 10, 8],
    },
    zoom: 2,
  });
  expect(guides).toContainEqual({ axis: "x", position: 24, distance: 2 });

  const outsideTolerance = alignmentGuides({
    element: active,
    elements: [active, { ...peer, x: 26 }],
    tag: guideTag,
    layerRecords,
    layerBounds: {
      active: [0, 0, 12, 8],
      peer: [0, 0, 10, 8],
    },
    zoom: 2,
  });
  expect(outsideTolerance.some(({ axis }) => axis === "x")).toBe(false);
});

test("move bounds and clamping account for visible ink and preserve caller ownership", () => {
  const item = element({ x: -3, y: -2 });
  const visible = [3, 2, 15, 12];
  expect(moveBound(item, tag, visible)).toBe(true);
  item.x = -8;
  item.y = -8;
  const clamped = clampMoved(item, tag, true, visible);
  expect(clamped).toMatchObject({ x: -3, y: -2 });
  expect(item).toMatchObject({ x: -8, y: -8 });
  expect(moveBound({ ...item, x: -20 }, tag, visible)).toBe(false);
});

test("resize clamping keeps renderer measured content inside tag dimensions", () => {
  const item = element({ x: -2, y: -1, width: 20, height: 20 });
  const record = {
    shape: elementShape(item),
    size: [20, 20],
  };
  const result = clampResized(item, {
    tag,
    layerRecords: { active: record },
    layerBounds: { active: [-4, -2, 20, 15] },
  });
  expect(result).toMatchObject({ x: 4, y: 2, width: 14, height: 17 });
  expect(item).toMatchObject({ x: -2, y: -1, width: 20, height: 20 });
});
