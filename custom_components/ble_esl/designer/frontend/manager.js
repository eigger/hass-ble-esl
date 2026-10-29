import { materialIcon } from "./editor/material-icons.js";
import { decodeAutomationDesign } from "./editor/automation-source.js";
import { t, language, bindStatic, localize, errorText } from "./i18n.js";
import { hasStoredDraft } from "./editor/draft-store.js";
import "./panel.js";
import "./automation-dialog.js";
import { chooseOne, closeChoiceDialogs } from "./choice-dialog.js";

export const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const valid = (state) =>
  state && !["unknown", "unavailable"].includes(state.state);
const css = `
:host{display:flex;flex-direction:column;height:var(--ble-esl-panel-height,100%);min-height:0;overflow:hidden;font:14px system-ui;color:var(--primary-text-color,#18232f);background:var(--primary-background-color,#f5f7fa)}
*{box-sizing:border-box}[hidden]{display:none!important}button,input,select{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#ccd4dc);border-radius:8px;padding:9px 12px}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #16838c;outline-offset:3px}button.primary{background:#166d75;color:white;border-color:#166d75}
#dashboard,#editor{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}.dashboard-content{flex:1;min-height:0;overflow:auto;scrollbar-gutter:stable}#editor-slot{flex:1;min-height:0;overflow:hidden}header,.editor-nav{flex:none;height:var(--header-height,56px);min-height:56px;padding:0 24px}header{display:flex;align-items:center;gap:12px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#ddd)}.header-title-wrap{display:flex;align-items:center;gap:8px;flex:1;min-width:0}h1{font-size:20px;font-weight:500;margin:0;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.version-tag{display:inline-flex;align-items:center;flex:none;font-size:12px;font-weight:600;color:var(--secondary-text-color,#64748b);background:var(--secondary-background-color,#f1f5f9);padding:2px 7px;border-radius:9999px;line-height:1.3;border:1px solid var(--divider-color,#dde3e8)}h2{margin:0;font-size:18px;overflow-wrap:anywhere}.controls{display:flex;flex-wrap:wrap;gap:10px;padding:20px 24px 12px}.controls input{flex:1;min-width:150px}.controls select{flex:none;min-width:12rem;max-width:100%}.controls input,.controls select{height:40px}.controls select{appearance:none;-webkit-appearance:none;padding-right:30px;background-image:linear-gradient(45deg,transparent 50%,currentColor 50%),linear-gradient(135deg,currentColor 50%,transparent 50%);background-position:calc(100% - 17px) 50%,calc(100% - 12px) 50%;background-size:5px 5px,5px 5px;background-repeat:no-repeat}.summary{padding:0 24px 16px;color:var(--secondary-text-color,#637083)}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px;padding:0 24px 24px}.card{min-width:0;padding:18px;background:var(--card-background-color,white);border:1px solid var(--divider-color,#dde3e8);border-radius:12px;display:flex;flex-direction:column;gap:12px}.top{display:flex;align-items:center;gap:8px}.top>h2{flex:1;min-width:0;height:24px;line-height:24px;overflow:hidden}.product{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;height:32px;line-height:16px}.dimensions{line-height:16px;white-space:nowrap}.alias{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.alias{border:0;padding:0;text-align:left;background:transparent;font-size:18px;font-weight:600;overflow-wrap:anywhere}.muted{color:var(--secondary-text-color,#637083);font-size:12px;overflow-wrap:anywhere}.battery{flex:none;margin-left:auto;white-space:nowrap;font-size:12px}.battery button,.battery>span{display:flex;align-items:center;gap:6px;line-height:24px}.battery button{padding:0;border:0;border-radius:0;background:transparent}.battery svg{width:24px;height:16px;flex:none}.image{height:180px;padding:10px;display:flex;align-items:center;justify-content:center;border-radius:8px;background:var(--secondary-background-color,#eef1f4);overflow:hidden}.image img{max-width:100%;max-height:100%;object-fit:contain;image-rendering:pixelated}.image button{display:contents}.badges{display:flex;flex-wrap:wrap;gap:8px}.badge{padding:4px 8px;border-radius:6px;font-size:12px;background:var(--secondary-background-color,#eef1f4);border:0}.bad{color:var(--error-color,#b3261e);background:#b3261e12}.good{color:var(--success-color,#28754a);background:#28754a12}.facts{display:grid;grid-template-columns:1fr minmax(0,1fr);gap:8px;margin:0;font-size:13px}.facts dt{color:var(--secondary-text-color,#637083)}.facts dd{margin:0;text-align:right;overflow-wrap:anywhere}.facts button{padding:0;border:0;background:transparent;text-align:right;font:inherit}.actions{display:flex;gap:8px;margin-top:auto}.actions button{flex:1}.message-wrap{position:fixed;left:12px;right:12px;bottom:16px;margin-inline:auto;width:fit-content;max-width:640px;z-index:60;display:flex;align-items:center;gap:8px;box-sizing:border-box;padding:10px 14px;border:1px solid var(--divider-color,#cbd3de);border-radius:8px;background:var(--card-background-color,white);box-shadow:0 5px 24px #0003}.message-wrap[hidden]{display:none}.message-wrap button{flex:none;padding:0 8px;line-height:20px}.message-wrap.error{border-color:var(--error-color,#b3261e)}.message{margin:0}.message.error{color:var(--error-color,#b3261e)}.message.success{color:var(--success-color,#28754a)}.message.info{color:var(--primary-text-color,#18232f)}.image-caption{min-height:15px;font-size:11px;color:var(--secondary-text-color,#637083);margin-top:-6px}.read-only{color:var(--secondary-text-color,#637083)}.low-battery{color:var(--warning-color,#986000);background:#98600012}.draft{color:var(--warning-color,#986000);background:#98600012}.actions{flex-direction:column}.actions button:not(.primary){font-size:12px;padding:7px 10px}.editor-nav{height:auto;padding-top:8px;padding-bottom:8px}.editor-context{min-width:0;overflow-wrap:anywhere;line-height:1.4;font-size:13px}.editor-nav{display:flex;align-items:center;gap:12px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#ddd)}.editor-nav span{flex:1}ble-esl-designer{height:100%;min-height:0}.empty{grid-column:1/-1;padding:40px;text-align:center;color:var(--secondary-text-color,#637083)}
@media(max-width:480px){#dashboard>header{gap:8px}#dashboard>header .version-tag{display:none!important}#dashboard>header button[data-action="refresh"]{padding:8px 9px}}
@media(max-width:650px){header,.editor-nav{padding:0 12px}.editor-nav{flex-wrap:wrap;height:auto;min-height:var(--header-height,56px);padding-top:6px;padding-bottom:6px;row-gap:6px}.editor-nav .editor-context{order:3;flex:1 1 100%}.controls{padding:16px 12px 12px}.summary{padding:0 12px 16px}.grid{padding:0 12px 16px;grid-template-columns:minmax(0,1fr);gap:12px}.message{margin:0}.card{padding:16px}}
`;

