import { clampBox, clone, onLabel } from "../../model.js";
import { t } from "../../i18n.js";

export function beginTextEdit(panel) {
  if (panel.element?.type !== "text") return;
  panel.invalidatePreview();
  panel.preview = null;
  // The exact image would show the old text under the one being typed.
  panel.shadowRoot.querySelector(".stage").classList.remove("exact-mode");
  panel.shadowRoot.querySelector(".stage img.exact")?.remove();
  const node = panel.shadowRoot.querySelector(`[data-id="${panel.selected}"]`);
  node.classList.add("editing");
  panel.shadowRoot.querySelector(".move-handle")?.setAttribute("hidden", "");
  const content = node.querySelector(".content");
  content.textContent = panel.element.text;
  content.contentEditable = "plaintext-only";
  content.dataset.editText = panel.selected;
  content.setAttribute("role", "textbox");
  content.setAttribute("aria-label", t(panel.hass, "Edit display text"));
  panel.editingTextId = panel.selected;
  content.focus();
  const text =
    content.firstChild || content.appendChild(document.createTextNode(""));
  const start = panel.element.text === "Your text" ? 0 : text.length;
  const select = () =>
    window.getSelection().setBaseAndExtent(text, start, text, text.length);
  select();
  // WebKit resets the selection in the triggering click's default action,
  // which left Safari without a caret: select again afterwards, unless the
  // user already started typing.
  setTimeout(() => {
    if (
      content.isConnected &&
      panel.editingTextId === content.dataset.editText &&
      panel.typingProperty !== content
    )
      select();
  });
}
export function finishTextEdit(panel) {
  if (!panel.editingTextId) return;
  panel.editingTextId = null;
  panel.typingProperty = null;
  panel.drawStage();
  panel.queuePreview();
}

