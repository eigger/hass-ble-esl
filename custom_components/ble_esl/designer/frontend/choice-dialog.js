import { t } from "./i18n.js";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const open = new Set();
const deepActive = () => {
  let node = document.activeElement;
  while (node?.shadowRoot?.activeElement) node = node.shadowRoot.activeElement;
  return node;
};
// Dismiss every open picker as cancelled, e.g. when the panel goes away.
export function closeChoiceDialogs() {
  for (const close of [...open]) close();
}
// Pick one of several items from a radio list. Resolves with the chosen index,
// or null when cancelled, so no typed value can be out of range.
export function chooseOne(hass, title, labels) {
  return new Promise((resolve) => {
    const host = document.createElement("div");
    const opener = deepActive();
    host.attachShadow({ mode: "open" }).innerHTML = `<style>
      dialog{width:min(560px,94vw);max-height:90vh;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
      dialog::backdrop{background:#0006}
      form{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:90vh;box-sizing:border-box}
      fieldset{margin:0;padding:0;border:0;display:flex;flex-direction:column;gap:6px;overflow:auto;min-width:0}
      legend{padding:0;margin-bottom:8px;font-size:16px;font-weight:600}
      label{display:flex;align-items:flex-start;gap:8px;padding:8px 10px;border:1px solid var(--divider-color,#cbd3de);border-radius:6px;cursor:pointer;overflow-wrap:anywhere}
      input{margin-top:2px}
      button{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px 12px;cursor:pointer}
      button.primary{background:var(--primary-color,#166d75);color:var(--text-primary-color,white);border-color:var(--primary-color,#166d75)}button.primary:hover:not(:disabled){filter:brightness(1.18);box-shadow:0 1px 4px #0003}
      .actions{display:flex;gap:6px;justify-content:flex-end}
    </style><dialog aria-label="${esc(title)}"><form method="dialog"><fieldset><legend>${esc(title)}</legend>${labels
      .map(
        (label, index) =>
          `<label><input type="radio" name="choice" value="${index}" ${index === 0 ? "checked" : ""}><span>${esc(label)}</span></label>`,
      )
      .join(
        "",
      )}</fieldset><div class="actions"><button type="button" data-cancel>${t(hass, "Cancel")}</button><button type="submit" class="primary">${t(hass, "Continue")}</button></div></form></dialog>`;
    const dialog = host.shadowRoot.querySelector("dialog");
    const finish = (value) => {
      if (!host.isConnected) return;
      open.delete(cancel);
      dialog.close();
      host.remove();
      // Back to what opened the picker, if it is still there.
      if (opener?.isConnected) opener.focus();
      resolve(value);
    };
    const cancel = () => finish(null);
    open.add(cancel);
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      finish(null);
    });
    host.shadowRoot
      .querySelector("[data-cancel]")
      .addEventListener("click", () => finish(null));
    host.shadowRoot
      .querySelector("form")
      .addEventListener("submit", (event) => {
        event.preventDefault();
        const checked = host.shadowRoot.querySelector("input:checked");
        finish(checked ? Number(checked.value) : null);
      });
    document.body.append(host);
    dialog.showModal();
    host.shadowRoot.querySelector("input:checked")?.focus();
  });
}
