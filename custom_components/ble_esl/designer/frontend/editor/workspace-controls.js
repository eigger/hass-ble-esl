// Accessible controls for collapsing the editor's library and inspector panels.
export function renderPanelToggle({
  action,
  open,
  label,
  id,
  translate,
  iconMarkup,
}) {
  const panelLabel = translate(label);
  return `<button class="icon-button" data-action="${action}" aria-label="${translate("Toggle {label} panel", { label: panelLabel })}" aria-controls="${id}" title="${open ? translate("Hide") : translate("Show")} ${panelLabel}" aria-expanded="${open}">${iconMarkup}</button>`;
}
