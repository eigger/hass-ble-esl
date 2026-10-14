const commonNames = [
  "value",
  "font",
  "font_size",
  "size",
  "color",
  "fill",
  "outline",
  "inner_radius",
  "image",
  "url",
  "points",
  "values",
  "data",
  "icon",
  "align",
  "rotate",
  "text",
  "source",
  "columns",
  "rows",
];

export function renderSpecEditorSections({
  markup,
  position,
  translate,
  advancedOpen,
}) {
  const template = document.createElement("template");
  template.innerHTML = markup;
  const common = [];
  const advanced = [];
  const information = [];
  for (const child of template.content.children) {
    const control = child.matches("[data-spec]")
      ? child
      : child.querySelector("[data-spec]");
    const requiredDescendant = child.querySelector(
      '[data-spec][data-required="true"]',
    );
    if (child.matches(".spec-doc, .muted")) information.push(child.outerHTML);
    else if (
      (child.tagName === "LABEL" ||
        (child.tagName === "FIELDSET" && requiredDescendant)) &&
      control &&
      (commonNames.includes(control.dataset.spec.split(".").at(-1)) ||
        control.dataset.required === "true" ||
        requiredDescendant)
    )
      common.push(child.outerHTML);
    else advanced.push(child.outerHTML);
  }
  common.sort((left, right) => {
    const rank = (markup) => {
      const node = document.createElement("template");
      node.innerHTML = markup;
      const path =
        node.content.querySelector("[data-spec]")?.dataset.spec || "";
      const name = path.split(".").at(-1);
      const index = commonNames.indexOf(name);
      return index < 0 ? commonNames.length : index;
    };
    return rank(left) - rank(right);
  });
  const commonSection = common.length
    ? `<h3 class="wide group-title">${translate("Common properties")}</h3>${common.join("")}`
    : "";
  const advancedSection = advanced.length
    ? `<details class="wide spec-advanced" ${advancedOpen ? "open" : ""}><summary>${translate("Advanced settings")}</summary><div class="props">${advanced.join("")}</div></details>`
    : "";
  return information.join("") + commonSection + position + advancedSection;
}
