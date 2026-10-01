import "./dynamic-fields.js";
import { clone, newElement } from "./model.js";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const components = [
  ["text", "Text / value", "mdi:format-text"],
  ["icon", "Icon", "mdi:star-outline"],
  ["conditional_icon", "Conditional icon", "mdi:state-machine"],
  ["image", "Image", "mdi:image-outline"],
  ["rectangle", "Shape", "mdi:shape-outline"],
  ["progress_bar", "Progress bar", "mdi:progress-upload"],
  ["gauge", "Gauge", "mdi:gauge"],
];
export class ComponentEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.sequence = 0;
  }
  open(panel, element) {
    this.panel = panel;
    this.hass = panel.hass;
    this.original = element;
    this.draft = element ? clone(element) : newElement("text", panel.tag);
    this.draft.background = "transparent";
    this.draft.data_field ||= "";
    this.draft.icon_rules ||= [];
    this.render();
    this.shadowRoot.querySelector("dialog").showModal();
    this.shadowRoot
      .querySelector("dialog")
      .addEventListener("cancel", (event) => {
        event.preventDefault();
        this.close();
      });
    this.queuePreview();
  }
  close() {
    clearTimeout(this.timer);
    this.sequence++;
    this.remove();
  }
  picker(value, label, target) {
    const picker = document.createElement("ha-icon-picker");
    picker.value = value === "{{icon}}" ? "" : value;
    picker.label = label;
    picker.placeholder = "mdi:help-circle-outline";
    picker.hass = this.hass;
    picker.addEventListener("value-changed", (event) => {
      event.stopPropagation();
      target(event.detail.value || "{{icon}}");
      this.queuePreview();
    });
    return picker;
  }
  async ensureIcons() {
    if (!customElements.get("ha-icon-picker")) {
      const form = document.createElement("ha-form");
      form.hass = this.hass;
      form.schema = [{ name: "icon", selector: { icon: {} } }];
      form.data = { icon: "" };
      form.hidden = true;
      this.shadowRoot.append(form);
      // HA's form lazily registers its standard icon selector and picker.
      await customElements.whenDefined("ha-icon-picker");
      form.remove();
    }
    if (this.isConnected) this.mountIcons();
  }
  mountIcons() {
    const draft = this.draft;
    this.shadowRoot
      .querySelector("#fallback-icon")
      ?.replaceChildren(
        this.picker(
          draft.icon,
          draft.type === "conditional_icon"
            ? "Fallback icon (blank = HA)"
            : "Icon (blank = HA)",
          (value) => (draft.icon = value),
        ),
      );
    this.shadowRoot.querySelectorAll("[data-rule-icon]").forEach((node) => {
      const rule = draft.icon_rules[Number(node.dataset.ruleIcon)];
      node.replaceChildren(
        this.picker(rule.icon, "Rule icon", (value) => (rule.icon = value)),
      );
    });
  }
  render() {
    const d = this.draft;
    const numeric = ["gauge", "progress_bar"].includes(d.type);
    const conditional = d.type === "conditional_icon";
    this.shadowRoot.innerHTML = `<style>:host{font-family:var(--primary-font-family,Roboto,Arial);color:var(--primary-text-color)}dialog{width:min(960px,calc(100vw - 40px));max-height:90vh;padding:0;border:0;border-radius:16px;background:var(--card-background-color,white);color:inherit;box-shadow:0 12px 70px #0005}dialog::backdrop{background:#0006}header,footer{display:flex;align-items:center;gap:12px;padding:16px 24px}header h2{margin:0;flex:1}button,input,select,textarea{font:inherit}button{padding:10px;border:1px solid var(--divider-color,#ccd4dc);border-radius:8px;background:var(--card-background-color,white);color:inherit;cursor:pointer}button.active,.primary{border-color:var(--primary-color,#16838b);color:var(--primary-color,#16838b)}.content{padding:0 24px 20px;display:grid;grid-template-columns:minmax(0,1.2fr) minmax(180px,1fr);gap:24px}.types{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;grid-column:1/-1}.types button{display:flex;gap:6px;align-items:center;justify-content:center}.controls{display:flex;flex-direction:column;gap:14px}label{display:flex;flex-direction:column;gap:6px}input,select,textarea{box-sizing:border-box;width:100%;padding:10px;border:1px solid var(--divider-color,#ccd4dc);border-radius:6px;background:inherit;color:inherit}.pair{display:flex;gap:8px}.pair>*{flex:1;min-width:0}.preview{position:sticky;top:0;align-self:start;min-height:220px;display:flex;flex-direction:column;gap:12px}.pixels{height:240px;display:flex;align-items:center;justify-content:center;background:repeating-conic-gradient(#e5e9ec 0% 25%,transparent 0% 50%) 0/16px 16px;border-radius:8px}.pixels img{width:100%;height:100%;object-fit:contain;image-rendering:pixelated}.state{padding:12px;border:1px solid var(--divider-color,#ccd4dc);border-radius:8px;display:flex;gap:10px;align-items:center}.rules{display:flex;flex-direction:column;gap:10px}.rule{padding:12px;border:1px solid var(--divider-color,#ccd4dc);border-radius:8px}.rule .pair{align-items:end}.remove{flex:0!important}.hint{font-size:12px;opacity:.7}.error{color:var(--error-color,#c33)}footer{justify-content:flex-end;border-top:1px solid var(--divider-color,#ddd)}ha-icon-picker,ha-entity-picker{display:block;min-width:0} @media(max-width:650px){.content{grid-template-columns:1fr}.types{grid-template-columns:repeat(2,1fr)}.preview{position:static}.pixels{height:160px}}</style>
      <dialog aria-label="Component editor"><header><h2>${this.original ? "Edit component" : "Add component"}</h2><button id="close" aria-label="Close component editor">×</button></header><div class="content"><div class="types">${components.map(([type, name, icon]) => `<button data-type="${type}" class="${d.type === type ? "active" : ""}"><ha-icon icon="${icon}"></ha-icon>${name}</button>`).join("")}</div><section class="controls"><button id="dynamic">ƒ Dynamic fields…</button><ha-entity-picker id="source"></ha-entity-picker><label>Data<select id="field" aria-label="Component data"><option value="">${this.panel.mode === "template" ? "Static / template tokens" : "Static content"}</option>${["state", "name", "unit", "icon", "attribute"].map((field) => `<option value="${field}" ${d.data_field === field ? "selected" : ""}>${field === "name" ? "Entity name" : field === "state" ? "State value" : field === "attribute" ? "Attribute" : field[0].toUpperCase() + field.slice(1)}</option>`).join("")}</select></label>${
        d.data_field === "attribute"
          ? `<label>Attribute<select id="attribute" aria-label="Component attribute">${Object.keys(
              this.hass.states[d.entity_id || this.panel.sampleEntity]
                ?.attributes || {},
            )
              .map(
                (name) =>
                  `<option ${d.attribute === name ? "selected" : ""}>${esc(name)}</option>`,
              )
              .join("")}</select></label>`
          : ""
      }
      ${d.type === "text" ? `<label>Text<textarea id="text" aria-label="Component text" ${d.data_field ? "disabled" : ""}>${esc(d.text)}</textarea></label><div class="pair"><label>Font size<input id="font_size" aria-label="Component font size" type="number" value="${d.font_size}"></label><label>Decimals<input id="decimals" aria-label="Component decimals" type="number" min="0" max="6" placeholder="Automatic" value="${d.decimals ?? ""}"></label></div>` : ""}
      ${["icon", "conditional_icon"].includes(d.type) ? '<div id="fallback-icon"></div>' : ""}
      ${conditional ? `<div class="rules"><strong>State → icon</strong><span class="hint">First match wins. Range includes the lower bound and excludes the upper bound. Blank bound = no limit.</span>${d.icon_rules.map((rule, index) => `<div class="rule"><div class="pair">${rule.kind === "range" ? `<label>From ≥<input type="number" step="any" data-rule="${index}" data-key="min" aria-label="Range ${index + 1} minimum" value="${rule.min ?? ""}"></label><label>To &lt;<input type="number" step="any" data-rule="${index}" data-key="max" aria-label="Range ${index + 1} maximum" value="${rule.max ?? ""}"></label>` : `<label>State<input data-rule="${index}" data-key="state" aria-label="Rule ${index + 1} state" value="${esc(rule.state)}"></label>`}<button class="remove" data-remove="${index}" aria-label="Remove rule ${index + 1}">×</button></div><div data-rule-icon="${index}"></div></div>`).join("")}<div class="pair"><button id="add-state">＋ State</button><button id="add-range">＋ Range</button></div></div>` : ""}
      ${numeric ? `<div class="pair"><label>Minimum<input id="min_value" aria-label="Component minimum" type="number" value="${d.min_value ?? 0}"></label><label>Maximum<input id="max_value" aria-label="Component maximum" type="number" value="${d.max_value ?? 100}"></label></div>${!d.data_field ? `<label>Value<input id="value" type="number" value="${d.value ?? 0}"></label>` : ""}` : ""}
      ${["rectangle", "rounded_rectangle", "ellipse", "triangle", "line"].includes(d.type) ? `<label>Shape<select id="shape" aria-label="Component shape">${["rectangle", "rounded_rectangle", "ellipse", "triangle", "line"].map((type) => `<option value="${type}" ${type === d.type ? "selected" : ""}>${type.replaceAll("_", " ")}</option>`).join("")}</select></label>` : ""}
      ${d.type === "image" ? '<label>Image<input id="upload" type="file" accept="image/*"></label>' : ""}
      <div class="pair"><label>Width<input id="width" aria-label="Component width" type="number" min="1" value="${d.width}"></label><label>Height<input id="height" aria-label="Component height" type="number" min="1" value="${d.height}"></label></div></section><section class="preview"><strong>Live preview</strong><div class="state" id="current-state"></div><div class="pixels"><img id="pixels" alt="Component pixel preview"></div><div class="error" role="status"></div></section></div><footer><button id="cancel">Cancel</button><button id="apply" class="primary">${this.original ? "Apply" : "Add to display"}</button></footer></dialog>`;
    const root = this.shadowRoot;
    root.querySelector("#dynamic").onclick = () => {
      const modal = document.createElement("ble-esl-dynamic-fields");
      this.shadowRoot.append(modal);
      modal.open(this);
    };
    this.bindSource(root.querySelector("#source"));
    root.querySelectorAll("[data-type]").forEach(
      (button) =>
        (button.onclick = () => {
          d.type = button.dataset.type;
          if (["icon", "conditional_icon"].includes(d.type)) {
            d.width = d.height = 32;
            d.icon = "{{icon}}";
          }
          if (d.type === "conditional_icon") {
            d.data_field = "state";
          }
          if (d.type === "gauge") {
            d.width = d.height = 80;
          }
          this.redraw();
        }),
    );
    root.querySelector("#shape")?.addEventListener("change", (event) => {
      d.type = event.target.value;
      this.redraw();
    });
    root.querySelector("#field").onchange = (event) => {
      d.data_field = event.target.value;
      if (d.data_field === "attribute")
        d.attribute =
          Object.keys(
            this.hass.states[d.entity_id || this.panel.sampleEntity]
              ?.attributes || {},
          )[0] || "";
      this.redraw();
    };
    root.querySelector("#attribute")?.addEventListener("change", (event) => {
      d.attribute = event.target.value;
      this.queuePreview();
    });
    root.querySelectorAll("input,textarea").forEach((input) => {
      if (input.type === "file" || input.dataset.rule) return;
      input.oninput = () => {
        if (input.id === "decimals" && input.value === "") delete d.decimals;
        else
          d[input.id] =
            input.type === "number" ? Number(input.value) : input.value;
        this.queuePreview();
      };
    });
    root.querySelectorAll("[data-rule]").forEach(
      (input) =>
        (input.oninput = () => {
          const rule = d.icon_rules[Number(input.dataset.rule)];
          const key = input.dataset.key;
          if (key !== "state" && input.value === "") delete rule[key];
          else rule[key] = key === "state" ? input.value : Number(input.value);
          this.queuePreview();
        }),
    );
    root.querySelectorAll("[data-remove]").forEach(
      (button) =>
        (button.onclick = () => {
          d.icon_rules.splice(Number(button.dataset.remove), 1);
          this.redraw();
        }),
    );
    root.querySelector("#add-state")?.addEventListener("click", () => {
      d.icon_rules.push({ kind: "state", state: "", icon: "{{icon}}" });
      this.redraw();
    });
    root.querySelector("#add-range")?.addEventListener("click", () => {
      d.icon_rules.push({ kind: "range", icon: "{{icon}}" });
      this.redraw();
    });
    root.querySelector("#upload")?.addEventListener("change", async (event) => {
      const reader = new FileReader();
      reader.onload = () => {
        d.image = reader.result;
        this.queuePreview();
      };
      reader.readAsDataURL(event.target.files[0]);
    });
    for (const id of ["cancel", "close"])
      root.querySelector("#" + id).onclick = () => this.close();
    root.querySelector("#apply").onclick = () => {
      if (d.type === "sensor" && !d.entity_id) {
        root.querySelector("[role=status]").textContent =
          "Choose an entity for the sensor tile.";
        return;
      }
      this.panel.checkpoint();
      if (this.original) Object.assign(this.original, clone(d));
      else this.panel.document.elements.push(clone(d));
      this.panel.selected = d.id;
      this.panel.edited();
      this.close();
    };
    this.ensureIcons();
    this.currentState();
  }
  bindSource(source) {
    const d = this.draft;
    const conditional = d.type === "conditional_icon";
    source.hass = this.hass;
    source.label =
      this.panel.mode === "template"
        ? "Data source (blank = sample sensor)"
        : "Data source";
    source.allowCustomEntity = false;
    source.value = d.entity_id || "";
    source.addEventListener("value-changed", (event) => {
      d.entity_id = event.detail.value || "";
      if (d.entity_id) {
        d.data_field ||= d.type === "icon" ? "icon" : "state";
        const state = this.hass.states[d.entity_id];
        if (conditional && !d.icon_rules.length) {
          d.icon_rules =
            this.panel.outputType(state) === "binary"
              ? [
                  { kind: "state", state: "on", icon: "{{icon}}" },
                  { kind: "state", state: "off", icon: "{{icon}}" },
                ]
              : [];
        }
      }
      this.redraw();
    });
  }
  // HA defined ha-entity-picker after this dialog was built: swap in a fresh
  // picker without render(), which would drop focus and a nested modal.
  upgradeSource() {
    const old = this.shadowRoot.querySelector("#source");
    if (!old) return;
    const fresh = document.createElement("ha-entity-picker");
    for (const { name, value } of old.attributes)
      fresh.setAttribute(name, value);
    old.replaceWith(fresh);
    this.bindSource(fresh);
  }
  redraw() {
    const dialog = this.shadowRoot.querySelector("dialog");
    const wasOpen = dialog.open;
    this.render();
    if (wasOpen) this.shadowRoot.querySelector("dialog").showModal();
    this.queuePreview();
  }
  currentState() {
    const state =
      this.hass.states[this.draft.entity_id || this.panel.sampleEntity];
    const node = this.shadowRoot.querySelector("#current-state");
    node.innerHTML = state
      ? `<ha-state-icon></ha-state-icon><span>${esc(this.panel.entityName(state))}<br><strong>${esc(this.hass.formatEntityState?.(state) || state.state)}</strong></span>`
      : "Static content";
    const icon = node.querySelector("ha-state-icon");
    if (icon) {
      icon.hass = this.hass;
      icon.stateObj = state;
    }
  }
  updateHass(hass) {
    const id = this.draft.entity_id || this.panel.sampleEntity;
    const changed = [id, ...(this.templateEntities || [])].some(
      (id) => this.hass.states[id] !== hass.states[id],
    );
    this.hass = hass;
    const picker = this.shadowRoot.querySelector("#source");
    if (picker) picker.hass = hass;
    this.currentState();
    this.shadowRoot.querySelector("ble-esl-dynamic-fields")?.updateHass(hass);
    if (changed) this.queuePreview();
  }
  queuePreview() {
    clearTimeout(this.timer);
    const seq = ++this.sequence;
    this.timer = setTimeout(async () => {
      if (this.pending) {
        this.queued = true;
        return;
      }
      this.pending = true;
      try {
        const sample =
          this.draft.entity_id ||
          this.panel.sampleEntity ||
          this.panel.entities()[0]?.entity_id;
        if (!sample) return;
        const draft = clone(this.draft);
        draft.x = draft.y = 0;
        const result = await this.panel.api("preview_template", {
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
          this.shadowRoot.querySelector("#pixels").src =
            result.layers[draft.id];
          this.shadowRoot.querySelector("[role=status]").textContent = "";
        }
      } catch (error) {
        if (this.isConnected)
          this.shadowRoot.querySelector("[role=status]").textContent =
            error.message;
      } finally {
        this.pending = false;
        if (this.queued) {
          this.queued = false;
          this.queuePreview();
        }
      }
    }, 250);
  }
}
customElements.define("ble-esl-component-editor", ComponentEditor);
