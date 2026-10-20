export function renderElementRotation(element, translate) {
  const label = translate("Rotate (°)");
  const value = Number(element.rotation || 0);
  return `<label class="wide">${label}<span style="display:flex;align-items:center;gap:8px"><input type="range" min="-360" max="360" step="0.1" data-property="rotation" aria-label="${label}" value="${value}" style="flex:1;min-width:0"><input type="number" min="-360" max="360" step="0.1" data-property="rotation" aria-label="${translate("Rotation value (°)")}" value="${element.rotationMixed ? "" : value}" placeholder="${translate("Mixed")}" style="width:80px"></span></label>`;
}

export function syncRotationInputs(root, value) {
  root.querySelectorAll('[data-property="rotation"]').forEach((input) => {
    if (Number(input.value) !== Number(value)) input.value = String(value);
  });
}
