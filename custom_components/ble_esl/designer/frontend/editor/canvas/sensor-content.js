// The panel resolves Home Assistant state, sensor templates, and display
// values. This module turns those explicit values into canvas tile markup.
export function renderSensorContent({
  element,
  stateValue,
  label,
  template,
  templateValues,
  iconName,
  value,
  visual,
  escapeHtml,
  iconGlyph,
}) {
  if (template && templateValues) {
    const text = (source) =>
      String(source).replace(
        /{{(name|state|unit|icon)}}/g,
        (_, key) => templateValues[key],
      );
    return template.document.elements
      .filter((child) => !child.state || child.state === stateValue)
      .map((child) => {
        const sx = element.width / template.width,
          sy = element.height / template.height;
        const content =
          child.type === "text"
            ? escapeHtml(text(child.text)).replace(/\n/g, "<br>")
            : child.type === "icon"
              ? iconGlyph(
                  text(child.icon),
                  Math.min(child.width * sx, child.height * sy),
                )
              : "";
        return `<div style="position:absolute;left:${child.x * sx}px;top:${child.y * sy}px;width:${child.width * sx}px;height:${child.height * sy}px;overflow:hidden;color:${child.color};background:${["rectangle", "line"].includes(child.type) ? child.color : child.background};font-size:${child.font_size * Math.min(sx, sy)}px;text-align:${child.align}">${content}</div>`;
      })
      .join("");
  }

  return `<div class="tile-icon">${iconGlyph(iconName, 32)}</div><div class="tile-copy">${element.show_label ? `<div class="label">${escapeHtml(label)}</div>` : ""}<div class="value">${visual ? "" : escapeHtml(value)}</div></div>`;
}
