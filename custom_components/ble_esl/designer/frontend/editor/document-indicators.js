// Update document-related controls without rebuilding the editor tree. The
// panel owns history and dirty state and supplies translated labels and icons.
export function syncDocumentHistoryControls(
  root,
  { undoCount, redoCount, busy },
) {
  const undo = root.querySelector('[data-action="undo"]');
  const redo = root.querySelector('[data-action="redo"]');
  if (undo) undo.disabled = !undoCount || busy;
  if (redo) redo.disabled = !redoCount || busy;
}

export function markDocumentDirty(
  root,
  {
    undoCount,
    redoCount,
    busy,
    automationSaveMode,
    mode,
    translate,
    saveIcon,
  },
) {
  syncDocumentHistoryControls(root, { undoCount, redoCount, busy });
  const save = root.querySelector('[data-action="save"]');
  if (save) {
    save.innerHTML = automationSaveMode
      ? translate("Save to automation")
      : `${saveIcon}<span>${translate("Save")} ·</span>`;
    const label = automationSaveMode
      ? translate("Save to automation")
      : translate("Save (unsaved changes)");
    save.setAttribute("aria-label", label);
    save.title = automationSaveMode
      ? label
      : translate("Save (unsaved changes) (⌘/Ctrl S)");
  }
  const badge = root.querySelector("#dirty-badge");
  if (badge) badge.hidden = false;
  const restore = root.querySelector('[data-action="restore"]');
  if (restore) restore.hidden = automationSaveMode || mode === "template";
  const title = root
    .querySelector(".canvas-wrap")
    ?.previousElementSibling?.querySelector("span");
  if (title) title.textContent = translate("Editing preview");
}
