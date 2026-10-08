import { language, t } from "./i18n.js";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
// A template's name, description or label is text or a map of language -> text.
const localized = (hass, value) => {
  if (!value || typeof value !== "object") return value || "";
  const code = language(hass);
  return (
    value[code] ||
    value[code.split("-")[0]] ||
    value.en ||
    Object.values(value)[0] ||
    ""
  );
};
const field = (hass, name, parameter, value) => {
  const label = esc(localized(hass, parameter.label) || name);
  const id = `p-${name}`;
  let control;
  if (parameter.type === "boolean")
    control = `<input id="${id}" data-param="${esc(name)}" type="checkbox" ${value ? "checked" : ""}>`;
  else if (parameter.type === "select")
    control = `<select id="${id}" data-param="${esc(name)}">${parameter.options
      .map(
        (option) =>
          `<option value="${esc(option)}" ${option === value ? "selected" : ""}>${esc(option)}</option>`,
      )
      .join("")}</select>`;
  else if (parameter.type === "color")
    control = `<select id="${id}" data-param="${esc(name)}">${[
      "black",
      "white",
      "red",
      "yellow",
    ]
      .map(
        (color) =>
          `<option value="${color}" ${color === value ? "selected" : ""}>${color}</option>`,
      )
      .join("")}</select>`;
  else if (parameter.type === "number")
    control = `<input id="${id}" data-param="${esc(name)}" type="number" step="any" value="${esc(value)}" ${"min" in parameter ? `min="${parameter.min}"` : ""} ${"max" in parameter ? `max="${parameter.max}"` : ""}>`;
  else if (parameter.type === "time")
    control = `<input id="${id}" data-param="${esc(name)}" type="time" step="1" value="${esc(value)}">`;
  else
    control = `<input id="${id}" data-param="${esc(name)}" type="text" value="${esc(value)}">`;
  return `<label>${label}${control}</label>`;
};
// A gallery of ready-made designs. A chosen one is added as ordinary elements,
// and the automation it suggests (triggers) is kept for Create automation.
export class TemplateDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
  }
  async open(panel, onClose, context) {
    this.panel = panel;
    this.onClose = onClose;
    this.context = context;
    this.templates = null;
    this.chosen = null;
    this.note = "";
    this.issues = [];
    this.render();
    try {
      this.templates = await panel.api("design_templates", {
        entry_id: context.entryId,
      });
    } catch (error) {
      this.note = error.message || String(error);
    }
    if (!this.closed) this.render();
  }
  close() {
    if (this.closed) return;
    this.closed = true;
    // Only while the design it was applied to is still the one being edited.
    const create =
      this.thenCreate && this.panel.isDocumentSessionOwner(this.context);
    if (this.context) this.context.cancelled = true;
    this.remove();
    this.onClose?.();
    if (create) this.panel.createAutomationFromTemplate();
  }
  updateHass() {
    if (!this.closed) this.render();
  }
  // Values typed so far, by parameter name.
  values() {
    const values = {};
    for (const input of this.shadowRoot.querySelectorAll("[data-param]")) {
      const name = input.dataset.param;
      const parameter = this.chosen.parameters[name];
      if (parameter.type === "boolean") values[name] = input.checked;
      else if (parameter.type === "number")
        values[name] =
          input.value === "" ? parameter.default : Number(input.value);
      else values[name] = input.value;
    }
    return values;
  }
  body() {
    const hass = this.panel.hass;
    if (this.chosen) {
      const entries = Object.entries(this.chosen.parameters);
      const group = (name) =>
        entries
          .filter(([, parameter]) => parameter.group === name)
          .map(([key, parameter]) =>
            field(hass, key, parameter, this.typed?.[key] ?? parameter.default),
          )
          .join("");
      const design = group("design"),
        automation = group("automation");
      return `<p class="muted">${esc(localized(hass, this.chosen.description))}</p>
        ${this.chosen.scaled ? `<p class="muted">${t(hass, "Adjusted to this display")} (${esc(this.chosen.layout)})</p>` : ""}
        ${design ? `<div class="fields">${design}</div>` : ""}
        ${automation ? `<h3>${t(hass, "Automation")}</h3><div class="fields">${automation}</div>` : ""}`;
    }
    if (!this.templates) return "";
    const save = this.panel.document.elements.length
      ? `<h3>${t(hass, "Save current design as a template")}</h3><div class="save"><input type="text" data-save-name maxlength="80" aria-label="${t(hass, "Template name")}" placeholder="${t(hass, "Template name")}" value="${esc(this.saveName || "")}"><button type="button" data-save>${t(hass, "Save as template")}</button></div>`
      : "";
    if (!this.templates.length)
      return `<p class="muted">${t(hass, "No design templates fit this display.")}</p>${save}`;
    return `<p class="muted">${t(hass, "Choose a ready-made design. It is added as ordinary elements you can edit.")}</p><div class="list">${this.templates
      .map(
        (template) =>
          `<button type="button" class="card" data-template="${esc(template.id)}"><b>${esc(localized(hass, template.name))}</b><span class="muted">${esc(localized(hass, template.description))}</span><span class="muted">${template.source === "user" ? `${t(hass, "My template")} · ` : ""}${esc(template.layout)}${template.scaled ? ` · ${t(hass, "Adjusted to this display")}` : ""}</span></button>`,
      )
      .join("")}</div>${save}`;
  }
  render() {
    if (this.chosen && this.shadowRoot.querySelector("[data-param]"))
      this.typed = this.values();
    const nameInput = this.shadowRoot.querySelector("[data-save-name]");
    if (nameInput) this.saveName = nameInput.value;
    const hass = this.panel.hass;
    const done = this.done;
    this.shadowRoot.innerHTML = `<style>
      dialog{width:min(560px,94vw);max-height:90vh;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
      dialog::backdrop{background:#0006}
      form{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:90vh;box-sizing:border-box;overflow:auto}
      h2,h3{margin:0;font-size:16px} h3{font-size:14px}
      button{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px 12px;cursor:pointer}
      button.primary{background:#166d75;color:white;border-color:#166d75}
      button:disabled{opacity:.5;cursor:default}
      .list{display:grid;gap:8px}
      .card{display:flex;flex-direction:column;gap:2px;text-align:left}
      .fields{display:grid;gap:10px}
      label{display:grid;gap:4px;font-size:13px}
      input[type=text],input[type=number],input[type=time],select{font:inherit;padding:6px 8px;border:1px solid var(--divider-color,#cbd3de);border-radius:6px;background:var(--secondary-background-color,#f5f7fa);color:inherit}
      input[type=checkbox]{justify-self:start}
      .save{display:flex;gap:6px} .save input{flex:1}
      .actions{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}
      .muted{color:var(--secondary-text-color,#637083);font-size:12px;margin:0}
      .note{margin:0;font-size:13px}
      .issues{color:#c33;margin:0;padding-left:18px;font-size:12px}
    </style><dialog aria-label="${t(hass, "Design templates")}"><form method="dialog">
      <h2>${t(hass, "Design templates")}</h2>
      ${this.body()}
      ${this.note ? `<p class="note" role="status">${esc(t(hass, this.note))}</p>` : ""}
      ${this.issues.length ? `<ul class="issues">${this.issues.map((issue) => `<li>${esc(issue)}</li>`).join("")}</ul>` : ""}
      <div class="actions">${
        done
          ? ""
          : this.chosen
            ? `<button type="button" data-back>${t(hass, "Back")}</button><button type="button" data-mode="add" class="primary">${t(hass, "Add to display")}</button><button type="button" data-mode="replace">${t(hass, "Replace display")}</button>${this.chosen.automation && this.panel.tag?.writable ? `<button type="button" data-mode="create">${t(hass, "Replace and create automation")}</button>` : ""}`
            : ""
      }<button type="button" data-close>${done ? t(hass, "Close") : t(hass, "Cancel")}</button></div>
    </form></dialog>`;
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
    dialog.showModal();
    this.shadowRoot
      .querySelector("[data-param], [data-template], button")
      ?.focus();
  }
  async click(event) {
    const button = event
      .composedPath()
      .find((node) => node.tagName === "BUTTON");
    if (!button) return;
    if ("close" in button.dataset) return this.close();
    if ("back" in button.dataset) {
      this.chosen = null;
      this.typed = null;
      this.note = "";
      this.issues = [];
      return this.render();
    }
    if ("save" in button.dataset) {
      if (this.pending) return;
      this.pending = true;
      const name = this.shadowRoot.querySelector("[data-save-name]").value;
      try {
        const saved = await this.panel.api("save_design_template", {
          entry_id: this.context.entryId,
          document: this.panel.document,
          name,
        });
        this.templates = await this.panel.api("design_templates", {
          entry_id: this.context.entryId,
        });
        this.saveName = "";
        this.note = {
          key: "Saved template {name}.",
          values: { name: saved.id },
        };
        this.issues = [];
      } catch (error) {
        this.note = error.message || String(error);
      } finally {
        this.pending = false;
      }
      if (!this.closed) this.render();
      return;
    }
    if (button.dataset.template) {
      this.chosen = this.templates.find(
        (template) => template.id === button.dataset.template,
      );
      this.typed = null;
      return this.render();
    }
    const mode = button.dataset.mode;
    if (!mode || this.pending) return;
    // The browser says what is wrong with a half-typed or out-of-range number.
    for (const input of this.shadowRoot.querySelectorAll("input"))
      if (!input.reportValidity()) return;
    this.pending = true;
    for (const other of this.shadowRoot.querySelectorAll(".actions button"))
      other.disabled = true;
    try {
      const result = await this.panel.applyDesignTemplate(
        this.chosen.id,
        this.values(),
        mode !== "add",
        this.context,
      );
      if (result.stale) return this.close();
      const placed = result.elements.length;
      if (placed && !result.issues.length) {
        const create = mode === "create";
        this.close();
        if (create) this.panel.createAutomationFromTemplate();
        return;
      }
      this.done = placed > 0;
      // Close still goes on to Create automation, as it would have without issues.
      this.thenCreate = placed > 0 && mode === "create";
      this.note = placed
        ? {
            key: "{count} placed, {skipped} skipped.",
            values: { count: placed, skipped: result.issues.length },
          }
        : "Nothing could be placed.";
      this.issues = result.issues;
      this.render();
    } catch (error) {
      if (this.panel.isDocumentSessionCurrent(this.context)) {
        this.note = error.message || String(error);
        this.render();
      } else this.close();
    } finally {
      this.pending = false;
    }
  }
}
if (!customElements.get("ble-esl-template-dialog"))
  customElements.define("ble-esl-template-dialog", TemplateDialog);
