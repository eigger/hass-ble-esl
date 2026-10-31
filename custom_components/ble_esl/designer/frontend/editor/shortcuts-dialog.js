import { t } from "../i18n.js";

// The two tip sentences under the canvas are lists of " · " separated items.
// The same translated copy fills the `?` dialog, so there is one source.
export const CANVAS_TIPS =
  "Click an element to select it · Click text to edit · Drag to move · Drag corner handles to resize · Alignment guides appear near edges and centres · Arrow keys move 1 px · Shift + arrows move 10 px · Enter edits selected text · Delete / Backspace removes · Right-click for actions · ⌘/Ctrl + D duplicates · ⌘/Ctrl + S saves · ⌘/Ctrl + Z undoes · ⌘/Ctrl + Shift + Z redoes";
export const SELECTION_TIPS =
  "Shift / Ctrl / ⌘ + click selects several elements · Drag on an empty part of the canvas to select an area · ? shows all shortcuts";

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const deepActive = () => {
  let node = document.activeElement;
  while (node?.shadowRoot?.activeElement) node = node.shadowRoot.activeElement;
  return node;
};
let current = null;

// A modal list of every keyboard and mouse shortcut of the canvas.
export function openShortcutsDialog(hass) {
  if (current) return;
  const host = document.createElement("div");
  const opener = deepActive();
  const items = [CANVAS_TIPS, SELECTION_TIPS]
    .flatMap((key) => t(hass, key).split(" · "))
    .map((item) => `<li>${esc(item.trim())}</li>`)
    .join("");
  const title = t(hass, "Keyboard & mouse tips");
  host.attachShadow({ mode: "open" }).innerHTML = `<style>
    dialog{width:min(560px,94vw);max-height:90vh;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
    dialog::backdrop{background:#0006}
    .body{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:90vh;box-sizing:border-box}
    h2{margin:0;font-size:16px}
    ul{margin:0;padding-left:20px;overflow:auto;line-height:1.7}
    .actions{display:flex;justify-content:flex-end}
    button{font:inherit;color:var(--text-primary-color,white);background:var(--primary-color,#166d75);border:1px solid var(--primary-color,#166d75);border-radius:6px;padding:8px 12px;cursor:pointer}
    button:hover{filter:brightness(1.18);box-shadow:0 1px 4px #0003}
  </style><dialog aria-label="${esc(title)}"><div class="body"><h2>${esc(title)}</h2><ul>${items}</ul><div class="actions"><button type="button" data-close>${esc(t(hass, "Close"))}</button></div></div></dialog>`;
  const dialog = host.shadowRoot.querySelector("dialog");
  const close = () => {
    if (!host.isConnected) return;
    current = null;
    dialog.close();
    host.remove();
    if (opener?.isConnected) opener.focus();
  };
  current = close;
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    close();
  });
  host.shadowRoot
    .querySelector("[data-close]")
    .addEventListener("click", close);
  document.body.append(host);
  dialog.showModal();
  host.shadowRoot.querySelector("[data-close]").focus();
}

export function closeShortcutsDialog() {
  current?.();
}
