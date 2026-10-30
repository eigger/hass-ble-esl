export const WORKSPACE_STYLE = `
.panel-heading{display:flex;align-items:center;gap:8px;margin-bottom:14px}.panel-heading h2{flex:1;margin:0}
.workspace{display:grid;grid-template-columns:240px minmax(320px,1fr) 260px;gap:18px;padding:0 24px 24px}.workspace.library-closed{grid-template-columns:minmax(0,1fr) 260px}.workspace.inspector-closed{grid-template-columns:240px minmax(0,1fr)}.workspace.library-closed.inspector-closed{grid-template-columns:minmax(0,1fr)}.workspace.library-closed .library,.workspace.inspector-closed .inspector{display:none}
.card{min-width:0;background:var(--card-background-color,white);border:1px solid var(--divider-color,#dfe5eb);border-radius:10px;padding:16px}
.canvas-wrap{min-width:0;overflow:auto;height:420px;min-height:0;display:flex;align-items:center;justify-content:flex-start;background:repeating-conic-gradient(var(--secondary-background-color,#edf0f4) 0% 25%,var(--primary-background-color,#f6f8fa) 0% 50%) 50%/16px 16px;border-radius:6px;padding:30px}.stage-space{margin:auto;flex:none;position:relative}
.empty-note{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:16px;color:var(--secondary-text-color,#637083);pointer-events:none}.tips{margin:8px 0 0}.tips summary{cursor:pointer;font-size:12px;color:var(--secondary-text-color,#637083)}
@media(max-width:1050px){.workspace{grid-template-columns:200px 1fr}.inspector{grid-column:1/-1}}
@media(min-width:651px) and (max-width:1050px){.workspace{grid-template-columns:200px minmax(0,1fr)}.workspace.library-closed{grid-template-columns:minmax(0,1fr)}.workspace.inspector-closed{grid-template-columns:200px minmax(0,1fr)}.workspace.library-closed.inspector-closed{grid-template-columns:minmax(0,1fr)}.workspace .inspector{grid-column:1/-1}}
@media(max-width:650px){.preview-card{order:1}.inspector{order:2}.library{order:3}.workspace.library-closed,.workspace.inspector-closed,.workspace.library-closed.inspector-closed{grid-template-columns:minmax(0,1fr)}.workspace{padding:0 12px 12px;grid-template-columns:minmax(0,1fr)}.library,.inspector{grid-column:auto}.canvas-wrap{height:300px}}
`;

export function renderWorkspace({
  tag,
  mode,
  libraryOpen,
  inspectorOpen,
  sessionLocked,
  preview,
  zoom,
  background,
  sampleEntity,
  tipsOpen,
  hasElement,
  translate,
  escapeHtml,
  toggles,
  libraryContent,
  elementActions,
  propertyContent,
  layerRows,
}) {
  const libraryToggle = libraryOpen
    ? toggles.libraryOpen
    : toggles.libraryClosed;
  const inspectorToggle = inspectorOpen
    ? toggles.inspectorOpen
    : toggles.inspectorClosed;

  return `<div class="workspace ${libraryOpen ? "" : "library-closed"} ${inspectorOpen ? "" : "inspector-closed"}"><section id="library" class="library card"><div class="template-start" ${mode === "template" || sessionLocked || !tag ? "hidden" : ""}><h2>${translate("Design gallery")}</h2><p class="template-hint">${translate("Start from a ready-made design such as a date label, Wi-Fi QR code or weather. Adjust its options, add it as editable elements and optionally create the automation that keeps it up to date.")}</p><button class="primary wide" data-action="design-templates">${translate("Browse design gallery")}</button></div><div class="panel-heading"><h2>${translate(mode === "template" ? "Tile style parts" : "Entities")}</h2>${libraryToggle}</div>${libraryContent}</section><section class="card preview-card"><div class="panel-heading">${libraryOpen ? "" : libraryToggle}<h2>${tag.width} × ${tag.height} · ${escapeHtml(tag.colors)} <span class="muted">${translate(preview ? "Rendered view" : "Edit view")}</span></h2>${inspectorOpen ? "" : inspectorToggle}</div><div class="canvas-wrap"><div class="stage-space" style="width:${tag.width * zoom}px;height:${tag.height * zoom}px"><div class="stage" style="width:${tag.width}px;height:${tag.height}px;transform:scale(${zoom});background:${background}" tabindex="0" role="group" aria-label="${translate("Display canvas")}" aria-describedby="canvas-tips canvas-tips-select"></div>${mode === "template" && !sampleEntity ? `<div class="empty-note">${translate("Choose a sample sensor above to preview this tile style.")}</div>` : ""}</div></div><details class="tips" ${tipsOpen ? "open" : ""}><summary>${translate("Keyboard & mouse tips")}</summary><p id="canvas-tips" class="muted">${translate("Click an element to select it · Click text to edit · Drag to move · Drag corner handles to resize · Alignment guides appear near edges and centres · Arrow keys move 1 px · Shift + arrows move 10 px · Enter edits selected text · Delete / Backspace removes · Right-click for actions · ⌘/Ctrl + D duplicates · ⌘/Ctrl + S saves · ⌘/Ctrl + Z undoes · ⌘/Ctrl + Shift + Z redoes")}</p><p id="canvas-tips-select" class="muted">${translate("Shift / Ctrl / ⌘ + click selects several elements · Drag on an empty part of the canvas to select an area")}</p></details></section><aside id="inspector" class="inspector side-column"><section class="card"><div class="panel-heading"><h2>${translate(hasElement ? "Element properties" : "Select an element")}</h2>${inspectorToggle}</div>${elementActions}<div class="props">${propertyContent}</div></section><section class="card layer-card"><h2>${translate("Layers")}</h2><div class="layers">${layerRows}</div></section></aside></div>`;
}
