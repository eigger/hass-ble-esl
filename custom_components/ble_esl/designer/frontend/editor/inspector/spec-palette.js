// Markup for adding renderer-supported imagespec element types. The panel
// supplies renderer metadata and localization; document creation stays there.
export function renderSpecPalette({ specs, mode, translate, escapeHtml }) {
  if (!specs || mode === "template") return "";
  const groups = {};
  for (const type of specs.types)
    (groups[type.category] ||= []).push(type.type);
  return `<p class="hint wide">${translate("Every element type the tag can draw, set field by field: choose one, then press")} <b>${translate("Add")}</b>.</p><label class="wide">${translate("All elements")}<select id="add-spec" aria-label="${translate("Add element")}"><option value="">${translate("Add element…")}</option>${Object.entries(
    groups,
  )
    .map(
      ([category, types]) =>
        `<optgroup label="${escapeHtml(category)}">${types
          .map(
            (type) =>
              `<option value="${escapeHtml(type)}">${escapeHtml(type.replaceAll("_", " "))}</option>`,
          )
          .join("")}</optgroup>`,
    )
    .join(
      "",
    )}</select></label><button class="wide" data-action="add-spec">${translate("Add")}</button>`;
}
