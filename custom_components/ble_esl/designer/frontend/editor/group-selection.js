import { renderTextAlignmentControls } from "./inspector/text-alignment.js";
import { renderElementRotation } from "./rotation-control.js";

export function sharedProperties(panel, translate, escape) {
  const items = panel.selectedElements;
  const read = (element, key) =>
    key.startsWith("spec.") ? element.spec[key.slice(5)] : element[key];
  const common = (key) =>
    items.every((e) => read(e, key) === read(items[0], key))
      ? read(items[0], key)
      : "";
  const number = (key, label, value = common(key)) =>
    `<label>${translate(label)}<input data-property="${key}" type="number" ${["width", "height", "font_size"].includes(key) ? 'min="1"' : ""} value="${escape(value ?? "")}" placeholder="${translate("Mixed")}" step="1"></label>`;
  const x = Math.min(...items.map((e) => e.x)),
    y = Math.min(...items.map((e) => e.y));
  const text = items.every((e) => ["text", "sensor"].includes(e.type));
  const nativeFields = items.every((e) => e.type === "imagespec")
    ? (panel.specDefinition(items[0])?.fields || [])
        .filter(
          (field) =>
            field.kind === "number" &&
            !["x", "y", "width", "height", "rotate"].includes(field.name) &&
            items.every((e) =>
              panel
                .specDefinition(e)
                ?.fields.some(
                  (f) => f.name === field.name && f.kind === field.kind,
                ),
            ),
        )
        .map((field) =>
          number(`spec.${field.name}`, field.name.replaceAll("_", " ")),
        )
        .join("")
    : "";
  return `<p class="wide">${items.length} ${translate("selected")}. ${translate("Changes apply to all selected components. Mixed values are blank.")}</p>${number("x", "X", x)}${number("y", "Y", y)}${number("width", "Width")}${number("height", "Height")}${renderElementRotation({ rotation: common("rotation"), rotationMixed: common("rotation") === "" }, translate)}${panel.colorPicker("color", common("color"), translate("Colour"))}${text ? renderTextAlignmentControls({ font_size: common("font_size"), align: common("align") }, { translate, escapeHtml: escape }) : ""}${nativeFields}<label class="check wide"><input type="checkbox" data-property="visible" ${common("visible") !== false ? "checked" : ""}>${translate("Visible")}${common("visible") === "" ? ` (${translate("Mixed")})` : ""}</label>${items.every((e) => e.type === "text") ? `<label class="wide">${translate("Text")}<textarea data-property="text" placeholder="${translate("Mixed")}">${escape(common("text"))}</textarea></label>` : ""}`;
}

export function setSharedProperty(panel, key, value) {
  const items = panel.selectedElements;
  if (key === "x" || key === "y") {
    const delta = value - Math.min(...items.map((e) => e[key]));
    items.forEach((e) => (e[key] += delta));
  } else {
    items.forEach((e) => {
      if (key.startsWith("spec.")) {
        e.spec[key.slice(5)] = value;
        return;
      }
      e[key] = value;
      if (e.type === "imagespec" && key === "color") {
        const fields = panel.specDefinition(e)?.fields || [];
        const field = fields.some((f) => f.name === "color")
          ? "color"
          : fields.some((f) => f.name === "fill")
            ? "fill"
            : null;
        if (field) e.spec[field] = value;
      }
    });
  }
}

export function beginMarquee(panel, event) {
  event.preventDefault();
  panel.finishTextEdit();
  const rect = panel.shadowRoot.querySelector(".stage").getBoundingClientRect();
  const startX = (event.clientX - rect.left) / panel.zoom,
    startY = (event.clientY - rect.top) / panel.zoom;
  const previous = [...panel.selectedIds],
    base = event.shiftKey || event.ctrlKey || event.metaKey ? previous : [];
  panel.selectIds(base);
  panel.drawStage();
  const box = document.createElement("div");
  box.className = "marquee";
  Object.assign(box.style, {
    position: "absolute",
    border: "1px solid #16838c",
    background: "#16838c22",
    pointerEvents: "none",
    zIndex: 10000,
  });
  const controller = new AbortController();
  panel.gesture = controller;
  const finish = (cancel = false) => {
    controller.abort();
    panel.gesture = null;
    panel.gestureFinish = null;
    panel.gestureCancel = null;
    if (cancel) panel.selectIds(previous);
    panel.render();
    panel.focusElement();
  };
  panel.gestureFinish = () => finish();
  panel.gestureCancel = () => finish(true);
  window.addEventListener(
    "pointermove",
    (move) => {
      if (move.pointerId !== event.pointerId) return;
      const x = (move.clientX - rect.left) / panel.zoom,
        y = (move.clientY - rect.top) / panel.zoom;
      const left = Math.min(x, startX),
        top = Math.min(y, startY),
        right = Math.max(x, startX),
        bottom = Math.max(y, startY);
      if (
        Math.hypot(move.clientX - event.clientX, move.clientY - event.clientY) <
        3
      )
        return;
      const ids = panel.document.elements
        .filter((e) => {
          const b = panel.visibleBounds(e);
          if (b === null) return false;
          const bounds = b || [0, 0, e.width, e.height];
          return (
            e.x + bounds[0] < right &&
            e.x + bounds[2] > left &&
            e.y + bounds[1] < bottom &&
            e.y + bounds[3] > top
          );
        })
        .map((e) => e.id);
      panel.selectIds([...base, ...ids]);
      panel.drawStage();
      Object.assign(box.style, {
        left: `${left}px`,
        top: `${top}px`,
        width: `${right - left}px`,
        height: `${bottom - top}px`,
      });
      panel.shadowRoot.querySelector(".stage").append(box);
    },
    { signal: controller.signal },
  );
  window.addEventListener(
    "pointerup",
    (up) => {
      if (up.pointerId === event.pointerId) finish();
    },
    { signal: controller.signal },
  );
  window.addEventListener("pointercancel", () => finish(true), {
    signal: controller.signal,
  });
  window.addEventListener("blur", () => finish(true), {
    signal: controller.signal,
  });
}
