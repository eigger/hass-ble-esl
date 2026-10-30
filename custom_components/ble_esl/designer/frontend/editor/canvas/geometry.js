import { clampBox, onLabel } from "../../model.js";

// Fit a tag inside the preview viewport while retaining the editor's margin,
// hundredth-step zoom, and supported zoom range.
export function fitZoom({
  viewportWidth,
  viewportHeight,
  tagWidth,
  tagHeight,
}) {
  return Math.max(
    0.1,
    Math.min(
      8,
      Math.floor(
        Math.min(
          (viewportWidth - 60) / tagWidth,
          (viewportHeight - 60) / tagHeight,
        ) * 100,
      ) / 100,
    ),
  );
}

export function selectionOverlayGeometry({
  element,
  visible,
  zoom,
  coarsePointer,
}) {
  if (!element) return null;
  const [left, top, right, bottom] = visible || [
      0,
      0,
      element.width,
      element.height,
    ],
    width = right - left,
    height = bottom - top;
  return {
    left: element.x + left,
    top: element.y + top,
    width,
    height,
    zoom,
    handleSize: (coarsePointer ? 32 : 20) / zoom,
  };
}

export function contextMenuPosition({
  pointerX,
  pointerY,
  viewportWidth,
  viewportHeight,
  menuWidth = 228,
  menuHeight = 220,
}) {
  return {
    left: Math.min(pointerX, viewportWidth - menuWidth),
    top: Math.min(pointerY, viewportHeight - menuHeight),
  };
}

// Place newly added elements beside existing ones without mutating either
// the source element or the document's element list.
export function staggerElement(element, elements, tag, step = 8) {
  const placed = { ...element };
  const taken = (x, y) => elements.some((item) => item.x === x && item.y === y);
  while (taken(placed.x, placed.y)) {
    const x = placed.x + step,
      y = placed.y + step;
    if (x + placed.width > tag.width || y + placed.height > tag.height) break;
    placed.x = x;
    placed.y = y;
  }
  return placed;
}

// Renderer records describe the visible content for a particular element
// shape, independently of its frame position and dimensions. Large data URLs
// are summarized so checking a render record does not duplicate megabytes.
export function elementShape(element) {
  const { image, ...rest } = element;
  return JSON.stringify({
    ...rest,
    image: image && [
      image.length,
      image.slice(0, 40),
      image.slice(image.length / 2 - 20, image.length / 2 + 20),
      image.slice(-40),
    ],
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });
}

// Snapshot the render identity and frame size used to decide which canvas
// previews and renderer bounds still describe the current elements.
export function createLayerRecords(elements) {
  return Object.fromEntries(
    elements.map((element) => [
      element.id,
      {
        shape: elementShape(element),
        size: [element.width, element.height],
      },
    ]),
  );
}

// Keep renderer results for previously measured elements when a server save
// returns the same document with normalized defaults filled in.
export function adoptLayerRecords({
  currentElements,
  savedElements,
  layerRecords,
  hasVisibleBounds,
}) {
  const records = layerRecords || {};
  const measuredIds = new Set(
    currentElements
      .filter((element) =>
        element.type === "image" || element.type === "imagespec"
          ? !!records[element.id]
          : hasVisibleBounds(element),
      )
      .map((element) => element.id),
  );
  return Object.fromEntries(
    savedElements
      .filter((element) => measuredIds.has(element.id))
      .map((element) => [
        element.id,
        {
          shape: elementShape(element),
          size: records[element.id].size,
        },
      ]),
  );
}

// undefined means unknown or frame-based, null means the renderer found no
// visible content, and an array is the visible box relative to the frame.
export function visibleBounds(element, { record, layerBounds }) {
  if (
    !element.rotation &&
    (element.type === "text" || element.type === "image")
  )
    return undefined;
  if (!record || record.shape !== elementShape(element)) return undefined;

  const dw = element.width - record.size[0];
  const dh = element.height - record.size[1];
  const bounds = layerBounds?.[element.id];
  if (!bounds) return dw || dh ? undefined : null;

  return [
    bounds[0],
    bounds[1],
    Math.max(bounds[0] + 1, bounds[2] + dw),
    Math.max(bounds[1] + 1, bounds[3] + dh),
  ];
}

function frameBounds(element, geometry) {
  return (
    visibleBounds(element, geometry) || [0, 0, element.width, element.height]
  );
}

