export function renderHeader({
  mode,
  loading,
  refreshing,
  sessionLocked,
  version,
  translate,
  escapeHtml,
}) {
  const disabled = loading || refreshing || sessionLocked;
  return `<header><ha-menu-button></ha-menu-button><h1>${translate("ESL Designer")}</h1><span>${translate("Live Home Assistant data on e-paper")}</span>${version ? `<span class="version" title="${translate("BLE ESL integration version")}">v${escapeHtml(version)}</span>` : ""}<nav class="tabs" aria-label="${translate("Designer mode")}"><button data-action="display-mode" aria-pressed="${mode === "display"}" ${disabled ? "disabled" : ""}>${translate("Display")}</button><button data-action="template-mode" aria-pressed="${mode === "template"}" ${disabled ? "disabled" : ""}>${translate("Sensor tile styles")}</button></nav></header>`;
}
