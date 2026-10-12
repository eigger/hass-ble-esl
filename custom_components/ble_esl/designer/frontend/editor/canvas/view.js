// Canvas markup stays separate from the panel's preview, state, and DOM work.
// The panel prepares each layer's content and renderer metadata, then passes
// those view values here for consistent accessible markup.
export function renderLayerImageMarkup({
  element,
  src,
  offset,
  bounds,
  record,
}) {
  if (!offset || !bounds)
    return `<img class="layer-preview" src="${src}" alt="" aria-hidden="true">`;
  // Grow by what the frame grew, as the selection box does, so the box stays
  // on the image while the frame is dragged.
  const grows = record && element.type !== "text",
    dw = grows ? element.width - record.size[0] : 0,
    dh = grows ? element.height - record.size[1] : 0,
    width = Math.max(1, bounds[2] - bounds[0] + dw),
    height = Math.max(1, bounds[3] - bounds[1] + dh);
  return `<img class="layer-preview" src="${src}" alt="" aria-hidden="true" style="inset:auto;left:${offset[0]}px;top:${offset[1]}px;width:${width}px;height:${height}px">`;
}

export function renderLayerMarkup({
  element,
  index,
  selected,
  rendered,
  label,
  content,
  hitBounds,
  layerImage = "",
  faded = false,
  escape,
}) {
  const hitArea = hitBounds
    ? `<div class="hit-area" style="left:${hitBounds[0]}px;top:${hitBounds[1]}px;width:${hitBounds[2] - hitBounds[0]}px;height:${hitBounds[3] - hitBounds[1]}px"></div>`
    : "";
  return `<div class="el ${element.visible === false ? "hidden-el" : ""} ${rendered ? "rendered" : ""} ${selected ? "selected" : ""}" data-id="${escape(element.id)}" role="button" tabindex="0" aria-pressed="${selected}" aria-label="${escape(label || (element.type === "text" ? element.text : "") || element.type)}" style="left:${element.x}px;top:${element.y}px;width:${element.width}px;height:${element.height}px;color:${element.color};background:transparent;font-size:${element.font_size}px;text-align:${element.align};z-index:${index + 1}">${rendered ? layerImage : ""}<div class="content" ${faded ? 'style="opacity:.2"' : ""}>${content}</div>${hitArea}</div>`;
}

export function renderStageMarkup({
  preview,
  previewLabel,
  layers,
  guides,
  selection,
}) {
  return `${preview ? `<img class="exact" src="${preview}" alt="${previewLabel}">` : ""}${layers.join("")}${guides}${selection}`;
}

export function renderSelectionMarkup({
  element,
  visible,
  zoom,
  coarsePointer,
  translate,
  escape,
  deleteIcon,
}) {
  if (!element) return "";
  const [left, top, right, bottom] = visible || [
      0,
      0,
      element.width,
      element.height,
    ],
    width = right - left,
    height = bottom - top,
    handleSize = (coarsePointer ? 32 : 20) / zoom;
  const moveTarget = `<span class="move-handle" aria-label="${translate("Move selected element")}" style="position:absolute;left:${width / 2 - handleSize / 2}px;top:${height / 2 - handleSize / 2}px;width:${handleSize}px;height:${handleSize}px;border:1px solid white;border-radius:50%;box-shadow:0 0 0 1px var(--primary-color,#16838b);background:var(--primary-color,#16838b);color:white;display:${Math.max(width, height) * zoom < 36 ? "grid" : "none"};place-items:center;pointer-events:auto;cursor:move"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 2v20M2 12h20M12 2l-3 3m3-3 3 3m-3 17-3-3m3 3 3-3M2 12l3-3m-3 3 3 3m17-3-3-3m3 3-3 3"/></svg></span>`;
  return `<div class="selection-box" data-id="${escape(element.id)}" style="position:absolute;left:${element.x + left}px;top:${element.y + top}px;width:${width}px;height:${height}px;outline:${1.5 / zoom}px solid var(--primary-color,#16838b);z-index:9999;pointer-events:none;overflow:visible">${["nw", "ne", "sw", "se"].map((corner) => `<span class="handle" data-corner="${corner}" aria-label="${translate("Resize {corner}", { corner })}" style="position:absolute;left:${corner.endsWith("w") ? -handleSize : width}px;top:${corner.startsWith("n") ? -handleSize : height}px;right:auto;bottom:auto;width:${handleSize}px;height:${handleSize}px;border:1px solid white;border-radius:50%;box-shadow:0 0 0 1px var(--primary-color,#16838b);pointer-events:auto;cursor:${corner === "nw" || corner === "se" ? "nwse" : "nesw"}-resize"></span>`).join("")}${moveTarget}<button class="delete-handle" data-action="delete" aria-label="${translate("Delete selected element")}" title="${translate("Delete")}" style="pointer-events:auto;transform:scale(${1 / zoom});transform-origin:bottom right">${deleteIcon}</button></div>`;
}

export function renderAlignmentGuides(guides) {
  return (guides || [])
    .map((guide) =>
      guide.axis === "x"
        ? `<span aria-hidden="true" style="position:absolute;left:${guide.position}px;top:0;height:100%;border-left:1px dashed #e53935;pointer-events:none;z-index:9998"></span>`
        : `<span aria-hidden="true" style="position:absolute;left:0;top:${guide.position}px;width:100%;border-top:1px dashed #e53935;pointer-events:none;z-index:9998"></span>`,
    )
    .join("");
}