export function alignmentGuides({
  element,
  elements,
  tag,
  layerRecords,
  layerBounds,
  zoom = 1,
  resize,
  snapTolerance = 6,
}) {
  const geometry = { record: layerRecords?.[element.id], layerBounds };
  const [left, top, right, bottom] = frameBounds(element, geometry);
  const xAnchors = resize
    ? [resize.endsWith("w") ? left : right]
    : [left, (left + right) / 2, right];
  const yAnchors = resize
    ? [resize.startsWith("n") ? top : bottom]
    : [top, (top + bottom) / 2, bottom];
  const xTargets = [0, tag.width / 2, tag.width];
  const yTargets = [0, tag.height / 2, tag.height];

  for (const peer of elements) {
    if (peer.id === element.id || peer.visible === false) continue;
    const bounds = visibleBounds(peer, {
      record: layerRecords?.[peer.id],
      layerBounds,
    });
    if (bounds === null) continue;
    const [x1, y1, x2, y2] = bounds || [0, 0, peer.width, peer.height];
    xTargets.push(peer.x + x1, peer.x + (x1 + x2) / 2, peer.x + x2);
    yTargets.push(peer.y + y1, peer.y + (y1 + y2) / 2, peer.y + y2);
  }

  const nearest = (axis, anchors, targets, origin) => {
    let result;
    for (const anchor of anchors) {
      for (const position of targets) {
        const distance = Math.abs(position - (origin + anchor));
        if (
          distance <= snapTolerance / zoom &&
          (!result || distance < result.distance)
        ) {
          result = { axis, position, distance };
        }
      }
    }
    return result;
  };

  return [
    nearest("x", xAnchors, xTargets, element.x),
    nearest("y", yAnchors, yTargets, element.y),
  ].filter(Boolean);
}

export function moveBound(element, tag, visible) {
  if (onLabel(element, tag)) return true;
  return (
    !!visible &&
    element.x + visible[0] >= 0 &&
    element.y + visible[1] >= 0 &&
    element.x + visible[2] <= tag.width &&
    element.y + visible[3] <= tag.height
  );
}

// How far a group may move without leaving the label. `boxes` are absolute
// [left, top, right, bottom] frames. A side that already hangs off the label
// is not pulled back: the group just cannot go further that way.
export function clampGroupMove(boxes, tag, dx, dy) {
  const left = Math.min(...boxes.map((box) => box[0])),
    top = Math.min(...boxes.map((box) => box[1])),
    right = Math.max(...boxes.map((box) => box[2])),
    bottom = Math.max(...boxes.map((box) => box[3]));
  return [
    Math.min(Math.max(dx, Math.min(0, -left)), Math.max(0, tag.width - right)),
    Math.min(Math.max(dy, Math.min(0, -top)), Math.max(0, tag.height - bottom)),
  ];
}

// Return a changed copy so callers retain ownership of document mutation and
// history. `bound` preserves the existing rule for imported off-label frames.
export function clampMoved(element, tag, bound, visible) {
  const moved = { ...element };
  if (bound && visible) {
    const fit = (pos, lo, hi, limit) =>
      Math.min(Math.max(pos, -lo), limit - hi);
    moved.x = fit(moved.x, visible[0], visible[2], tag.width);
    moved.y = fit(moved.y, visible[1], visible[3], tag.height);
    return clampBox(moved, tag, false);
  }
  return clampBox(moved, tag, bound);
}

export function clampResized(element, geometry) {
  const resized = { ...element };
  for (const [pos, size, lo, hi, limit] of [
    ["x", "width", 0, 2, geometry.tag.width],
    ["y", "height", 1, 3, geometry.tag.height],
  ]) {
    let visible = visibleBounds(resized, {
      record: geometry.layerRecords?.[resized.id],
      layerBounds: geometry.layerBounds,
    });
    if (!visible) return resized;
    const low = -(resized[pos] + visible[lo]);
    if (low > 0) {
      resized[pos] += low;
      resized[size] = Math.max(1, resized[size] - low);
      visible = visibleBounds(resized, {
        record: geometry.layerRecords?.[resized.id],
        layerBounds: geometry.layerBounds,
      });
    }
    const over = resized[pos] + visible[hi] - limit;
    if (over > 0) resized[size] = Math.max(1, resized[size] - over);
  }
  return resized;
}
