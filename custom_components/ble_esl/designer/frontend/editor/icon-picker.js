// Markup helpers for the Material Design icon chooser. The panel owns the icon
// catalog and the live search field; this module only renders the supplied data.
export function renderIconGlyph(name, size, icons, escapeHtml) {
  return `<span class="mdi" aria-hidden="true" style="font-size:${size}px">${escapeHtml(icons[name] || "")}</span>`;
}

export function renderIconChoices(icons, search, escapeHtml) {
  const query = String(search ?? "").toLowerCase();
  return Object.keys(icons)
    .filter((name) => name.includes(query))
    .slice(0, 120)
    .map(
      (name) =>
        `<button data-icon="${escapeHtml(name)}" aria-label="${escapeHtml(name)}" title="${escapeHtml(name)}">${renderIconGlyph(name, 24, icons, escapeHtml)}</button>`,
    )
    .join("");
}
