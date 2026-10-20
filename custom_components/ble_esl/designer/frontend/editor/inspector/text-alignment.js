import { materialIcon } from "../material-icons.js";
const alignments = ["left", "center", "right"];

export function renderTextAlignmentControls(
  element,
  { translate, escapeHtml },
) {
  const alignmentButtons = alignments
    .map((value) => {
      return `<button class="align-button" data-pick="align" data-value="${value}" aria-label="${translate(`Align ${value}`)}" title="${translate(`Align ${value}`)}" aria-pressed="${element.align === value}">${materialIcon(`mdi:format-align-${value}`)}</button>`;
    })
    .join("");

  return `<label class="">${translate("Font size")}<input data-property="font_size" type="number" value="${escapeHtml(element.font_size ?? "")}" step="1"></label><label>${translate("Align")}<div class="picker" role="group" aria-label="${translate("Text alignment")}">${alignmentButtons}</div></label>`;
}
