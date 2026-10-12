// Renders accessible color swatches from the tag palette. The panel retains
// palette selection and routes each data-pick event through document history.
export function renderColorPicker({ key, value, label, colors, translate }) {
  const options = [...colors, ...(key === "background" ? ["transparent"] : [])];
  return `<label>${label}<div class="picker" role="group" aria-label="${label}">${options
    .map(
      (color) =>
        `<button class="swatch" style="--swatch:${color};${color === "transparent" ? "background:repeating-conic-gradient(#ccc 0% 25%,white 0% 50%) 50%/8px 8px" : ""}" data-pick="${key}" data-value="${color}" aria-label="${label}: ${translate(color)}" title="${translate(color)}" aria-pressed="${value === color}"></button>`,
    )
    .join("")}</div></label>`;
}