export function handleKey(panel, event) {
  if (
    event
      .composedPath()
      .some((node) =>
        [
          "BLE-ESL-COMPONENT-EDITOR",
          "BLE-ESL-YAML-DIALOG",
          "HA-ENTITY-PICKER",
        ].includes(node.tagName),
      )
  )
    return;
  if (panel.busy) return;
  if (panel.gesture) {
    if (event.key === "Escape") {
      event.preventDefault();
      panel.gestureCancel?.();
      return;
    }
    panel.gestureFinish?.(false);
  }
  const context = event.target.closest(".context-menu");
  if (context && ["ArrowDown", "ArrowUp"].includes(event.key)) {
    event.preventDefault();
    const buttons = [...context.querySelectorAll("button")];
    const index = buttons.indexOf(event.target);
    buttons[
      (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) %
        buttons.length
    ].focus();
    return;
  }
  if (event.key === "Escape") {
    panel.finishTextEdit();
    panel.closeContextMenu();
    panel.focusElement();
    return;
  }
  const editing =
    ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName) ||
    event.target.isContentEditable;
  // The browser's own "Save page" must not open from inside a field.
  if (
    editing &&
    (event.metaKey || event.ctrlKey) &&
    event.key.toLowerCase() === "s"
  ) {
    event.preventDefault();
    panel.shadowRoot.querySelector('[data-action="save"]')?.click();
    return;
  }
  if (editing) return;
  const interactiveControl = event.target.closest(
      "button, a, input, select, textarea, [contenteditable=true]",
    ),
    canvasNode = interactiveControl
      ? null
      : event.target.closest(".el[data-id]"),
    inCanvas =
      !!canvasNode || (!!event.target.closest(".stage") && !interactiveControl);
  if (canvasNode && panel.selected !== canvasNode.dataset.id) {
    panel.selected = canvasNode.dataset.id;
    panel.render();
    panel.focusElement();
  }
  if (canvasNode && ["Enter", " "].includes(event.key)) {
    event.preventDefault();
    if (event.key === "Enter" && panel.element?.type === "text")
      panel.beginTextEdit();
    return;
  }
  const cmd = event.metaKey || event.ctrlKey,
    key = event.key.toLowerCase();
  if (cmd && key === "a" && inCanvas) {
    event.preventDefault();
    panel.selectIds(panel.document.elements.map((e) => e.id));
    panel.render();
    panel.focusElement();
    return;
  }
  if (cmd && ["z", "y", "s", "d"].includes(key)) {
    event.preventDefault();
    if (key === "d") panel.transform("duplicate");
    else
      panel.shadowRoot
        .querySelector(
          `[data-action="${key === "s" ? "save" : key === "y" || event.shiftKey ? "redo" : "undo"}"]`,
        )
        ?.click();
    return;
  }
  if (inCanvas && (key === "delete" || key === "backspace")) {
    event.preventDefault();
    panel.transform("delete");
    return;
  }
  const directions = {
    ArrowLeft: [-1, 0],
    ArrowRight: [1, 0],
    ArrowUp: [0, -1],
    ArrowDown: [0, 1],
  };
  if (inCanvas && panel.element && directions[event.key]) {
    event.preventDefault();
    if (panel.selectedElements.length > 1) {
      panel.checkpoint();
      const step = event.shiftKey ? 10 : 1;
      const [dx, dy] = directions[event.key];
      for (const element of panel.selectedElements) {
        element.x += dx * step;
        element.y += dy * step;
      }
      panel.edited();
      panel.focusElement();
      return;
    }
    const before = clone(panel.element),
      visible = panel.visibleBounds(before),
      snapshot = clone(panel.document),
      step = event.shiftKey ? 10 : 1,
      [x, y] = directions[event.key];
    panel.element.x += x * step;
    panel.element.y += y * step;
    panel.clampMoved(panel.element, panel.moveBound(before, visible), visible);
    if (panel.element.x === before.x && panel.element.y === before.y) return;
    panel.pushUndo(snapshot);
    panel.edited();
    panel.focusElement();
  }
}
export function handlePointer(panel, event) {
  if (
    panel.busy ||
    event.button !== 0 ||
    !event.isPrimary ||
    panel.gesture ||
    event.target.isContentEditable ||
    event.target.closest("button")
  )
    return;
  const node = event.target.closest("[data-id]");
  if (!node) {
    if (event.target.closest(".canvas-wrap")) panel.beginMarquee(event);
    return;
  }
  if (event.shiftKey || event.ctrlKey || event.metaKey) {
    event.preventDefault();
    panel.toggleSelection(node.dataset.id);
    panel.render();
    panel.focusElement();
    return;
  }
  const resize = event.target.closest(".handle")?.dataset.corner,
    selectionOverlay = event.target.closest(".selection-box");
  event.preventDefault();
  if (panel.selectedIds.has(node.dataset.id))
    panel.selectIds(panel.selectedIds, node.dataset.id);
  else panel.selected = node.dataset.id;
  const group = panel.selectedElements.map((element) => ({
    element,
    start: clone(element),
  }));
  const element = panel.element,
    start = clone(element),
    startX = event.clientX,
    startY = event.clientY,
    pointerId = event.pointerId,
    snapshot = clone(panel.document),
    // An element that hangs off the label (an imported frame) is not pulled
    // back by the first move.
    bound = onLabel(start, panel.tag),
    startVisible = panel.visibleBounds(start);
  let moved = false,
    pendingMove = null,
    gestureFrame = 0;
  const applyMove = (move) => {
    const dx = Math.round((move.clientX - startX) / panel.zoom),
      dy = Math.round((move.clientY - startY) / panel.zoom);
    if (!moved && Math.hypot(move.clientX - startX, move.clientY - startY) < 3)
      return;
    if (!moved) {
      moved = true;
      panel.preview = null;
      panel.invalidatePreview();
    }
    if (resize) {
      // The dragged edge stops at the label's edge; the other stays put.
      const edge = (from, size, limit, lower, delta) => {
        if (!bound)
          return lower
            ? [
                from + Math.min(delta, size - 1),
                size - Math.min(delta, size - 1),
              ]
            : [from, Math.max(1, size + delta)];
        const [near, far] = lower
          ? [Math.min(Math.max(0, from + delta), from + size - 1), from + size]
          : [from, Math.max(Math.min(limit, from + size + delta), from + 1)];
        return [near, far - near];
      };
      [element.x, element.width] = edge(
        start.x,
        start.width,
        panel.tag.width,
        resize.endsWith("w"),
        dx,
      );
      [element.y, element.height] = edge(
        start.y,
        start.height,
        panel.tag.height,
        resize.startsWith("n"),
        dy,
      );
    } else {
      if (group.length > 1) {
        for (const item of group) {
          item.element.x = item.start.x + dx;
          item.element.y = item.start.y + dy;
        }
        panel.snapGuides = [];
        panel.drawStage();
        return;
      }
      element.x = start.x + dx;
      element.y = start.y + dy;
      panel.clampMoved(
        element,
        panel.moveBound(start, startVisible),
        startVisible,
      );
      panel.snapGuides = panel.alignmentGuides(element, resize);
      panel.drawStage();
      return;
    }
    clampBox(element, panel.tag, bound);
    if (resize && (bound || panel.moveBound(start, startVisible)))
      panel.clampResized(element);
    panel.snapGuides = panel.alignmentGuides(element, resize);
    panel.drawStage();
  };
  const flushPendingMove = () => {
    if (gestureFrame) cancelAnimationFrame(gestureFrame);
    gestureFrame = 0;
    const move = pendingMove;
    pendingMove = null;
    if (move) applyMove(move);
  };
  // A plain click leaves the exact preview alone; only a drag swaps it for
  // the movable layers.
  panel.render();
  panel.focusElement();
  const controller = new AbortController();
  panel.gesture = controller;
  const previewBeforeGesture = panel.preview;
  const cancelGesture = () => {
    if (gestureFrame) cancelAnimationFrame(gestureFrame);
    gestureFrame = 0;
    pendingMove = null;
    controller.abort();
    if (panel.gesture !== controller) return;
    panel.gesture = null;
    panel.gestureCancel = null;
    panel.snapGuides = [];
    if (moved) {
      group.forEach((item) => Object.assign(item.element, item.start));
      panel.preview = previewBeforeGesture;
      panel.drawStage();
      if (panel.isConnected && !panel.preview) panel.queuePreview();
    }
  };
  panel.gestureCancel = cancelGesture;
  const finishGesture = (editText = true) => {
    if (panel.gesture !== controller) return;
    flushPendingMove();
    controller.abort();
    if (panel.gesture !== controller) return;
    panel.gesture = null;
    panel.gestureCancel = null;
    panel.gestureFinish = null;
    panel.snapGuides = [];
    const changed =
      moved &&
      (element.x !== start.x ||
        element.y !== start.y ||
        element.width !== start.width ||
        element.height !== start.height);
    if (changed) {
      panel.pushUndo(snapshot);
      panel.edited();
      panel.focusElement();
    } else {
      if (moved) {
        panel.preview = previewBeforeGesture;
        panel.drawStage();
        if (!panel.preview) panel.queuePreview();
      }
      if (
        editText &&
        !moved &&
        !resize &&
        (!selectionOverlay || event.target.closest(".move-handle")) &&
        group.length === 1 &&
        element.type === "text"
      ) {
        panel.beginTextEdit();
      }
    }
  };
  panel.gestureFinish = finishGesture;
  window.addEventListener(
    "pointermove",
    (move) => {
      if (move.pointerId !== pointerId) return;
      if (
        !moved &&
        Math.hypot(move.clientX - startX, move.clientY - startY) >= 3
      ) {
        moved = true;
        panel.preview = null;
        panel.invalidatePreview();
      }
      pendingMove = move;
      if (gestureFrame) return;
      gestureFrame = requestAnimationFrame(() => {
        gestureFrame = 0;
        const latest = pendingMove;
        pendingMove = null;
        if (latest) applyMove(latest);
      });
    },
    { signal: controller.signal },
  );
  window.addEventListener(
    "pointerup",
    (up) => {
      if (up.pointerId === pointerId) {
        flushPendingMove();
        finishGesture();
      }
    },
    { signal: controller.signal },
  );
  window.addEventListener(
    "pointercancel",
    (cancel) => {
      if (cancel.pointerId !== pointerId) return;
      // A cancelled gesture is rolled back and never becomes an undo step.
      cancelGesture();
    },
    { signal: controller.signal },
  );
  window.addEventListener("blur", cancelGesture, {
    once: true,
    signal: controller.signal,
  });
}
