import "./panel.js";

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
:host{display:block;height:100%;overflow:auto;font:14px system-ui;color:var(--primary-text-color,#18232f);background:var(--primary-background-color,#f5f7fa)}
*{box-sizing:border-box}[hidden]{display:none!important}button,input,select{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#ccd4dc);border-radius:8px;padding:9px 12px}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #16838c;outline-offset:3px}button.primary{background:#166d75;color:white;border-color:#166d75}
header{display:flex;align-items:center;gap:12px;padding:12px 24px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#ddd)}h1{font-size:20px;font-weight:500;margin:0;flex:1}h2{margin:0;font-size:18px;overflow-wrap:anywhere}.controls{display:flex;flex-wrap:wrap;gap:10px;padding:20px 24px 12px}.controls input{flex:1;min-width:150px}.summary{padding:0 24px 16px;color:var(--secondary-text-color,#637083)}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px;padding:0 24px 24px}.card{min-width:0;padding:18px;background:var(--card-background-color,white);border:1px solid var(--divider-color,#dde3e8);border-radius:12px;display:flex;flex-direction:column;gap:12px}.top{display:flex;align-items:start;gap:8px}.top>div{flex:1;min-width:0}.alias{border:0;padding:0;text-align:left;background:transparent;font-size:18px;font-weight:600;overflow-wrap:anywhere}.muted{color:var(--secondary-text-color,#637083);font-size:12px;overflow-wrap:anywhere}.battery{white-space:nowrap;font-size:12px}.image{height:180px;display:flex;align-items:center;justify-content:center;border-radius:8px;background:var(--secondary-background-color,#eef1f4);overflow:hidden}.image img{max-width:100%;max-height:100%;object-fit:contain;image-rendering:pixelated}.image button{display:contents}.badges{display:flex;flex-wrap:wrap;gap:8px}.badge{padding:4px 8px;border-radius:6px;font-size:12px;background:var(--secondary-background-color,#eef1f4);border:0}.bad{color:var(--error-color,#b3261e);background:#b3261e12}.good{color:var(--success-color,#28754a);background:#28754a12}.facts{display:grid;grid-template-columns:1fr minmax(0,1fr);gap:8px;margin:0;font-size:13px}.facts dt{color:var(--secondary-text-color,#637083)}.facts dd{margin:0;text-align:right;overflow-wrap:anywhere}.facts button{padding:0;border:0;background:transparent;text-align:right;font:inherit}.actions{display:flex;gap:8px;margin-top:auto}.actions button{flex:1}.message{margin:12px 24px}.message.error{color:var(--error-color,#b3261e)}.editor-nav{display:flex;align-items:center;gap:12px;padding:10px 24px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#ddd)}.editor-nav span{flex:1}ble-esl-designer{display:block}.empty{grid-column:1/-1;padding:40px;text-align:center;color:var(--secondary-text-color,#637083)}
@media(max-width:650px){header,.editor-nav{padding:12px}.controls{padding:16px 12px 12px}.summary{padding:0 12px 16px}.grid{padding:0 12px 16px;grid-template-columns:minmax(0,1fr);gap:12px}.message{margin:12px}.card{padding:16px}}
`;

class EslManager extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.tags = [];
    this.query = "";
    this.filter = "all";
    this.view = "dashboard";
    this.shadowRoot.innerHTML = `<style>${css}</style><section id="dashboard"><header><ha-menu-button></ha-menu-button><h1>ESL Manager</h1><button data-action="refresh">Refresh</button></header><div class="controls"><input id="search" type="search" aria-label="Search ESLs" placeholder="Search aliases or devices"><select id="filter" aria-label="Filter ESLs"><option value="all">All ESLs</option><option value="error">Errors</option><option value="unsynced">Not in sync</option></select></div><div class="summary" role="status"></div><div class="grid"></div></section><p class="message" role="alert" hidden></p><section id="editor" hidden><div class="editor-nav"><button data-action="dashboard">← Dashboard</button><span>Designer</span></div><div id="editor-slot"></div></section>`;
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
    if (this.editor) this.editor.hass = value;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    menu.hass = value;
    menu.narrow = this.narrow;
    if (this.isConnected && !this.started) this.refresh();
    else if (
      this.tags.some((tag) =>
        Object.values(tag.entities || {}).some(
          (id) => previous?.states[id] !== value.states[id],
        ),
      )
    )
      this.renderCards();
  }
  get hass() {
    return this._hass;
  }
  connectedCallback() {
    if (this.hass && !this.started) this.refresh();
    this.clockTimer = setInterval(() => {
      if (this.view === "dashboard") this.renderCards();
    }, 60000);
  }
  disconnectedCallback() {
    clearInterval(this.clockTimer);
  }
  api(action, extra = {}) {
    return this.hass.callWS({ type: "ble_esl/designer", action, ...extra });
  }
  message(error = "") {
    const node = this.shadowRoot.querySelector(".message");
    node.textContent = error;
    node.hidden = !error;
    node.classList.toggle("error", !!error);
  }
  async refresh() {
    this.started = true;
    this.message();
    const button = this.shadowRoot.querySelector('[data-action="refresh"]');
    button.disabled = true;
    this.shadowRoot.querySelector(".summary").textContent = "Loading ESLs…";
    try {
      this.tags = await this.api("list");
      this.renderCards();
    } catch (error) {
      this.message(error.message || String(error));
    } finally {
      button.disabled = false;
    }
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
      ? "Sync unknown"
      : synced
        ? "In sync"
        : "Not in sync";
    const at = valid(image) ? image.state : null;
    // ImageEntity's state is its image_last_updated timestamp. Never use last_changed:
    // that can be the entity's restore time rather than the last successful write.
    const url = valid(image) && image.attributes.entity_picture;
    const durationValue =
      valid(duration) && Number.isFinite(Number(duration.state))
        ? `${Number(duration.state).toFixed(1)} s`
        : "—";
    return `<article class="card" data-entry="${e(tag.entry_id)}"><div class="top"><div><h2>${this.entityButton(tag, "alias", alias, 'class="alias" title="Edit alias"')}</h2><div class="muted">${e(tag.title)}</div><div class="muted">${tag.width} × ${tag.height} · ${e(tag.colors)}</div></div><div class="battery">${this.entityButton(tag, "battery", valid(battery) ? `Battery ${battery.state}${battery.attributes.unit_of_measurement || "%"}` : "Battery —")}</div></div><div class="image">${url ? `<button data-entity="${e(tag.entities.last_updated_content)}" aria-label="Last successful image for ${e(alias)}"><img src="${e(url)}" alt="Last successful image for ${e(alias)}"></button>` : '<span class="muted">No successful image</span>'}</div><div class="badges">${this.entityButton(tag, "display_in_sync", syncLabel, `class="badge ${synced ? "good" : ""}"`)}${this.entityButton(tag, "write_duration", error ? "Transmission error" : !valid(duration) || (!duration.attributes.success && !duration.attributes.skipped && !duration.attributes.error) ? "No transmission result" : duration.attributes.skipped ? `Skipped: ${duration.attributes.skipped}` : "No error", `class="badge ${error ? "bad" : ""}"`)}</div><dl class="facts"><dt>Last successful send</dt><dd>${this.entityButton(tag, "last_updated_content", this.relative(at), `title="${e(at ? new Date(at).toLocaleString(this.hass?.locale?.language || navigator.language) : "No successful send")}"`)}</dd><dt>Transmission duration</dt><dd>${this.entityButton(tag, "write_duration", durationValue)}</dd></dl><div class="actions"><button class="primary" data-action="edit" data-entry="${e(tag.entry_id)}">Edit design</button></div></article>`;
  }
  renderCards() {
    const errors = this.tags.filter((tag) => this.hasError(tag)).length;
    const unsynced = this.tags.filter(
      (tag) => this.state(tag, "display_in_sync")?.state === "off",
    ).length;
    this.shadowRoot.querySelector(".summary").textContent =
      `${this.tags.length} ESLs · ${errors} errors · ${unsynced} not in sync`;
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
    grid.innerHTML =
      tags.map((tag) => this.card(tag)).join("") ||
      `<div class="empty">${this.tags.length ? "No ESLs match your search or filter." : "Add a BLE ESL device in Settings → Devices & services."}</div>`;
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
