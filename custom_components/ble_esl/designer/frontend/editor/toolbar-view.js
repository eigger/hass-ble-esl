import { renderOrientation } from "./orientation-control.js";
export const TOOLBAR_STYLE = `
.stage.exact-mode .el.ghost .layer-preview{display:block}.el.ghost.hidden-el{opacity:1}.el.ghost .layer-preview{opacity:.25;filter:grayscale(1)}
.toolbar [data-tag-orientation] button[aria-pressed="true"],.toolbar button[data-action="show-hidden-icons"][aria-pressed="true"]{background:#16838c22;border-color:#16838c}
.toolbar button.labeled{width:auto;min-width:max-content;gap:6px;padding:7px 12px;white-space:nowrap}.toolbar button.labeled ha-icon{flex:none}.toolbar .automation-save{width:auto;min-width:max-content;height:auto;min-height:38px;padding:7px 12px;white-space:nowrap}
header{position:sticky;top:0;z-index:30}.toolbar{position:sticky;top:var(--bar-top,var(--header-height,56px));z-index:29;background:var(--primary-background-color,#f5f7fa);border-bottom:1px solid var(--divider-color,#e0e5eb);margin-bottom:12px;padding-top:8px;padding-bottom:8px}
@media(max-width:650px){header,.toolbar{position:static}:host([managed]) header,:host([managed]) .toolbar{position:sticky}}
`;

export function renderToolbar({
  tag,
  mode,
  sessionLocked,
  refreshing,
  busy,
  status,
  dirty,
  automationSessionPending,
  automationSaveMode,
  undoAvailable,
  redoAvailable,
  showHiddenIcons = false,
  zoomMode,
  zoom,
  tags,
  translate,
  escapeHtml,
  icon,
  tagName,
  renderTagOptions,
  sendHint,
}) {
  const sendMessage = sendHint(tag);
  const zoomOptions = [
    ...new Set([
      0.25,
      0.5,
      0.75,
      1,
      1.5,
      2,
      3,
      4,
      6,
      8,
      ...(zoomMode === "manual" ? [zoom] : []),
    ]),
  ]
    .sort((a, b) => a - b)
    .map(
      (value) =>
        `<option value="${value}" ${zoomMode === "manual" && value === zoom ? "selected" : ""}>${Math.round(value * 100)}%</option>`,
    )
    .join("");

  return `<div class="toolbar"><select id="tag" aria-label="${translate("Tag")}" ${mode === "template" ? "hidden" : ""} ${sessionLocked ? "disabled" : ""}>${renderTagOptions(tags, tag, { tagName, escapeHtml })}</select>${renderOrientation(tag, mode, busy, translate)}<button data-action="reload" ${mode === "template" ? "hidden" : ""} ${refreshing || sessionLocked ? "disabled" : ""} class="icon-button ${refreshing ? "spinning" : ""}" aria-label="${translate("Refresh tags")}" title="${translate("Refresh tags")}">${icon("reload")}</button><button data-action="save" ${!tag || busy || automationSessionPending ? "disabled" : ""} class="icon-button labeled" aria-label="${dirty ? translate("Save (unsaved changes)") : translate("Save")}" title="${dirty ? translate("Save (unsaved changes)") : translate("Save")} (⌘/Ctrl S)">${icon("save")}<span>${translate("Save")}${dirty ? " ·" : ""}</span></button><button data-action="restore" ${!dirty || automationSaveMode || mode === "template" ? "hidden" : ""} ${busy || sessionLocked ? "disabled" : ""} class="icon-button labeled" aria-label="${translate("Restore saved design")}" title="${translate("Restore saved design")}">${icon("reload")}<span>${translate("Restore")}</span></button><button data-action="preview-variables" ${automationSaveMode ? "" : "hidden"} aria-label="${translate("Preview parameters")}" title="${translate("Preview parameters")}">${translate("Preview parameters")}</button><span id="dirty-badge" class="dirty-badge" ${dirty ? "" : "hidden"}>${translate("Unsaved changes")}</span><button class="primary icon-button labeled ${busy && status === "Sending display…" ? "spinning" : ""}" aria-label="${translate("Send to tag")}" title="${escapeHtml(sendMessage)}" ${mode === "template" || sessionLocked || !tag?.writable || busy ? `aria-description="${escapeHtml(sendMessage)}"` : ""} data-action="send" ${mode === "template" || sessionLocked ? "hidden" : ""} ${mode === "template" || sessionLocked || !tag?.writable || busy ? "disabled" : ""}>${icon("send")}<span>${translate("Send to tag")}</span></button><button data-action="undo" ${undoAvailable ? "" : "disabled"} class="icon-button" aria-label="${translate("Undo")}" title="${translate("Undo (⌘/Ctrl Z)")}">${icon("undo")}</button><button data-action="redo" ${redoAvailable ? "" : "disabled"} class="icon-button" aria-label="${translate("Redo")}" title="${translate("Redo (⌘/Ctrl Shift Z)")}">${icon("redo")}</button><button class="icon-button labeled" data-action="show-hidden-icons" aria-label="${translate("Show hidden icons")}" aria-pressed="${showHiddenIcons}" title="${translate("Show invisible icons faintly for editing; does not change the label image")}">${icon("preview")}<span>${translate("Show hidden icons")}</span></button><button data-action="zoom-out" aria-label="${translate("Zoom out")}">${icon("minus")}</button><label><select id="zoom" aria-label="${translate("Preview zoom")}"><option value="fit" ${zoomMode === "fit" ? "selected" : ""}>${translate("Fit")}</option>${zoomOptions}</select></label><button data-action="zoom-in" aria-label="${translate("Zoom in")}">${icon("plus")}</button><button data-action="create-automation" ${mode === "template" || sessionLocked || !tag?.writable ? "hidden" : ""}>${translate("Create automation")}</button></div>`;
}
