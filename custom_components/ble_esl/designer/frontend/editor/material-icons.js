const icons = {
  menu: "menu",
  delete: "delete-outline",
  duplicate: "content-copy",
  back: "arrange-send-to-back",
  front: "arrange-bring-to-front",
  center: "align-horizontal-center",
  text: "format-text",
  shape: "shape-outline",
  image: "image-outline",
  icon: "star-outline",
  reload: "refresh",
  save: "content-save-outline",
  preview: "eye-outline",
  send: "bluetooth",
  undo: "undo",
  redo: "redo",
  eyeoff: "eye-off-outline",
  up: "chevron-up",
  down: "chevron-down",
  move: "cursor-move",
  close: "close",
  plus: "plus",
  minus: "minus",
};

export function materialIcon(name, size = 20) {
  const icon = name.startsWith("mdi:") ? name : `mdi:${icons[name]}`;
  if (icon === "mdi:undefined") throw new Error(`Unknown editor icon: ${name}`);
  return `<ha-icon icon="${icon}" aria-hidden="true" style="--mdc-icon-size:${size}px;display:inline-flex;flex:none;vertical-align:middle"></ha-icon>`;
}
