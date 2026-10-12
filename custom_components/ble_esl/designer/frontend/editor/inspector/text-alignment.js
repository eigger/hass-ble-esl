const alignments = ["left", "center", "right"];

export function renderTextAlignmentControls(
  element,
  { translate, escapeHtml },
) {
  const alignmentButtons = alignments
    .map((value) => {
      const indent = value === "right" ? 9 : value === "center" ? 6 : 3;
      return `<button class="align-button" data-pick="align" data-value="${value}" aria-label="${translate(`Align ${value}`)}" title="${translate(`Align ${value}`)}" aria-pressed="${element.align === value}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 4h18M${indent} 9h12M3 14h18M${indent} 19h12"/></svg></button>`;
    })
    .join("");

  return `<label class="">${translate("Font size")}<input data-property="font_size" type="number" value="${escapeHtml(element.font_size ?? "")}" step="1"></label><label>${translate("Align")}<div class="picker" role="group" aria-label="${translate("Text alignment")}">${alignmentButtons}</div></label>`;
}
