export function renderLayerRows({
  elements,
  selected,
  selectedIds = new Set(selected ? [selected] : []),
  layerLabel,
  t,
  esc,
  icon,
  toolIcon,
}) {
  return [...elements]
    .reverse()
    .map((item) => {
      const label = layerLabel(item);
      const hidden = item.visible === false;
      return `<div class="layer-row ${hidden ? "hidden-layer" : ""}"><button class="layer ${selectedIds.has(item.id) ? "active" : ""}" data-select="${esc(item.id)}" aria-pressed="${selectedIds.has(item.id)}">${esc(label)}</button><button class="icon-button" data-layer="${esc(item.id)}" data-layer-action="visible" aria-label="${hidden ? t("Show") : t("Hide")} ${esc(label)}" aria-pressed="${hidden}" title="${hidden ? t("Hidden: click to show") : t("Hide")}">${toolIcon(hidden ? "eyeoff" : "preview")}</button><button class="icon-button" data-layer="${esc(item.id)}" data-layer-action="up" aria-label="${esc(t("Move {label} forward", { label }))}" title="${t("Bring forward")}">${toolIcon("up")}</button><button class="icon-button" data-layer="${esc(item.id)}" data-layer-action="down" aria-label="${esc(t("Move {label} backward", { label }))}" title="${t("Send backward")}">${toolIcon("down")}</button><button class="icon-button danger" data-delete-layer="${esc(item.id)}" aria-label="${esc(t("Delete {label}", { label }))}" title="${t("Delete")}">${icon("delete")}</button></div>`;
    })
    .join("");
}

export function handleLayerListClick(panel, button) {
  if (button.dataset.deleteLayer) {
    const kept = panel.selected;
    panel.selected = button.dataset.deleteLayer;
    panel.transform("delete");
    if (
      kept &&
      kept !== button.dataset.deleteLayer &&
      panel.document.elements.some((element) => element.id === kept)
    ) {
      panel.selected = kept;
      panel.render();
    }
    return true;
  }

  if (button.dataset.layerAction) {
    const elements = panel.document.elements;
    const index = elements.findIndex(
      (element) => element.id === button.dataset.layer,
    );
    const item = elements[index];
    if (!item) return true;

    const target =
      button.dataset.layerAction === "up"
        ? index + 1
        : button.dataset.layerAction === "down"
          ? index - 1
          : index;
    if (target < 0 || target >= elements.length) return true;

    panel.checkpoint();
    if (button.dataset.layerAction === "visible")
      item.visible = item.visible === false;
    else
      [elements[index], elements[target]] = [elements[target], elements[index]];
    panel.edited();
    // Rebuilding the panel must keep keyboard focus on the activated control.
    panel.shadowRoot
      .querySelector(
        `[data-layer="${CSS.escape(item.id)}"][data-layer-action="${button.dataset.layerAction}"]`,
      )
      ?.focus();
    return true;
  }

  if (button.dataset.select) {
    panel.selected = button.dataset.select;
    panel.render();
    panel.focusElement();
    return true;
  }

  return false;
}
