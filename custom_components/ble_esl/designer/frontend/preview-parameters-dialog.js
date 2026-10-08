import { t } from "./i18n.js";

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const forbiddenKeys = new Set(["__proto__", "prototype", "constructor"]);

function safeValue(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean")
    return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(safeValue);
  if (typeof value === "object")
    return Object.entries(value).every(
      ([key, item]) => !forbiddenKeys.has(key) && safeValue(item),
    );
  return false;
}

function valueType(value) {
  if (typeof value === "string") return "string";
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  return "json";
}

export class PreviewParametersDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
    this.shadowRoot.addEventListener("change", (event) => this.change(event));
    this.shadowRoot.addEventListener("submit", (event) => {
      event.preventDefault();
      this.apply();
    });
  }

  open(panel, variables = {}, missingName = null) {
    this.panel = panel;
    this.hass = panel.hass;
    this.closed = false;
    this.resolvePromise = null;
    this._missingName = missingName || null;
    this.allowEmptyMissing = false;
    this.values = structuredClone(variables || {});
    if (missingName && !Object.hasOwn(this.values, missingName))
      this.values[missingName] = "";
    this.render();
    return new Promise((resolve) => {
      this.resolvePromise = resolve;
    });
  }

  updateHass(hass) {
    const advanced = this.shadowRoot.querySelector("details.advanced");
    const snapshot = {
      advancedOpen: Boolean(advanced?.open),
      advancedText: this.shadowRoot.querySelector("[data-all-json]")?.value,
      activeRow:
        this.shadowRoot.activeElement?.closest("fieldset")?.dataset.row,
      activeKind:
        this.shadowRoot.activeElement?.dataset.name !== undefined
          ? "name"
          : this.shadowRoot.activeElement?.dataset.type !== undefined
            ? "type"
            : this.shadowRoot.activeElement?.hasAttribute("data-value")
              ? "value"
              : this.shadowRoot.activeElement?.hasAttribute("data-all-json")
                ? "all-json"
                : null,
      rows: [...this.shadowRoot.querySelectorAll("fieldset")].map((row) => ({
        name: row.querySelector("[data-name]").value,
        type: row.querySelector("[data-type]").value,
        value: row.querySelector("[data-value]").value,
      })),
      allowEmptyMissing: Boolean(
        this.shadowRoot.querySelector("[data-allow-empty]")?.checked,
      ),
    };
    this.allowEmptyMissing = snapshot.allowEmptyMissing;
    this.hass = hass;
    this.render();
    for (const [index, state] of snapshot.rows.entries()) {
      const row = this.shadowRoot.querySelector(`[data-row="${index}"]`);
      if (!row) continue;
      row.querySelector("[data-name]").value = state.name;
      row.querySelector("[data-type]").value = state.type;
      row.querySelector("[data-value]").value = state.value;
    }
    if (snapshot.advancedOpen) {
      this.shadowRoot.querySelector("details.advanced").open = true;
      this.shadowRoot.querySelector("[data-all-json]").value =
        snapshot.advancedText;
    }
    if (this.shadowRoot.querySelector("[data-allow-empty]"))
      this.shadowRoot.querySelector("[data-allow-empty]").checked =
        snapshot.allowEmptyMissing;
    if (snapshot.activeKind) {
      const row =
        snapshot.activeRow === undefined
          ? this.shadowRoot
          : this.shadowRoot.querySelector(`[data-row="${snapshot.activeRow}"]`);
      row?.querySelector(`[data-${snapshot.activeKind}]`)?.focus();
    }
  }

  render(error = "") {
    const previousDialog = this.shadowRoot.querySelector("dialog");
    if (previousDialog?.open) previousDialog.close();
    const missingName = this.missingName;
    const rows = Object.entries(this.values)
      .map(([name, value], index) => {
        const type = valueType(value);
        const field =
          type === "boolean"
            ? `<select data-value aria-label="${esc(name)}"><option value="true" ${value ? "selected" : ""}>${t(this.hass, "True")}</option><option value="false" ${!value ? "selected" : ""}>${t(this.hass, "False")}</option></select>`
            : type === "json"
              ? `<textarea data-value aria-label="${esc(name)}" rows="3">${esc(JSON.stringify(value, null, 2))}</textarea>`
              : `<input data-value aria-label="${esc(name)}" value="${esc(value)}" ${type === "number" ? 'inputmode="decimal"' : ""}>`;
        return `<fieldset data-row="${index}"><legend>${esc(name || t(this.hass, "New parameter"))}</legend><label>${t(this.hass, "Parameter name")}<input data-name value="${esc(name)}" autocomplete="off" spellcheck="false"></label><label>${t(this.hass, "Type")}<select data-type><option value="string" ${type === "string" ? "selected" : ""}>${t(this.hass, "String")}</option><option value="number" ${type === "number" ? "selected" : ""}>${t(this.hass, "Number")}</option><option value="boolean" ${type === "boolean" ? "selected" : ""}>${t(this.hass, "Boolean")}</option><option value="json" ${type === "json" ? "selected" : ""}>${t(this.hass, "Object, array or null")}</option></select></label><label class="value-label">${t(this.hass, "Value")}${field}</label><button type="button" data-remove="${index}" aria-label="${t(this.hass, "Remove parameter {name}", { name })}">${t(this.hass, "Remove")}</button></fieldset>`;
      })
      .join("");
    const missing = missingName
      ? `<p class="missing" role="status">${t(this.hass, "Enter a preview value for {name}.", { name: missingName })}</p>`
      : "";
    this.shadowRoot.innerHTML = `<style>
      dialog{width:min(680px,94vw);max-height:90vh;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
      dialog::backdrop{background:#0006} form{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:90vh;box-sizing:border-box;overflow:auto}
      h2{margin:0;font-size:18px} p{margin:0;line-height:1.45}.muted{color:var(--secondary-text-color,#637083);font-size:13px}.missing{padding:9px;background:var(--secondary-background-color,#f5f7fa);border-inline-start:3px solid #bb7500}
      fieldset{display:grid;grid-template-columns:minmax(120px,1fr) minmax(120px,.8fr) minmax(180px,1.4fr) auto;align-items:end;gap:8px;border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:9px}.field-error{grid-column:1/-1;color:#b42318;font-size:12px}
      legend{font-weight:600;padding:0 4px} label{display:flex;flex-direction:column;gap:4px;font-size:12px}input,select,textarea,button{font:inherit;color:inherit}input,select,textarea{min-width:0;box-sizing:border-box;padding:7px;border:1px solid var(--divider-color,#cbd3de);border-radius:5px;background:var(--secondary-background-color,#f5f7fa)}textarea{font:12px ui-monospace,Menlo,Consolas,monospace;resize:vertical}.value-label textarea{min-height:58px}
      button{background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px 12px;cursor:pointer}button.primary{background:#166d75;color:white;border-color:#166d75}.actions{display:flex;gap:8px;justify-content:space-between;flex-wrap:wrap}.right{display:flex;gap:8px}.error{color:#b42318;font-weight:600}.empty-option{display:flex;flex-direction:row;align-items:center;gap:8px}.advanced summary{cursor:pointer;font-weight:600;margin:4px 0}.advanced textarea{width:100%;min-height:220px}.actions button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:2px solid #087e8b;outline-offset:2px}
      @media(max-width:560px){fieldset{grid-template-columns:1fr 1fr}.value-label{grid-column:1/-1}fieldset button{justify-self:start}}
    </style><dialog aria-labelledby="preview-parameters-title" aria-describedby="preview-parameters-description"><form novalidate>
      <h2 id="preview-parameters-title">${t(this.hass, "Preview parameters")}</h2>
      <p id="preview-parameters-description" class="muted">${t(this.hass, "These typed values are used only to preview and validate this design. They are not saved to the automation.")}</p>
      ${missing}${rows || `<p class="muted">${t(this.hass, "No preview parameters yet. Add one for a variable used by a template.")}</p>`}
      ${missingName ? `<label class="empty-option"><input type="checkbox" data-allow-empty ${this.allowEmptyMissing ? "checked" : ""}>${t(this.hass, "Use an empty string for {name}", { name: missingName })}</label>` : ""}
      <button type="button" data-add>${t(this.hass, "Add parameter")}</button>
      <details class="advanced"><summary>${t(this.hass, "Advanced: edit all parameters as JSON")}</summary><label>${t(this.hass, "Preview parameter object")}<textarea data-all-json spellcheck="false" aria-label="${t(this.hass, "Preview parameter object")}">${esc(JSON.stringify(this.values, null, 2))}</textarea></label></details>
      <p class="error" role="alert" ${error ? "" : "hidden"}>${esc(error)}</p>
      <div class="actions"><button type="button" data-cancel>${t(this.hass, "Cancel")}</button><span class="right"><button type="submit" class="primary">${t(this.hass, "Apply preview values")}</button></span></div>
    </form></dialog>`;
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close(null);
    });
    const advanced = this.shadowRoot.querySelector("details.advanced");
    advanced?.querySelector("summary")?.addEventListener("click", (event) => {
      event.preventDefault();
      if (!advanced.open) {
        const parsed = this.readRows();
        if (!parsed.ok) {
          this.showError(parsed.reason);
          return;
        }
        this.shadowRoot.querySelector("[data-all-json]").value = JSON.stringify(
          parsed.value,
          null,
          2,
        );
        advanced.open = true;
        return;
      }
      try {
        const parsed = JSON.parse(
          this.shadowRoot.querySelector("[data-all-json]").value,
        );
        if (!this.validMap(parsed)) {
          this.showError("unsafe");
          return;
        }
        this.values = parsed;
        this.render();
        this.shadowRoot.querySelector("details.advanced summary")?.focus();
      } catch {
        this.showError("invalid-json");
      }
    });
    dialog.showModal();
    const initial = this.shadowRoot.querySelector("[data-name]");
    initial?.focus();
  }

  get missingName() {
    return this._missingName || null;
  }

  change(event) {
    const emptyCheckbox = event
      .composedPath()
      .find((node) => node?.matches?.("[data-allow-empty]"));
    if (emptyCheckbox) {
      this.allowEmptyMissing = emptyCheckbox.checked;
      return;
    }
    const typeSelect = event
      .composedPath()
      .find((node) => node?.matches?.("[data-type]"));
    if (typeSelect) {
      const row = typeSelect.closest("fieldset");
      const name = row.querySelector("[data-name]").value.trim();
      const previousName = Object.keys(this.values)[Number(row.dataset.row)];
      const previousType = valueType(this.values[previousName]);
      const nextType = typeSelect.value;
      typeSelect.value = previousType;
      const map = this.readRows();
      if (!map.ok) return;
      if (previousName !== name) delete map.value[previousName];
      typeSelect.value = nextType;
      map.value[name] = this.defaultForType(nextType);
      this.values = map.value;
      this.render();
      this.shadowRoot
        .querySelector(
          `[data-row="${[...this.shadowRoot.querySelectorAll("fieldset")].findIndex((item) => item.querySelector("[data-name]").value === name)}"] [data-value]`,
        )
        ?.focus();
      return;
    }
  }

  defaultForType(type) {
    return type === "number"
      ? 0
      : type === "boolean"
        ? false
        : type === "json"
          ? {}
          : "";
  }

  readRows(showError = true) {
    const result = Object.create(null);
    const invalid = (row, reason) => {
      if (showError) {
        this.setFieldError(row, reason);
        this.showError(reason);
      }
      return { ok: false, reason };
    };
    for (const row of this.shadowRoot.querySelectorAll("fieldset")) {
      const name = row.querySelector("[data-name]").value.trim();
      if (!name || forbiddenKeys.has(name)) return invalid(row, "invalid-name");
      if (Object.hasOwn(result, name)) return invalid(row, "duplicate-name");
      const type = row.querySelector("[data-type]").value;
      const input = row.querySelector("[data-value]");
      let value;
      if (type === "string") value = input.value;
      else if (type === "boolean") value = input.value === "true";
      else if (type === "number") {
        if (!input.value.trim()) return invalid(row, "invalid-number");
        value = Number(input.value);
        if (!Number.isFinite(value)) return invalid(row, "invalid-number");
      } else {
        try {
          value = JSON.parse(input.value);
        } catch {
          return invalid(row, "invalid-json");
        }
        if (value !== null && typeof value !== "object")
          return invalid(row, "invalid-json-type");
      }
      row.querySelectorAll("[aria-invalid], .field-error").forEach((node) => {
        node.removeAttribute("aria-invalid");
        if (node.classList.contains("field-error")) node.remove();
      });
      result[name] = value;
    }
    if (!safeValue(result))
      return invalid(this.shadowRoot.querySelector("fieldset"), "unsafe");
    return { ok: true, value: result };
  }

  setFieldError(row, reason) {
    if (!row) return;
    const control = row.querySelector(
      reason === "invalid-name" || reason === "duplicate-name"
        ? "[data-name]"
        : "[data-value]",
    );
    control?.setAttribute("aria-invalid", "true");
    let note = row.querySelector(".field-error");
    if (!note) {
      note = document.createElement("span");
      note.className = "field-error";
      note.setAttribute("role", "alert");
      row.append(note);
    }
    note.textContent = this.errorText(reason);
  }

  validMap(value) {
    return Boolean(
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value).every(
        (key) => key.trim() && !forbiddenKeys.has(key),
      ) &&
      safeValue(value),
    );
  }

  errorText(reason) {
    const messages = {
      "invalid-name":
        "Enter a parameter name without reserved prototype names.",
      "duplicate-name": "Parameter names must be unique.",
      "invalid-number": "Enter a finite number.",
      "invalid-json": "Enter valid JSON for the object or array value.",
      "invalid-json-type": "The JSON value must be an object, array or null.",
      unsafe: "Preview parameters must contain only finite JSON values.",
      "too-large": "Preview parameters are too large.",
      "missing-value":
        "Enter a value for the missing parameter before applying.",
    };
    return t(this.hass, messages[reason] || "Preview parameter is invalid.");
  }

  click(event) {
    const button = event
      .composedPath()
      .find((node) => node?.tagName === "BUTTON");
    if (!button) return;
    if (button.hasAttribute("data-cancel")) return this.close(null);
    if (button.hasAttribute("data-add")) {
      const parsed = this.readRows();
      if (!parsed.ok) return;
      this.values = parsed.value;
      let index = Object.keys(this.values).length + 1;
      while (Object.hasOwn(this.values, `parameter_${index}`)) index += 1;
      this.values[`parameter_${index}`] = "";
      this.render();
      this.shadowRoot
        .querySelector("fieldset:last-of-type [data-name]")
        ?.focus();
      return;
    }
    const remove = button.getAttribute("data-remove");
    if (remove !== null) {
      const row = button.closest("fieldset");
      const parent = row.parentNode;
      const next = row.nextSibling;
      row.remove();
      const parsed = this.readRows();
      if (!parsed.ok) {
        parent.insertBefore(row, next);
        return;
      }
      this.values = parsed.value;
      this.render();
      this.shadowRoot.querySelector("[data-add]").focus();
    }
  }

  apply() {
    const advanced = this.shadowRoot.querySelector("details.advanced");
    let map;
    if (advanced.open) {
      try {
        map = JSON.parse(
          this.shadowRoot.querySelector("[data-all-json]").value,
        );
      } catch {
        return this.showError("invalid-json");
      }
      if (!this.validMap(map)) return this.showError("unsafe");
    } else {
      const parsed = this.readRows();
      if (!parsed.ok) return this.showError(parsed.reason);
      map = parsed.value;
    }
    if (this.missingName && !Object.hasOwn(map, this.missingName)) {
      this.showError("missing-value");
      return;
    }
    if (
      this.missingName &&
      map[this.missingName] === "" &&
      !this.shadowRoot.querySelector("[data-allow-empty]")?.checked
    ) {
      const missingRow = [...this.shadowRoot.querySelectorAll("fieldset")].find(
        (row) =>
          row.querySelector("[data-name]").value.trim() === this.missingName,
      );
      this.setFieldError(missingRow, "missing-value");
      return this.showError("missing-value");
    }
    if (new TextEncoder().encode(JSON.stringify(map)).length > 65536)
      return this.showError("too-large");
    this.close(map);
  }

  showError(reason) {
    const node = this.shadowRoot.querySelector('[role="alert"]');
    node.textContent = this.errorText(reason);
    node.hidden = false;
  }

  close(value) {
    if (this.closed) return;
    this.closed = true;
    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog?.open) dialog.close();
    this.remove();
    this.resolvePromise?.(value);
    this.resolvePromise = null;
  }
}

customElements.define(
  "ble-esl-preview-parameters-dialog",
  PreviewParametersDialog,
);
