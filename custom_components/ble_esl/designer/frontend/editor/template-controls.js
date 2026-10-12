// Sensor-template control markup. The editor supplies current state,
// localization, escaping, and the already-classified template choices.
export function renderTemplateControls({
  mode,
  translate,
  escapeHtml,
  sampleOutput,
  templateTypes,
  templates,
  templateDrafts,
  templateKey,
  templateName,
  width,
  height,
}) {
  if (mode !== "template") return "";
  const t = translate;
  const esc = escapeHtml;
  return `<div class="template-controls"><p class="muted template-note" style="flex:1 1 100%;margin:0">${t("Tile styles set how a sensor appears as a tile. Build one from Name, State and Unit parts and every sensor of that type uses it.")}</p><div style="min-width:240px;max-width:360px"><ha-entity-picker id="template-sample"></ha-entity-picker><span class="muted">${t("{type} output", { type: sampleOutput })}</span></div><label>${t("Name")} <input id="template-name" aria-label="${t("Style name")}" value="${esc(templateName)}"></label><label>${t("Tile style")} <select id="template-type" aria-label="${t("Tile style")}">${templateTypes
    .map(
      (key) =>
        `<option value="${esc(key)}" ${key === templateKey ? "selected" : ""}>${esc(templates[key]?.name || templateDrafts.get(key)?.name || (key.startsWith("output:") ? t("{type} style", { type: key.split(":")[1] }) : key.replace(":", " · ")))}</option>`,
    )
    .join(
      "",
    )}</select></label><label>${t("W")} <input id="template-width" aria-label="${t("Style width")}" type="number" min="16" max="1000" value="${width}"></label><label>${t("H")} <input id="template-height" aria-label="${t("Style height")}" type="number" min="16" max="1000" value="${height}"></label></div>`;
}

export function renderTemplateParts({ mode, translate }) {
  if (mode !== "template") return "";
  return `<div class="tools">${["name", "state", "unit"].map((name) => `<button data-token="${name}">${translate(name[0].toUpperCase() + name.slice(1))}</button>`).join("")}<button data-action="add-state-icon">${translate("State icon")}</button></div>`;
}
