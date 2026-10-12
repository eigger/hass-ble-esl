// Render the tag choices while leaving tag lookup and selection state to the panel.
export function resolveTagName(tag, aliasState) {
  return aliasState &&
    !["unknown", "unavailable"].includes(aliasState.state) &&
    aliasState.state.trim()
    ? aliasState.state
    : tag.title;
}

export function renderTagOptions(tags, selectedTag, { tagName, escapeHtml }) {
  return tags
    .map(
      (tag) =>
        `<option value="${escapeHtml(tag.entry_id)}" ${tag === selectedTag ? "selected" : ""}>${escapeHtml(tagName(tag))} · ${tag.width}×${tag.height}</option>`,
    )
    .join("");
}
