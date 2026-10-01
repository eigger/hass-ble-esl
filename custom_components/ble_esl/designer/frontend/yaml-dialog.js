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
  ["service", "Automation action", "A complete action for a script or automation."],
];
// The display as YAML for an automation: exactly the payload the preview and
// the tag are rendered from, as produced by the server.
export class YamlDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
  }
  open(result) {
    this.result = result;
    this.view = "payload";
    this.render();
  }
  render() {
    const [, , hint] = views.find(([key]) => key === this.view);
    this.shadowRoot.innerHTML = `<style>
      dialog{width:min(720px,94vw);max-height:90vh;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
      dialog::backdrop{background:#0006}
      form{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:90vh;box-sizing:border-box}
      h2{margin:0;font-size:16px}
      .tabs,.actions{display:flex;gap:6px}.actions{justify-content:flex-end}
      button{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px 12px;cursor:pointer}
      button[aria-pressed="true"],button.primary{background:#166d75;color:white;border-color:#166d75}
      textarea{flex:1;min-height:280px;font:12px ui-monospace,Menlo,Consolas,monospace;resize:vertical;padding:10px;border:1px solid var(--divider-color,#cbd3de);border-radius:6px;background:var(--secondary-background-color,#f5f7fa);color:inherit}
      .muted{color:var(--secondary-text-color,#637083);font-size:12px;margin:0}
      .issues{color:#c33;margin:0;padding-left:18px;font-size:12px}
    </style><dialog aria-label="Payload YAML"><form method="dialog">
      <h2>Payload YAML</h2>
      <div class="tabs">${views
        .map(
          ([key, label]) =>
            `<button type="button" data-view="${key}" aria-pressed="${key === this.view}">${label}</button>`,
        )
        .join("")}</div>
      <p class="muted">${esc(hint)} It is the same payload the preview and the tag are rendered from.</p>
      ${this.result.issues.length ? `<ul class="issues">${this.result.issues.map((issue) => `<li>${esc(issue)}</li>`).join("")}</ul>` : ""}
      <textarea readonly aria-label="YAML" spellcheck="false">${esc(this.result[this.view])}</textarea>
      <div class="actions"><button type="button" data-copy class="primary">Copy</button><button type="button" data-close>Close</button></div>
    </form></dialog>`;
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.remove();
    });
    dialog.showModal();
  }
  async click(event) {
    const button = event.composedPath().find((node) => node.tagName === "BUTTON");
    if (!button) return;
    if (button.dataset.view) {
      this.view = button.dataset.view;
      this.render();
    } else if ("close" in button.dataset) {
      this.remove();
    } else if ("copy" in button.dataset) {
      try {
        await navigator.clipboard.writeText(this.result[this.view]);
      } catch {
        this.shadowRoot.querySelector("textarea").select();
        document.execCommand("copy");
      }
      button.textContent = "Copied";
    }
  }
}
customElements.define("ble-esl-yaml-dialog", YamlDialog);
