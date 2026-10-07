import { t, language } from "./i18n.js";
import { clone } from "./model.js";
const fields = [
  "color",
  "icon",
  "background",
  "text",
  "image",
  "font_size",
  "width",
  "height",
  "x",
  "y",
  "value",
  "min_value",
  "max_value",
  "align",
  "label",
  "show_label",
  "show_unit",
  "decimals",
  "image_fit",
  "visible",
];
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const focusSelectorFor = (element) => {
  if (!element) return null;
  if (element.id) return `#${CSS.escape(element.id)}`;
  const identity = [...element.attributes]
    .filter((attribute) => attribute.name.startsWith("data-"))
    .map((attribute) => `[${attribute.name}="${CSS.escape(attribute.value)}"]`)
    .join("");
  return identity ? `${element.tagName.toLowerCase()}${identity}` : null;
};
export class DynamicFields extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.sequence = 0;
  }
  open(owner) {
    this.owner = owner;
    this.opener = owner.shadowRoot.activeElement;
    this.hass = owner.hass;
    this.templates = clone(owner.draft.field_templates || {});
    this.field = Object.keys(this.templates)[0] || "color";
    this.render();
    this.shadowRoot.querySelector("dialog").showModal();
    this.preview();
  }
  close() {
    clearTimeout(this.timer);
    this.sequence++;
    this.remove();
    this.opener?.focus({ preventScroll: true });
  }
  render() {
    this.shadowRoot.innerHTML = `<style>:host{font:inherit;color:var(--primary-text-color)}dialog{padding:24px;width:min(850px,calc(100vw - 64px));border:0;border-radius:16px;color:inherit;background:var(--card-background-color,white)}dialog::backdrop{background:#0006}header,footer,.tools{display:flex;gap:12px;align-items:center}h2{flex:1;margin:0 0 12px}.body{display:grid;grid-template-columns:180px 1fr;gap:20px}.fields{display:flex;flex-direction:column;gap:6px;max-height:55vh;overflow:auto}button,input,select,textarea{font:inherit;color:inherit;background:inherit;border:1px solid var(--divider-color,#ccd4dc);border-radius:6px;padding:10px}button{cursor:pointer}.active{border-color:var(--primary-color,#16838b);color:var(--primary-color,#16838b)}textarea{box-sizing:border-box;width:100%;height:240px;font:14px/1.5 monospace;margin-top:12px;resize:vertical}.hint{font-size:12px;opacity:.75}pre{overflow:auto;white-space:pre-wrap;padding:12px;background:var(--secondary-background-color,#eee)}img{max-width:200px;max-height:100px;image-rendering:pixelated}.error{color:var(--error-color,#c33)}footer{justify-content:flex-end;margin-top:16px}@media(max-width:600px){.body{grid-template-columns:1fr}.fields{flex-direction:row;max-height:80px}.tools{flex-wrap:wrap}}</style><dialog aria-label="${t(this.hass, "Dynamic fields")}"><header><h2>${t(this.hass, "Dynamic fields")}</h2><button id="close" aria-label="${t(this.hass, "Close dynamic fields")}">×</button></header><div class="body"><aside class="fields">${fields
      .map(
        (field) =>
          `<button data-field="${field}" aria-pressed="${field === this.field}" class="${field === this.field ? "active" : ""}">${esc(
            t(
              this.hass,
              field.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase()),
            ),
          )}${this.templates[field] ? " ƒ" : ""}</button>`,
      )
      .join("")}</aside><section><div class="tools"><strong>${esc(
      t(
        this.hass,
        this.field.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase()),
      ),
    )}</strong><select id="insert" aria-label="${t(this.hass, "Insert template")}"><option value="">${t(this.hass, "＋ Insert template…")}</option><option value="state">${t(this.hass, "State value")}</option><option value="binary">${t(this.hass, "Binary condition")}</option><option value="numeric">${t(this.hass, "Numeric condition")}</option><option value="attribute">${t(this.hass, "Attribute")}</option><option value="entity">${t(this.hass, "Another HA entity")}</option></select><button id="remove">${t(this.hass, "Use static value")}</button></div><textarea id="template" aria-label="${t(this.hass, "Field template")}" spellcheck="false" placeholder="{{ 'red' if value | float(0) >= 20 else 'black' }}">${esc(this.templates[this.field] || "")}</textarea><p class="hint">${t(this.hass, "HA Jinja templates. Variables: value, entity, entity_id, attributes. states(), is_state(), state_attr(), now() and other HA template helpers are available.")}</p><strong>${t(this.hass, "Resolved value")}</strong><pre id="result">—</pre><div class="error" role="status"></div><img id="preview" alt="${t(this.hass, "Dynamic field pixel preview")}"></section></div><footer><button id="cancel">${t(this.hass, "Cancel")}</button><button id="apply">${t(this.hass, "Apply templates")}</button></footer></dialog>`;
    const root = this.shadowRoot;
    root.querySelector("dialog").addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
    root.querySelectorAll("[data-field]").forEach(
      (button) =>
        (button.onclick = () => {
          this.field = button.dataset.field;
          this.redraw();
          this.preview();
        }),
    );
    root.querySelector("#template").oninput = (event) => {
      if (event.target.value.trim())
        this.templates[this.field] = event.target.value;
      else delete this.templates[this.field];
      this.preview();
    };
    root.querySelector("#remove").onclick = () => {
      delete this.templates[this.field];
      this.redraw("#template");
      this.preview();
    };
    root.querySelector("#insert").onchange = (event) => {
      const source = {
        state: "{{ value }}",
        binary:
          "{{ 'mdi:washing-machine' if value == 'on' else 'mdi:washing-machine-off' }}",
        numeric: "{{ 'red' if value | float(0) >= 20 else 'black' }}",
        attribute: "{{ attributes.get('battery', 0) }}",
        entity: "{{ states('sensor.example') }}",
      }[event.target.value];
      if (source) {
        this.templates[this.field] = source;
        root.querySelector("#template").value = source;
        this.preview();
      }
    };
    root.querySelector("#apply").onclick = () => {
      this.owner.draft.field_templates = clone(this.templates);
      this.owner.queuePreview();
      this.close();
    };
    for (const id of ["close", "cancel"])
      root.querySelector("#" + id).onclick = () => this.close();
  }
  redraw(fallback = "#template") {
    const active = this.shadowRoot.activeElement,
      selector = focusSelectorFor(active),
      wasOpen = this.shadowRoot.querySelector("dialog")?.open;
    this.render();
    if (wasOpen) {
      this.shadowRoot.querySelector("dialog").showModal();
      (
        (selector && this.shadowRoot.querySelector(selector)) ||
        this.shadowRoot.querySelector(fallback)
      )?.focus({
        preventScroll: true,
      });
    }
  }
  updateHass(hass) {
    const changedLanguage = language(this.hass) !== language(hass);
    const ids = [
      this.owner.draft.entity_id || this.owner.panel.sampleEntity,
      ...(this.templateEntities || []),
    ];
    const changed = ids.some((id) => this.hass.states[id] !== hass.states[id]);
    this.hass = hass;
    if (changedLanguage) this.redraw();
    if (changed) this.preview();
  }
  preview() {
    clearTimeout(this.timer);
    const seq = ++this.sequence;
    this.timer = setTimeout(async () => {
      if (this.pending) {
        this.queued = true;
        return;
      }
      this.pending = true;
      try {
        const owner = this.owner,
          draft = clone(owner.draft);
        draft.field_templates = clone(this.templates);
        draft.x = draft.y = 0;
        const sample =
          draft.entity_id ||
          owner.panel.sampleEntity ||
          owner.panel.entities()[0]?.entity_id;
        const result = await owner.panel.api("preview_template", {
          entity_id: sample,
          template: {
            width: Math.max(16, draft.width),
            height: Math.max(16, draft.height),
            document: { version: 1, elements: [draft] },
          },
        });
        if (seq === this.sequence && this.isConnected) {
          this.templateEntities = [
            ...new Set(Object.values(result.layers._dependencies || {}).flat()),
          ];
          this.shadowRoot.querySelector("#result").textContent = JSON.stringify(
            result.layers._values?.[draft.id]?.[this.field] ??
              draft[this.field],
            null,
            2,
          );
          this.shadowRoot.querySelector("#preview").src =
            result.layers[draft.id];
          this.shadowRoot.querySelector("[role=status]").textContent = "";
        }
      } catch (error) {
        // An older request failing must not overwrite a newer one's result.
        if (seq === this.sequence && this.isConnected)
          this.shadowRoot.querySelector("[role=status]").textContent =
            error.message;
      } finally {
        this.pending = false;
        if (this.queued) {
          this.queued = false;
          this.preview();
        }
      }
    }, 300);
  }
}
if (!customElements.get("ble-esl-dynamic-fields"))
  customElements.define("ble-esl-dynamic-fields", DynamicFields);
