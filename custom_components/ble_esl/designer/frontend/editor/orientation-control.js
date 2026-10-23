import { materialIcon } from "./material-icons.js";
export function renderOrientation(tag, mode, busy, translate) {
  if (!tag || mode === "template" || tag.width === tag.height) return "";
  const portrait = tag.height > tag.width;
  return `<span role="group" aria-label="${translate("Tag orientation")}" data-tag-orientation>${[
    false,
    true,
  ]
    .map((value) => {
      const label = translate(value ? "Portrait" : "Landscape");
      // Dimensions describe the current logical canvas, not the physical panel.
      const physicalPortrait = (tag.rotation || 0) % 180 ? !portrait : portrait;
      // The pressed button keeps the design's own angle (e.g. 180 or 270).
      const rotation =
        portrait === value
          ? tag.rotation || 0
          : value === physicalPortrait
            ? 0
            : 90;
      return `<button class="icon-button" data-action="tag-orientation" data-rotation="${rotation}" aria-label="${label}" title="${label}" aria-pressed="${portrait === value}" ${busy ? "disabled" : ""}>${materialIcon(value ? "mdi:crop-portrait" : "mdi:crop-landscape")}</button>`;
    })
    .join("")}</span>`;
}
