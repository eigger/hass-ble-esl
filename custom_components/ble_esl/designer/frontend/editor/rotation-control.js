export function renderElementRotation(element, translate) {
  const label = translate("Rotate (°)");
  return `<label>${label}<select data-property="rotation" aria-label="${label}">${[0, 90, 180, 270].map((angle) => `<option value="${angle}" ${Number(element.rotation || 0) === angle ? "selected" : ""}>${angle}°</option>`).join("")}</select></label>`;
}
