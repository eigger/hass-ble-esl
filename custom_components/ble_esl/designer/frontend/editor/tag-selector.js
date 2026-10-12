// Render the tag choices while leaving tag lookup and selection state to the panel.
export function renderTagOptions(tags, selectedTag, { tagName, escapeHtml }) {
  return tags
    .map(
      (tag) =>
        `<option value="${escapeHtml(tag.entry_id)}" ${tag === selectedTag ? "selected" : ""}>${escapeHtml(tagName(tag))} · ${tag.width}×${tag.height}</option>`,
    )
    .join("");
}