const AUTOMATION_DRAFT_KEY = "ble_esl_designer_automation_draft";
class EslManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.tags = [];
    this.automationCache = new Map();
    this.automationErrors = new Set();
    this.automationVersions = new Map();
    this.query = "";
    this.filter = "all";
    this.sort = "default";
    this.view = "dashboard";
    this.shadowRoot.innerHTML = `<style>${css}</style><section id="dashboard"><header><ha-menu-button></ha-menu-button><div class="header-title-wrap"><h1>${t(this.hass, "ESL Manager")}</h1><span class="version-tag" id="panel-version" title="${t(this.hass, "BLE ESL integration version")}" style="display: none;"></span></div><button data-action="refresh" aria-label="${t(this.hass, "Refresh")}" title="${t(this.hass, "Refresh")}">${materialIcon("reload")}</button></header><div class="dashboard-content"><div class="controls"><input id="search" type="search" aria-label="${t(this.hass, "Search ESLs")}" placeholder="${t(this.hass, "Search aliases or devices")}"><select id="filter" aria-label="${t(this.hass, "Filter ESLs")}"><option value="all">${t(this.hass, "All ESLs")}</option><option value="error">${t(this.hass, "Errors")}</option><option value="unsynced">${t(this.hass, "Not in sync")}</option><option value="low-battery">${t(this.hass, "Low battery")}</option></select><select id="sort" aria-label="${t(this.hass, "Sort ESLs")}"><option value="default">${t(this.hass, "Default order")}</option><option value="attention">${t(this.hass, "Needs attention first")}</option><option value="battery">${t(this.hass, "Battery: lowest first")}</option><option value="name">${t(this.hass, "Name (A–Z)")}</option></select></div><div class="summary" role="status"></div><div class="grid"></div></div></section><div class="message-wrap" hidden><p class="message" role="status"></p><button type="button" data-action="dismiss-message">${materialIcon("close")}</button></div><section id="editor" hidden><div class="editor-nav"><button data-action="dashboard">${t(this.hass, "← Dashboard")}</button><span class="editor-context"></span><button data-action="editor-automations">${t(this.hass, "Connected automations")}</button></div><div id="editor-slot"></div></section>`;
    this.editorNav = this.shadowRoot.querySelector(".editor-nav");
    this.editorContext = this.editorNav.querySelector(".editor-context");
    bindStatic(this.shadowRoot);
    this.automationDialog = document.createElement("ble-esl-automation-dialog");
    this.shadowRoot.append(this.automationDialog);
    this.addEventListener("automations-changed", (event) => {
      const entryId = event.detail.entry_id;
      this.automationVersions.set(
        entryId,
        (this.automationVersions.get(entryId) || 0) + 1,
      );
      this.automationCache.set(entryId, event.detail.data);
      this.automationErrors.delete(event.detail.entry_id);
      this.renderCards();
    });
    this.addEventListener("designer-context-changed", () =>
      this.updateEditorContext(),
    );
    this.addEventListener("automation-edit-request", (event) =>
      this.editAutomation(event.detail.entry_id, event.detail.entity_id),
    );
    this.addEventListener("automation-save-request", (event) =>
      this.saveAutomation(event.detail),
    );
    this.addEventListener("automation-save-as-request", (event) =>
      this.saveToOtherAutomation(event.detail),
    );
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
    this.editorNav.addEventListener("click", (event) => {
      event.stopPropagation();
      this.click(event);
    });
    this.shadowRoot
      .querySelector("#search")
      .addEventListener("input", (event) => {
        this.query = event.target.value;
        this.renderCards();
      });
    this.shadowRoot
      .querySelector("#filter")
      .addEventListener("change", (event) => {
        this.filter = event.target.value;
        this.renderCards();
      });
    this.shadowRoot
      .querySelector("#sort")
      .addEventListener("change", (event) => {
        this.sort = event.target.value;
        this.renderCards();
      });
    this._updateVersionTag();
  }
  set panel(value) {
    this._panel = value;
    if (this.editor) this.editor.panel = value;
    this._updateVersionTag();
  }
  get panel() {
    return this._panel;
  }
  get version() {
    return (
      this._panel?.config?.version ||
      this._backendVersion ||
      import.meta.url.match(/\/ble_esl_designer\/([^/]+)\//)?.[1] ||
      ""
    );
  }
  _updateVersionTag() {
    const el = this.shadowRoot?.getElementById("panel-version");
    if (!el) return;
    const v = this.version;
    if (v) {
      el.textContent = `v${v}`;
      const titleStr =
        t(this.hass, "BLE ESL integration version") ||
        "BLE ESL integration version";
      el.title = `${titleStr} v${v}`;
      el.style.display = "inline-flex";
    } else {
      el.style.display = "none";
    }
  }
  set narrow(value) {
    this._narrow = value;
    if (this.editor) this.editor.narrow = value;
  }
  get narrow() {
    return this._narrow;
  }
  set hass(value) {
    const previous = this._hass;
    this._hass = value;
    localize(this.shadowRoot, value);
    this._updateVersionTag();
    if (this.messageKey)
      this.message(this.messageKey, this.messageKind, this.messageValues);
    if (this.editor) this.editor.hass = value;
    this.automationDialog.updateHass(value);
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    menu.hass = value;
    menu.narrow = this.narrow;
    if (this.isConnected && !this.started) this.refresh();
    else if (
      language(previous) !== language(value) ||
      this.tags.some((tag) =>
        Object.values(tag.entities || {}).some(
          (id) => previous?.states[id] !== value.states[id],
        ),
      ) ||
      Object.keys({ ...previous?.states, ...value.states }).some(
        (id) =>
          id.startsWith("automation.") &&
          previous?.states[id] !== value.states[id],
      )
    )
      this.renderCards();
  }
  get hass() {
    return this._hass;
  }
  connectedCallback() {
    // HA's custom-panel wrapper may have an automatic height. Bound our own
    // panel to the available viewport so that only the content can overflow.
    this.resizePanel = () => {
      const height = Math.max(
        0,
        window.innerHeight - this.getBoundingClientRect().top,
      );
      this.style.setProperty("--ble-esl-panel-height", `${height}px`);
    };
    this.panelObserver = new ResizeObserver(this.resizePanel);
    this.panelObserver.observe(this);
    window.addEventListener("resize", this.resizePanel);
    this.resizePanel();
    if (typeof ResizeObserver === "function") {
      this.toastObserver = new ResizeObserver(() => this.updateToastOffset());
      this.toastObserver.observe(
        this.shadowRoot.querySelector(".message-wrap"),
      );
    }
    if (this.hass && !this.started) this.refresh();
    this.onHistory = () => this.restoreLocation();
    window.addEventListener("popstate", this.onHistory);
    this.onTagChanged = (event) => {
      if (this.view === "editor") this.rememberTag(event.detail.entry_id);
    };
    this.addEventListener("tag-changed", this.onTagChanged);
    this.clockTimer = setInterval(() => {
      if (this.view === "dashboard") this.renderCards();
    }, 60000);
  }
  disconnectedCallback() {
    this.persistAutomationDraft();
    window.removeEventListener("popstate", this.onHistory);
    this.removeEventListener("tag-changed", this.onTagChanged);
    clearInterval(this.clockTimer);
    clearTimeout(this.messageTimer);
    this.toastObserver?.disconnect();
    closeChoiceDialogs();
    this.panelObserver?.disconnect();
    window.removeEventListener("resize", this.resizePanel);
  }
  api(action, extra = {}) {
    return this.hass.callWS({ type: "ble_esl/designer", action, ...extra });
  }
  // The designer's own toast stacks above this one instead of overlapping it.
  updateToastOffset() {
    const wrap = this.shadowRoot.querySelector(".message-wrap");
    this.editor?.style.setProperty(
      "--toast-offset",
      wrap.hidden ? "0px" : `${wrap.offsetHeight + 8}px`,
    );
  }
  message(message = "", kind = "error", values = undefined) {
    const node = this.shadowRoot.querySelector(".message");
    this.messageKey = message;
    this.messageKind = kind;
    this.messageValues = values;
    node.textContent = t(this.hass, message, values);
    const wrap = node.parentElement;
    wrap.hidden = !message;
    wrap.classList.toggle("error", !!message && kind === "error");
    wrap
      .querySelector("button")
      .setAttribute("aria-label", t(this.hass, "Dismiss message"));
    this.updateToastOffset();
    node.classList.toggle("error", !!message && kind === "error");
    node.classList.toggle("success", !!message && kind === "success");
    node.classList.toggle("info", !!message && kind === "info");
    node.setAttribute("role", kind === "error" ? "alert" : "status");
    clearTimeout(this.messageTimer);
    if (!message) return;
    // Errors stay until dismissed; confirmations clear themselves.
    if (kind !== "error")
      this.messageTimer = setTimeout(() => this.message(), 6000);
  }
  async refresh() {
    this.started = true;
    this.message();
    const button = this.shadowRoot.querySelector('[data-action="refresh"]');
    button.disabled = true;
    this.shadowRoot.querySelector(".summary").textContent = t(
      this.hass,
      "Loading ESLs…",
    );
    try {
      this.tags = await this.api("list");
      this.renderCards();
      this.restoreLocation();
      await this.loadAutomations();
    } catch (error) {
      this.message(errorText(this.hass, "Could not load ESL data", error));
    } finally {
      button.disabled = false;
    }
  }
  async loadAutomations() {
    const run = (this.automationRun = (this.automationRun || 0) + 1);
    const tags = [...this.tags];
    // Bound concurrent requests when many ESLs are configured.
    for (let offset = 0; offset < tags.length; offset += 4) {
      await Promise.all(
        tags.slice(offset, offset + 4).map(async (tag) => {
          const version = this.automationVersions.get(tag.entry_id);
          try {
            const data = await this.api("automations", {
              entry_id: tag.entry_id,
            });
            if (
              run !== this.automationRun ||
              version !== this.automationVersions.get(tag.entry_id)
            )
              return;
            this.automationCache.set(tag.entry_id, data);
            this.automationErrors.delete(tag.entry_id);
          } catch (error) {
            if (
              run === this.automationRun &&
              version === this.automationVersions.get(tag.entry_id)
            )
              this.automationErrors.add(tag.entry_id);
          }
        }),
      );
      if (run !== this.automationRun) return;
      this.renderCards();
    }
  }
  automationLabel(tag) {
    if (this.automationErrors.has(tag.entry_id))
      return t(this.hass, "Automations unavailable · Retry");
    const data = this.automationCache.get(tag.entry_id);
    if (!data) return t(this.hass, "Loading automations…");
    const linked = data.linked.map((item) => {
      const state = !item.missing && this.hass.states[item.entity_id];
      return state
        ? {
            ...item,
            state: state.state,
            name: state.attributes.friendly_name || item.name,
          }
        : { ...item, state: "unavailable" };
    });
    if (!linked.length) return t(this.hass, "No connected automations");
    const active = linked.filter((item) => item.state === "on").length;
    if (linked.length === 1)
      return `${linked[0].name} · ${linked[0].missing || !["on", "off"].includes(linked[0].state) ? t(this.hass, "Unavailable") : active ? t(this.hass, "Active") : t(this.hass, "Inactive")}`;
    return t(this.hass, "{count} automations · {active} active", {
      count: linked.length,
      active,
    });
  }
  showAutomations(tag, anchor) {
    this.automationDialog.show(
      this.hass,
      { ...tag, name: this.alias(tag) },
      anchor,
      () => {
        if (anchor.isConnected) anchor.focus();
        else
          (
            this.shadowRoot.querySelector(
              `[data-action="automations"][data-entry="${CSS.escape(tag.entry_id)}"]`,
            ) ||
            this.shadowRoot.querySelector(
              `[data-action="edit"][data-entry="${CSS.escape(tag.entry_id)}"]`,
            )
          )?.focus();
      },
    );
  }
  state(tag, key) {
    return this.hass?.states[tag.entities?.[key]];
  }
  alias(tag) {
    const state = this.state(tag, "alias");
    return valid(state) && state.state.trim() ? state.state : tag.title;
  }
  // An unsaved tag design in the editor, or one kept from before the panel was left.
  hasDraft(tag) {
    return this.editor?.ready
      ? this.editor.hasDraft(tag.entry_id)
      : hasStoredDraft(tag.entry_id);
  }
  hasError(tag) {
    const state = this.state(tag, "write_duration");
    return (
      valid(state) && !!state.attributes.error && !state.attributes.skipped
    );
  }
  batteryValue(tag) {
    const state = this.state(tag, "battery");
    return valid(state) &&
      state.state.trim() !== "" &&
      Number.isFinite(Number(state.state))
      ? Number(state.state)
      : Infinity;
  }
  lowBattery(tag) {
    if (tag.entities?.battery_low) {
      const state = this.state(tag, "battery_low");
      return valid(state) && state.state === "on";
    }
    return false;
  }
  editableAutomations(tag) {
    return (this.automationCache.get(tag.entry_id)?.linked || []).filter(
      (item) =>
        !item.missing &&
        item.id &&
        ["on", "off"].includes(this.hass.states[item.entity_id]?.state),
    );
  }
  cardActions(tag) {
    const entry = escapeHtml(tag.entry_id);
    return `<button class="primary" data-action="edit" data-entry="${entry}">${t(this.hass, "Edit tag design")}</button>`;
  }
  updateEditorContext() {
    const node = this.editorContext;
    const session = this.automationEditSession;
    const entry =
      session?.entry_id ||
      (this.editor?.mode === "template"
        ? this.editor.displaySession?.tag
        : this.editor?.tag
      )?.entry_id;
    const tag = this.tags.find((item) => item.entry_id === entry);
    if (!tag) {
      node.textContent = t(this.hass, "Designer");
      return;
    }
    const entity = this.automationEditSource?.entity_id || session?.entity_id;
    const name =
      entity &&
      (this.hass.states[entity]?.attributes.friendly_name ||
        this.automationEditSource?.name ||
        entity);
    const context = session
      ? this.automationEditSource
        ? t(this.hass, "Automation design")
        : t(this.hass, "Importing automation…")
      : t(
          this.hass,
          this.editor?.mode === "template"
            ? "Sensor tile styles"
            : "Tag design",
        );
    node.textContent = [this.alias(tag), name, context]
      .filter(Boolean)
      .join(" › ");
  }
  relative(value) {
    const date = new Date(value);
    if (!value || !Number.isFinite(date.getTime())) return "—";
    const minutes = Math.max(
      0,
      Math.floor((Date.now() - date.getTime()) / 60000),
    );
    const locale = this.hass?.locale?.language || navigator.language;
    const format = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
    if (minutes < 1) return format.format(0, "minute");
    if (minutes < 60) return format.format(-minutes, "minute");
    if (minutes < 1440) return format.format(-Math.floor(minutes / 60), "hour");
    return format.format(-Math.floor(minutes / 1440), "day");
  }
  entityButton(tag, key, label, extra = "") {
    const id = tag.entities?.[key];
    return id
      ? `<button data-entity="${escapeHtml(id)}" ${extra}>${escapeHtml(label)}</button>`
      : escapeHtml(label);
  }
  batteryHtml(tag, battery) {
    const known = valid(battery) && Number.isFinite(Number(battery.state));
    const value = known
      ? `${battery.state}${battery.attributes.unit_of_measurement || "%"}`
      : "—";
    const label = known
      ? t(this.hass, "Battery {value}", { value })
      : t(this.hass, "Battery —");
    const level = known
      ? Math.min(100, Math.max(0, Math.round(Number(battery.state) / 10) * 10))
      : null;
    const batteryIcon =
      level === null
        ? "mdi:battery-unknown"
        : level === 100
          ? "mdi:battery"
          : level === 0
            ? "mdi:battery-outline"
            : `mdi:battery-${level}`;
    const content = `${materialIcon(batteryIcon, 24)}<span>${escapeHtml(value)}</span>`;
    return tag.entities?.battery
      ? `<button data-entity="${escapeHtml(tag.entities.battery)}" aria-label="${escapeHtml(label)}" title="${escapeHtml(label)}">${content}</button>`
      : `<span role="img" aria-label="${escapeHtml(label)}" title="${escapeHtml(label)}">${content}</span>`;
  }
  card(tag) {
    const e = escapeHtml;
    const alias = this.alias(tag);
    const battery = this.state(tag, "battery");
    const image = this.state(tag, "last_updated_content");
    const sync = this.state(tag, "display_in_sync");
    const duration = this.state(tag, "write_duration");
    const error = this.hasError(tag);
    const synced = valid(sync) && sync.state === "on";
    const syncLabel = !valid(sync)
      ? t(this.hass, "Sync unknown")
      : synced
        ? t(this.hass, "In sync")
        : t(this.hass, "Not in sync");
    const at = valid(image) ? image.state : null;
    // ImageEntity's state is its image_last_updated timestamp. Never use last_changed:
    // that can be the entity's restore time rather than the last successful write.
    const picture = valid(image) && image.attributes.entity_picture;
    // ImageEntity's proxy URL/token stays constant across successful writes.
    // Include its state timestamp so the browser fetches the new image.
    const url = picture
      ? `${picture}${picture.includes("?") ? "&" : "?"}updated=${encodeURIComponent(at)}`
      : null;
    const durationValue =
      valid(duration) && Number.isFinite(Number(duration.state))
        ? `${Number(duration.state).toFixed(1)} s`
        : "—";
    const automationData = this.automationCache.get(tag.entry_id);
    const showAutomationDialog =
      !automationData ||
      automationData.linked.length > 0 ||
      this.automationErrors.has(tag.entry_id);
    const automationLabel = this.automationLabel(tag);
    return `<article class="card" data-entry="${e(tag.entry_id)}"><div class="card-heading"><div class="top"><h2>${this.entityButton(tag, "alias", alias, `class="alias" title="${t(this.hass, "Edit alias")}"`)}</h2><div class="battery">${this.batteryHtml(tag, battery)}</div></div><div class="muted product" title="${e(tag.title)}">${e(tag.title)}</div><div class="muted dimensions">${tag.baseWidth ?? tag.width} × ${tag.baseHeight ?? tag.height} · ${e(tag.colors)}</div></div><div class="image">${url ? `<button data-entity="${e(tag.entities.last_updated_content)}" aria-label="${e(t(this.hass, "Last successful image for {alias}", { alias }))}"><img src="${e(url)}" alt="${e(t(this.hass, "Last successful image for {alias}", { alias }))}"></button>` : `<span class="muted">${t(this.hass, "No successful image")}</span>`}</div><div class="image-caption">${url ? t(this.hass, "Last successful image") : ""}</div><div class="badges">${this.hasDraft(tag) ? `<span class="badge draft">${t(this.hass, "Unsaved changes")}</span>` : ""}${tag.writable === false ? `<span class="badge read-only">${t(this.hass, "Read only")}</span>` : ""}${this.lowBattery(tag) ? this.entityButton(tag, tag.entities?.battery_low ? "battery_low" : "battery", t(this.hass, "Low battery"), `class="badge low-battery" title="${t(this.hass, "Low battery")}"`) : ""}${this.entityButton(tag, "display_in_sync", syncLabel, `class="badge ${synced ? "good" : ""}"`)}${this.entityButton(tag, "write_duration", error ? t(this.hass, "Transmission error") : !valid(duration) || (!duration.attributes.success && !duration.attributes.skipped && !duration.attributes.error) ? t(this.hass, "No transmission result") : duration.attributes.skipped ? t(this.hass, "Skipped: {reason}", { reason: duration.attributes.skipped }) : t(this.hass, "No error"), `class="badge ${error ? "bad" : ""}"`)}</div><dl class="facts"><dt>${t(this.hass, "Last successful send")}</dt><dd>${this.entityButton(tag, "last_updated_content", this.relative(at), `title="${e(at ? new Date(at).toLocaleString(this.hass?.locale?.language || navigator.language) : t(this.hass, "No successful send"))}"`)}</dd><dt>${t(this.hass, "Transmission duration")}</dt><dd>${this.entityButton(tag, "write_duration", durationValue)}</dd><dt>${t(this.hass, "Automations")}</dt><dd>${showAutomationDialog ? `<button data-action="automations" data-entry="${e(tag.entry_id)}" title="${e(automationLabel)}">${e(automationLabel)}</button>` : e(automationLabel)}</dd></dl><div class="actions">${this.cardActions(tag)}</div></article>`;
  }
  renderCards() {
    this.updateEditorContext();
    const errors = this.tags.filter((tag) => this.hasError(tag)).length;
    const unsynced = this.tags.filter(
      (tag) => this.state(tag, "display_in_sync")?.state === "off",
    ).length;
    this.shadowRoot.querySelector(".summary").textContent = t(
      this.hass,
      "{count} ESLs · {errors} errors · {unsynced} not in sync",
      { count: this.tags.length, errors, unsynced },
    );
    const query = this.query.toLocaleLowerCase().trim();
    const tags = this.tags.filter(
      (tag) =>
        `${this.alias(tag)} ${tag.title}`.toLocaleLowerCase().includes(query) &&
        (this.filter !== "error" || this.hasError(tag)) &&
        (this.filter !== "unsynced" ||
          this.state(tag, "display_in_sync")?.state === "off") &&
        (this.filter !== "low-battery" || this.lowBattery(tag)),
    );
    if (this.sort !== "default") {
      const attention = (tag) =>
        this.hasError(tag)
          ? 0
          : this.state(tag, "display_in_sync")?.state === "off"
            ? 1
            : this.lowBattery(tag)
              ? 2
              : 3;
      const compareName = (a, b) =>
        this.alias(a).localeCompare(
          this.alias(b),
          this.hass?.locale?.language || navigator.language,
          { numeric: true },
        ) || a.entry_id.localeCompare(b.entry_id);
      tags.sort((a, b) => {
        const difference =
          this.sort === "attention"
            ? attention(a) - attention(b)
            : this.sort === "battery"
              ? this.batteryValue(a) - this.batteryValue(b)
              : 0;
        return (Number.isNaN(difference) ? 0 : difference) || compareName(a, b);
      });
    }
    const grid = this.shadowRoot.querySelector(".grid");
    const focused = this.shadowRoot.activeElement;
    const entry = focused?.closest("[data-entry]")?.dataset.entry;
    const entity = focused?.dataset.entity;
    const action = focused?.dataset.action;
    const existing = new Map(
      [...grid.querySelectorAll(".card")].map((card) => [
        card.dataset.entry,
        card,
      ]),
    );
    const cards = tags.map((tag) => {
      const template = document.createElement("template");
      template.innerHTML = this.card(tag);
      const next = document.adoptNode(template.content.firstElementChild);
      const current = existing.get(tag.entry_id);
      if (!current) return next;
      const image = current.querySelector(".image");
      const replacement = next.querySelector(".image");
      const oldImg = image.querySelector("img");
      const newImg = replacement.querySelector("img");
      image.dataset.requestedSrc = newImg?.getAttribute("src") || "";
      if (oldImg && newImg) {
        replacement.replaceWith(image);
        if (oldImg.getAttribute("src") === newImg.getAttribute("src")) {
          oldImg.alt = newImg.alt;
          image
            .querySelector("button")
            .setAttribute(
              "aria-label",
              replacement.querySelector("button").getAttribute("aria-label"),
            );
        } else {
          // Keep the last successful bitmap visible until the next one is
          // decoded. Ignore an obsolete response after another state update.
          const src = newImg.getAttribute("src");
          newImg
            .decode()
            .then(() => {
              if (image.isConnected && image.dataset.requestedSrc === src)
                image.replaceChildren(...replacement.childNodes);
            })
            .catch(() => {});
        }
      }
      current.replaceChildren(...next.childNodes);
      return current;
    });
    if (cards.length) grid.replaceChildren(...cards);
    else
      grid.innerHTML = `<div class="empty">${this.tags.length ? `${t(this.hass, "No ESLs match your search or filter.")} <button type="button" data-action="clear-filters">${t(this.hass, "Clear search and filter")}</button>` : t(this.hass, "Add a BLE ESL device in Settings → Devices & services.")}</div>`;
    if (entry && (entity || action))
      grid
        .querySelector(
          `[data-entry="${CSS.escape(entry)}"] [${entity ? "data-entity" : "data-action"}="${CSS.escape(entity || action)}"]`,
        )
        ?.focus();
  }
  rememberTag(entryId, replace = false) {
    const url = new URL(window.location.href);
    if ((url.searchParams.get("tag") || null) === (entryId || null)) return;
    if (entryId) url.searchParams.set("tag", entryId);
    else url.searchParams.delete("tag");
    window.history[replace ? "replaceState" : "pushState"](
      { ...window.history.state },
      "",
      url,
    );
  }
  restoreLocation() {
    const entryId = new URL(window.location.href).searchParams.get("tag");
    const tag = this.tags.find((t) => t.entry_id === entryId);
    if (tag) this.openEditor(tag);
    else if (!entryId && this.view === "editor")
      this.shadowRoot.querySelector('[data-action="dashboard"]').click();
  }
  openEditor(tag) {
    if (
      this.automationEditSession &&
      this.automationEditSession.entry_id !== tag.entry_id
    ) {
      // Switching ESLs (the browser's Back included) hands the editor back to
      // the tag design: ask before dropping unsaved automation changes.
      if (!this.confirmDiscardAutomationEdit()) return false;
      this.automationEditRun = (this.automationEditRun || 0) + 1;
      this.clearAutomationEdit(this.automationEditSession);
    }
    if (this.editor?.busy || this.editor?.refreshing) {
      this.message(
        "Finish the current editor operation before switching ESLs.",
      );
      return false;
    }
    this.message();
    this.rememberTag(tag.entry_id);
    this.view = "editor";
    this.shadowRoot.querySelector("#dashboard").hidden = true;
    this.shadowRoot.querySelector("#editor").hidden = false;
    if (!this.editor) {
      const editor = document.createElement("ble-esl-designer");
      editor.setAttribute("managed", "");
      this.editorNav.slot = "managed-navigation";
      editor.append(this.editorNav);
      editor.tag = tag;
      editor.panel = this._panel;
      editor.narrow = this.narrow;
      editor.hass = this.hass;
      this.editor = editor;
      this.shadowRoot.querySelector("#editor-slot").append(editor);
      this.updateToastOffset();
    } else if (!this.editor.ready) {
      this.editor.tag = tag;
    } else {
      this.editor.switchMode("display");
      if (this.editor.tag?.entry_id !== tag.entry_id)
        this.editor.load(
          this.editor.tags.find((item) => item.entry_id === tag.entry_id) ||
            tag,
        );
    }
    this.editorNav.querySelector('[data-action="dashboard"]').focus();
    this.updateEditorContext();
    return this.editor?.tag?.entry_id === tag.entry_id || !this.editor?.ready;
  }
  // Leaving an automation design hands the editor back to the tag design. Until
  // the import is done the editor still holds that tag design, which is kept.
  // Declining puts the URL back, as the browser's Back may already have left it.
  confirmDiscardAutomationEdit() {
    if (
      !this.automationEditSession ||
      !this.automationEditSource ||
      !this.editor?.dirty ||
      window.confirm(
        t(this.hass, "Discard the unsaved changes to this automation design?"),
      )
    )
      return true;
    this.rememberTag(this.automationEditSession.entry_id, true);
    return false;
  }
  clearAutomationEdit(session = this.automationEditSession) {
    if (!session || this.automationEditSession !== session) return;
    const source = this.automationEditSource;
    this.automationEditSession = null;
    this.automationEditSource = null;
    this.clearAutomationDraft(source);
    this.automationSaveRun = (this.automationSaveRun || 0) + 1;
    this.updateEditorContext();
    this.automationSaving = false;
    session.editor.restoreEditorSession(session.returnState, session.token);
    this.updateEditorContext();
  }
  safeAutomationVariables(config, selectedPath) {
    const excluded = Symbol("not a literal JSON value");
    const safeValue = (value) => {
      if (value === null || typeof value === "boolean") return value;
      if (typeof value === "number")
        return Number.isFinite(value) ? value : excluded;
      if (typeof value === "string")
        return /{{|{%|{#/.test(value) ? excluded : value;
      if (Array.isArray(value)) {
        const result = value.map(safeValue);
        return result.some((item) => item === excluded) ? excluded : result;
      }
      if (value && typeof value === "object") {
        const result = Object.create(null);
        for (const [key, item] of Object.entries(value)) {
          if (["__proto__", "prototype", "constructor"].includes(key))
            return excluded;
          const safe = safeValue(item);
          if (safe === excluded) return excluded;
          result[key] = safe;
        }
        return result;
      }
      return excluded;
    };
    const variables = Object.create(null);
    const include = (candidate) => {
      if (
        !candidate ||
        typeof candidate !== "object" ||
        Array.isArray(candidate)
      )
        return;
      for (const [key, value] of Object.entries(candidate)) {
        if (["__proto__", "prototype", "constructor"].includes(key)) continue;
        const safe = safeValue(value);
        if (safe === excluded) delete variables[key];
        else variables[key] = safe;
      }
    };
    const invalidateNestedAssignments = (action) => {
      if (!action || typeof action !== "object") return;
      if (action.enabled === false) return;
      if (typeof action.response_variable === "string")
        delete variables[action.response_variable];
      if (action.variables && typeof action.variables === "object")
        for (const key of Object.keys(action.variables)) delete variables[key];
      for (const [key, child] of Object.entries(action)) {
        if (["target", "data", "service_data", "payload"].includes(key))
          continue;
        if (Array.isArray(child)) child.forEach(invalidateNestedAssignments);
        else if (child && typeof child === "object")
          invalidateNestedAssignments(child);
      }
    };
    include(config.variables);
    let node = config;
    let uncertainScope = false;
    for (const part of selectedPath) {
      if (["choose", "if", "parallel", "default"].includes(part))
        uncertainScope = true;
      if (Array.isArray(node) && Number.isInteger(part)) {
        for (const action of node.slice(0, part)) {
          if (action?.enabled === false) continue;
          if (uncertainScope) {
            for (const key of Object.keys(action?.variables || {}))
              delete variables[key];
          } else {
            include(action?.variables);
          }
          if (typeof action?.response_variable === "string")
            delete variables[action.response_variable];
          for (const [key, child] of Object.entries(action || {})) {
            if (
              [
                "variables",
                "response_variable",
                "target",
                "data",
                "service_data",
                "payload",
              ].includes(key)
            )
              continue;
            if (Array.isArray(child))
              child.forEach(invalidateNestedAssignments);
            else if (child && typeof child === "object")
              invalidateNestedAssignments(child);
          }
        }
        node = node[part];
      } else {
        node = node?.[part];
      }
    }
    return variables;
  }
  async editAutomation(entryId, entityId) {
    const tag = this.tags.find((item) => item.entry_id === entryId);
    if (!tag) return;
    if (
      this.editor?.dirty &&
      !window.confirm(
        t(
          this.hass,
          "Replace the current design with this automation payload?",
        ),
      )
    )
      return;
    const run = (this.automationEditRun = (this.automationEditRun || 0) + 1);
    if (this.automationEditSession)
      this.clearAutomationEdit(this.automationEditSession);
    const previousState = this.editor?.ready
      ? this.editor.captureEditorSession()
      : null;
    if (!this.openEditor(tag)) return;
    const editor = this.editor;
    let returnState =
      previousState || (editor.ready ? editor.captureEditorSession() : null);
    const token = (this.automationSessionSequence || 0) + 1;
    this.automationSessionSequence = token;
    const session = {
      token,
      entry_id: entryId,
      entity_id: entityId,
      editor,
      returnState,
    };
    this.automationEditSession = session;
    this.updateEditorContext();
    editor.beginAutomationSession(token);
    if (returnState) editor.setAutomationReturnState(returnState, token);
    const current = () =>
      run === this.automationEditRun &&
      this.automationEditSession === session &&
      this.editor === editor &&
      this.view === "editor" &&
      editor.tag?.entry_id === entryId;
    this.message();
    try {
      if (!editor.ready) await editor.readyPromise;
      if (!current()) return;
      if (!returnState) {
        returnState = editor.captureEditorSession();
        session.returnState = returnState;
        editor.setAutomationReturnState(returnState, token);
      }
      if (!editor.ready)
        throw new Error(t(this.hass, "The designer could not be loaded."));
      const source = await this.api("automation_edit_source", {
        entry_id: entryId,
        entity_id: entityId,
      });
      if (!current()) return;
      const configId = source.config_id;
      if (!configId || source.entity_id !== entityId)
        throw new Error(
          t(this.hass, "Automation configuration identity is missing."),
        );
      const config = await this.hass.callApi(
        "GET",
        `config/automation/config/${encodeURIComponent(configId)}`,
      );
      if (!current()) return;
      if (
        !config ||
        Array.isArray(config) ||
        typeof config !== "object" ||
        config.id !== configId
      )
        throw new Error(
          t(this.hass, "Automation configuration could not be loaded safely."),
        );
      const { matches, unsupported } = this.findWriteActions(config, source);
      if (unsupported.length && !matches.length)
        throw new Error(
          t(
            this.hass,
            "This automation uses area, floor, label, or templated targets that cannot be safely matched to one ESL.",
          ),
        );
      if (!matches.length)
        throw new Error(
          t(this.hass, "No ble_esl.write action targeting this ESL was found."),
        );
      let selectedIndex = 0;
      if (matches.length > 1) {
        const choice = await chooseOne(
          this.hass,
          t(this.hass, "Choose the write action to import:"),
          matches.map((item) => item.label),
        );
        if (!current()) return;
        if (choice === null) {
          this.clearAutomationEdit(session);
          return;
        }
        selectedIndex = choice;
      }
      const selectedPath = matches[selectedIndex].path;
      const selectedAction = this.actionAt(config, selectedPath);
      if (
        !selectedAction ||
        (selectedAction.action || selectedAction.service) !== "ble_esl.write"
      )
        throw new Error(
          t(
            this.hass,
            "The matching write action changed. Reopen the automation and try again.",
          ),
        );
      const data = selectedAction.data || selectedAction.service_data;
      if (!data || !Array.isArray(data.payload))
        throw new Error(
          t(this.hass, "This write action has no editable payload list."),
        );
      if (
        data.background !== undefined &&
        data.background !== null &&
        ![
          "black",
          "white",
          ...(editor.tag.colors.includes("R") ? ["red"] : []),
          ...(editor.tag.colors.includes("Y") ? ["yellow"] : []),
        ].includes(data.background)
      )
        throw new Error(
          t(
            this.hass,
            "This automation background is not supported by the selected ESL.",
          ),
        );
      let previewVariables = this.safeAutomationVariables(config, selectedPath);
      const prompted = new Set();
      const design =
        data.design === undefined ? null : decodeAutomationDesign(data.design);
      // The action's own `rotate` wins, as it does when the automation runs.
      const rotate = Number(data.rotate ?? design?.rotate ?? 0);
      if (![0, 90, 180, 270].includes(rotate))
        throw new Error(
          t(this.hass, "This automation rotation is not supported."),
        );
      const importPayload = async () => {
        let result;
        for (let attempt = 0; attempt < 64; attempt++) {
          result = await editor.prepareAutomationPayload(
            data.payload,
            data.background,
            entryId,
            previewVariables,
            rotate,
          );
          if (!current()) return null;
          const missing = result.missing_parameters || [];
          if (!missing.length) break;
          const unresolved = missing.filter((name) => !prompted.has(name));
          if (!unresolved.length)
            throw new Error(
              t(this.hass, "This preview parameter is still undefined: {name}", {
                name: missing[0],
              }),
            );
          unresolved.forEach((name) => prompted.add(name));
          const values = await editor.requestPreviewVariables(
            previewVariables,
            unresolved,
          );
          if (!current()) return null;
          if (values === null) {
            this.clearAutomationEdit(session);
            return null;
          }
          previewVariables = values;
        }
        if (result?.missing_parameters?.length)
          throw new Error(
            t(this.hass, "Too many preview parameters are missing."),
          );
        return result;
      };
      let imported = null;
      if (design) {
        // The design is what runs; the stored payload only helps to ask for the
        // preview parameters, so a payload that cannot be imported is no reason
        // to refuse a design that opens fine.
        try {
          await importPayload();
        } catch {
          if (!current()) return;
        }
        if (!current()) return;
        imported = {
          elements: design.elements,
          issues: [],
          different_pixels: 0,
        };
      } else {
        imported = await importPayload();
        if (!imported) return;
      }
      if (
        imported.issues.length ||
        (data.payload.length && imported.different_pixels !== 0)
      )
        throw new Error(
          t(
            this.hass,
            "This payload cannot be represented exactly in the designer. Nothing was imported.",
          ),
        );
      if (
        !editor.applyAutomationPayload(
          imported,
          data.payload,
          design?.background ?? data.background,
          data.payload.length === 0,
          entryId,
          token,
          previewVariables,
          rotate,
        )
      ) {
        if (!current()) return;
        throw new Error(
          t(this.hass, "The automation import is no longer current."),
        );
      }
      this.automationEditSource = {
        session_token: token,
        entry_id: entryId,
        entity_id: entityId,
        configId,
        name: config.alias || entityId,
        device_id: source.device_id,
        entity_ids: source.entity_ids,
        background: editor.document.background,
        originalAction: structuredClone(selectedAction),
        selectedPath,
      };
      this.updateEditorContext();
      this.message(
        "Automation payload imported. Edit the design, then save it to this automation.",
        "info",
      );
      if (this.restoreAutomationDraft(editor, this.automationEditSource))
        return;
    } catch (error) {
      if (!current()) return;
      this.clearAutomationEdit(session);
      this.message(
        errorText(this.hass, "Could not open the automation design", error),
      );
    }
  }
  // Unsaved automation changes outlive a navigation inside Home Assistant, which
  // fires no beforeunload: they are set aside per automation and offered back.
  persistAutomationDraft() {
    const source = this.automationEditSource;
    const editor = this.editor;
    if (
      !source ||
      this.automationEditSession?.editor !== editor ||
      editor.mode !== "display"
    )
      return;
    if (!editor.dirty) {
      this.clearAutomationDraft(source);
      return;
    }
    try {
      window.sessionStorage.setItem(
        AUTOMATION_DRAFT_KEY,
        JSON.stringify({
          ...this.automationDraftIdentity(source),
          document: editor.document,
        }),
      );
    } catch {
      // Storage may be full or blocked; the draft is then simply not kept.
    }
  }
  // Which write action of which automation a draft belongs to: an edited or
  // different action must not get another one's unsaved design.
  automationDraftIdentity(source) {
    return {
      config_id: source.configId,
      entry_id: source.entry_id,
      entity_id: source.entity_id,
      path: JSON.stringify(source.selectedPath),
      signature: this.configSignature(source.originalAction),
    };
  }
  readAutomationDraft(source) {
    try {
      const draft = JSON.parse(
        window.sessionStorage.getItem(AUTOMATION_DRAFT_KEY) || "null",
      );
      const identity = this.automationDraftIdentity(source);
      return draft &&
        Object.keys(identity).every((key) => draft[key] === identity[key])
        ? draft
        : null;
    } catch {
      return null;
    }
  }
  // Removes the stored draft only when it belongs to `source`: the end of an
  // unrelated session must not discard another automation's unsaved work.
  clearAutomationDraft(source) {
    if (!source || !this.readAutomationDraft(source)) return;
    try {
      window.sessionStorage.removeItem(AUTOMATION_DRAFT_KEY);
    } catch {
      // Nothing to clean up.
    }
  }
  // True when an unsaved draft of this very automation action was put back.
  restoreAutomationDraft(editor, source) {
    const draft = this.readAutomationDraft(source);
    if (!draft) return false;
    this.clearAutomationDraft(source);
    if (
      !Array.isArray(draft.document?.elements) ||
      !window.confirm(
        t(
          this.hass,
          "Restore the unsaved changes you made to this automation design? Cancel discards them.",
        ),
      )
    )
      return false;
    return editor.restoreAutomationDraft(draft.document, source.session_token);
  }
  configSignature(value) {
    if (Array.isArray(value))
      return `[${value.map((item) => this.configSignature(item)).join(",")}]`;
    if (value && typeof value === "object")
      return `{${Object.keys(value)
        .sort()
        .map(
          (key) => `${JSON.stringify(key)}:${this.configSignature(value[key])}`,
        )
        .join(",")}}`;
    return JSON.stringify(value);
  }
  findWriteActions(config, source) {
    const deviceIds = new Set(source.device_id ? [source.device_id] : []);
    const entityIds = new Set(source.entity_ids || []);
    const valuesFor = (value) =>
      (Array.isArray(value) ? value : [value]).filter(
        (item) => typeof item === "string" && item.length > 0,
      );
    const targetMatch = (action) => {
      const rawTarget = action.target;
      const target =
        rawTarget && typeof rawTarget === "object" && !Array.isArray(rawTarget)
          ? rawTarget
          : {};
      const legacyData = [
        action.data,
        action.service_data,
        action.service_data_template,
      ].filter(
        (value) => value && typeof value === "object" && !Array.isArray(value),
      );
      const effectiveTarget = Object.assign({}, ...legacyData, target);
      // HA applies the legacy service entity_id after preparing target.
      if (action.entity_id !== undefined)
        effectiveTarget.entity_id = action.entity_id;
      const refs = [
        ...valuesFor(effectiveTarget.device_id).filter((id) =>
          deviceIds.has(id),
        ),
        ...valuesFor(effectiveTarget.entity_id).filter((id) =>
          entityIds.has(id),
        ),
      ];
      const unsupported =
        (rawTarget !== undefined &&
          rawTarget !== null &&
          (typeof rawTarget !== "object" || Array.isArray(rawTarget))) ||
        ["area_id", "floor_id", "label_id"].some(
          (key) => valuesFor(effectiveTarget[key]).length,
        );
      const templatedTarget = Object.entries(effectiveTarget).some(
        ([key, value]) =>
          [
            "device_id",
            "entity_id",
            "area_id",
            "floor_id",
            "label_id",
          ].includes(key) &&
          valuesFor(value).some(
            (item) =>
              item.includes("{{") || item.includes("{%") || item.includes("{#"),
          ),
      );
      return {
        matches: refs.length > 0,
        unsupported: unsupported || templatedTarget,
      };
    };
    const matches = [];
    const unsupported = [];
    const visit = (value, path = []) => {
      if (Array.isArray(value)) {
        value.forEach((item, index) => visit(item, [...path, index]));
        return;
      }
      if (!value || typeof value !== "object") return;
      // A disabled step never runs, and neither do the steps inside it.
      if (value.enabled === false) return;
      const service = value.action || value.service;
      if (service === "ble_esl.write") {
        const target = targetMatch(value);
        if (target.unsupported)
          unsupported.push({
            path,
            label: String(value.alias || "ble_esl.write"),
          });
        else if (target.matches)
          matches.push({
            path,
            label: String(
              value.alias || `ble_esl.write (${matches.length + 1})`,
            ),
          });
      }
      for (const [key, child] of Object.entries(value)) {
        if (
          [
            "target",
            "data",
            "service_data",
            "service_data_template",
            "payload",
          ].includes(key)
        )
          continue;
        visit(child, [...path, key]);
      }
    };
    const actions = Array.isArray(config.actions)
      ? config.actions
      : Array.isArray(config.action)
        ? config.action
        : null;
    if (!actions)
      return { matches, unsupported: [{ label: "malformed actions" }] };
    visit(actions, [Array.isArray(config.actions) ? "actions" : "action"]);
    return { matches, unsupported };
  }
  actionAt(config, path) {
    if (!Array.isArray(path)) return null;
    return path.reduce((value, key) => value?.[key], config);
  }
  async saveAutomation(snapshot) {
    const source = this.automationEditSource;
    const session = this.automationEditSession;
    if (
      !source ||
      !session ||
      this.automationSaving ||
      this.view !== "editor" ||
      this.editor !== session.editor ||
      session.token !== source.session_token ||
      snapshot?.session_token !== session.token ||
      snapshot?.entry_id !== source.entry_id ||
      session.editor.tag?.entry_id !== source.entry_id
    )
      return;
    this.automationSaving = true;
    const run = (this.automationSaveRun = (this.automationSaveRun || 0) + 1);
    const current = () =>
      run === this.automationSaveRun &&
      this.automationEditSession === session &&
      this.automationEditSource === source &&
      this.view === "editor" &&
      this.editor === session.editor &&
      session.token === source.session_token &&
      session.editor.tag?.entry_id === source.entry_id;
    try {
      if (session.editor.mode !== "display")
        throw new Error(
          t(this.hass, "Switch to Display mode before saving this automation."),
        );
      const exported = await this.exportForAutomation(
        session.editor,
        source.entry_id,
        snapshot,
      );
      if (!current()) return;
      const written = await this.replaceWriteAction({
        configId: source.configId,
        matchSource: source,
        expectedAction: source.originalAction,
        exported,
        current,
        background: snapshot.document?.background,
      });
      if (!written) return;
      const { action, path } = written;
      if (!current()) return;
      // A draft left by leaving the panel mid-save holds edits newer than what
      // was saved: it moves to the saved action's identity; otherwise it goes.
      const newer =
        JSON.stringify(session.editor.document) !==
        JSON.stringify(snapshot.document);
      const draft = this.readAutomationDraft(source);
      this.clearAutomationDraft(source);
      this.message("Automation saved.", "success");
      if (!newer) {
        session.editor.dirty = false;
        session.editor.render();
      } else {
        // What is shown differs from what was saved, even if an undo during
        // the save had made it look like the loaded design.
        session.editor.session.markSaved(snapshot.document);
        if (!session.editor.dirty) {
          session.editor.dirty = true;
          session.editor.render();
        }
      }
      source.originalAction = structuredClone(action);
      source.selectedPath = path;
      if (draft && newer) this.persistAutomationDraft();
    } catch (error) {
      if (current())
        this.message(
          errorText(this.hass, "Could not save to the automation", error),
        );
    } finally {
      if (run === this.automationSaveRun) this.automationSaving = false;
    }
  }
  // The design as ble_esl.write data, refusing anything a payload cannot hold.
  async exportForAutomation(editor, entryId, snapshot) {
    const exported = await editor.api("export", {
      entry_id: entryId,
      document: snapshot.document,
      preview_variables: snapshot.preview_variables || {},
      automation_edit: true,
    });
    if (
      exported.writable !== true ||
      !Array.isArray(exported.validation_errors) ||
      exported.validation_errors.length > 0 ||
      !Array.isArray(exported.payload_data)
    ) {
      const issues = (exported.validation_errors || []).slice(0, 3).join("; ");
      throw new Error(
        issues
          ? errorText(
              this.hass,
              "The current design cannot be saved as a payload.",
              new Error(issues),
            )
          : t(this.hass, "The current design cannot be saved as a payload."),
      );
    }
    return exported;
  }
  // Replace the design data of one ble_esl.write action in the latest saved
  // automation: the one that still equals `expectedAction`, at `path` when
  // given. Everything else in the automation stays as it is. Resolves with the
  // written action, or null when `current()` says the request is obsolete.
  async replaceWriteAction({
    configId,
    matchSource,
    expectedAction,
    exported,
    current,
    path = null,
    background,
  }) {
    const latest = await this.hass.callApi(
      "GET",
      `config/automation/config/${encodeURIComponent(configId)}`,
    );
    if (!current()) return null;
    if (
      !latest ||
      Array.isArray(latest) ||
      typeof latest !== "object" ||
      latest.id !== configId ||
      !(Array.isArray(latest.actions) || Array.isArray(latest.action))
    )
      throw new Error(
        t(this.hass, "The latest automation configuration is malformed."),
      );
    const expected = this.configSignature(expectedAction);
    const { matches, unsupported } = this.findWriteActions(latest, matchSource);
    if (unsupported.length && !matches.length)
      throw new Error(
        t(
          this.hass,
          "This automation uses area, floor, label, or templated targets that cannot be safely matched to one ESL.",
        ),
      );
    const unchanged = matches.filter(
      (candidate) =>
        this.configSignature(this.actionAt(latest, candidate.path)) ===
        expected,
    );
    let selected;
    if (path) {
      // A target picked moments ago: it must still be at that place, unchanged.
      selected = unchanged.find(
        (candidate) => JSON.stringify(candidate.path) === JSON.stringify(path),
      );
      if (!selected)
        throw new Error(
          t(this.hass, "The selected write action is no longer available."),
        );
    } else {
      // A duplicate of the imported action makes path-based selection unsafe,
      // even if the old path still points at an unchanged copy.
      selected = unchanged.length === 1 ? unchanged[0] : null;
      if (!selected)
        throw new Error(
          t(
            this.hass,
            "The selected write action changed since import. Reopen the automation before saving.",
          ),
        );
    }
    const updated = structuredClone(latest);
    const action = this.actionAt(updated, selected.path);
    const data = action?.data || action?.service_data;
    if (
      !action ||
      (action.action || action.service) !== "ble_esl.write" ||
      !data ||
      !Array.isArray(data.payload)
    )
      throw new Error(
        t(this.hass, "The selected write action is no longer available."),
      );
    data.payload = exported.payload_data;
    if (exported.rotate) data.rotate = exported.rotate;
    else delete data.rotate;
    if (exported.design_source !== undefined)
      data.design = exported.design_source;
    else delete data.design;
    if (exported.design_specs) data.design_specs = exported.design_specs;
    else delete data.design_specs;
    // White is what the action draws on when it names no background.
    if (
      background !== undefined &&
      (data.background !== undefined || background !== "white")
    )
      data.background = background;
    await this.hass.callApi(
      "POST",
      `config/automation/config/${encodeURIComponent(configId)}`,
      updated,
    );
    return { action, path: selected.path };
  }
  // Automations that could take this design: those linked to the ESL whose
  // ble_esl.write actions target it. The automation being edited is not
  // offered at all: none of its actions is "another automation".
  async automationTargets(entryId, excludeConfigId = null) {
    const listing = await this.api("automations", { entry_id: entryId });
    const candidates = (listing?.linked || []).filter(
      (item) =>
        !item.missing &&
        item.id &&
        ["on", "off"].includes(this.hass.states[item.entity_id]?.state),
    );
    const targets = await Promise.all(
      candidates.map(async (item) => {
        try {
          const source = await this.api("automation_edit_source", {
            entry_id: entryId,
            entity_id: item.entity_id,
          });
          if (!source?.config_id || source.entity_id !== item.entity_id)
            return null;
          const config = await this.hass.callApi(
            "GET",
            `config/automation/config/${encodeURIComponent(source.config_id)}`,
          );
          if (
            !config ||
            Array.isArray(config) ||
            typeof config !== "object" ||
            config.id !== source.config_id ||
            (excludeConfigId !== null && config.id === excludeConfigId)
          )
            return null;
          const { matches } = this.findWriteActions(config, source);
          if (!matches.length) return null;
          return {
            name:
              this.hass.states[item.entity_id]?.attributes.friendly_name ||
              config.alias ||
              item.name ||
              item.entity_id,
            source,
            config,
            matches,
          };
        } catch {
          // An automation that cannot be read safely is simply not offered.
          return null;
        }
      }),
    );
    return targets.filter(Boolean);
  }
  // Save the design being edited into an existing automation of this ESL,
  // chosen now: from a blank start, or a copy of a loaded automation's design.
  async saveToOtherAutomation(snapshot) {
    const editor = this.editor;
    const session = this.automationEditSession;
    const source = this.automationEditSource;
    const entryId = snapshot?.entry_id;
    const token = snapshot?.session_token || null;
    if (
      !editor ||
      this.automationSaving ||
      this.view !== "editor" ||
      editor.mode !== "display" ||
      editor.tag?.entry_id !== entryId ||
      (session ? session.token : null) !== token ||
      (session && (!source || source.session_token !== token))
    )
      return;
    this.automationSaving = true;
    const run = (this.automationSaveRun = (this.automationSaveRun || 0) + 1);
    const current = () =>
      run === this.automationSaveRun &&
      this.view === "editor" &&
      this.editor === editor &&
      this.automationEditSession === session &&
      editor.mode === "display" &&
      editor.tag?.entry_id === entryId &&
      (editor._automationSessionToken || null) === token;
    try {
      const targets = await this.automationTargets(
        entryId,
        source ? source.configId : null,
      );
      if (!current()) return;
      if (!targets.length)
        throw new Error(
          t(
            this.hass,
            "No automation with a ble_esl.write action for this ESL was found.",
          ),
        );
      const choice = await chooseOne(
        this.hass,
        t(this.hass, "Choose the automation to save to:"),
        targets.map((target) => target.name),
      );
      if (!current() || choice === null) return;
      const target = targets[choice];
      let match = target.matches[0];
      if (target.matches.length > 1) {
        const index = await chooseOne(
          this.hass,
          t(this.hass, "Choose the write action to replace:"),
          target.matches.map((item) => item.label),
        );
        if (!current() || index === null) return;
        match = target.matches[index];
      }
      const exported = await this.exportForAutomation(
        editor,
        entryId,
        snapshot,
      );
      if (!current()) return;
      const written = await this.replaceWriteAction({
        configId: target.source.config_id,
        matchSource: target.source,
        expectedAction: this.actionAt(target.config, match.path),
        exported,
        current,
        path: match.path,
        background: snapshot.document?.background,
      });
      if (!written || !current()) return;
      this.message("Saved to {name}.", "success", { name: target.name });
      // A loaded automation keeps its own unsaved state; a design started here
      // is now kept in the automation it was saved to.
      if (
        !session &&
        JSON.stringify(editor.document) === JSON.stringify(snapshot.document)
      ) {
        editor.markSavedElsewhere();
      }
    } catch (error) {
      if (current())
        this.message(
          errorText(this.hass, "Could not save to the automation", error),
        );
    } finally {
      if (run === this.automationSaveRun) this.automationSaving = false;
    }
  }
  async click(event) {
    const entity = event.target.closest("[data-entity]");
    if (entity) {
      this.dispatchEvent(
        new CustomEvent("hass-more-info", {
          detail: { entityId: entity.dataset.entity },
          bubbles: true,
          composed: true,
        }),
      );
      return;
    }
    const button = event.target.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "refresh") await this.refresh();
    if (button.dataset.action === "clear-filters") {
      this.query = "";
      this.filter = "all";
      const search = this.shadowRoot.querySelector("#search");
      search.value = "";
      this.shadowRoot.querySelector("#filter").value = "all";
      this.renderCards();
      search.focus();
      return;
    }
    if (button.dataset.action === "automations") {
      const tag = this.tags.find(
        (tag) => tag.entry_id === button.dataset.entry,
      );
      if (tag) this.showAutomations(tag, button);
    }
    if (button.dataset.action === "editor-automations") {
      const entry =
        this.editor?.mode === "template"
          ? this.editor.displaySession?.tag
          : this.editor?.tag;
      const tag = this.tags.find((tag) => tag.entry_id === entry?.entry_id);
      if (tag) this.showAutomations(tag, button);
    }
    if (button.dataset.action === "edit") {
      const tag = this.tags.find(
        (tag) => tag.entry_id === button.dataset.entry,
      );
      if (tag) this.openEditor(tag);
    }
    if (button.dataset.action === "dismiss-message") {
      this.message();
      return;
    }
    if (button.dataset.action === "dashboard") {
      // Leaving an automation design hands the editor back to the tag design,
      // so its unsaved changes would be lost; the tag design's own draft is kept.
      if (!this.confirmDiscardAutomationEdit()) return;
      this.rememberTag(null);
      this.view = "dashboard";
      this.automationEditRun = (this.automationEditRun || 0) + 1;
      this.automationSaveRun = (this.automationSaveRun || 0) + 1;
      this.clearAutomationEdit();
      this.shadowRoot.querySelector("#dashboard").hidden = false;
      this.shadowRoot.querySelector("#editor").hidden = true;
      await this.refresh();
      this.shadowRoot.querySelector("#search").focus();
    }
  }
}
customElements.define("ble-esl-manager", EslManager);
