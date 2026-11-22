import { language, t, serverMessage } from "./i18n.js";
import { buttonHover, primaryHover } from "./button-hover.js";
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
const field = (hass, name, parameter, value, untouched = false) => {
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
  else if (parameter.type === "entity") {
    // The entities of the wanted domain are offered; any id may still be typed.
    const prefix = parameter.domain ? `${parameter.domain}.` : null;
    const ids = prefix
      ? Object.keys(hass?.states || {})
          .filter((entity) => entity.startsWith(prefix))
          .sort()
          .slice(0, 500)
      : [];
    // Untouched, a default that is not on this system gives way to one that is.
    const shown =
      untouched && ids.length && !hass.states[value] ? ids[0] : value;
    control = `<input id="${id}" data-param="${esc(name)}" type="text" list="${id}-list" autocomplete="off" spellcheck="false" value="${esc(shown)}"><datalist id="${id}-list">${ids.map((entity) => `<option value="${esc(entity)}"></option>`).join("")}</datalist>`;
  } else if (parameter.type === "number")
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
    for (const type of ["input", "change"])
      this.shadowRoot.addEventListener(type, (event) => {
        if (event.target.dataset?.param !== undefined) this.schedulePreview();
      });
    this.previews = {};
    this.previewFailures = new Set();
    this.category = "all";
  }
  async open(panel, onClose, context) {
    this.panel = panel;
    this.onClose = onClose;
    this.context = context;
    this.templates = null;
    this.chosen = null;
    this.note = "";
    this.issues = [];
    this.onResize = () => this.loadThumbnails();
    window.addEventListener("resize", this.onResize);
    this.render();
    try {
      this.templates = await panel.api("design_templates", {
        entry_id: context.entryId,
      });
    } catch (error) {
      this.note = serverMessage(this.panel.hass, error);
    }
    if (!this.closed) this.render();
    this.loadThumbnails();
  }
  // Only visible cards compete for the server's shared render lock. A single
  // in-flight request is allowed to finish, then the current viewport wins.
  loadThumbnails() {
    if (this.closed || this.chosen || this.thumbnailPending || this.formPending)
      return;
    const list = this.shadowRoot.querySelector(".list");
    if (!list) return;
    const gallery = this.shadowRoot.querySelector(".gallery-content");
    const viewport =
      getComputedStyle(gallery).overflowY === "auto" ? gallery : list;
    const bounds = viewport.getBoundingClientRect();
    const card = [...list.querySelectorAll("[data-template]")].find((node) => {
      const rect = node.getBoundingClientRect();
      return (
        rect.bottom > bounds.top &&
        rect.top < bounds.bottom &&
        !this.previews[node.dataset.template] &&
        !this.previewFailures.has(node.dataset.template)
      );
    });
    if (!card) return;
    const id = card.dataset.template;
    this.thumbnailPending = true;
    this.panel
      .api("preview_design_template", {
        entry_id: this.context.entryId,
        template_id: id,
      })
      .then((result) => {
        this.previews[id] = result.png;
        const image = [
          ...this.shadowRoot.querySelectorAll("[data-preview]"),
        ].find((node) => node.dataset.preview === id);
        if (image && !this.chosen && !this.closed) {
          image.src = result.png;
          image.hidden = false;
        }
      })
      .catch(() => this.previewFailures.add(id))
      .finally(() => {
        this.thumbnailPending = false;
        this.loadThumbnails();
      });
  }
  // The chosen template drawn with the values typed so far.
  schedulePreview(immediate = false) {
    clearTimeout(this.previewTimer);
    this.previewTimer = setTimeout(
      () => this.updateFormPreview(),
      immediate ? 0 : 350,
    );
  }
  async updateFormPreview() {
    if (this.closed || !this.chosen) return;
    const token = (this.previewToken = (this.previewToken || 0) + 1);
    let png;
    this.formPending = (this.formPending || 0) + 1;
    try {
      png = (
        await this.panel.api("preview_design_template", {
          entry_id: this.context.entryId,
          template_id: this.chosen.id,
          parameters: this.values(),
        })
      ).png;
    } catch (error) {
      if (this.closed || token !== this.previewToken) return;
      this.formPreview = null;
      this.formPreviewNote = "";
      this.showFormPreview(null, serverMessage(this.panel.hass, error));
      return;
    } finally {
      this.formPending--;
      this.loadThumbnails();
    }
    if (this.closed || token !== this.previewToken) return;
    this.formPreview = png;
    this.showFormPreview(png, "");
  }
  showFormPreview(png, message) {
    this.formPreviewNote = message;
    const image = this.shadowRoot.querySelector("[data-form-preview]");
    const note = this.shadowRoot.querySelector("[data-form-preview-note]");
    if (image) {
      if (png) image.src = png;
      image.hidden = !png;
    }
    if (note) {
      note.textContent = message;
      note.hidden = !message;
    }
  }
  close() {
    if (this.closed) return;
    this.closed = true;
    clearTimeout(this.previewTimer);
    window.removeEventListener("resize", this.onResize);
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
  templateOptions(note) {
    const hass = this.panel.hass;
    const entries = Object.entries(this.chosen.parameters);
    const group = (name) =>
      entries
        .filter(([, parameter]) => parameter.group === name)
        .map(([key, parameter]) =>
          field(
            hass,
            key,
            parameter,
            this.typed?.[key] ?? parameter.default,
            this.typed?.[key] === undefined,
          ),
        )
        .join("");
    const design = group("design"),
      automation = group("automation");
    return `<div class="scroll-area options">
        ${note}
        ${this.issues.length ? `<ul class="issues">${this.issues.map((issue) => `<li>${esc(issue)}</li>`).join("")}</ul>` : ""}
        <p class="muted">${esc(localized(hass, this.chosen.description))}</p>
        <img class="preview" data-form-preview alt="${esc(localized(hass, this.chosen.name))}" ${this.formPreview ? `src="${esc(this.formPreview)}"` : "hidden"}><p class="issues" data-form-preview-note ${this.formPreviewNote ? "" : "hidden"}>${esc(this.formPreviewNote || "")}</p>
        ${this.chosen.scaled ? `<p class="muted">${t(hass, "Adjusted to this display")} (${esc(this.chosen.layout)})</p>` : ""}
        ${design ? `<div class="fields">${design}</div>` : ""}
        ${automation ? `<h3>${t(hass, "Automation")}</h3><div class="fields">${automation}</div>` : ""}
      </div>`;
  }
  gallery(note) {
    if (!this.templates) return note;
    const hass = this.panel.hass;
    const save = this.panel.document.elements.length
      ? `<h3>${t(hass, "Save current design as a template")}</h3><div class="save"><input type="text" data-save-name maxlength="80" aria-label="${t(hass, "Design template name")}" placeholder="${t(hass, "Design template name")}" value="${esc(this.saveName || "")}"><button type="button" data-save>${t(hass, "Save as template")}</button></div>`
      : "";
    const categories = [
      ["all", "All"],
      ["weather", "Weather"],
      ["schedule", "Schedule"],
      ["smart_home", "Smart home"],
      ["labels", "Labels"],
    ];
    const filters = `<div class="filters" role="group" aria-label="${t(hass, "Template categories")}">${categories.map(([key, label]) => `<button type="button" data-category="${key}" aria-pressed="${this.category === key}">${t(hass, label)}</button>`).join("")}</div>`;
    const shown = this.templates.filter(
      (template) =>
        this.category === "all" || template.categories?.includes(this.category),
    );
    const list = this.templates.length
      ? `<p class="muted">${t(hass, "Choose a ready-made design. It is added as ordinary elements you can edit.")}</p><div class="scroll-area list">${
          shown.length
            ? shown
                .map(
                  (template) =>
                    `<button type="button" class="card" data-template="${esc(template.id)}"><img class="thumb" data-preview="${esc(template.id)}" alt="" ${this.previews[template.id] ? `src="${esc(this.previews[template.id])}"` : "hidden"}><b>${esc(localized(hass, template.name))}</b><span class="muted">${esc(localized(hass, template.description))}</span><span class="muted">${template.source === "user" ? `${t(hass, "My template")} · ` : ""}${esc(template.layout)}${template.scaled ? ` · ${t(hass, "Adjusted to this display")}` : ""}</span></button>`,
                )
                .join("")
            : `<p class="muted">${t(hass, "No templates in this category.")}</p>`
        }</div>`
      : `<p class="muted">${t(hass, "No design templates fit this display.")}</p>`;
    return `<div class="gallery-content">${this.templates.length ? filters : ""}${list}${save}${note}</div>`;
  }
  render() {
    if (this.chosen && this.shadowRoot.querySelector("[data-param]"))
      this.typed = this.values();
    const nameInput = this.shadowRoot.querySelector("[data-save-name]");
    if (nameInput) this.saveName = nameInput.value;
    const oldList = this.shadowRoot.querySelector(".list");
    const oldGallery = this.shadowRoot.querySelector(".gallery-content");
    if (oldList && !this.chosen) {
      this.listScroll = oldList.scrollTop;
      this.galleryScroll = oldGallery.scrollTop;
    }
    const active = this.shadowRoot.activeElement;
    const focusKey = active?.dataset?.category
      ? `[data-category="${active.dataset.category}"]`
      : active?.dataset?.template
        ? `[data-template="${CSS.escape(active.dataset.template)}"]`
        : null;
    const hass = this.panel.hass;
    const { width, height } = this.context.tag;
    const done = this.done;
    const note = this.note
      ? `<p class="note" role="status" tabindex="-1" autofocus>${esc(t(hass, this.note))}</p>`
      : "";
    this.shadowRoot.innerHTML = `<style>
      dialog{width:min(560px,94vw);max-height:90vh;max-height:90dvh;box-sizing:border-box;overflow:hidden;padding:0;border:1px solid var(--divider-color,#cbd3de);border-radius:10px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui}
      dialog::backdrop{background:#0006}
      form{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:calc(90vh - 2px);max-height:calc(90dvh - 2px);box-sizing:border-box}
      form > :not(.scroll-area,.gallery-content),.gallery-content > :not(.scroll-area){flex-shrink:0}
      .scroll-area{min-height:0;overflow:auto;overscroll-behavior:contain;padding:3px;margin:-3px}
      .gallery-content,.options{display:flex;flex-direction:column;gap:12px;min-height:0}
      .options > *{flex-shrink:0}
      h2,h3{margin:0;font-size:16px} h3{font-size:14px}
      button{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px 12px;cursor:pointer}
      button.primary{background:var(--primary-color,#166d75);color:var(--text-primary-color,white);border-color:var(--primary-color,#166d75)}${primaryHover}${buttonHover()}
      button:disabled{opacity:.5;cursor:default}
      .list{display:grid;gap:8px}
      .filters{display:flex;gap:5px;flex-wrap:wrap}.filters button{padding:5px 8px}.filters [aria-pressed="true"]{border-color:var(--primary-color,#166d75);color:var(--primary-color,#166d75)}
      .card{display:flex;flex-direction:column;gap:2px;text-align:left}
      .thumb,.preview{max-width:100%;box-sizing:border-box;border:1px solid var(--divider-color,#cbd3de);border-radius:4px;image-rendering:pixelated;background:white;align-self:flex-start}
      .thumb{display:block;width:${width}px;height:auto;aspect-ratio:${width}/${height};object-fit:contain}
      .thumb[hidden]{visibility:hidden}
      .fields{display:grid;grid-template-columns:minmax(0,1fr);gap:10px}
      .fields input,.fields select{min-width:0}
      label{display:grid;gap:4px;font-size:13px}
      input[type=text],input[type=number],input[type=time],select{font:inherit;padding:6px 8px;border:1px solid var(--divider-color,#cbd3de);border-radius:6px;background:var(--secondary-background-color,#f5f7fa);color:inherit}
      input[type=checkbox]{justify-self:start}
      .save{display:flex;gap:6px} .save input{flex:1;min-width:0}
      .actions{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}
      .muted{color:var(--secondary-text-color,#637083);font-size:12px;margin:0}
      .note{margin:0;font-size:13px;overflow-wrap:anywhere}
      .issues{color:#c33;margin:0;padding-left:18px;font-size:12px}
      @media (max-height:400px){
        form{padding:10px;gap:8px}
        .actions button{padding:6px 8px}
        .gallery-content{overflow:auto;overscroll-behavior:contain;padding:3px;margin:-3px}
        .list{flex-shrink:0;overflow:visible}
      }
      @media (max-width:420px){
        .options + .actions:has([data-mode]){display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px}
        .options + .actions button{padding:4px 6px;min-width:0;font-size:12px;overflow-wrap:anywhere}
        .options + .actions [data-mode=create]{grid-column:span 2}
        .options + .actions [data-close]{grid-column:3}
      }
    </style><dialog aria-label="${t(hass, "Design gallery")}"><form method="dialog">
      <h2>${t(hass, "Design gallery")}</h2>
      ${this.chosen ? this.templateOptions(note) : this.gallery(note)}
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
    const list = this.shadowRoot.querySelector(".list");
    const gallery = this.shadowRoot.querySelector(".gallery-content");
    if (list) {
      list.scrollTop = this.listScroll || 0;
      gallery.scrollTop = this.galleryScroll || 0;
      list.addEventListener("scroll", () => this.loadThumbnails());
      gallery.addEventListener("scroll", () => this.loadThumbnails());
      const compact = getComputedStyle(gallery).overflowY === "auto";
      if (this.focusTemplate && !(this.note && compact)) {
        list
          .querySelector(`[data-template="${CSS.escape(this.focusTemplate)}"]`)
          ?.focus();
      }
      this.focusTemplate = null;
      if (this.note && compact)
        this.shadowRoot
          .querySelector(".note")
          ?.scrollIntoView({ block: "nearest" });
      requestAnimationFrame(() => this.loadThumbnails());
    }
    if (focusKey && !this.chosen)
      this.shadowRoot.querySelector(focusKey)?.focus();
    else if (!this.note && !this.shadowRoot.activeElement?.dataset?.template)
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
    if (this.pending) return;
    if ("back" in button.dataset) {
      this.chosen = null;
      this.typed = null;
      this.formPreview = null;
      this.formPreviewNote = "";
      this.previewToken = (this.previewToken || 0) + 1;
      this.focusTemplate = this.lastTemplate;
      this.note = "";
      this.issues = [];
      return this.render();
    }
    if (button.dataset.category) {
      this.category = button.dataset.category;
      this.listScroll = 0;
      this.galleryScroll = 0;
      // Discard the old scroll positions before rebuilding the filtered list.
      this.shadowRoot.querySelector(".list").scrollTop = 0;
      this.shadowRoot.querySelector(".gallery-content").scrollTop = 0;
      this.render();
      return;
    }
    if ("save" in button.dataset) {
      if (this.pending) return;
      this.pending = true;
      for (const control of this.shadowRoot.querySelectorAll(
        "[data-category], [data-template], [data-save]",
      ))
        control.disabled = true;
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
        const input = this.shadowRoot.querySelector("[data-save-name]");
        if (input) input.value = "";
        this.saveName = "";
        this.category = "all";
        this.focusTemplate = saved.id;
        this.note = {
          key: "Saved template {name}.",
          values: { name: saved.id },
        };
        this.issues = [];
      } catch (error) {
        this.note = serverMessage(this.panel.hass, error);
      } finally {
        this.pending = false;
      }
      if (!this.closed) this.render();
      // The saved template needs its thumbnail.
      this.loadThumbnails();
      return;
    }
    if (button.dataset.template) {
      this.lastTemplate = button.dataset.template;
      this.listScroll = this.shadowRoot.querySelector(".list")?.scrollTop || 0;
      this.galleryScroll =
        this.shadowRoot.querySelector(".gallery-content")?.scrollTop || 0;
      this.chosen = this.templates.find(
        (template) => template.id === button.dataset.template,
      );
      this.note = "";
      this.typed = null;
      this.formPreview = null;
      this.formPreviewNote = "";
      this.render();
      this.schedulePreview(true);
      return;
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
        this.note = serverMessage(this.panel.hass, error);
        this.render();
      } else this.close();
    } finally {
      this.pending = false;
    }
  }
}
if (!customElements.get("ble-esl-template-dialog"))
  customElements.define("ble-esl-template-dialog", TemplateDialog);
