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
// this moment; the tag keeps up with sensors through Auto update sensor.
export class YamlDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
  }
  open(result, onClose) {
    this.result = result;
    this.onClose = onClose;
    this.view = "payload";
    this.render();
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
      .issues{color:#c33;margin:0;padding-left:18px;font-size:12px}
    </style><dialog aria-label="Payload YAML"><form method="dialog">
      <h2>Payload YAML</h2>
      <div class="tabs" role="tablist">${shown
        .map(
          ([key, label]) =>
            `<button type="button" role="tab" data-view="${key}" aria-selected="${key === this.view}">${label}</button>`,
        )
        .join("")}</div>
      <p class="muted">${esc(hint)} Values are as of now: the payload is the one the preview and the tag are rendered from, so use Auto update sensor to keep a tag current.</p>
      ${this.result.issues.length ? `<ul class="issues">${this.result.issues.map((issue) => `<li>${esc(issue)}</li>`).join("")}</ul>` : ""}
      <textarea readonly aria-label="YAML" spellcheck="false">${esc(this.result[this.view])}</textarea>
      <div class="actions"><button type="button" data-copy class="primary">Copy</button><button type="button" data-close>Close</button></div>
    </form></dialog>`;
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
    dialog.showModal();
  }
  async click(event) {
    const button = event
      .composedPath()
      .find((node) => node.tagName === "BUTTON");
    if (!button) return;
    if (button.dataset.view) {
      this.view = button.dataset.view;
      this.render();
    } else if ("close" in button.dataset) {
      this.close();
    } else if ("copy" in button.dataset) {
      let copied = true;
      try {
        await navigator.clipboard.writeText(this.result[this.view]);
      } catch {
        this.shadowRoot.querySelector("textarea").select();
        copied = document.execCommand("copy");
      }
      button.textContent = copied ? "Copied" : "Press Ctrl+C to copy";
    }
  }
}
customElements.define("ble-esl-yaml-dialog", YamlDialog);
