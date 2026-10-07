import { t } from "./i18n.js";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const views = [
  ["payload", "Payload", "Paste under `payload:` of a ble_esl.write action."],
  [
    "service",
    "Automation action",
    "A complete action for a script or automation.",
  ],
];
// The display as YAML for an automation: exactly the payload the preview and
// the tag are rendered from, as produced by the server. Values are those of
// this moment; schedule transmissions through Home Assistant automations.
export class YamlDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
    this.shadowRoot.addEventListener("change", (event) => this.change(event));
  }
  open(result, onClose, hass) {
    this.hass = hass;
    this.result = result;
    this.onClose = onClose;
    this.view = "payload";
    // With templates in the design the automation should keep them.
    this.live = "live_payload" in result;
    this.render();
  }
  updateHass(hass) {
    this.hass = hass;
    this.render();
  }
  get text() {
    return this.result[(this.live ? "live_" : "") + this.view];
  }
  close() {
    this.remove();
    this.onClose?.();
  }
  render() {
    const shown = views.filter(
      ([key]) => key === "payload" || this.result.writable,
    );
    const [, , hint] = views.find(([key]) => key === this.view);
    this.shadowRoot.innerHTML = `<style>
      dialog{width:min(720px,94vw);max-height:90vh;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
      dialog::backdrop{background:#0006}
      form{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:90vh;box-sizing:border-box}
      h2{margin:0;font-size:16px}
      .tabs,.actions{display:flex;gap:6px}.actions{justify-content:flex-end}
      button{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px 12px;cursor:pointer}
      button[aria-selected="true"],button.primary{background:#166d75;color:white;border-color:#166d75}
      textarea{flex:1;min-height:280px;font:12px ui-monospace,Menlo,Consolas,monospace;resize:vertical;padding:10px;border:1px solid var(--divider-color,#cbd3de);border-radius:6px;background:var(--secondary-background-color,#f5f7fa);color:inherit}
      .muted{color:var(--secondary-text-color,#637083);font-size:12px;margin:0}
      .check{display:flex;gap:6px;align-items:center;font-size:13px}
      .issues{color:#c33;margin:0;padding-left:18px;font-size:12px}
    </style><dialog aria-label="${t(this.hass, "Payload YAML")}"><form method="dialog">
      <h2>${t(this.hass, "Payload YAML")}</h2>
      <div class="tabs" role="tablist">${shown
        .map(
          ([key, label]) =>
            `<button type="button" role="tab" data-view="${key}" aria-selected="${key === this.view}">${t(this.hass, label)}</button>`,
        )
        .join("")}</div>
      <p class="muted">${esc(t(this.hass, hint))} ${
        this.live
          ? t(
              this.hass,
              "Element templates stay as written: Home Assistant renders them each time the automation runs. Sensor components and field templates are as of now.",
            )
          : t(
              this.hass,
              "Values are as of now. Use the automation action to schedule tag updates in Home Assistant.",
            )
      }</p>
      ${"live_payload" in this.result ? `<label class="check"><input type="checkbox" data-live ${this.live ? "checked" : ""}> ${t(this.hass, "Keep templates (values follow the sensors)")}</label>` : ""}
      ${this.result.issues.length ? `<ul class="issues">${this.result.issues.map((issue) => `<li>${esc(issue)}</li>`).join("")}</ul>` : ""}
      <textarea readonly aria-label="YAML" spellcheck="false">${esc(this.text)}</textarea>
      <div class="actions"><button type="button" data-copy class="primary">${t(this.hass, "Copy")}</button><button type="button" data-close>${t(this.hass, "Close")}</button></div>
    </form></dialog>`;
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
    dialog.showModal();
  }
  change(event) {
    const box = event
      .composedPath()
      .find((node) => node.dataset?.live !== undefined);
    if (!box) return;
    this.live = box.checked;
    this.render();
    // The dialog is rebuilt: keep the keyboard where it was.
    this.shadowRoot.querySelector("[data-live]")?.focus();
  }
  async click(event) {
    const button = event
      .composedPath()
      .find((node) => node.tagName === "BUTTON");
    if (!button) return;
    if (button.dataset.view) {
      this.view = button.dataset.view;
      this.render();
      this.shadowRoot.querySelector(`[data-view="${this.view}"]`)?.focus();
    } else if ("close" in button.dataset) {
      this.close();
    } else if ("copy" in button.dataset) {
      let copied = true;
      try {
        await navigator.clipboard.writeText(this.text);
      } catch {
        this.shadowRoot.querySelector("textarea").select();
        copied = document.execCommand("copy");
      }
      button.textContent = copied
        ? t(this.hass, "Copied")
        : t(this.hass, "Press Ctrl+C to copy");
    }
  }
}
if (!customElements.get("ble-esl-yaml-dialog"))
  customElements.define("ble-esl-yaml-dialog", YamlDialog);
