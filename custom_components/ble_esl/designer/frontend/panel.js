import "./component-editor.js";
import "./yaml-dialog.js";
import "./import-dialog.js";
import {
  applySpecInput,
  newSpecElement,
  specEditorHtml,
  specLabel,
} from "./spec-editor.js";
import {
  clone,
  createId,
  palette,
  emptyDocument,
  clampBox,
  onLabel,
  newElement,
  jpegOrientation,
} from "./model.js";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const icon = (name) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${name === "menu" ? '<path d="M4 6h16M4 12h16M4 18h16"/>' : '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>'}</svg>`;
// Settings the inspector leaves unset until asked: blank means imagespec's default.
const optionalProperties = new Set([
  "valign",
  "fit",
  "max_lines",
  "min_font_size",
  "padding",
  "line_spacing",
  "font",
  "line_width",
  "radius",
  "stroke_width",
  "rotate",
  "direction",
  "thickness",
]);
// Whole-number ranges the schema accepts, kept when a value is typed.
const propertyRanges = {
  max_lines: [1, 20],
  min_font_size: [1, 200],
  padding: [0, 100],
  line_spacing: [0, 100],
  line_width: [1, 20],
  radius: [0, 200],
  stroke_width: [0, 20],
  thickness: [1, 100],
};
const shapeTypes = [
  "rectangle",
  "rounded_rectangle",
  "ellipse",
  "triangle",
  "line",
];
const toolIcon = (name) =>
  `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${
    {
      duplicate:
        '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
      back: '<path d="m3 8 9-5 9 5-9 5-9-5Zm0 5 9 5 9-5M3 18l9 5 9-5"/>',
      front: '<path d="m3 16 9 5 9-5-9-5-9 5Zm0-5 9-5 9 5M3 6l9-5 9 5"/>',
      center: '<path d="M12 2v20M3 6h18M6 12h12M3 18h18"/>',
      text: '<path d="M4 4h16M12 4v16M8 20h8"/>',
      shape: '<rect x="4" y="4" width="16" height="16" rx="2"/>',
      image:
        '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="2"/><path d="m3 18 6-6 4 4 3-4 5 6"/>',
      icon: '<path d="m12 3 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z"/>',
      reload: '<path d="M20 7v5h-5M20 12a8 8 0 1 0-2 6"/>',
      save: '<path d="M4 3h13l4 4v14H3V3h1M7 3v6h9V3M7 21v-8h10v8"/>',
      preview:
        '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
      send: '<path d="m7 7 10 10-5 4V3l5 4L7 17"/>',
      undo: '<path d="M8 4 3 9l5 5M3 9h10a7 7 0 0 1 0 14"/>',
      redo: '<path d="m16 4 5 5-5 5M21 9H11a7 7 0 0 0 0 14"/>',
      eyeoff:
        '<path d="M3 3l18 18M10.6 6.2A10 10 0 0 1 12 5c6 0 10 7 10 7a17 17 0 0 1-3.2 4M6.1 7.1A17 17 0 0 0 2 12s4 7 10 7a9.7 9.7 0 0 0 4-.9"/>',
      up: '<path d="m6 15 6-6 6 6"/>',
      down: '<path d="m6 9 6 6 6-6"/>',
    }[name]
  }</svg>`;
const iconFont = new FontFace(
  "LabelMDI",
  "url(/ble_esl_designer_fonts/materialdesignicons-webfont.ttf)",
)
  .load()
  .then((font) => document.fonts.add(font));
const textFont = new FontFace(
  "LabelText",
  "url(/ble_esl_designer_fonts/NotoSansKR-Regular.ttf)",
)
  .load()
  .then((font) => document.fonts.add(font));
const style = `
.mdi{font-family:LabelMDI;line-height:1;display:inline-block;font-weight:normal;font-style:normal}.icon-popover{margin-top:8px}.icon-popover .icon-picker{margin-top:8px}.icon-choice{display:flex;align-items:center;gap:8px;width:100%;text-align:left}.toolbar .icon-button{border:1px solid var(--divider-color,#cbd3de)}:host{display:block;color:var(--primary-text-color,#18232f);background:var(--primary-background-color,#f5f7fa);font:14px system-ui;height:100%;overflow:auto}*{box-sizing:border-box}header{display:flex;align-items:center;gap:14px;box-sizing:border-box;min-height:var(--header-height,56px);padding:0 12px 0 24px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#e0e5eb)}h1{font-size:20px;font-weight:400;margin:0}header span{color:var(--secondary-text-color,#637083)}button,input,select,textarea{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px}button{cursor:pointer}button:hover{border-color:#257d86}button:disabled{opacity:.45;cursor:default}button.primary{background:#166d75;color:white;border-color:#166d75}button:focus-visible,input:focus-visible,select:focus-visible,.el:focus-visible{outline:2px solid #167c88;outline-offset:2px}.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:14px 24px}.toolbar select{max-width:360px}.editor-bar{display:flex;align-items:center;gap:12px;padding:0 24px 12px}.editor-bar .spacer{flex:1}.icon-button{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;padding:7px;border:0;background:transparent}.icon-button[aria-expanded="true"]{background:var(--secondary-background-color,#e9eff2)}.icon-button.danger:hover{color:#c33;background:#c331}.context-menu{position:fixed;z-index:1000;width:220px;padding:6px;background:var(--card-background-color,white);box-shadow:0 5px 24px #0003;border:1px solid var(--divider-color,#ddd);border-radius:8px}.context-menu button{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:0}.context-menu kbd{margin-left:auto}.panel-heading{display:flex;align-items:center;gap:8px;margin-bottom:14px}.panel-heading h2{flex:1;margin:0}.delete-handle{position:absolute;right:0;top:-24px;width:24px;height:24px;display:flex;align-items:center;justify-content:center;padding:2px;border:1px solid #16838c;color:#b33;background:var(--card-background-color,white);z-index:5;border-radius:4px}.delete-handle svg{width:18px;height:18px}.context-menu kbd{float:right;font-size:11px;color:var(--secondary-text-color,#637083)}.template-controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:0 24px 14px}.template-controls input[type="number"]{width:75px}.tabs{display:flex;gap:4px;margin-left:auto}.tabs button[aria-pressed="true"]{background:#166d75;color:white}.tile-icon{position:absolute;left:4px;top:10px;width:36px;height:36px;display:flex;align-items:center;justify-content:center}.tile-copy{margin-left:48px;padding:6px 0}.tile-copy .value{font-size:18px}.el ha-icon{--mdc-icon-size:32px}.el.icon-content ha-icon{--mdc-icon-size:inherit}.state-rules{margin:0}.template-note{margin:0 24px 12px}.picker{display:flex;gap:5px;flex-wrap:wrap}.swatch{width:28px;height:28px;padding:0;background:var(--swatch);border:1px solid #888;border-radius:50%}.swatch[aria-pressed="true"]{outline:2px solid #16838c;outline-offset:2px}.align-button{width:32px;height:32px;padding:5px}.align-button[aria-pressed="true"]{background:#16838c22;border-color:#16838c}.align-button svg{width:20px;height:20px}.icon-picker{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;max-height:200px;overflow:auto}.icon-picker button{padding:6px}.icon-picker ha-icon{--mdc-icon-size:24px}.state-rules input{width:100%}.muted.help{display:none}.workspace{display:grid;grid-template-columns:240px minmax(320px,1fr) 260px;gap:18px;padding:0 24px 24px}.workspace.library-closed{grid-template-columns:minmax(0,1fr) 260px}.workspace.inspector-closed{grid-template-columns:240px minmax(0,1fr)}.workspace.library-closed.inspector-closed{grid-template-columns:minmax(0,1fr)}.workspace.library-closed .library,.workspace.inspector-closed .inspector{display:none}.card{min-width:0;background:var(--card-background-color,white);border:1px solid var(--divider-color,#dfe5eb);border-radius:10px;padding:16px}h2{font-size:15px;margin:0 0 14px}p{line-height:1.5}.muted{color:var(--secondary-text-color,#637083);font-size:12px}.entity-preview{margin:12px 0 20px}.entity-state{display:flex;align-items:center;gap:10px;padding:10px;border:1px solid var(--divider-color,#ddd);border-radius:8px}.entity-state .state-copy{flex:1;min-width:0}.entity-state .state-name{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.entity-state .state-value{font-size:18px;margin-top:4px}.entity-state ha-state-icon{--mdc-icon-size:28px}.entity-state button{flex:none}ha-entity-picker{display:block;width:100%;margin-bottom:12px}.entity{display:block;text-align:left;width:100%;margin:5px 0}.entity small{display:block;color:var(--secondary-text-color,#637083);font-size:11px;overflow:hidden;text-overflow:ellipsis}.entity[draggable]{cursor:grab}.tools{display:flex;flex-wrap:wrap;gap:6px}.canvas-wrap{min-width:0;overflow:auto;height:420px;min-height:0;display:flex;align-items:center;justify-content:flex-start;background:repeating-conic-gradient(var(--secondary-background-color,#edf0f4) 0% 25%,var(--primary-background-color,#f6f8fa) 0% 50%) 50%/16px 16px;border-radius:6px;padding:30px}.stage-space{margin:auto;flex:none;position:relative}.stage{position:relative;transform-origin:top left;background:white;color:black;box-shadow:0 8px 24px #15293825;outline:1px solid #c5ced9;touch-action:none}.el{position:absolute;overflow:visible;cursor:move;outline:1px dashed transparent;touch-action:none;user-select:none}.el{pointer-events:none}.el .content{pointer-events:none}.hit-area{position:absolute;pointer-events:auto}.el:hover .hit-area{outline:1px dashed #1c8990}.el.editing .content{pointer-events:auto}.el.editing .hit-area{pointer-events:none}.el.selected{outline:1px solid #16838c}.el .content{height:100%;overflow:hidden;font-family:LabelText, sans-serif}.el.editing .content{visibility:visible!important;-webkit-user-select:text;user-select:text;cursor:text;white-space:pre-wrap;outline:0}.el.rendered .content{visibility:hidden}.layer-preview{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;image-rendering:pixelated}.el.editing .layer-preview,.stage.exact-mode .layer-preview{display:none}.label{font-size:12px;height:18px;white-space:nowrap;overflow:hidden}.value{white-space:nowrap;overflow:hidden}.handle{position:absolute;right:-3px;bottom:-3px;width:6px;height:6px;background:#16838c;cursor:nwse-resize;z-index:3}.exact{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;image-rendering:pixelated}.stage.exact-mode .content{visibility:hidden}.stage.exact-mode .el{background:transparent!important}.stage.exact-mode .el.selected{z-index:100}.status{min-height:24px;padding:0 24px 12px;color:var(--secondary-text-color,#637083)}.error{color:#c33}.props{display:grid;grid-template-columns:1fr 1fr;gap:9px}.props label{font-size:12px;display:flex;flex-direction:column;gap:5px}.props label.check{flex-direction:row;align-items:center}.props .wide{grid-column:1/-1}.props input,.props select,.props textarea{width:100%;min-width:0}.check{display:flex;align-items:center;gap:7px;margin:12px 0}.check input{width:auto}.layers{margin-top:16px;max-height:260px;overflow:auto}.layer-row{display:flex;align-items:center;gap:4px;margin:4px 0}.layer-row .layer{flex:1;min-width:0;margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.layer-row .icon-button{flex:none;width:32px;height:32px;padding:4px}.layer-row .icon-button svg{width:18px;height:18px}.layer{display:block;width:100%;text-align:left;margin:4px 0}.layer.active{border-color:#16838c}.side-column{display:flex;flex-direction:column;gap:18px}.side-column .layers{margin-top:0}.footer-tools{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}@media(max-width:1050px){.workspace{grid-template-columns:200px 1fr}.inspector{grid-column:1/-1}.props{grid-template-columns:repeat(4,1fr)}}@media(max-width:650px){.workspace.library-closed,.workspace.inspector-closed,.workspace.library-closed.inspector-closed{grid-template-columns:minmax(0,1fr)}.toolbar,.editor-bar,.template-controls{padding:12px}header{flex-wrap:wrap;padding:4px 12px}header span{display:none}.workspace{padding:0 12px 12px;grid-template-columns:minmax(0,1fr)}.library,.inspector{grid-column:auto}.entities{height:150px}.canvas-wrap{height:300px}.props{grid-template-columns:1fr 1fr}}
`;

export class BleEslDesigner extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.tags = [];
    this.document = emptyDocument();
    this.selected = null;
    this.undoStack = [];
    this.redoStack = [];
    this.zoom = 1;
    this.zoomMode = "fit";
    this.resizeObserver = new ResizeObserver(() => {
      this.fitPreview();
      this.stickyOffsets();
    });
    this.search = "";
    this.libraryEntity = "";
    this.status = "";
    this.preview = null;
    this.layerPreviews = {};
    this.dirty = false;
    this.busy = false;
    this.previewSequence = 0;
    this.pendingUploads = new Set();
    this.drafts = new Map();
    this.libraryOpen = true;
    this.inspectorOpen = true;
    this.templates = {};
    this.icons = {};
    this.templateDrafts = new Map();
    this.sampleEntity = "";
    this.mode = "display";
    this.templateKey = "output:numeric";
    this.shadowRoot.addEventListener("contextmenu", (event) =>
      this.contextMenu(event),
    );
    this.shadowRoot.addEventListener("pointerdown", (event) => {
      if (!event.target.closest(".context-menu")) this.closeContextMenu();
    });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
    this.shadowRoot.addEventListener("change", (event) => this.change(event));
    this.shadowRoot.addEventListener("input", (event) => this.input(event));
    this.shadowRoot.addEventListener("focusout", (event) => {
      this.typingProperty = null;
      if (event.target.dataset.editText) this.finishTextEdit();
    });
    this.shadowRoot.addEventListener("keydown", (event) => this.key(event));
    this.shadowRoot.addEventListener("pointerdown", (event) =>
      this.pointer(event),
    );
    this.shadowRoot.addEventListener("dragstart", (event) => {
      const button = event.target.closest("[data-entity]");
      if (button)
        event.dataTransfer.setData("text/plain", button.dataset.entity);
    });
    this.shadowRoot.addEventListener("dragover", (event) => {
      if (event.target.closest(".stage")) event.preventDefault();
    });
    this.shadowRoot.addEventListener("drop", (event) => this.drop(event));
  }
  set panel(value) {
    this._panelInfo = value;
    if (this.started) this.render();
  }
  set hass(value) {
    const previous = this._hass;
    this._hass = value;
    this.renderEntityPreview();
    this.shadowRoot
      .querySelector("ble-esl-component-editor")
      ?.updateHass(value);
    this.shadowRoot.querySelectorAll("ha-entity-picker").forEach((picker) => {
      picker.hass = value;
    });
    if (this.isConnected && !this.started) this.boot();
    else if (
      this.tag &&
      !this.gesture &&
      ((this.templateEntities || []).some(
        (id) => previous?.states[id] !== value.states[id],
      ) ||
        (this.mode === "template" &&
          previous?.states[this.sampleEntity] !==
            value.states[this.sampleEntity]) ||
        this.document.elements.some(
          (element) =>
            element.entity_id &&
            previous?.states[element.entity_id] !==
              value.states[element.entity_id],
        ))
    ) {
      this.drawStage();
      this.queuePreview();
    }
  }
  get hass() {
    return this._hass;
  }
  connectedCallback() {
    this.beforeUnload = (event) => {
      // Work set aside by switching between Display and Sensor templates counts.
      if (
        this.dirty ||
        this.drafts.size ||
        (this.mode === "template" && this.displaySession?.dirty) ||
        [...this.templateDrafts].some(
          ([key, draft]) =>
            draft.dirty &&
            !(this.mode === "template" && key === this.templateKey),
        )
      )
        event.preventDefault();
    };
    window.addEventListener("beforeunload", this.beforeUnload);
    this.render();
    if (this.hass && !this.started) this.boot();
  }
  disconnectedCallback() {
    window.removeEventListener("beforeunload", this.beforeUnload);
    clearTimeout(this.previewTimer);
    this.previewSequence++;
    this.gestureCancel?.();
    this.gesture = null;
    this.resizeObserver.disconnect();
  }
  async boot() {
    this.started = true;
    try {
      // The tag list must not wait for HA's lazily loaded entity picker:
      // in Safari the card helpers that load it may never settle.
      if (!customElements.get("ha-entity-picker") && !this.pickerPending) {
        // Once per panel: boot() runs again on "Refresh tags".
        this.pickerPending = true;
        loadEntityPicker();
        customElements.whenDefined("ha-entity-picker").then(() => {
          this.pickerPending = false;
          if (this.isConnected) this.upgradeEntityPickers();
        });
      }
      await Promise.all([iconFont, textFont]);
      this.icons = await fetch(new URL("./icons.json", import.meta.url)).then(
        (response) => response.json(),
      );
      this.templates = await this.api("templates");
      this.specs = await this.api("specs");
      this.tags = await this.api("list");
      this.mode = "display";
      // Stay on the tag being edited: load() files an unsaved design under
      // the tag it is leaving, so this.tag must still be that one.
      const tag =
        this.tags.find((item) => item.entry_id === this.tag?.entry_id) ||
        this.tags[0];
      if (tag) this.load(tag);
      else {
        this.tag = undefined;
        this.status =
          "Add a BLE ESL device in Settings → Devices & services first.";
        this.render();
      }
    } catch (error) {
      this.report(error);
    }
  }
  api(action, extra = {}) {
    return this.hass.callWS({ type: "ble_esl/designer", action, ...extra });
  }
  load(tag) {
    if (this.tag && this.dirty)
      this.drafts.set(this.tag.entry_id, clone(this.document));
    this.tag = tag;
    this.document = clone(
      this.drafts.get(tag.entry_id) || tag.document || emptyDocument(),
    );
    this.selected = null;
    this.undoStack = [];
    this.redoStack = [];
    this.dirty = this.drafts.has(tag.entry_id);
    this.preview = null;
    this.layerPreviews = {};
    this.error = false;
    this.status = tag.writable
      ? "Ready"
      : "Discovery only: preview is available; sending is not supported yet.";
    this.render();
    this.queuePreview();
  }
  checkpoint() {
    this.undoStack.push(clone(this.document));
    if (this.undoStack.length > 100) this.undoStack.shift();
    this.redoStack = [];
  }
  // Without a full render: show that there is something to save, and that
  // the picture is no longer the exact render.
  markDirty() {
    const save = this.shadowRoot.querySelector('[data-action="save"]');
    if (save) {
      save.innerHTML = toolIcon("save") + "·";
      save.setAttribute("aria-label", "Save (unsaved changes)");
      save.title = "Save (unsaved changes) (⌘/Ctrl S)";
    }
    const badge = this.shadowRoot.querySelector("#dirty-badge");
    if (badge) badge.hidden = false;
    const title = this.shadowRoot
      .querySelector(".canvas-wrap")
      ?.previousElementSibling?.querySelector("span");
    if (title) title.textContent = "Editing preview";
  }
  edited(render = true) {
    this.dirty = true;
    this.preview = null;
    this.previewSequence++;
    if (render) this.render();
    else {
      this.drawStage();
      this.markDirty();
    }
    this.queuePreview();
  }
  report(error) {
    this.status = error.message || String(error);
    this.error = true;
    this.renderStatus();
  }
  renderStatus() {
    const node = this.shadowRoot.querySelector(".status");
    if (node) {
      node.textContent = this.status;
      node.classList.toggle("error", !!this.error);
      if (this.error && this.status) {
        const dismiss = document.createElement("button");
        dismiss.dataset.action = "dismiss-status";
        dismiss.setAttribute("aria-label", "Dismiss message");
        dismiss.textContent = "×";
        node.append(dismiss);
      }
    }
  }
  get element() {
    return this.document.elements.find(
      (element) => element.id === this.selected,
    );
  }
  entities() {
    return Object.values(this.hass?.states || {}).filter((state) =>
      /^(sensor|binary_sensor|weather|input_number|number|input_boolean|input_select|select|counter)\./.test(
        state.entity_id,
      ),
    );
  }
  entityName(state) {
    return (
      this.hass.formatEntityName?.(state) ||
      state.attributes.friendly_name ||
      state.entity_id
    );
  }
  value(element) {
    if (element.type === "text") return element.text;
    const state = this.hass.states[element.entity_id];
    if (!state) return "Unavailable";
    if (
      element.decimals !== undefined &&
      !["unknown", "unavailable"].includes(state.state)
    )
      return (
        Number(state.state).toFixed(element.decimals) +
        (element.show_unit && state.attributes.unit_of_measurement
          ? " " + state.attributes.unit_of_measurement
          : "")
      );
    const formatted = this.hass.formatEntityState?.(state) || state.state;
    if (!element.show_unit && state.attributes.unit_of_measurement)
      return state.state;
    return formatted;
  }
  sensorType(state) {
    return (
      state.entity_id.split(".")[0] +
      ":" +
      (state.attributes.device_class || "default")
    );
  }
  sampleState() {
    return this.hass.states[this.sampleEntity];
  }
  defaultTemplate() {
    const tag = { width: 140, height: 60, colors: "BWRY" };
    const make = (type, fields) => ({ ...newElement(type, tag), ...fields });
    return {
      ...emptyDocument(),
      elements: [
        make("icon", { x: 4, y: 14, width: 32, height: 32, icon: "{{icon}}" }),
        make("text", {
          x: 44,
          y: 4,
          width: 92,
          height: 18,
          font_size: 12,
          text: "{{name}}",
        }),
        make("text", {
          x: 44,
          y: 25,
          width: 92,
          height: 31,
          font_size: 20,
          text: "{{state}} {{unit}}",
        }),
      ],
    };
  }
  outputType(state) {
    if (!state) return "text";
    if (state.entity_id.startsWith("weather.")) return "weather";
    if (
      state.entity_id.startsWith("binary_sensor.") ||
      ["on", "off"].includes(state.state)
    )
      return "binary";
    return (state.state.trim() !== "" &&
      Number.isFinite(Number(state.state))) ||
      state.attributes.unit_of_measurement
      ? "numeric"
      : "text";
  }
  templateCompatibility(template, key) {
    const type = template?.sensor_type || key;
    if (type.startsWith("output:")) return type.split(":")[1];
    if (type.startsWith("binary_sensor:")) return "binary";
    if (type.startsWith("weather:")) return "weather";
    return "numeric";
  }
  templateTypes() {
    return [
      ...new Set([
        "output:numeric",
        "output:binary",
        "output:text",
        "output:weather",
        ...Object.keys(this.templates),
        ...this.templateDrafts.keys(),
      ]),
    ];
  }
  templateControls() {
    if (this.mode !== "template") return "";
    return `<div class="template-controls"><div style="min-width:240px;max-width:360px"><ha-entity-picker id="template-sample"></ha-entity-picker><span class="muted">${this.outputType(this.sampleState())} output</span></div><label>Name <input id="template-name" aria-label="Template name" value="${esc(this.templateName)}"></label><label>Template <select id="template-type" aria-label="Template">${this.templateTypes()
      .map(
        (key) =>
          `<option value="${esc(key)}" ${key === this.templateKey ? "selected" : ""}>${esc(this.templates[key]?.name || this.templateDrafts.get(key)?.name || (key.startsWith("output:") ? key.split(":")[1] + " template" : key.replace(":", " · ")))}</option>`,
      )
      .join(
        "",
      )}</select></label><label>W <input id="template-width" aria-label="Template width" type="number" min="16" max="1000" value="${this.tag?.width}"></label><label>H <input id="template-height" aria-label="Template height" type="number" min="16" max="1000" value="${this.tag?.height}"></label></div>`;
  }
  templateParts() {
    if (this.mode !== "template") return "";
    return `<div class="tools">${["name", "state", "unit"].map((name) => `<button data-token="${name}">${name[0].toUpperCase() + name.slice(1)}</button>`).join("")}<button data-action="add-state-icon">State icon</button></div>`;
  }
  switchMode(mode) {
    if (mode === this.mode) return;
    if (mode === "template") {
      this.displaySession = {
        tag: this.tag,
        document: this.document,
        selected: this.selected,
        dirty: this.dirty,
        undo: this.undoStack,
        redo: this.redoStack,
      };
      this.mode = mode;
      this.loadTemplate(this.templateKey);
    } else {
      this.rememberTemplate();
      this.mode = mode;
      const session = this.displaySession;
      this.tag = session.tag;
      this.document = session.document;
      this.selected = session.selected;
      this.dirty = session.dirty;
      this.undoStack = session.undo;
      this.redoStack = session.redo;
      this.preview = null;
      this.layerPreviews = {};
      this.render();
      this.queuePreview();
    }
  }
  rememberTemplate() {
    if (this.mode === "template" && this.tag)
      this.templateDrafts.set(this.templateKey, {
        width: this.tag.width,
        height: this.tag.height,
        document: clone(this.document),
        name: this.templateName,
        sensor_type: this.templateSensorType,
        dirty: this.dirty,
      });
  }
  loadTemplate(key) {
    if (this.tag?.title === this.templateKey) this.rememberTemplate();
    this.templateKey = key;
    const template = this.templateDrafts.get(key) ||
      this.templates[key] || {
        width: 140,
        height: 60,
        document: this.defaultTemplate(),
        dirty: false,
      };
    this.tag = {
      width: template.width,
      height: template.height,
      colors: "BWRY",
      title: key,
      writable: false,
    };
    this.layerPreviews = {};
    this.templateName =
      template.name ||
      (key.startsWith("output:")
        ? key.split(":")[1] + " template"
        : key.replace(":", " · "));
    this.templateSensorType =
      template.sensor_type || key.split(":").slice(0, 2).join(":");
    this.document = clone(template.document);
    if (
      !this.templates[key] &&
      !this.templateDrafts.has(key) &&
      /^(binary_sensor|weather):|^output:(binary|weather)/.test(key)
    )
      this.document.elements = this.document.elements.filter(
        (el) => el.text !== "{{state}} {{unit}}",
      );
    this.dirty = !!template.dirty;
    this.sampleEntity =
      this.entities().find(
        (state) =>
          this.outputType(state) === this.templateCompatibility(template, key),
      )?.entity_id ||
      this.entities().find(
        (state) =>
          state.entity_id.split(".")[0] ===
          this.templateSensorType.split(":")[0],
      )?.entity_id ||
      "";
    this.selected = null;
    this.undoStack = [];
    this.redoStack = [];
    this.preview = null;
    this.status = "";
    this.render();
    this.queuePreview();
  }
  createSensorTemplate() {
    const element = this.element;
    const state = this.hass.states[element.entity_id];
    const type = "output:" + this.outputType(state);
    const sample = element.entity_id;
    const source =
      this.templates[element.template === "auto" ? type : element.template];
    const initial = clone(source?.document || this.defaultTemplate());
    if (!source && /^output:(binary|weather)/.test(type))
      initial.elements = initial.elements.filter(
        (el) => el.text !== "{{state}} {{unit}}",
      );
    this.switchMode("template");
    const key = type + ":custom:" + createId();
    this.templateDrafts.set(key, {
      width: source?.width || 140,
      height: source?.height || 60,
      name: this.entityName(state) + " style",
      sensor_type: type,
      document: initial,
      dirty: true,
    });
    this.loadTemplate(key);
    this.sampleEntity = sample;
    this.createdForElement = element.id;
    this.render();
    this.queuePreview();
  }
  previewRequest() {
    if (this.mode === "template")
      return this.api("preview_template", {
        template: {
          width: this.tag.width,
          height: this.tag.height,
          name: this.templateName,
          sensor_type: this.templateSensorType,
          document: clone(this.document),
        },
        entity_id: this.sampleEntity,
      });
    return this.api("preview", {
      entry_id: this.tag.entry_id,
      document: clone(this.document),
    });
  }
  tokenText(text) {
    if (this.mode !== "template") return text;
    const state = this.sampleState();
    const values = {
      name: state ? this.entityName(state) : "Name",
      state: state?.state || "State",
      unit: state?.attributes.unit_of_measurement || "",
      icon: state?.attributes.icon || this.defaultIcon(state),
    };
    return text.replace(/{{(name|state|unit|icon)}}/g, (_, key) => values[key]);
  }
  defaultIcon(state) {
    if (!state) return "mdi:eye";
    if (state.attributes.icon) return state.attributes.icon;
    const active = state.state === "on",
      dc = state.attributes.device_class;
    if (state.entity_id.startsWith("weather."))
      return (
        "mdi:" +
        ({
          sunny: "weather-sunny",
          "clear-night": "weather-night",
          partlycloudy: "weather-partly-cloudy",
          cloudy: "weather-cloudy",
          rainy: "weather-rainy",
          pouring: "weather-pouring",
          snowy: "weather-snowy",
          "snowy-rainy": "weather-snowy-rainy",
          fog: "weather-fog",
          windy: "weather-windy",
          "windy-variant": "weather-windy-variant",
          lightning: "weather-lightning",
          "lightning-rainy": "weather-lightning-rainy",
          hail: "weather-hail",
          exceptional: "alert-circle",
        }[state.state] || "weather-cloudy")
      );
    if (state.entity_id.startsWith("binary_sensor.")) {
      const pairs = {
        window: ["window-closed", "window-open"],
        door: ["door-closed", "door-open"],
        motion: ["motion-sensor-off", "motion-sensor"],
        plug: ["power-plug-off", "power-plug"],
        power: ["flash-off", "flash"],
        lock: ["lock", "lock-open"],
      };
      return (
        "mdi:" +
        (pairs[dc] || ["radiobox-blank", "checkbox-marked-circle"])[
          Number(active)
        ]
      );
    }
    return (
      "mdi:" +
      ({
        temperature: "thermometer",
        humidity: "water-percent",
        battery: "battery",
        power: "flash",
        energy: "lightning-bolt",
        timestamp: "calendar-clock",
      }[dc] || "eye")
    );
  }
  iconGlyph(name, size = 24) {
    return `<span class="mdi" aria-hidden="true" style="font-size:${size}px">${esc(this.icons[name] || "")}</span>`;
  }
  renderIconChoices(search = "") {
    const grid = this.shadowRoot.querySelector(".icon-picker");
    if (grid)
      grid.innerHTML = Object.keys(this.icons)
        .filter((name) => name.includes(search.toLowerCase()))
        .slice(0, 120)
        .map(
          (name) =>
            `<button data-icon="${name}" aria-label="${name}" title="${name}">${this.iconGlyph(name)}</button>`,
        )
        .join("");
  }
  colorPicker(key, value, label) {
    return `<label>${label}<div class="picker" role="group" aria-label="${label}">${[
      ...palette(this.tag.colors),
      ...(["background", "display-background"].includes(key) &&
      key !== "display-background"
        ? ["transparent"]
        : []),
    ]
      .map(
        (color) =>
          `<button class="swatch" style="--swatch:${color};${color === "transparent" ? "background:repeating-conic-gradient(#ccc 0% 25%,white 0% 50%) 50%/8px 8px" : ""}" data-pick="${key}" data-value="${color}" aria-label="${label}: ${color}" title="${color}" aria-pressed="${value === color}"></button>`,
      )
      .join("")}</div></label>`;
  }
  panelMenu(action, open, label, id) {
    return `<button class="icon-button" data-action="${action}" aria-label="Toggle ${label} panel" aria-controls="${id}" title="${open ? "Hide" : "Show"} ${label}" aria-expanded="${open}">${icon("menu")}</button>`;
  }
  render() {
    this.finishTextEdit();
    // Rebuilding the tree resets every scroll position; keep the canvas,
    // the layer list and the inspector where the user left them.
    const scrolled = [".canvas-wrap", ".layers", ".inspector"].map(
      (selector) => {
        const node = this.shadowRoot.querySelector(selector);
        return [selector, node?.scrollLeft, node?.scrollTop];
      },
    );
    const tag = this.tag,
      element = this.element;
    this.shadowRoot.innerHTML = `<style>${style} .el.selected{outline:none!important;border:none!important} [hidden]{display:none!important} header{position:sticky;top:0;z-index:30} .toolbar{position:sticky;top:var(--bar-top,var(--header-height,56px));z-index:29;background:var(--primary-background-color,#f5f7fa);border-bottom:1px solid var(--divider-color,#e0e5eb);margin-bottom:12px;padding-top:8px;padding-bottom:8px} @media(max-width:650px),(max-height:600px){header,.toolbar{position:static}} .spec-group{border:1px solid var(--divider-color,#cbd3de);border-radius:6px;margin:0;padding:6px 8px} .spec-group legend{font-size:12px} .spec-doc{display:block;font-size:12px} .props textarea[data-json]{font:11px ui-monospace,Menlo,Consolas,monospace} [aria-invalid="true"]{border-color:#c33!important} .field-error{display:block;color:#c33;font-size:12px;margin-top:2px} .group-title{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--secondary-text-color,#637083);margin:12px 0 0;font-weight:600} .advanced summary{cursor:pointer;margin:10px 0 6px;color:var(--secondary-text-color,#637083)} .tips{margin:8px 0 0} .tips summary{cursor:pointer;font-size:12px;color:var(--secondary-text-color,#637083)} .swatch{box-shadow:0 0 0 1px var(--secondary-text-color,#888)} .dirty-badge{font-size:12px;color:#b45309;white-space:nowrap} .status.error{display:flex;align-items:center;gap:8px;color:#c33} .status button{padding:0 8px;line-height:20px} .empty-note{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:16px;color:var(--secondary-text-color,#637083);pointer-events:none} .hint{font-size:12px;line-height:1.4;color:var(--secondary-text-color,#637083);margin:4px 0 8px} .layer-row.hidden-layer .layer{opacity:.5;text-decoration:line-through} .el.hidden-el{opacity:.3}</style><header><ha-menu-button></ha-menu-button><h1>ESL Designer</h1><span>Live Home Assistant data on e-paper</span>${this._panelInfo?.config?.version ? `<span class="version" title="BLE ESL integration version">v${esc(this._panelInfo.config.version)}</span>` : ""}<nav class="tabs" aria-label="Designer mode"><button data-action="display-mode" aria-pressed="${this.mode === "display"}">Display</button><button data-action="template-mode" aria-pressed="${this.mode === "template"}">Sensor templates</button></nav></header>${this.templateControls()}<div class="toolbar"><select id="tag" aria-label="Tag" ${this.mode === "template" ? "hidden" : ""}>${this.tags.map((item) => `<option value="${esc(item.entry_id)}" ${item === tag ? "selected" : ""}>${esc(item.title)} · ${item.width}×${item.height}</option>`).join("")}</select><button data-action="reload" ${this.mode === "template" ? "hidden" : ""} class="icon-button" aria-label="Refresh tags" title="Refresh tags">${toolIcon("reload")}</button><button data-action="save" ${!tag || this.busy ? "disabled" : ""} class="icon-button" aria-label="${this.dirty ? "Save (unsaved changes)" : "Save"}" title="${this.dirty ? "Save (unsaved changes)" : "Save"} (⌘/Ctrl S)">${toolIcon("save")}${this.dirty ? "·" : ""}</button><span id="dirty-badge" class="dirty-badge" ${this.dirty ? "" : "hidden"}>Unsaved changes</span><button class="primary icon-button" aria-label="Send to tag" title="Send to tag" data-action="send" ${this.mode === "template" ? "hidden" : ""} ${this.mode === "template" || !tag?.writable || this.busy ? "disabled" : ""}>${toolIcon("send")}</button><label class="check" ${this.mode === "template" ? "hidden" : ""}><input id="auto" type="checkbox" ${this.document.auto_update ? "checked" : ""} ${!tag?.writable ? "disabled" : ""}>Auto-send when data changes</label>${this.document.auto_update && this.mode === "display" ? `<label title="Minimum time between automatic sends">Every <input id="interval" aria-label="Update interval" type="number" min="10" max="86400" value="${this.document.interval}" style="width:75px"> s</label>` : ""}<button data-action="undo" ${!this.undoStack.length ? "disabled" : ""} class="icon-button" aria-label="Undo" title="Undo (⌘/Ctrl Z)">${toolIcon("undo")}</button><button data-action="redo" ${!this.redoStack.length ? "disabled" : ""} class="icon-button" aria-label="Redo" title="Redo (⌘/Ctrl Shift Z)">${toolIcon("redo")}</button><button data-action="zoom-out" aria-label="Zoom out">−</button><label><select id="zoom" aria-label="Preview zoom"><option value="fit" ${this.zoomMode === "fit" ? "selected" : ""}>Fit</option>${[
      ...new Set([
        0.25,
        0.5,
        0.75,
        1,
        1.5,
        2,
        3,
        4,
        6,
        8,
        ...(this.zoomMode === "manual" ? [this.zoom] : []),
      ]),
    ]
      .sort((a, b) => a - b)
      .map(
        (value) =>
          `<option value="${value}" ${this.zoomMode === "manual" && value === this.zoom ? "selected" : ""}>${Math.round(value * 100)}%</option>`,
      )
      .join(
        "",
      )}</select></label><button data-action="zoom-in" aria-label="Zoom in">+</button><button data-action="fit" aria-label="Fit preview">Fit</button></div><div class="status" role="status"></div>${
      tag
        ? `<div class="workspace ${this.libraryOpen ? "" : "library-closed"} ${this.inspectorOpen ? "" : "inspector-closed"}"><section id="library" class="library card"><div class="panel-heading"><h2>${this.mode === "template" ? "Template parts" : "Entities"}</h2>${this.panelMenu("toggle-library", this.libraryOpen, "entities", "library")}</div>${this.templateParts()}<div ${this.mode === "template" ? "hidden" : ""}><ha-entity-picker id="entity-picker"></ha-entity-picker><div class="entity-preview"></div></div><h2>Components</h2><p class="hint">The four icon buttons add a text, shape, icon or image in one click. <b>＋ Add component</b> opens the component editor first, with more choices: a value from a sensor, progress bar, gauge, conditional icon.</p><button data-action="add-component">＋ Add component</button><div class="tools"><button class="icon-button" data-add="text" aria-label="Add text" title="Text">${toolIcon("text")}</button><button class="icon-button" data-add="rectangle" aria-label="Add shape" title="Shape">${toolIcon("shape")}</button><button class="icon-button" data-add="icon" aria-label="Add icon" title="Icon">${toolIcon("icon")}</button><button class="icon-button" data-add="image" aria-label="Add image" title="Image">${toolIcon("image")}</button></div>${this.specPalette()}<div class="footer-tools"><button data-action="yaml" ${this.mode === "template" ? "hidden" : ""}>Payload YAML</button><button data-action="import-yaml" ${this.mode === "template" ? "hidden" : ""}>Import YAML</button><button data-action="export">Export JSON</button><button data-action="import" ${this.mode === "template" ? "hidden" : ""}>Import JSON</button><input id="file" type="file" accept="application/json" hidden></div></section><section class="card preview-card"><div class="panel-heading">${!this.libraryOpen ? this.panelMenu("toggle-library", false, "entities", "library") : ""}<h2>${tag.width} × ${tag.height} · ${esc(tag.colors)} <span class="muted">${this.preview ? "Exact rendered preview" : "Editing preview"}</span></h2>${!this.inspectorOpen ? this.panelMenu("toggle-inspector", false, "properties", "inspector") : ""}</div><div class="canvas-wrap"><div class="stage-space" style="width:${tag.width * this.zoom}px;height:${tag.height * this.zoom}px"><div class="stage" style="width:${tag.width}px;height:${tag.height}px;transform:scale(${this.zoom});background:${this.document.background}" tabindex="0" role="group" aria-label="Display canvas"></div>${this.mode === "template" && !this.sampleEntity ? '<div class="empty-note">Choose a sample sensor above to preview this template.</div>' : ""}</div></div><details class="tips" ${this.tipsOpen ? "open" : ""}><summary>Keyboard &amp; mouse tips</summary><p class="muted">Click selects · Arrow keys move 1 px · Shift + arrows move 10 px · Double-click or Enter edits text · Delete / Backspace removes · Right-click for actions · ⌘/Ctrl + D duplicates · ⌘/Ctrl + S saves · ⌘/Ctrl + Z undoes · ⌘/Ctrl + Shift + Z redoes</p></details></section><aside id="inspector" class="inspector side-column"><section class="card"><div class="panel-heading"><h2>${element ? "Element properties" : "Select an element"}</h2>${this.panelMenu("toggle-inspector", this.inspectorOpen, "properties", "inspector")}</div><div class="props">${element && element.type !== "imagespec" ? `<button class="wide" data-action="configure-component">Configure</button>${this.mode === "template" ? "" : `<button class="wide" data-action="convert" title="Turn this into plain imagespec elements to edit field by field; a sensor's value becomes a template">Convert to elements</button>`}` : ""}${this.properties(element)}</div></section><section class="card layer-card"><h2>Layers</h2><div class="layers">${[
            ...this.document.elements,
          ]
            .reverse()
            .map(
              (item) =>
                `<div class="layer-row ${item.visible === false ? "hidden-layer" : ""}"><button class="layer ${item.id === this.selected ? "active" : ""}" data-select="${esc(item.id)}">${esc(this.layerLabel(item))}</button><button class="icon-button" data-layer="${esc(item.id)}" data-layer-action="visible" aria-label="${item.visible === false ? "Show" : "Hide"} ${esc(this.layerLabel(item))}" aria-pressed="${item.visible === false}" title="${item.visible === false ? "Hidden: click to show" : "Hide"}">${toolIcon(item.visible === false ? "eyeoff" : "preview")}</button><button class="icon-button" data-layer="${esc(item.id)}" data-layer-action="up" aria-label="Move ${esc(this.layerLabel(item))} forward" title="Bring forward">${toolIcon("up")}</button><button class="icon-button" data-layer="${esc(item.id)}" data-layer-action="down" aria-label="Move ${esc(this.layerLabel(item))} backward" title="Send backward">${toolIcon("down")}</button><button class="icon-button danger" data-delete-layer="${esc(item.id)}" aria-label="Delete ${esc(this.layerLabel(item))}" title="Delete">${icon("delete")}</button></div>`,
            )
            .join("")}</div></section></aside></div>`
        : ""
    }`;
    this.renderEntities();
    this.bindEntityPickers();
    this.shadowRoot
      .querySelector("details.advanced")
      ?.addEventListener("toggle", (event) => {
        this.advancedOpen = event.target.open;
      });
    this.shadowRoot
      .querySelector("details.tips")
      ?.addEventListener("toggle", (event) => {
        this.tipsOpen = event.target.open;
      });
    this.drawStage();
    this.renderStatus();
    this.resizeObserver.disconnect();
    const previewWindow = this.shadowRoot.querySelector(".canvas-wrap");
    if (previewWindow) {
      this.resizeObserver.observe(previewWindow);
      this.fitPreview();
    }
    // The bars wrap with the width: follow their real height.
    // and the panel itself, as the bars turn static on a short window.
    for (const bar of this.shadowRoot.querySelectorAll("header, .toolbar"))
      this.resizeObserver.observe(bar);
    this.resizeObserver.observe(this);
    this.stickyOffsets();
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) {
      menu.hass = this.hass;
      menu.narrow = this.narrow;
    }
    if (this.yamlExport) {
      // render() rebuilds the shadow tree, so the dialog opens after it.
      const dialog = document.createElement("ble-esl-yaml-dialog");
      this.shadowRoot.append(dialog);
      dialog.open(this.yamlExport, () =>
        this.shadowRoot.querySelector('[data-action="yaml"]')?.focus(),
      );
      this.yamlExport = null;
    }
    if (this.busy) {
      this.shadowRoot.querySelector(".workspace")?.setAttribute("inert", "");
      this.shadowRoot
        .querySelectorAll("button")
        .forEach((button) => (button.disabled = true));
      this.shadowRoot
        .querySelectorAll("input, select, textarea, ha-entity-picker")
        .forEach((control) => {
          if ("disabled" in control) control.disabled = true;
          control.setAttribute("aria-disabled", "true");
        });
    }
    for (const [selector, left, top] of scrolled) {
      const node = this.shadowRoot.querySelector(selector);
      if (node && top !== undefined) {
        node.scrollLeft = left;
        node.scrollTop = top;
      }
    }
  }
  openComponentEditor(element) {
    const modal = document.createElement("ble-esl-component-editor");
    this.shadowRoot.append(modal);
    modal.open(this, element);
  }
  // The toolbar sticks under the header, and a control scrolled into view must
  // land below both bars instead of behind them.
  stickyOffsets() {
    const header = this.shadowRoot.querySelector("header"),
      toolbar = this.shadowRoot.querySelector(".toolbar");
    if (!header || !toolbar) return;
    const fixed = getComputedStyle(header).position === "sticky";
    this.style.setProperty("--bar-top", `${header.offsetHeight}px`);
    this.style.scrollPaddingTop = fixed
      ? `${header.offsetHeight + toolbar.offsetHeight}px`
      : "";
  }
  fitPreview() {
    if (this.zoomMode !== "fit" || !this.tag) return;
    const previewWindow = this.shadowRoot.querySelector(".canvas-wrap");
    if (!previewWindow) return;
    this.zoom = Math.max(
      0.1,
      Math.min(
        8,
        Math.floor(
          Math.min(
            (previewWindow.clientWidth - 60) / this.tag.width,
            (previewWindow.clientHeight - 60) / this.tag.height,
          ) * 100,
        ) / 100,
      ),
    );
    const stage = this.shadowRoot.querySelector(".stage"),
      space = this.shadowRoot.querySelector(".stage-space");
    stage.style.transform = `scale(${this.zoom})`;
    space.style.width = `${this.tag.width * this.zoom}px`;
    space.style.height = `${this.tag.height * this.zoom}px`;
    this.updateSelectionOverlay();
    const option = this.shadowRoot.querySelector('#zoom option[value="fit"]');
    if (option) option.textContent = `Fit (${Math.round(this.zoom * 100)}%)`;
  }
  stateIconRows(element) {
    const sample = this.sampleState();
    const states = [
      ...new Set([
        ...(this.outputType(sample) === "binary"
          ? ["on", "off"]
          : sample
            ? [sample.state]
            : []),
        ...Object.keys(element.state_icons || {}),
      ]),
    ];
    return `<div class="wide"><strong>State → icon</strong>${states
      .map((state) => {
        const name = element.state_icons?.[state] || "{{icon}}";
        const stateObj = sample && { ...sample, state };
        return `<div style="display:flex;gap:8px;align-items:center;margin-top:6px"><span style="min-width:48px">${esc(state)}</span><span>→</span><button class="icon-choice" data-action="pick-icon" data-icon-state="${esc(state)}" aria-label="Choose icon for ${esc(state)}">${this.iconGlyph(name === "{{icon}}" ? this.defaultIcon(stateObj) : name)}<span>${name === "{{icon}}" ? "HA state icon" : esc(name.replace("mdi:", ""))}</span></button></div>`;
      })
      .join(
        "",
      )}<div style="display:flex;gap:6px;margin-top:8px"><input id="new-icon-state" aria-label="New icon state" placeholder="Another state"><button data-action="add-icon-state" aria-label="Add state mapping">+</button></div><div class="icon-popover" hidden><input id="icon-search" type="search" aria-label="Search icons" placeholder="Search icons"><button data-icon="{{icon}}">HA state icon</button><div class="icon-picker"></div></div></div>`;
  }
  // The layer of an element that draws beyond its frame is cropped to what it
  // drew: it sits at an offset from the frame and follows the frame's scale.
  layerImage(element, src) {
    const offset = this.layerOffsets?.[element.id],
      bounds = this.layerBounds?.[element.id],
      record = this.layerRecords?.[element.id];
    if (!offset || !bounds)
      return `<img class="layer-preview" src="${src}" alt="" aria-hidden="true">`;
    // Grow by what the frame grew, as the selection box does, so the box
    // stays on the image while the frame is dragged.
    const grows = record && element.type !== "text",
      dw = grows ? element.width - record.size[0] : 0,
      dh = grows ? element.height - record.size[1] : 0,
      width = Math.max(1, bounds[2] - bounds[0] + dw),
      height = Math.max(1, bounds[3] - bounds[1] + dh);
    return `<img class="layer-preview" src="${src}" alt="" aria-hidden="true" style="inset:auto;left:${offset[0]}px;top:${offset[1]}px;width:${width}px;height:${height}px">`;
  }
  layerLabel(item) {
    if (item.type === "imagespec") return specLabel(item);
    if (item.type === "text") return item.text || item.type;
    if (item.type === "icon") return item.icon || item.type;
    // "text" is only a leftover default on the other kinds.
    const state = this.hass?.states[item.entity_id];
    return (
      item.label ||
      (state ? this.entityName(state) : item.entity_id) ||
      item.type.replaceAll("_", " ")
    );
  }
  specDefinition(element) {
    return this.specs?.types.find((type) => type.type === element.spec?.type);
  }
  // Every imagespec element, by category, to add beside the quick buttons.
  specPalette() {
    if (!this.specs || this.mode === "template") return "";
    const groups = {};
    for (const type of this.specs.types)
      (groups[type.category] ||= []).push(type.type);
    return `<p class="hint wide">Every element type the tag can draw, set field by field: choose one, then press <b>Add</b>.</p><label class="wide">All elements<select id="add-spec" aria-label="Add element"><option value="">Add element…</option>${Object.entries(
      groups,
    )
      .map(
        ([category, types]) =>
          `<optgroup label="${esc(category)}">${types
            .map(
              (type) =>
                `<option value="${esc(type)}">${esc(type.replaceAll("_", " "))}</option>`,
            )
            .join("")}</optgroup>`,
      )
      .join(
        "",
      )}</select></label><button class="wide" data-action="add-spec">Add</button>`;
  }
  addSpec(type) {
    const definition = this.specs.types.find((item) => item.type === type);
    if (!definition) return;
    this.checkpoint();
    const element = newSpecElement(definition, newElement, this.tag);
    this.stagger(element);
    if (type === "plot") {
      // The example names a sensor nobody has; start from one that records numbers.
      const sensor = this.entities().find(
        (state) =>
          state.entity_id.startsWith("sensor.") &&
          Number.isFinite(Number.parseFloat(state.state)),
      );
      if (sensor) element.spec.data[0].entity = sensor.entity_id;
    }
    this.document.elements.push(element);
    this.selected = element.id;
    this.edited();
    this.focusElement();
  }
  // The selected element as imagespec elements, in its place, saying how
  // exactly they draw what it did.
  async convertSelected() {
    const element = this.element;
    // One at a time: the element has to be where the request left it.
    if (!element || this.converting) return;
    this.converting = true;
    try {
      await this.convertElement(element);
    } finally {
      this.converting = false;
    }
  }
  async convertElement(element) {
    this.status = "Converting…";
    this.renderStatus();
    const result = await this.api("convert", {
      entry_id: this.tag.entry_id,
      document: this.document,
      element_id: element.id,
    });
    const index = this.document.elements.findIndex(
      (el) => el.id === element.id,
    );
    if (index < 0) {
      // Deleted or undone while the server worked: nothing to replace.
      this.status = "The element changed; nothing was converted";
      this.renderStatus();
      return;
    }
    if (!result.elements.length) {
      this.error = true;
      this.status = result.issues.join("; ") || "Nothing to convert";
      this.renderStatus();
      return;
    }
    this.checkpoint();
    this.document.elements.splice(index, 1, ...result.elements);
    this.selected = result.elements[0].id;
    this.error = false;
    const skipped = result.issues.length
      ? `; ${result.issues.length} not converted`
      : "";
    this.status =
      result.different_pixels === 0
        ? `Converted to ${result.elements.length} elements, drawn exactly as before${skipped}`
        : `Converted to ${result.elements.length} elements; ${result.different_pixels ?? "?"} pixels differ from before${skipped}`;
    this.edited();
  }
  // A pasted payload as elements, added to the display or replacing it.
  async importYaml(text, replace) {
    const result = await this.api("import_yaml", {
      entry_id: this.tag.entry_id,
      text,
      // A display holds a limited number of elements; the server keeps to it.
      existing: replace ? 0 : this.document.elements.length,
    });
    if (result.elements.length) {
      this.checkpoint();
      if (replace) {
        this.document.elements = [];
        if (palette(this.tag.colors).includes(result.background))
          this.document.background = result.background;
      }
      this.document.elements.push(...result.elements);
      this.selected = result.elements.at(-1).id;
      this.edited();
    }
    return result;
  }
  // Undo steps only for edits that took: half-typed input changes nothing.
  pushUndo(snapshot) {
    this.undoStack.push(snapshot);
    if (this.undoStack.length > 100) this.undoStack.shift();
    this.redoStack = [];
  }
  specInput(input) {
    const element = this.element;
    if (element?.type !== "imagespec") return;
    const first = this.typingProperty !== input,
      before = first ? clone(this.document) : null;
    if (!applySpecInput(input, element.spec, this.specDefinition(element)))
      return;
    if (first) {
      this.pushUndo(before);
      this.typingProperty = input;
    }
    this.edited(false);
    this.markDirty();
  }
  // Optional settings of the older kinds: left blank they keep imagespec's
  // default, so a design that never sets one draws as before.
  extraProperties(element) {
    const type = element.type,
      text = ["sensor", "text"].includes(type),
      shape = shapeTypes.includes(type) && type !== "line";
    const choice = (key, label, options, fallback = "default") =>
      `<label>${label}<select data-property="${key}" aria-label="${label}"><option value="">${fallback}</option>${options.map((value) => `<option value="${value}" ${element[key] === value ? "selected" : ""}>${value.replaceAll("_", " ")}</option>`).join("")}</select></label>`;
    const number = (key, label, min, max, placeholder = "") =>
      `<label>${label}<input data-property="${key}" type="number" step="1" min="${min}" max="${max}" placeholder="${placeholder}" value="${esc(element[key] ?? "")}"></label>`;
    const flag = (key, label, fallback) =>
      `<label class="wide check"><input type="checkbox" data-property="${key}" ${(element[key] ?? fallback) ? "checked" : ""}>${label}</label>`;
    const methods = (
      this.specs?.dither_methods?.length
        ? this.specs.dither_methods
        : ["none", "floyd"]
    ).filter((method) => method !== "none");
    const dither =
      element.dither === true
        ? "floyd"
        : element.dither === false
          ? "none"
          : (element.dither ?? "");
    let style = "",
      advanced = "";
    if (text)
      advanced +=
        choice("valign", "Vertical align", ["top", "middle", "bottom"]) +
        choice(
          "fit",
          "Fit",
          ["shrink", "ellipsis", "shrink_ellipsis"],
          "default (shrink ellipsis)",
        ) +
        number("max_lines", "Max lines", 1, 20, type === "text" ? "3" : "1") +
        number("min_font_size", "Min font size", 1, 200, "8") +
        number("padding", "Padding", 0, 100, "0") +
        number("line_spacing", "Line spacing", 0, 100, "2") +
        `<label class="wide">Font file<input data-property="font" placeholder="Default font" value="${esc(element.font ?? "")}"></label>`;
    if (shape)
      style +=
        flag("filled", "Filled", true) +
        number("line_width", "Outline width", 1, 20, "1") +
        (type === "rounded_rectangle"
          ? number("radius", "Corner radius", 0, 200, "auto")
          : "");
    if (type === "icon")
      advanced +=
        number("stroke_width", "Outline width", 0, 20, "0") +
        this.colorPicker(
          "stroke_fill",
          element.stroke_fill ?? "white",
          "Outline colour",
        );
    if (type === "image")
      style +=
        number("rotate", "Rotate (°)", -360, 360, "0") +
        flag("circle", "Crop to circle", false);
    if (type === "progress_bar")
      style +=
        choice(
          "direction",
          "Direction",
          ["right", "left", "up", "down"],
          "default (right)",
        ) +
        number("radius", "Corner radius", 0, 200, "0") +
        number("line_width", "Outline width", 1, 20, "1") +
        flag("show_percentage", "Show percentage", false);
    if (type === "gauge")
      style +=
        number("thickness", "Arc thickness", 1, 100, "8") +
        flag("show_value", "Show value", true);
    if (["progress_bar", "gauge"].includes(type))
      advanced += `<label class="wide">Font file<input data-property="font" placeholder="Default font" value="${esc(element.font ?? "")}"></label>`;
    advanced += `<label class="wide">Dither<select data-property="dither" aria-label="Dither"><option value="">${type === "image" ? "default (floyd)" : "off (default)"}</option><option value="none" ${dither === "none" ? "selected" : ""}>none</option>${methods.map((method) => `<option value="${esc(method)}" ${dither === method ? "selected" : ""}>${esc(method)}</option>`).join("")}</select></label>`;
    return { style, advanced };
  }
  properties(element) {
    if (!element)
      return `<p class="muted wide">Click a block to move, resize, or bind it to an entity.</p>${this.mode === "display" ? `<h3 class="wide group-title">Display</h3>${this.colorPicker("display-background", this.document.background, "Background")}` : ""}`;
    const field = (key, label, type = "text", wide = false) =>
      `<label class="${wide ? "wide" : ""}">${label}<input data-property="${key}" type="${type}" value="${esc(element[key] ?? "")}" ${type === "number" ? 'step="1"' : ""}></label>`;
    const group = (title, body) =>
      body ? `<h3 class="wide group-title">${title}</h3>${body}` : "";
    const position = group(
      "Position & size (px)",
      ["x", "y", "width", "height"]
        .map((key) => field(key, key[0].toUpperCase() + key.slice(1), "number"))
        .join(""),
    );
    let html = "",
      style = "",
      picker = "";
    if (element.type === "imagespec")
      return (
        position +
        specEditorHtml(
          this.specDefinition(element),
          element.spec,
          this.tag.colors,
          this.specs?.dither_methods || [],
        )
      );
    if (["progress_bar", "gauge"].includes(element.type))
      html +=
        field("min_value", "Minimum", "number") +
        field("max_value", "Maximum", "number") +
        field("value", "Value", "number", true);
    if (element.type === "gauge")
      style += field("font_size", "Font size", "number");
    if (["sensor", "text"].includes(element.type))
      style +=
        field("font_size", "Font size", "number") +
        `<label>Align<div class="picker" role="group" aria-label="Text alignment">${["left", "center", "right"].map((value) => `<button class="align-button" data-pick="align" data-value="${value}" aria-label="Align ${value}" title="Align ${value}" aria-pressed="${element.align === value}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 4h18M${value === "right" ? 9 : value === "center" ? 6 : 3} 9h12M3 14h18M${value === "right" ? 9 : value === "center" ? 6 : 3} 19h12"/></svg></button>`).join("")}</div></label>`;
    style += this.colorPicker("color", element.color, "Colour");
    if (shapeTypes.includes(element.type))
      style += `<label class="wide">Shape<select data-property="type" aria-label="Shape">${shapeTypes.map((type) => `<option value="${type}" ${element.type === type ? "selected" : ""}>${type.replace("_", " ")}</option>`).join("")}</select></label>`;

    if (element.type === "image")
      html += `<label class="wide">Image URL<input data-property="image" aria-label="Image URL" placeholder="Paste a URL, or upload below" value="${esc(element.image?.startsWith("data:") ? "" : (element.image ?? ""))}"></label><label class="wide">Image<input id="image-file" aria-label="Upload image" type="file" accept="image/*"></label><label class="wide">Fit<select data-property="image_fit" aria-label="Image fit">${["contain", "fill", "stretch"].map((value) => `<option value="${value}" ${element.image_fit === value ? "selected" : ""}>${value}</option>`).join("")}</select></label>`;
    if (element.type === "icon")
      html += `<label class="wide">Icon<button class="icon-choice" data-action="pick-icon" aria-label="Choose icon">${this.iconGlyph(this.tokenText(element.icon), 24)}<span>${element.icon === "{{icon}}" ? "HA state icon" : esc(element.icon.replace("mdi:", ""))}</span></button><input data-property="icon" aria-label="Icon name" value="${esc(element.icon)}" hidden></label>`;

    const extra = this.extraProperties(element);
    style += extra.style;
    style += `<label class="wide check"><input type="checkbox" data-property="visible" ${element.visible === false ? "" : "checked"}>Visible</label>`;
    if (this.mode === "template" && element.type === "icon")
      html += this.stateIconRows(element);
    if (this.mode === "template" && element.type !== "icon")
      html += `<label class="wide">Show for state<input data-property="state" aria-label="Visible state" placeholder="All states" list="template-states" value="${esc(element.state || "")}"><datalist id="template-states">${[
        ...new Set([
          "on",
          "off",
          ...(this.templateKey.startsWith("weather:")
            ? [
                "sunny",
                "cloudy",
                "partlycloudy",
                "rainy",
                "pouring",
                "snowy",
                "snowy-rainy",
                "clear-night",
                "fog",
                "windy",
                "hail",
                "lightning",
                "lightning-rainy",
              ]
            : []),
          ...this.entities()
            .filter(
              (state) => this.sensorType(state) === this.templateSensorType,
            )
            .map((state) => state.state),
        ]),
      ]
        .map((state) => `<option value="${esc(state)}"></option>`)
        .join("")}</datalist></label>`;
    if (element.type === "text")
      html += `<label class="wide">Text<textarea data-property="text" rows="3">${esc(element.text)}</textarea></label>`;
    if (element.type === "sensor") {
      if (element.entity_id.startsWith("weather."))
        html += `<label>When<select data-property="weather_when" aria-label="Weather time">${[
          ["now", "Now"],
          ["later_today", "Later today"],
          ["tomorrow", "Tomorrow"],
          ["in_2_days", "In 2 days"],
          ["in_3_days", "In 3 days"],
        ]
          .map(
            ([key, label]) =>
              `<option value="${key}" ${(element.weather_when || "now") === key ? "selected" : ""}>${label}</option>`,
          )
          .join(
            "",
          )}</select></label><label>Show<select data-property="weather_field" aria-label="Weather value">${[
          ["condition", "Condition"],
          ["temperature", "Temperature"],
          ["templow", "Low temperature"],
          ["precipitation", "Rain / snow"],
          ["precipitation_probability", "Rain chance"],
          ["wind_speed", "Wind speed"],
          ["humidity", "Humidity"],
        ]
          .map(
            ([key, label]) =>
              `<option value="${key}" ${(element.weather_field || "condition") === key ? "selected" : ""}>${label}</option>`,
          )
          .join("")}</select></label>`;
      html += `<label class="wide">Template<select data-property="template" aria-label="Sensor template"><option value="auto">By sensor type</option><option value="default" ${element.template === "default" ? "selected" : ""}>HA tile</option>${Object.keys(
        this.templates,
      )
        .filter(
          (key) =>
            this.templateCompatibility(this.templates[key], key) ===
            this.outputType(this.hass.states[element.entity_id]),
        )
        .map(
          (key) =>
            `<option value="${esc(key)}" ${element.template === key ? "selected" : ""}>${esc(this.templates[key]?.name || this.templateDrafts.get(key)?.name || (key.startsWith("output:") ? key.split(":")[1] + " template" : key.replace(":", " · ")))}</option>`,
        )
        .join(
          "",
        )}<option value="__new__">＋ Create template…</option></select></label>`;
      picker = `<ha-entity-picker class="wide" data-property="entity_id"></ha-entity-picker>`;
      html += `<label class="wide check"><input type="checkbox" data-property="show_label" ${element.show_label ? "checked" : ""}>Show label</label>`;
      if (element.show_label)
        html += field("label", "Label override", "text", true);
      const state = this.hass.states[element.entity_id];
      const numeric =
        state &&
        !state.entity_id.startsWith("binary_sensor.") &&
        (state.entity_id.startsWith("weather.")
          ? element.weather_field && element.weather_field !== "condition"
          : state.state.trim() !== "" && Number.isFinite(Number(state.state)));
      if (numeric) {
        html += `<label class="wide check"><input type="checkbox" data-property="show_unit" ${element.show_unit ? "checked" : ""}>Show unit</label>`;
        if (element.show_unit)
          html += field(
            "decimals",
            "Decimals (auto when blank)",
            "number",
            true,
          );
      }
    }
    return (
      group("Content", picker + html) +
      position +
      group("Style", style) +
      (extra.advanced
        ? `<details class="wide advanced" ${this.advancedOpen ? "open" : ""}><summary>Advanced</summary><div class="props">${extra.advanced}</div></details>`
        : "")
    );
  }
  // Pickers created before HA defined the element keep their properties as
  // plain fields that can shadow the upgraded element's accessors. Swap in
  // fresh ones without a full render(), which would end inline editing and
  // drop an open dialog or menu.
  upgradeEntityPickers() {
    for (const old of this.shadowRoot.querySelectorAll("ha-entity-picker")) {
      const fresh = document.createElement("ha-entity-picker");
      for (const { name, value } of old.attributes)
        fresh.setAttribute(name, value);
      old.replaceWith(fresh);
    }
    this.renderEntities();
    this.bindEntityPickers();
    this.shadowRoot.querySelector("ble-esl-component-editor")?.upgradeSource();
  }
  renderEntities() {
    const picker = this.shadowRoot.querySelector("#entity-picker");
    if (!picker) return;
    picker.hass = this.hass;
    picker.includeDomains = [
      "sensor",
      "binary_sensor",
      "weather",
      "input_number",
      "number",
      "input_boolean",
      "input_select",
      "select",
      "counter",
    ];
    picker.label = "Sensor";
    picker.searchLabel = "Search sensors";
    picker.allowCustomEntity = false;
    picker.value = this.libraryEntity;
    picker.addEventListener("value-changed", (event) => {
      const id = event.detail.value;
      if (!id) {
        this.libraryEntity = "";
        this.renderEntityPreview();
        return;
      }
      this.libraryEntity = id;
      this.add("sensor", this.hass.states[id]);
    });
    this.renderEntityPreview();
  }
  bindEntityPickers() {
    const configure = (picker, value, label) => {
      picker.label = label;
      picker.searchLabel = label;
      picker.allowCustomEntity = false;
      picker.required = true;
      picker.value = value;
      picker.hass = this.hass;
      picker.includeDomains =
        this.shadowRoot.querySelector("#entity-picker").includeDomains;
      picker.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        const next = event.detail.value;
        if (!next || next === value) return;
        this.change({
          target: { id: picker.id, dataset: picker.dataset, value: next },
        });
      });
    };
    const bound = this.shadowRoot.querySelector(
      'ha-entity-picker[data-property="entity_id"]',
    );
    if (bound) configure(bound, this.element.entity_id, "Bound entity");
    const sample = this.shadowRoot.querySelector("#template-sample");
    if (sample) configure(sample, this.sampleEntity, "Sample sensor");
  }
  renderEntityPreview() {
    const node = this.shadowRoot.querySelector(".entity-preview");
    const state = this.hass?.states[this.libraryEntity];
    if (!node) return;
    node.innerHTML = state
      ? `<div class="entity-state" data-entity="${esc(state.entity_id)}" draggable="true"><ha-state-icon></ha-state-icon><div class="state-copy"><div class="state-name">${esc(this.entityName(state))}</div><div class="state-value">${esc(this.hass.formatEntityState?.(state) || state.state)}</div></div><button class="icon-button" data-action="add-current-entity" aria-label="Add selected sensor" title="Add selected sensor">+</button></div>`
      : "";
    const icon = node.querySelector("ha-state-icon");
    if (icon) {
      icon.hass = this.hass;
      icon.stateObj = state;
    }
  }
  filteredEntities() {
    return this.entities().filter((state) =>
      (state.entity_id + " " + this.entityName(state))
        .toLowerCase()
        .includes(this.search.toLowerCase()),
    );
  }
  sensorContent(element, state, label) {
    let key = element.template || "auto";
    if (key === "auto" && state) {
      key = this.sensorType(state);
      if (!this.templates[key])
        key = state.entity_id.split(".")[0] + ":default";
    }
    const template = this.templates[key];
    if (template && state) {
      const values = {
        name: label,
        state:
          element.decimals === undefined ||
          ["unknown", "unavailable"].includes(state.state)
            ? state.state
            : Number(state.state).toFixed(element.decimals),
        unit: element.show_unit
          ? state.attributes.unit_of_measurement || ""
          : "",
        icon: this.defaultIcon(state),
      };
      const text = (value) =>
        String(value).replace(
          /{{(name|state|unit|icon)}}/g,
          (_, name) => values[name],
        );
      return template.document.elements
        .filter((child) => !child.state || child.state === state.state)
        .map((child) => {
          const sx = element.width / template.width,
            sy = element.height / template.height;
          const content =
            child.type === "text"
              ? esc(text(child.text)).replace(/\n/g, "<br>")
              : child.type === "icon"
                ? this.iconGlyph(
                    text(child.icon),
                    Math.min(child.width * sx, child.height * sy),
                  )
                : "";
          return `<div style="position:absolute;left:${child.x * sx}px;top:${child.y * sy}px;width:${child.width * sx}px;height:${child.height * sy}px;overflow:hidden;color:${child.color};background:${["rectangle", "line"].includes(child.type) ? child.color : child.background};font-size:${child.font_size * Math.min(sx, sy)}px;text-align:${child.align}">${content}</div>`;
        })
        .join("");
    }
    const weatherNumber =
      state?.entity_id.startsWith("weather.") &&
      element.weather_field &&
      element.weather_field !== "condition";
    const visual =
      state?.entity_id.startsWith("binary_sensor.") ||
      (state?.entity_id.startsWith("weather.") && !weatherNumber);
    const value = weatherNumber
      ? String(state.attributes[element.weather_field] ?? "") +
        (element.show_unit && state.attributes[element.weather_field + "_unit"]
          ? " " + state.attributes[element.weather_field + "_unit"]
          : "")
      : this.value(element);
    const icon = weatherNumber
      ? this.defaultIcon({
          entity_id: "sensor.weather",
          state: value,
          attributes: { device_class: element.weather_field },
        })
      : this.defaultIcon(state);
    return `<div class="tile-icon">${this.iconGlyph(icon, 32)}</div><div class="tile-copy">${element.show_label ? `<div class="label">${esc(label)}</div>` : ""}<div class="value">${visual ? "" : esc(value)}</div></div>`;
  }
  drawStage() {
    const stage = this.shadowRoot.querySelector(".stage");
    if (!stage || this.editingTextId) return;
    const focusedId = this.shadowRoot.activeElement?.dataset.id;
    stage.classList.toggle("exact-mode", !!this.preview);
    stage.innerHTML =
      (this.preview
        ? `<img class="exact" src="${this.preview}" alt="Exact rendered display">`
        : "") +
      this.document.elements
        .map((element, index) => {
          const state = this.hass?.states[element.entity_id];
          const label =
            element.label ||
            (state ? this.entityName(state) : element.entity_id);
          let content = "";
          if (element.type === "sensor")
            content = this.sensorContent(element, state, label);
          if (element.type === "image" && element.image)
            content = `<img src="${esc(element.image)}" alt="" style="width:100%;height:100%;object-fit:${element.image_fit === "stretch" ? "fill" : element.image_fit === "fill" ? "cover" : "contain"}${element.circle ? ";border-radius:50%" : ""}${element.rotate ? `;transform:rotate(${Number(element.rotate) || 0}deg)` : ""}">`;
          if (element.type === "text")
            content = esc(this.tokenText(element.text)).replace(/\n/g, "<br>");
          if (element.type === "icon")
            content = this.iconGlyph(
              this.tokenText(
                element.state_icons?.[this.sampleState()?.state] ||
                  element.icon,
              ),
              Math.min(element.width, element.height),
            );
          if (shapeTypes.includes(element.type)) {
            const hollow = element.type !== "line" && element.filled === false;
            const paint = hollow
              ? `fill="none" stroke="currentColor" stroke-width="${(element.line_width || 1) * 2}" vector-effect="non-scaling-stroke"`
              : 'fill="currentColor"';
            const radius =
              element.radius ?? Math.min(element.width, element.height) / 5;
            const shape =
              element.type === "triangle"
                ? `<polygon points="50,0 100,100 0,100" ${paint}/>`
                : element.type === "ellipse"
                  ? `<ellipse cx="50" cy="50" rx="50" ry="50" ${paint}/>`
                  : `<rect width="100" height="100" rx="${element.type === "rounded_rectangle" ? (radius / element.width) * 100 : 0}" ry="${element.type === "rounded_rectangle" ? (radius / element.height) * 100 : 0}" ${paint}/>`;
            content = `<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${shape}</svg>`;
          }
          // A dragged image is shown by its own <img> (laid out in the
          // frame) until the next render: the cropped layer cannot follow a
          // frame that is resized.
          const record = this.layerRecords?.[element.id];
          const rendered =
            element.type === "image" &&
            (this.gesture ||
              !record ||
              record.shape !== this.shape(element) ||
              record.size[0] !== element.width ||
              record.size[1] !== element.height)
              ? undefined
              : this.layerPreviews[element.id];
          const visible = this.visibleBounds(element);
          const box = [0, 0, element.width, element.height];
          const hitBounds =
            visible === undefined ? box : (visible ?? (rendered ? null : box));
          const hitArea = hitBounds
            ? `<div class="hit-area" style="left:${hitBounds[0]}px;top:${hitBounds[1]}px;width:${hitBounds[2] - hitBounds[0]}px;height:${hitBounds[3] - hitBounds[1]}px"></div>`
            : "";
          const selected = element.id === this.selected;
          return `<div class="el ${element.visible === false ? "hidden-el" : ""} ${rendered ? "rendered" : ""} ${selected ? "selected" : ""}" data-id="${esc(element.id)}" role="button" tabindex="0" aria-pressed="${selected}" aria-label="${esc(element.type === "imagespec" ? this.layerLabel(element) : label || (element.type === "text" ? element.text : "") || element.type)}" style="left:${element.x}px;top:${element.y}px;width:${element.width}px;height:${element.height}px;color:${element.color};background:transparent;font-size:${element.font_size}px;text-align:${element.align};z-index:${index + 1}">${rendered ? this.layerImage(element, rendered) : ""}<div class="content" ${this.mode === "template" && element.state && element.state !== this.sampleState()?.state ? 'style="opacity:.2"' : ""}>${content}</div>${hitArea}</div>`;
        })
        .join("") + this.selectionMarkup();
    if (focusedId) this.focusElement();
    stage.querySelectorAll("ha-state-icon").forEach((icon) => {
      const element = this.document.elements.find(
        (el) => el.id === icon.closest("[data-id]").dataset.id,
      );
      icon.hass = this.hass;
      icon.stateObj = this.hass.states[element.entity_id];
    });
  }
  selectionMarkup() {
    const element = this.element;
    if (!element) return "";
    const handleSize =
      (window.matchMedia("(pointer: coarse)").matches ? 32 : 20) / this.zoom;
    const moveTarget = `<span class="move-handle" aria-label="Move selected element" style="position:absolute;left:${element.width / 2 - handleSize / 2}px;top:${element.height / 2 - handleSize / 2}px;width:${handleSize}px;height:${handleSize}px;border:1px solid white;border-radius:50%;box-shadow:0 0 0 1px var(--primary-color,#16838b);background:var(--primary-color,#16838b);color:white;display:${Math.max(element.width, element.height) * this.zoom < 36 ? "grid" : "none"};place-items:center;pointer-events:auto;cursor:move"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 2v20M2 12h20M12 2l-3 3m3-3 3 3m-3 17-3-3m3 3 3-3M2 12l3-3m-3 3 3 3m17-3-3-3m3 3-3 3"/></svg></span>`;
    return `<div class="selection-box" data-id="${esc(element.id)}" style="position:absolute;left:${element.x}px;top:${element.y}px;width:${element.width}px;height:${element.height}px;outline:${1.5 / this.zoom}px solid var(--primary-color,#16838b);z-index:9999;pointer-events:none;overflow:visible">${["nw", "ne", "sw", "se"].map((corner) => `<span class="handle" data-corner="${corner}" aria-label="Resize ${corner}" style="position:absolute;left:${corner.endsWith("w") ? -handleSize : element.width}px;top:${corner.startsWith("n") ? -handleSize : element.height}px;right:auto;bottom:auto;width:${handleSize}px;height:${handleSize}px;border:1px solid white;border-radius:50%;box-shadow:0 0 0 1px var(--primary-color,#16838b);pointer-events:auto;cursor:${corner === "nw" || corner === "se" ? "nwse" : "nesw"}-resize"></span>`).join("")}${moveTarget}<button class="delete-handle" data-action="delete" aria-label="Delete selected element" title="Delete" style="pointer-events:auto;transform:scale(${1 / this.zoom});transform-origin:bottom right">${icon("delete")}</button></div>`;
  }
  updateSelectionOverlay() {
    const overlay = this.shadowRoot.querySelector(".selection-box"),
      element = this.element;
    if (!overlay || !element) return;
    const handleSize =
      (window.matchMedia("(pointer: coarse)").matches ? 32 : 20) / this.zoom;
    overlay.style.left = `${element.x}px`;
    overlay.style.top = `${element.y}px`;
    overlay.style.width = `${element.width}px`;
    overlay.style.height = `${element.height}px`;
    overlay.style.outlineWidth = `${1.5 / this.zoom}px`;
    for (const handle of overlay.querySelectorAll(".handle")) {
      const corner = handle.dataset.corner;
      handle.style.left = `${corner.endsWith("w") ? -handleSize : element.width}px`;
      handle.style.top = `${corner.startsWith("n") ? -handleSize : element.height}px`;
      handle.style.width = `${handleSize}px`;
      handle.style.height = `${handleSize}px`;
    }
    const moveTarget = overlay.querySelector(".move-handle");
    if (moveTarget) {
      moveTarget.style.left = `${element.width / 2 - handleSize / 2}px`;
      moveTarget.style.top = `${element.height / 2 - handleSize / 2}px`;
      moveTarget.style.width = `${handleSize}px`;
      moveTarget.style.height = `${handleSize}px`;
      moveTarget.style.display =
        Math.max(element.width, element.height) * this.zoom < 36
          ? "grid"
          : "none";
    }
    const trash = overlay.querySelector(".delete-handle");
    if (trash) trash.style.transform = `scale(${1 / this.zoom})`;
  }
  // Content bounds come from the last render and are relative to the element.
  // Moving the element keeps them. Resizing it grows or shrinks them with the
  // frame, so a dragged handle stays under the pointer. Any other edit (font
  // size, text...) leaves them describing the old content, so the element's
  // frame stands in until the new preview arrives.
  shape(element) {
    // An uploaded image is a data URL of megabytes: stand in for it.
    const { image, ...rest } = element;
    return JSON.stringify({
      ...rest,
      image: image && [
        image.length,
        image.slice(0, 40),
        image.slice(image.length / 2 - 20, image.length / 2 + 20),
        image.slice(-40),
      ],
      x: 0,
      y: 0,
      width: 0,
      height: 0,
    });
  }
  // The server returns the saved document with its defaults filled in. That
  // changes nothing on screen, so what the last render still describes stays.
  adoptDocument(saved) {
    const current = this.document.elements
      .filter((el) => (el.type === "image" ? !!this.layerRecords?.[el.id] : this.visibleBounds(el) !== undefined))
      .map((el) => el.id);
    this.document = saved;
    const records = this.layerRecords || {};
    this.layerRecords = Object.fromEntries(
      saved.elements
        .filter((el) => current.includes(el.id))
        .map((el) => [
          el.id,
          { shape: this.shape(el), size: records[el.id].size },
        ]),
    );
  }
  renderRecords() {
    return Object.fromEntries(
      this.document.elements.map((el) => [
        el.id,
        { shape: this.shape(el), size: [el.width, el.height] },
      ]),
    );
  }
  // undefined: not known, use the frame. null: rendered with nothing visible.
  visibleBounds(element) {
    const record = this.layerRecords?.[element.id];
    // A text box is its frame: the text fits into it, so its box must not
    // follow the ink and jump back when the frame is resized.
    // An image is its frame as well: "contain" leaves margins around the
    // picture, and a box on the ink would not match what x/y/size move.
    if (element.type === "text" || element.type === "image") return undefined;
    if (!record || record.shape !== this.shape(element)) return undefined;
    const dw = element.width - record.size[0],
      dh = element.height - record.size[1],
      bounds = this.layerBounds[element.id];
    if (!bounds) return dw || dh ? undefined : null;
    return [
      bounds[0],
      bounds[1],
      Math.max(bounds[0] + 1, bounds[2] + dw),
      Math.max(bounds[1] + 1, bounds[3] + dh),
    ];
  }
  // A new element lands beside the ones already there, not exactly on them.
  stagger(element) {
    const taken = (x, y) =>
      this.document.elements.some((item) => item.x === x && item.y === y);
    while (taken(element.x, element.y)) {
      const x = element.x + 8,
        y = element.y + 8;
      if (
        x + element.width > this.tag.width ||
        y + element.height > this.tag.height
      )
        break;
      element.x = x;
      element.y = y;
    }
  }
  add(type, entity, x, y) {
    this.checkpoint();
    const element = newElement(type, this.tag, entity);
    if (x !== undefined) {
      element.x = x;
      element.y = y;
      clampBox(element, this.tag);
    } else this.stagger(element);
    this.document.elements.push(element);
    this.selected = element.id;
    this.edited();
    this.focusElement();
  }
  focusElement() {
    this.shadowRoot
      .querySelector(this.selected ? `[data-id="${this.selected}"]` : ".stage")
      ?.focus({ preventScroll: true });
  }
  async click(event) {
    const button = event.target.closest("button");
    if (!button || this.busy) return;
    this.gestureFinish?.(false);
    this.closeContextMenu();
    if (["display-mode", "template-mode"].includes(button.dataset.action)) {
      this.switchMode(
        button.dataset.action === "template-mode" ? "template" : "display",
      );
      return;
    }
    if (button.dataset.action === "convert") {
      try {
        await this.convertSelected();
      } catch (error) {
        this.report(error);
      }
      return;
    }
    if (button.dataset.action === "import-yaml") {
      // Outside the panel: a change to the display rebuilds the panel's tree.
      const dialog = document.createElement("ble-esl-import-dialog");
      document.body.append(dialog);
      dialog.open(this, () =>
        this.shadowRoot.querySelector('[data-action="import-yaml"]')?.focus(),
      );
      return;
    }
    if (button.dataset.action === "add-spec") {
      const type = this.shadowRoot.querySelector("#add-spec")?.value;
      if (type) this.addSpec(type);
      return;
    }
    if (button.dataset.action === "add-current-entity") {
      this.add("sensor", this.hass.states[this.libraryEntity]);
      return;
    }
    if (button.dataset.action === "add-icon-state") {
      const state = this.shadowRoot
        .querySelector("#new-icon-state")
        .value.trim();
      if (!state) return;
      this.checkpoint();
      this.element.state_icons ||= {};
      this.element.state_icons[state] = "{{icon}}";
      this.edited();
      return;
    }
    if (button.dataset.iconState !== undefined) {
      // A state row: choose its icon here instead of opening the editor.
      const popover = this.shadowRoot.querySelector(".icon-popover");
      this.iconMappingState = button.dataset.iconState;
      popover.hidden = false;
      this.renderIconChoices();
      popover.querySelector("#icon-search").focus();
      return;
    }
    if (
      ["add-component", "configure-component", "pick-icon"].includes(
        button.dataset.action,
      )
    ) {
      this.openComponentEditor(
        button.dataset.action === "add-component" ? null : this.element,
      );
      return;
    }
    if (button.dataset.icon) {
      this.checkpoint();
      if (this.iconMappingState !== undefined) {
        this.element.state_icons ||= {};
        this.element.state_icons[this.iconMappingState] = button.dataset.icon;
        this.element.state = "";
        this.iconMappingState = undefined;
      } else this.element.icon = button.dataset.icon;
      this.edited();
      return;
    }
    if (button.dataset.action === "add-state-icon") {
      this.add("icon");
      this.element.icon = "{{icon}}";
      this.edited();
      return;
    }
    if (button.dataset.pick) {
      this.checkpoint();
      if (button.dataset.pick === "display-background")
        this.document.background = button.dataset.value;
      else if (this.element)
        this.element[button.dataset.pick] = button.dataset.value;
      this.edited();
      return;
    }
    if (button.dataset.token) {
      this.add("text");
      this.element.text = `{{${button.dataset.token}}}`;
      this.edited();
      this.focusElement();
      return;
    }
    if (
      ["duplicate", "delete", "back", "front", "center"].includes(
        button.dataset.action,
      )
    ) {
      this.transform(button.dataset.action);
      return;
    }
    if (
      ["toggle-library", "toggle-inspector"].includes(button.dataset.action)
    ) {
      if (button.dataset.action === "toggle-library")
        this.libraryOpen = !this.libraryOpen;
      else this.inspectorOpen = !this.inspectorOpen;
      this.render();
      return;
    }
    if (["zoom-in", "zoom-out", "fit"].includes(button.dataset.action)) {
      if (button.dataset.action === "fit") this.zoomMode = "fit";
      else {
        this.zoomMode = "manual";
        this.zoom = Math.max(
          0.1,
          Math.min(
            8,
            Math.round(
              this.zoom *
                (button.dataset.action === "zoom-in" ? 1.25 : 0.8) *
                100,
            ) / 100,
          ),
        );
      }
      this.render();
      return;
    }
    if (button.dataset.entity) {
      this.add("sensor", this.hass.states[button.dataset.entity]);
      return;
    }
    if (button.dataset.add) {
      this.add(button.dataset.add);
      return;
    }
    if (button.dataset.deleteLayer) {
      const kept = this.selected;
      this.selected = button.dataset.deleteLayer;
      this.transform("delete");
      if (
        kept &&
        kept !== button.dataset.deleteLayer &&
        this.document.elements.some((el) => el.id === kept)
      ) {
        this.selected = kept;
        this.render();
      }
      return;
    }
    if (button.dataset.layerAction) {
      const elements = this.document.elements,
        index = elements.findIndex((el) => el.id === button.dataset.layer),
        item = elements[index];
      if (!item) return;
      const target =
        button.dataset.layerAction === "up"
          ? index + 1
          : button.dataset.layerAction === "down"
            ? index - 1
            : index;
      if (target < 0 || target >= elements.length) return;
      this.checkpoint();
      if (button.dataset.layerAction === "visible")
        item.visible = item.visible === false;
      else
        [elements[index], elements[target]] = [
          elements[target],
          elements[index],
        ];
      this.edited();
      // The panel was rebuilt: keep keyboard focus on the same control.
      this.shadowRoot
        .querySelector(
          `[data-layer="${CSS.escape(item.id)}"][data-layer-action="${button.dataset.layerAction}"]`,
        )
        ?.focus();
      return;
    }
    if (button.dataset.select) {
      this.selected = button.dataset.select;
      this.render();
      this.focusElement();
      return;
    }
    const action = button.dataset.action;
    if (action === "dismiss-status") {
      this.error = false;
      this.status = "Ready";
      this.renderStatus();
      this.shadowRoot.querySelector(".stage")?.focus();
      return;
    }
    try {
      if (["save", "preview", "send"].includes(action)) {
        // Finish canvas edits and in-flight uploads before freezing the request.
        this.gestureFinish?.(false);
        this.busy = true;
        this.error = false;
        this.status = action === "send" ? "Sending display…" : "Working…";
        this.render();
        if (this.pendingUploads.size)
          await Promise.all([...this.pendingUploads]);
        if (action === "send") {
          this.adoptDocument(
            await this.api("save", {
              entry_id: this.tag.entry_id,
              document: this.document,
            }),
          );
          this.tag.document = clone(this.document);
          this.dirty = false;
          this.drafts.delete(this.tag.entry_id);
        }
        const result =
          this.mode === "template"
            ? action === "save"
              ? await this.api("save_template", {
                  key: this.templateKey,
                  template: {
                    width: this.tag.width,
                    height: this.tag.height,
                    name: this.templateName,
                    sensor_type: this.templateSensorType,
                    document: this.document,
                  },
                })
              : await this.previewRequest()
            : await this.api(action, {
                entry_id: this.tag.entry_id,
                document: this.document,
              });
        if (action === "save") {
          this.adoptDocument(
            this.mode === "template" ? result.document : result,
          );
          if (this.mode === "template")
            this.templates[this.templateKey] = clone(result);
          this.tag.document = clone(this.document);
          this.drafts.delete(this.tag.entry_id);
          this.dirty = false;
          if (this.mode === "template" && this.createdForElement) {
            const session = this.displaySession;
            session.undo.push(clone(session.document));
            session.redo = [];
            session.document.elements.find(
              (el) => el.id === this.createdForElement,
            ).template = this.templateKey;
            session.dirty = true;
            this.createdForElement = null;
          }
          this.status =
            this.mode === "template" ? "Template saved" : "Display saved";
        }
        if (action === "preview") {
          this.preview = result.png;
          this.layerPreviews = result.layers;
          this.layerBounds = result.layers._bounds || {};
          this.layerOffsets = result.layers._offsets || {};
          this.layerRecords = this.renderRecords();
          this.templateEntities = [
            ...new Set(Object.values(result.layers._dependencies || {}).flat()),
          ];
          this.status = "Exact rendered preview";
        }
        if (action === "send") {
          const sent = {
            written: "Display sent and acknowledged",
            locked: "Not sent: the tag's write lock is on",
            duplicate: "Not sent: the display is unchanged",
            dropped: "Not sent: a newer write replaced this one",
            failed: `Sending failed${result.error ? `: ${result.error}` : ""}`,
          };
          this.status = sent[result.status] || result.status;
          this.error = ["locked", "failed"].includes(result.status);
        }
      } else if (action === "reload") {
        this.started = false;
        await this.boot();
        return;
      } else if (action === "undo" || action === "redo") {
        const source = action === "undo" ? this.undoStack : this.redoStack,
          target = action === "undo" ? this.redoStack : this.undoStack;
        if (source.length) {
          target.push(clone(this.document));
          this.document = source.pop();
          if (!this.element) this.selected = null;
          this.edited();
        }
      } else if (action === "yaml") {
        this.busy = true;
        this.error = false;
        this.status = "Exporting payload…";
        this.render();
        this.yamlExport = await this.api("export", {
          entry_id: this.tag.entry_id,
          document: this.document,
        });
        this.status = "Payload exported";
      } else if (action === "export") {
        const blob = new Blob([JSON.stringify(this.document, null, 2)], {
            type: "application/json",
          }),
          url = URL.createObjectURL(blob),
          link = document.createElement("a");
        link.href = url;
        link.download = `${
          (this.mode === "template" ? this.templateName : this.tag?.title)
            ?.replace(/[\\/:*?"<>|\s]+/g, "-")
            .replace(/^[-.]+|[-.]+$/g, "") || "label-display"
        }.json`;
        link.click();
        URL.revokeObjectURL(url);
      } else if (action === "import")
        this.shadowRoot.querySelector("#file").click();
      else this.transform(action);
    } catch (error) {
      this.report(error);
    } finally {
      this.busy = false;
      this.render();
    }
  }
  transform(action) {
    const element = this.element;
    if (!element) return;
    if (!["duplicate", "delete", "back", "front", "center"].includes(action))
      return;
    this.checkpoint();
    const elements = this.document.elements,
      index = elements.indexOf(element);
    if (action === "duplicate") {
      const copy = clone(element);
      copy.id = createId();
      // Step back instead when the copy would be clamped onto the original.
      copy.x += copy.x + copy.width + 8 > this.tag.width ? -8 : 8;
      copy.y += copy.y + copy.height + 8 > this.tag.height ? -8 : 8;
      clampBox(copy, this.tag, onLabel(element, this.tag));
      elements.push(copy);
      this.selected = copy.id;
    }
    if (action === "delete") {
      elements.splice(index, 1);
      this.selected = null;
    }
    if (action === "back") {
      elements.splice(index, 1);
      elements.unshift(element);
    }
    if (action === "front") {
      elements.splice(index, 1);
      elements.push(element);
    }
    if (action === "center")
      element.x = Math.round((this.tag.width - element.width) / 2);
    this.edited();
    this.focusElement();
  }
  closeContextMenu() {
    this.shadowRoot.querySelector(".context-menu")?.remove();
  }
  contextMenu(event) {
    if (event.target.isContentEditable) return;
    const node = event.target.closest("[data-id], [data-select]");
    if (!node || this.busy) return;
    event.preventDefault();
    this.selected = node.dataset.id || node.dataset.select;
    this.render();
    const menu = document.createElement("div");
    menu.className = "context-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "Element actions");
    menu.style.left = `${Math.min(event.clientX, window.innerWidth - 228)}px`;
    menu.style.top = `${Math.min(event.clientY, window.innerHeight - 220)}px`;
    menu.innerHTML = [
      ["duplicate", "Duplicate", "⌘/Ctrl D"],
      ["delete", "Delete", "⌫"],
      ["back", "Send back", ""],
      ["front", "Bring front", ""],
      ["center", "Center horizontally", ""],
    ]
      .map(
        ([action, label, key]) =>
          `<button role="menuitem" data-action="${action}">${action === "delete" ? icon("delete") : toolIcon(action)}<span>${label}</span><kbd>${key}</kbd></button>`,
      )
      .join("");
    this.shadowRoot.append(menu);
    menu.querySelector("button").focus();
  }
  beginTextEdit() {
    if (this.element?.type !== "text") return;
    clearTimeout(this.previewTimer);
    this.previewSequence++;
    this.preview = null;
    // The exact image would show the old text under the one being typed.
    this.shadowRoot.querySelector(".stage").classList.remove("exact-mode");
    this.shadowRoot.querySelector(".stage img.exact")?.remove();
    const node = this.shadowRoot.querySelector(`[data-id="${this.selected}"]`);
    node.classList.add("editing");
    this.shadowRoot.querySelector(".move-handle")?.setAttribute("hidden", "");
    const content = node.querySelector(".content");
    content.textContent = this.element.text;
    content.contentEditable = "plaintext-only";
    content.dataset.editText = this.selected;
    content.setAttribute("role", "textbox");
    content.setAttribute("aria-label", "Edit display text");
    this.editingTextId = this.selected;
    content.focus();
    const text =
      content.firstChild || content.appendChild(document.createTextNode(""));
    const start = this.element.text === "Your text" ? 0 : text.length;
    const select = () =>
      window.getSelection().setBaseAndExtent(text, start, text, text.length);
    select();
    // WebKit resets the selection in the triggering click's default action,
    // which left Safari without a caret: select again afterwards, unless the
    // user already started typing.
    setTimeout(() => {
      if (
        content.isConnected &&
        this.editingTextId === content.dataset.editText &&
        this.typingProperty !== content
      )
        select();
    });
  }
  finishTextEdit() {
    if (!this.editingTextId) return;
    this.editingTextId = null;
    this.typingProperty = null;
    this.drawStage();
    this.queuePreview();
  }
  input(event) {
    if (this.busy) return;
    this.gestureFinish?.(false);
    const input = event.target;
    if (input.dataset.editText) {
      if (this.typingProperty !== input) {
        this.checkpoint();
        this.typingProperty = input;
      }
      this.element.text = input.innerText;
      this.dirty = true;
      const field = this.shadowRoot.querySelector('[data-property="text"]');
      if (field) field.value = this.element.text;
      const layer = this.shadowRoot.querySelector(
        `[data-select="${this.selected}"]`,
      );
      if (layer) layer.textContent = this.element.text;
      this.markDirty();
      return;
    }
    if (input.id === "template-name") {
      this.templateName = input.value;
      this.dirty = true;
      return;
    }
    if (["template-width", "template-height"].includes(input.id)) {
      if (!input.validity.valid || !input.value) return;
      this.tag[input.id === "template-width" ? "width" : "height"] = Number(
        input.value,
      );
      this.document.elements.forEach((el) => clampBox(el, this.tag, false));
      const stage = this.shadowRoot.querySelector(".stage");
      stage.style.width = `${this.tag.width}px`;
      stage.style.height = `${this.tag.height}px`;
      this.edited(false);
      this.fitPreview();
      return;
    }
    if (input.id === "icon-search") {
      this.renderIconChoices(input.value);
      return;
    }
    if (input.id === "search") {
      this.search = input.value;
      this.renderEntities();
    } else if (
      input.dataset.spec &&
      ["text", "textarea"].includes(input.type)
    ) {
      this.specInput(input);
    } else if (
      input.dataset.property &&
      this.element &&
      ["text", "textarea", "number"].includes(input.type)
    ) {
      if (input.type === "number" && !input.validity.valid) return;
      if (this.typingProperty !== input) {
        this.checkpoint();
        this.typingProperty = input;
        this.typedOnLabel = onLabel(this.element, this.tag);
      }
      this.updateProperty(input);
      this.edited(false);
      this.markDirty();
      const layer = this.shadowRoot.querySelector(
        `[data-select="${this.selected}"]`,
      );
      if (layer) layer.textContent = this.layerLabel(this.element);
    }
  }
  updateProperty(input) {
    const key = input.dataset.property;
    if (key === "weather_field" && input.value === "condition")
      delete this.element.decimals;
    if (key === "type") {
      if (input.value === "line") this.element.height = 2;
      else if (this.element.type === "line") this.element.height = 40;
    }
    if (key === "entity_id" && this.element.entity_id !== input.value) {
      const defaults = newElement(
        "sensor",
        this.tag,
        this.hass.states[input.value],
      );
      delete this.element.decimals;
      if (defaults.decimals !== undefined)
        this.element.decimals = defaults.decimals;
      this.element.show_unit = defaults.show_unit;
    }
    if (
      (key === "decimals" || optionalProperties.has(key)) &&
      input.type !== "checkbox" &&
      input.value === ""
    )
      delete this.element[key];
    else if (key === "dither") {
      if (input.value === "") delete this.element.dither;
      else this.element.dither = input.value === "none" ? false : input.value;
    } else
      this.element[key] =
        input.type === "checkbox"
          ? input.checked
          : input.type === "number"
            ? Number(input.value)
            : input.value;
    if (key === "font_size")
      this.element.font_size = Math.max(
        8,
        Math.min(200, this.element.font_size),
      );
    if (propertyRanges[key] && this.element[key] !== undefined)
      this.element[key] = Math.max(
        propertyRanges[key][0],
        Math.min(propertyRanges[key][1], Math.round(this.element[key])),
      );
    if (key === "decimals" && this.element.decimals !== undefined)
      this.element.decimals = Math.max(0, Math.min(6, this.element.decimals));
    // Typed geometry is kept to the label when the field is committed.
    clampBox(this.element, this.tag, false);
  }
  async change(event) {
    if (this.busy) return;
    this.gestureFinish?.(false);
    const input = event.target,
      id = input.id;
    if (id === "template-type") {
      this.loadTemplate(input.value);
      return;
    }
    if (id === "template-sample") {
      this.sampleEntity = input.value;
      this.templateSensorType = "output:" + this.outputType(this.sampleState());
      this.dirty = true;
      this.render();
      this.preview = null;
      this.drawStage();
      this.queuePreview();
      return;
    }
    if (["template-width", "template-height"].includes(id)) {
      this.tag[id === "template-width" ? "width" : "height"] = Math.max(
        16,
        Math.min(1000, Number(input.value)),
      );
      this.document.elements.forEach((el) => clampBox(el, this.tag, false));
      this.edited();
      return;
    }
    if (id === "tag") {
      this.gestureFinish?.(false);
      this.load(this.tags.find((tag) => tag.entry_id === input.value));
      return;
    }
    if (id === "zoom") {
      this.zoomMode = input.value === "fit" ? "fit" : "manual";
      if (this.zoomMode === "manual") this.zoom = Number(input.value);
      this.render();
      return;
    }
    if (id === "image-file") {
      const file = input.files[0];
      if (!file) return;
      const id = this.element.id,
        sequence = (this.uploadSequence = (this.uploadSequence || 0) + 1),
        ownerTag = this.tag,
        ownerDocument = this.document;
      const reader = new FileReader();
      const upload = new Promise((resolve, reject) => {
        reader.onload = async () => {
          try {
            let image = reader.result;
            // The renderer ignores a photo's EXIF orientation, which the browser
            // applies: a portrait phone photo would print turned 90°. A photo that
            // carries one is redrawn (and, as a tag is small, capped in size) so
            // the orientation is in its pixels. The rest is kept byte for byte.
            try {
              const head = new Uint8Array(await file.slice(0, 65536).arrayBuffer());
              if (jpegOrientation(head) > 1) {
                const bitmap = await createImageBitmap(file, {
                  imageOrientation: "from-image",
                });
                const scale = Math.min(1, 2048 / Math.max(bitmap.width, bitmap.height)),
                  canvas = document.createElement("canvas");
                canvas.width = Math.max(1, Math.round(bitmap.width * scale));
                canvas.height = Math.max(1, Math.round(bitmap.height * scale));
                canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
                bitmap.close();
                const redrawn = canvas.toDataURL("image/jpeg", 0.92);
                // A canvas the browser refuses gives "data:," rather than an error.
                if (redrawn.length > 100) image = redrawn;
              }
            } catch {
              // Keep the file as it is when the browser cannot decode it.
            }
            const element = ownerDocument.elements.find((item) => item.id === id);
            if (
              !element ||
              sequence !== this.uploadSequence ||
              this.document !== ownerDocument ||
              this.tag !== ownerTag
            ) {
              resolve();
              return;
            }
            this.checkpoint();
            element.image = image;
            if (!this.error) this.status = "Image added";
            this.edited();
            resolve();
          } catch (error) {
            reject(error);
          }
        };
        reader.onerror = () => reject(reader.error || new Error("Image upload failed"));
        reader.readAsDataURL(file);
      });
      this.pendingUploads.add(upload);
      this.busy = true;
      this.error = false;
      this.status = "Loading image…";
      this.render();
      upload.catch((error) => this.report(error)).finally(() => {
        this.pendingUploads.delete(upload);
        this.busy = false;
        this.render();
      });
      return;
    }
    if (id === "file") {
      const file = input.files?.[0];
      if (!file) return;
      const targetTag = this.tag;
      this.busy = true;
      this.status = "Checking display…";
      this.render();
      try {
        const imported = JSON.parse(await file.text());
        await this.api("preview", {
          entry_id: targetTag.entry_id,
          document: imported,
        });
        if (this.tag !== targetTag) return;
        this.checkpoint();
        this.document = this.normalizeImportedDocument(imported);
        this.selected = null;
        this.edited();
      } catch (error) {
        this.report(error);
      } finally {
        this.busy = false;
        this.render();
      }
      return;
    }
    if (["auto", "interval", "background"].includes(id)) {
      this.checkpoint();
      if (id === "auto") this.document.auto_update = input.checked;
      if (id === "interval")
        this.document.interval = Math.max(
          10,
          Math.min(86400, Number(input.value) || 60),
        );
      if (id === "background") this.document.background = input.value;
      this.edited();
      return;
    }
    // Chosen with the Add button: arrow keys move through the list, they
    // must not add an element at every step.
    if (id === "add-spec") return;
    if (input.dataset.spec) {
      if (input.matches("select") && this.element?.type === "imagespec") {
        const before = clone(this.document);
        if (
          applySpecInput(
            input,
            this.element.spec,
            this.specDefinition(this.element),
          )
        ) {
          this.pushUndo(before);
          this.edited();
        }
      }
      return;
    }
    if (input.dataset.property === "template" && input.value === "__new__") {
      this.createSensorTemplate();
      return;
    }
    if (input.dataset.property && this.element) {
      if (["text", "textarea", "number"].includes(input.type)) {
        if (["x", "y", "width", "height"].includes(input.dataset.property)) {
          // Judged before the edit: an off-label imported frame stays put.
          clampBox(this.element, this.tag, this.typedOnLabel ?? true);
          this.edited();
        } else if (input.type === "number") {
          // Show the value the element kept: it may have been clamped to the
          // allowed range, or refused as out of range.
          const key = input.dataset.property,
            snapshot = clone(this.document),
            before = JSON.stringify(this.element[key]);
          this.updateProperty(input);
          input.value = this.element[key] ?? "";
          if (JSON.stringify(this.element[key]) !== before) {
            if (this.typingProperty !== input) this.pushUndo(snapshot);
            this.edited(false);
          }
        }
        return;
      }
      this.checkpoint();
      this.updateProperty(input);
      this.edited();
    }
  }
  normalizeImportedDocument(document) {
    const normalized = {
      ...emptyDocument(),
      ...document,
      elements: Array.isArray(document?.elements) ? document.elements : [],
    };
    // Mirror the server schema defaults so preview, imported display and the
    // next save all render the same minimal-but-valid document identically.
    const defaults = {
      spec: {},
      color: "black",
      background: "transparent",
      visible: true,
      font_size: 24,
      text: "Text",
      image: "",
      image_fit: "contain",
      icon: "{{icon}}",
      state: "",
      state_icons: {},
      template: "auto",
      weather_when: "now",
      weather_field: "condition",
      entity_id: "",
      field_templates: {},
      data_field: "",
      attribute: "",
      value: 0,
      min_value: 0,
      max_value: 100,
      icon_rules: [],
      label: "",
      show_label: true,
      show_unit: true,
      align: "left",
    };
    normalized.elements = normalized.elements.map((element) => ({
      ...clone(defaults),
      ...element,
      id: element.id || createId(),
    }));
    return normalized;
  }

  key(event) {
    if (
      event
        .composedPath()
        .some((node) =>
          [
            "BLE-ESL-COMPONENT-EDITOR",
            "BLE-ESL-YAML-DIALOG",
            "HA-ENTITY-PICKER",
          ].includes(node.tagName),
        )
    )
      return;
    if (this.busy) return;
    if (this.gesture) {
      if (event.key === "Escape") {
        event.preventDefault();
        this.gestureCancel?.();
        return;
      }
      this.gestureFinish?.(false);
    }
    const context = event.target.closest(".context-menu");
    if (context && ["ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      const buttons = [...context.querySelectorAll("button")];
      const index = buttons.indexOf(event.target);
      buttons[
        (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) %
          buttons.length
      ].focus();
      return;
    }
    if (event.key === "Escape") {
      this.finishTextEdit();
      this.closeContextMenu();
      this.focusElement();
      return;
    }
    const editing =
      ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName) ||
      event.target.isContentEditable;
    // The browser's own "Save page" must not open from inside a field.
    if (
      editing &&
      (event.metaKey || event.ctrlKey) &&
      event.key.toLowerCase() === "s"
    ) {
      event.preventDefault();
      this.shadowRoot.querySelector('[data-action="save"]')?.click();
      return;
    }
    if (editing) return;
    const interactiveControl = event.target.closest(
        "button, a, input, select, textarea, [contenteditable=true]",
      ),
      canvasNode = interactiveControl
        ? null
        : event.target.closest(".el[data-id]"),
      inCanvas =
        !!canvasNode ||
        (!!event.target.closest(".stage") && !interactiveControl);
    if (canvasNode && ["Enter", " "].includes(event.key)) {
      event.preventDefault();
      if (this.selected !== canvasNode.dataset.id) {
        this.selected = canvasNode.dataset.id;
        this.render();
        this.focusElement();
      }
      if (event.key === "Enter" && this.element?.type === "text")
        this.beginTextEdit();
      return;
    }
    const cmd = event.metaKey || event.ctrlKey,
      key = event.key.toLowerCase();
    if (cmd && ["z", "y", "s", "d"].includes(key)) {
      event.preventDefault();
      if (key === "d") this.transform("duplicate");
      else
        this.shadowRoot
          .querySelector(
            `[data-action="${key === "s" ? "save" : key === "y" || event.shiftKey ? "redo" : "undo"}"]`,
          )
          ?.click();
      return;
    }
    if (inCanvas && (key === "delete" || key === "backspace")) {
      event.preventDefault();
      this.transform("delete");
      return;
    }
    const directions = {
      ArrowLeft: [-1, 0],
      ArrowRight: [1, 0],
      ArrowUp: [0, -1],
      ArrowDown: [0, 1],
    };
    if (inCanvas && this.element && directions[event.key]) {
      event.preventDefault();
      this.checkpoint();
      const before = clone(this.element),
        step = event.shiftKey ? 10 : 1,
        [x, y] = directions[event.key];
      this.element.x += x * step;
      this.element.y += y * step;
      clampBox(this.element, this.tag, onLabel(before, this.tag));
      this.edited();
      this.focusElement();
    }
  }
  pointer(event) {
    if (
      this.busy ||
      event.button !== 0 ||
      !event.isPrimary ||
      this.gesture ||
      event.target.isContentEditable ||
      event.target.closest("button")
    )
      return;
    const node = event.target.closest("[data-id]");
    if (!node) {
      this.lastCanvasClick = null;
      if (this.selected && !this.busy && event.target.closest(".canvas-wrap")) {
        this.finishTextEdit();
        this.selected = null;
        this.render();
      }
      return;
    }
    const clicked = this.document.elements.find(
        (item) => item.id === node.dataset.id,
      ),
      resize = event.target.closest(".handle")?.dataset.corner,
      selectionOverlay = event.target.closest(".selection-box"),
      moveTarget = event.target.closest(".move-handle"),
      previousClick = this.lastCanvasClick,
      editTextOnRelease =
        !resize &&
        (!selectionOverlay || moveTarget) &&
        clicked?.type === "text" &&
        previousClick?.id === clicked.id &&
        performance.now() - previousClick.time <= 500 &&
        Math.hypot(
          event.clientX - previousClick.x,
          event.clientY - previousClick.y,
        ) <= 5;
    if (!editTextOnRelease) this.lastCanvasClick = null;
    event.preventDefault();
    this.selected = node.dataset.id;
    const element = this.element,
      start = clone(element),
      startX = event.clientX,
      startY = event.clientY,
      pointerId = event.pointerId,
      snapshot = clone(this.document),
      // An element that hangs off the label (an imported frame) is not pulled
      // back by the first move.
      bound = onLabel(start, this.tag);
    let moved = false;
    // A plain click leaves the exact preview alone; only a drag swaps it for
    // the movable layers.
    this.render();
    this.focusElement();
    const controller = new AbortController();
    this.gesture = controller;
    const previewBeforeGesture = this.preview;
    const cancelGesture = () => {
      controller.abort();
      if (this.gesture !== controller) return;
      this.gesture = null;
      this.gestureCancel = null;
      if (moved) {
        Object.assign(element, start);
        this.preview = previewBeforeGesture;
        this.drawStage();
        if (this.isConnected && !this.preview) this.queuePreview();
      }
    };
    this.gestureCancel = cancelGesture;
    const finishGesture = () => {
      controller.abort();
      if (this.gesture !== controller) return;
      this.gesture = null;
      this.gestureCancel = null;
      this.gestureFinish = null;
      const changed =
        moved &&
        (element.x !== start.x ||
          element.y !== start.y ||
          element.width !== start.width ||
          element.height !== start.height);
      if (changed) {
        this.pushUndo(snapshot);
        this.edited();
        this.focusElement();
      } else {
        if (moved) {
          this.preview = previewBeforeGesture;
          this.drawStage();
          if (!this.preview) this.queuePreview();
        }
        if (editTextOnRelease && !moved && !resize && element.type === "text") {
          this.lastCanvasClick = null;
          this.beginTextEdit();
        } else if (
          !moved &&
          !resize &&
          (!selectionOverlay || moveTarget) &&
          element.type === "text"
        ) {
          this.lastCanvasClick = {
            id: element.id,
            x: startX,
            y: startY,
            time: performance.now(),
          };
        }
      }
    };
    this.gestureFinish = finishGesture;
    window.addEventListener(
      "pointermove",
      (move) => {
        if (move.pointerId !== pointerId) return;
        const dx = Math.round((move.clientX - startX) / this.zoom),
          dy = Math.round((move.clientY - startY) / this.zoom);
        if (
          !moved &&
          Math.hypot(move.clientX - startX, move.clientY - startY) < 3
        )
          return;
        if (!moved) {
          moved = true;
          this.lastCanvasClick = null;
          this.preview = null;
          this.previewSequence++;
          clearTimeout(this.previewTimer);
        }
        if (resize) {
          // The dragged edge stops at the label's edge; the other stays put.
          const edge = (from, size, limit, lower, delta) => {
            if (!bound)
              return lower
                ? [
                    from + Math.min(delta, size - 1),
                    size - Math.min(delta, size - 1),
                  ]
                : [from, Math.max(1, size + delta)];
            const [near, far] = lower
              ? [
                  Math.min(Math.max(0, from + delta), from + size - 1),
                  from + size,
                ]
              : [
                  from,
                  Math.max(Math.min(limit, from + size + delta), from + 1),
                ];
            return [near, far - near];
          };
          [element.x, element.width] = edge(
            start.x,
            start.width,
            this.tag.width,
            resize.endsWith("w"),
            dx,
          );
          [element.y, element.height] = edge(
            start.y,
            start.height,
            this.tag.height,
            resize.startsWith("n"),
            dy,
          );
        } else {
          element.x = start.x + dx;
          element.y = start.y + dy;
        }
        clampBox(element, this.tag, bound);
        this.drawStage();
      },
      { signal: controller.signal },
    );
    window.addEventListener(
      "pointerup",
      (up) => {
        if (up.pointerId === pointerId) finishGesture();
      },
      { signal: controller.signal },
    );
    window.addEventListener(
      "pointercancel",
      (cancel) => {
        if (cancel.pointerId !== pointerId) return;
        // A cancelled gesture is rolled back and never becomes an undo step.
        cancelGesture();
      },
      { signal: controller.signal },
    );
    window.addEventListener("blur", cancelGesture, {
      once: true,
      signal: controller.signal,
    });
  }
  drop(event) {
    if (this.busy) return;
    const stage = event.target.closest(".stage");
    if (!stage) return;
    event.preventDefault();
    const rect = stage.getBoundingClientRect();
    this.gestureFinish?.(false);
    const entity = this.hass.states[event.dataTransfer.getData("text/plain")];
    if (!entity) return;
    this.add(
      "sensor",
      entity,
      Math.round((event.clientX - rect.left) / this.zoom),
      Math.round((event.clientY - rect.top) / this.zoom),
    );
  }
  queuePreview() {
    clearTimeout(this.previewTimer);
    if (!this.tag || this.editingTextId) return;
    const sequence = ++this.previewSequence;
    this.previewTimer = setTimeout(async () => {
      if (this.previewInFlight) {
        this.previewQueued = true;
        return;
      }
      this.previewInFlight = true;
      try {
        if (this.mode === "template" && !this.sampleEntity) return;
        const result = await this.previewRequest();
        if (sequence === this.previewSequence && !this.gesture) {
          this.preview = result.png;
          this.layerPreviews = result.layers;
          this.layerBounds = result.layers._bounds || {};
          this.layerOffsets = result.layers._offsets || {};
          this.layerRecords = this.renderRecords();
          this.templateEntities = [
            ...new Set(Object.values(result.layers._dependencies || {}).flat()),
          ];
          this.drawStage();
          const title = this.shadowRoot
            .querySelector(".canvas-wrap")
            ?.previousElementSibling?.querySelector("span");
          if (title) title.textContent = "Exact rendered preview";
          if (this.error) {
            // The render that failed has been fixed.
            this.error = false;
            this.status = "Exact rendered preview";
            this.renderStatus();
          }
        }
      } catch (error) {
        if (sequence === this.previewSequence) this.report(error);
      } finally {
        this.previewInFlight = false;
        if (this.previewQueued) {
          this.previewQueued = false;
          this.queuePreview();
        }
      }
    }, 200);
  }
}
// HA loads ha-entity-picker lazily. Opening this panel directly (or reloading
// it) happens before any page that uses the picker, so load it through a card
// editor. Runs in the background: nothing may wait on it.
async function loadEntityPicker() {
  try {
    const helpers = await window.loadCardHelpers?.();
    const card = await helpers?.createCardElement({
      type: "entities",
      entities: [],
    });
    await card?.constructor?.getConfigElement?.();
  } catch (error) {
    console.warn("ESL Designer: could not load the entity picker", error);
  }
}

if (!customElements.get("ble-esl-designer")) customElements.define("ble-esl-designer", BleEslDesigner);
