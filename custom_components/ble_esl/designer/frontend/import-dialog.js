import { t } from "./i18n.js";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
// Paste the payload of a ble_esl.write action (or the whole action) to edit it
// in the designer. The designer says what it could not place and whether what
// it builds draws exactly what the pasted payload did.
export class ImportDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
  }
  open(panel, onClose, context) {
    this.panel = panel;
    this.onClose = onClose;
    this.context = context;
    this.render();
  }
  close() {
    if (this.closed) return;
    this.closed = true;
    if (this.context) this.context.cancelled = true;
    this.remove();
    this.onClose?.();
  }
  updateHass() {
    this.render(...this.renderState);
  }
  render(note = "", issues = [], done = false) {
    this.renderState = [note, issues, done];
    const text = this.shadowRoot.querySelector("textarea")?.value ?? "";
    this.shadowRoot.innerHTML = `<style>
      dialog{width:min(720px,94vw);max-height:90vh;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
      dialog::backdrop{background:#0006}
      form{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:90vh;box-sizing:border-box}
      h2{margin:0;font-size:16px}
      button{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px 12px;cursor:pointer}
      button.primary{background:#166d75;color:white;border-color:#166d75}
      button:disabled{opacity:.5;cursor:default}
      textarea{min-height:260px;font:12px ui-monospace,Menlo,Consolas,monospace;resize:vertical;padding:10px;border:1px solid var(--divider-color,#cbd3de);border-radius:6px;background:var(--secondary-background-color,#f5f7fa);color:inherit}
      .actions{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}
      .muted{color:var(--secondary-text-color,#637083);font-size:12px;margin:0}
      .note{margin:0;font-size:13px}
      .issues{color:#c33;margin:0;padding-left:18px;font-size:12px}
    </style><dialog aria-label="${t(this.panel.hass, "Import YAML")}"><form method="dialog">
      <h2>${t(this.panel.hass, "Import YAML")}</h2>
      <p class="muted">${t(this.panel.hass, "Paste a payload (a list of imagespec elements) or a whole ble_esl.write action. Elements placed by a template or a flow layout cannot be placed in the designer and are listed.")}</p>
      <textarea aria-label="${t(this.panel.hass, "YAML to import")}" spellcheck="false" placeholder="- type: text&#10;  value: Hello&#10;  x: 10&#10;  y: 10">${esc(text)}</textarea>
      ${note ? `<p class="note" role="status">${esc(t(this.panel.hass, note))}</p>` : ""}
      ${issues.length ? `<ul class="issues">${issues.map((issue) => `<li>${esc(issue)}</li>`).join("")}</ul>` : ""}
      <div class="actions">${done ? "" : `<button type="button" data-mode="add" class="primary">${t(this.panel.hass, "Add to display")}</button><button type="button" data-mode="replace">${t(this.panel.hass, "Replace display")}</button>`}<button type="button" data-close>${done ? t(this.panel.hass, "Close") : t(this.panel.hass, "Cancel")}</button></div>
    </form></dialog>`;
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
    dialog.showModal();
    this.shadowRoot.querySelector("textarea").focus();
  }
  async click(event) {
    const button = event
      .composedPath()
      .find((node) => node.tagName === "BUTTON");
    if (!button) return;
    if ("close" in button.dataset) return this.close();
    const mode = button.dataset.mode;
    if (!mode) return;
    // One request at a time: a second click would add everything again.
    if (this.pending) return;
    this.pending = true;
    for (const other of this.shadowRoot.querySelectorAll(".actions button"))
      other.disabled = true;
    const text = this.shadowRoot.querySelector("textarea").value;
    try {
      const result = await this.panel.importYaml(
        text,
        mode === "replace",
        this.context,
      );
      if (result.stale) return this.close();
      const placed = result.elements.length;
      if (placed && !result.issues.length) return this.close();
      // What was placed is in the display already: only closing is left.
      this.render(
        placed
          ? {
              key: "{count} placed, {skipped} skipped.",
              values: { count: placed, skipped: result.issues.length },
            }
          : "Nothing could be placed.",
        result.issues,
        placed > 0,
      );
    } catch (error) {
      if (this.panel.isDocumentSessionCurrent(this.context))
        this.render(error.message || String(error));
      else this.close();
    } finally {
      this.pending = false;
    }
  }
}
if (!customElements.get("ble-esl-import-dialog"))
  customElements.define("ble-esl-import-dialog", ImportDialog);
