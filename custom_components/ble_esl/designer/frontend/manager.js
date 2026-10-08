import { t, language, bindStatic, localize } from "./i18n.js";
import "./panel.js";
import "./automation-dialog.js";

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
#dashboard,#editor{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}.dashboard-content{flex:1;min-height:0;overflow:auto}#editor-slot{flex:1;min-height:0;overflow:hidden}header,.editor-nav{flex:none;height:var(--header-height,56px);min-height:56px;padding:0 24px}header{display:flex;align-items:center;gap:12px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#ddd)}h1{font-size:20px;font-weight:500;margin:0;flex:1}h2{margin:0;font-size:18px;overflow-wrap:anywhere}.controls{display:flex;flex-wrap:wrap;gap:10px;padding:20px 24px 12px}.controls input{flex:1;min-width:150px}.summary{padding:0 24px 16px;color:var(--secondary-text-color,#637083)}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px;padding:0 24px 24px}.card{min-width:0;padding:18px;background:var(--card-background-color,white);border:1px solid var(--divider-color,#dde3e8);border-radius:12px;display:flex;flex-direction:column;gap:12px}.top{display:flex;align-items:center;gap:8px}.top>h2{flex:1;min-width:0;height:24px;line-height:24px;overflow:hidden}.product{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;height:32px;line-height:16px}.dimensions{line-height:16px;white-space:nowrap}.alias{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.alias{border:0;padding:0;text-align:left;background:transparent;font-size:18px;font-weight:600;overflow-wrap:anywhere}.muted{color:var(--secondary-text-color,#637083);font-size:12px;overflow-wrap:anywhere}.battery{flex:none;margin-left:auto;white-space:nowrap;font-size:12px}.battery button,.battery>span{display:flex;align-items:center;gap:6px;line-height:24px}.battery button{padding:0;border:0;border-radius:0;background:transparent}.battery svg{width:24px;height:16px;flex:none}.image{height:180px;display:flex;align-items:center;justify-content:center;border-radius:8px;background:var(--secondary-background-color,#eef1f4);overflow:hidden}.image img{max-width:100%;max-height:100%;object-fit:contain;image-rendering:pixelated}.image button{display:contents}.badges{display:flex;flex-wrap:wrap;gap:8px}.badge{padding:4px 8px;border-radius:6px;font-size:12px;background:var(--secondary-background-color,#eef1f4);border:0}.bad{color:var(--error-color,#b3261e);background:#b3261e12}.good{color:var(--success-color,#28754a);background:#28754a12}.facts{display:grid;grid-template-columns:1fr minmax(0,1fr);gap:8px;margin:0;font-size:13px}.facts dt{color:var(--secondary-text-color,#637083)}.facts dd{margin:0;text-align:right;overflow-wrap:anywhere}.facts button{padding:0;border:0;background:transparent;text-align:right;font:inherit}.actions{display:flex;gap:8px;margin-top:auto}.actions button{flex:1}.message{margin:12px 24px}.message.error{color:var(--error-color,#b3261e)}.editor-nav{display:flex;align-items:center;gap:12px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#ddd)}.editor-nav span{flex:1}ble-esl-designer{height:100%;min-height:0}.empty{grid-column:1/-1;padding:40px;text-align:center;color:var(--secondary-text-color,#637083)}
@media(max-width:650px){header,.editor-nav{padding:0 12px}.controls{padding:16px 12px 12px}.summary{padding:0 12px 16px}.grid{padding:0 12px 16px;grid-template-columns:minmax(0,1fr);gap:12px}.message{margin:12px}.card{padding:16px}}
`;

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
    this.view = "dashboard";
    this.shadowRoot.innerHTML = `<style>${css}</style><section id="dashboard"><header><ha-menu-button></ha-menu-button><h1>${t(this.hass, "ESL Manager")}</h1><button data-action="refresh">${t(this.hass, "Refresh")}</button></header><div class="dashboard-content"><div class="controls"><input id="search" type="search" aria-label="${t(this.hass, "Search ESLs")}" placeholder="${t(this.hass, "Search aliases or devices")}"><select id="filter" aria-label="${t(this.hass, "Filter ESLs")}"><option value="all">${t(this.hass, "All ESLs")}</option><option value="error">${t(this.hass, "Errors")}</option><option value="unsynced">${t(this.hass, "Not in sync")}</option></select></div><div class="summary" role="status"></div><div class="grid"></div></div></section><p class="message" role="alert" hidden></p><section id="editor" hidden><div class="editor-nav"><button data-action="dashboard">${t(this.hass, "← Dashboard")}</button><span>${t(this.hass, "Designer")}</span><button data-action="editor-automations">${t(this.hass, "Connected automations")}</button></div><div id="editor-slot"></div></section>`;
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
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
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
  }
  set panel(value) {
    this._panel = value;
    if (this.editor) this.editor.panel = value;
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
    if (this.messageKey) this.message(this.messageKey);
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
    if (this.hass && !this.started) this.refresh();
    this.clockTimer = setInterval(() => {
      if (this.view === "dashboard") this.renderCards();
    }, 60000);
  }
  disconnectedCallback() {
    clearInterval(this.clockTimer);
    this.panelObserver?.disconnect();
    window.removeEventListener("resize", this.resizePanel);
  }
  api(action, extra = {}) {
    return this.hass.callWS({ type: "ble_esl/designer", action, ...extra });
  }
  message(error = "") {
    const node = this.shadowRoot.querySelector(".message");
    this.messageKey = error;
    node.textContent = t(this.hass, error);
    node.hidden = !error;
    node.classList.toggle("error", !!error);
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
      await this.loadAutomations();
    } catch (error) {
      this.message(error.message || String(error));
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
    if (!linked.length) return t(this.hass, "Link automation");
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
          this.shadowRoot
            .querySelector(
              `[data-action="automations"][data-entry="${CSS.escape(tag.entry_id)}"]`,
            )
            ?.focus();
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
  hasError(tag) {
    const state = this.state(tag, "write_duration");
    return (
      valid(state) && !!state.attributes.error && !state.attributes.skipped
    );
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
    const fill = known
      ? (Math.max(0, Math.min(100, Number(battery.state))) / 100) * 16
      : 0;
    const content = `<svg viewBox="0 0 26 16" aria-hidden="true"><rect x="1" y="1" width="21" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M24 5v6" stroke="currentColor" stroke-width="2"/><rect x="3.5" y="3.5" width="${fill}" height="9" rx=".5" fill="currentColor"/></svg><span>${escapeHtml(value)}</span>`;
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
    return `<article class="card" data-entry="${e(tag.entry_id)}"><div class="card-heading"><div class="top"><h2>${this.entityButton(tag, "alias", alias, `class="alias" title="${t(this.hass, "Edit alias")}"`)}</h2><div class="battery">${this.batteryHtml(tag, battery)}</div></div><div class="muted product" title="${e(tag.title)}">${e(tag.title)}</div><div class="muted dimensions">${tag.width} × ${tag.height} · ${e(tag.colors)}</div></div><div class="image">${url ? `<button data-entity="${e(tag.entities.last_updated_content)}" aria-label="${e(t(this.hass, "Last successful image for {alias}", { alias }))}"><img src="${e(url)}" alt="${e(t(this.hass, "Last successful image for {alias}", { alias }))}"></button>` : `<span class="muted">${t(this.hass, "No successful image")}</span>`}</div><div class="badges">${this.entityButton(tag, "display_in_sync", syncLabel, `class="badge ${synced ? "good" : ""}"`)}${this.entityButton(tag, "write_duration", error ? t(this.hass, "Transmission error") : !valid(duration) || (!duration.attributes.success && !duration.attributes.skipped && !duration.attributes.error) ? t(this.hass, "No transmission result") : duration.attributes.skipped ? t(this.hass, "Skipped: {reason}", { reason: duration.attributes.skipped }) : t(this.hass, "No error"), `class="badge ${error ? "bad" : ""}"`)}</div><dl class="facts"><dt>${t(this.hass, "Last successful send")}</dt><dd>${this.entityButton(tag, "last_updated_content", this.relative(at), `title="${e(at ? new Date(at).toLocaleString(this.hass?.locale?.language || navigator.language) : t(this.hass, "No successful send"))}"`)}</dd><dt>${t(this.hass, "Transmission duration")}</dt><dd>${this.entityButton(tag, "write_duration", durationValue)}</dd><dt>${t(this.hass, "Automations")}</dt><dd><button data-action="automations" data-entry="${e(tag.entry_id)}" title="${e(this.automationLabel(tag))}">${e(this.automationLabel(tag))}</button></dd></dl><div class="actions"><button class="primary" data-action="edit" data-entry="${e(tag.entry_id)}">${t(this.hass, "Edit design")}</button></div></article>`;
  }
  renderCards() {
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
          this.state(tag, "display_in_sync")?.state === "off"),
    );
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
      grid.innerHTML = `<div class="empty">${this.tags.length ? t(this.hass, "No ESLs match your search or filter.") : t(this.hass, "Add a BLE ESL device in Settings → Devices & services.")}</div>`;
    if (entry && (entity || action))
      grid
        .querySelector(
          `[data-entry="${CSS.escape(entry)}"] [${entity ? "data-entity" : "data-action"}="${CSS.escape(entity || action)}"]`,
        )
        ?.focus();
  }
  openEditor(tag) {
    if (this.editor?.busy || this.editor?.refreshing) {
      this.message(
        "Finish the current editor operation before switching ESLs.",
      );
      return;
    }
    this.message();
    this.view = "editor";
    this.shadowRoot.querySelector("#dashboard").hidden = true;
    this.shadowRoot.querySelector("#editor").hidden = false;
    if (!this.editor) {
      const editor = document.createElement("ble-esl-designer");
      editor.setAttribute("managed", "");
      editor.tag = tag;
      editor.panel = this._panel;
      editor.narrow = this.narrow;
      editor.hass = this.hass;
      this.editor = editor;
      this.shadowRoot.querySelector("#editor-slot").append(editor);
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
    this.shadowRoot.querySelector('[data-action="dashboard"]').focus();
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
    if (button.dataset.action === "dashboard") {
      // Keep the editor mounted so drafts, undo and unsaved-change protection survive.
      this.view = "dashboard";
      this.shadowRoot.querySelector("#dashboard").hidden = false;
      this.shadowRoot.querySelector("#editor").hidden = true;
      await this.refresh();
      this.shadowRoot.querySelector("#search").focus();
    }
  }
}
customElements.define("ble-esl-manager", EslManager);
