// Shared action labels and markup for the canvas context menu and inspector.
export const ELEMENT_ACTIONS = [
  ["duplicate", "Duplicate", "⌘/Ctrl D"],
  ["delete", "Delete", "⌫"],
  ["back", "Send back", ""],
  ["front", "Bring front", ""],
  ["center", "Center horizontally", ""],
];

export function renderElementActionMenu({ t, icon, toolIcon }) {
  return ELEMENT_ACTIONS.map(
    ([action, label, key]) =>
      `<button role="menuitem" data-action="${action}">${action === "delete" ? icon("delete") : toolIcon(action)}<span>${t(label)}</span><kbd>${key}</kbd></button>`,
  ).join("");
}

export function renderElementActionBar({ busy, t, icon, toolIcon }) {
  return `<div class="element-actions" role="toolbar" aria-label="${t("Element actions")}">${ELEMENT_ACTIONS.map(
    ([action, label, key]) =>
      `<button class="icon-button ${action === "delete" ? "danger" : ""}" data-action="${action}" ${busy ? "disabled" : ""} aria-label="${t(label)}" title="${t(label)}${key ? ` (${key})` : ""}">${action === "delete" ? icon("delete") : toolIcon(action)}</button>`,
  ).join("")}</div>`;
}
