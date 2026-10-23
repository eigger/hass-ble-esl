import { materialIcon } from "../material-icons.js";
// Renders imagespec state-to-icon controls from explicit entity/icon helpers.
// Editing the mappings continues through the panel's existing action path.
export function renderStateIconRows({
  element,
  sample,
  outputType,
  defaultIcon,
  iconGlyph,
  translate,
  escapeHtml,
}) {
  const states = [
    ...new Set([
      ...(outputType(sample) === "binary"
        ? ["on", "off"]
        : sample
          ? [sample.state]
          : []),
      ...Object.keys(element.state_icons || {}),
    ]),
  ];
  return `<div class="wide"><strong>${translate("State → icon")}</strong>${states
    .map((state) => {
      const name = element.state_icons?.[state] || "{{icon}}";
      const stateObj = sample && { ...sample, state };
      return `<div style="display:flex;gap:8px;align-items:center;margin-top:6px"><span style="min-width:48px">${escapeHtml(state)}</span><span>→</span><button class="icon-choice" data-action="pick-icon" data-icon-state="${escapeHtml(state)}" aria-label="${escapeHtml(translate("Choose icon for {state}", { state }))}">${iconGlyph(name === "{{icon}}" ? defaultIcon(stateObj) : name)}<span>${name === "{{icon}}" ? translate("HA state icon") : escapeHtml(name.replace("mdi:", ""))}</span></button></div>`;
    })
    .join(
      "",
    )}<div style="display:flex;gap:6px;margin-top:8px"><input id="new-icon-state" aria-label="${translate("New icon state")}" placeholder="${translate("Another state")}"><button data-action="add-icon-state" aria-label="${translate("Add state mapping")}">${materialIcon("plus")}</button></div><div class="icon-popover" hidden><input id="icon-search" type="search" aria-label="${translate("Search icons")}" placeholder="${translate("Search icons")}"><button data-icon="{{icon}}">${translate("HA state icon")}</button><div class="icon-picker"></div></div></div>`;
}
