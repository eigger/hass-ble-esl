const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

class AutomationDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>
    dialog{position:fixed;margin:0;inset:auto;width:440px;max-width:calc(100vw - 24px);max-height:calc(100dvh - 24px);overflow:auto;padding:20px;border:1px solid var(--divider-color,#ddd);border-radius:12px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);font:14px system-ui;box-shadow:0 12px 48px #0003}dialog::backdrop{background:#0003}*{box-sizing:border-box}header{display:flex;align-items:center;gap:12px}h2{font-size:18px;margin:0;flex:1}p{line-height:1.5;font-size:12px;color:var(--secondary-text-color,#637083)}button,input,select{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#ccd4dc);border-radius:6px;padding:8px}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #16838c;outline-offset:2px}.close{border:0;background:transparent;font-size:20px}.row{display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid var(--divider-color,#ddd)}.copy{flex:1;min-width:0}.name{color:inherit;overflow-wrap:anywhere;text-decoration:none}.name:hover{text-decoration:underline}.state{font-size:12px;color:var(--secondary-text-color,#637083);margin-top:4px}.on{color:var(--success-color,#28754a)}.off{color:var(--secondary-text-color,#637083)}.error{color:var(--error-color,#b3261e)}.link-controls{display:grid;gap:8px;margin-top:16px}label{display:grid;gap:6px;font-size:12px}input,select{width:100%;min-width:0}.primary{background:#166d75;color:white;border-color:#166d75}.empty{padding:16px 0;color:var(--secondary-text-color,#637083)}
    @media(max-width:650px){dialog{left:0!important;right:0;bottom:0;top:auto!important;width:100%;max-width:100%;max-height:85dvh;border-radius:16px 16px 0 0;padding:20px 16px}}
    </style><dialog aria-labelledby="title"><header><h2 id="title">Connected automations</h2><button class="close" aria-label="Close automations">×</button></header><p class="tag"></p><p>Links associate existing automations with this ESL. They do not change automation actions or apply this design.</p><div class="result" role="status"></div><div class="list"></div><div class="link-controls"><label>Search automations<input id="search" type="search" placeholder="Search by name"></label><label>Existing automation<select id="automation" aria-label="Existing automation"></select></label><button class="primary" data-action="link">Link automation</button></div></dialog>`;
    this.dialog = this.shadowRoot.querySelector("dialog");
    this.shadowRoot.querySelector(".close").onclick = () => this.dialog.close();
    this.dialog.addEventListener("close", () => {
      this.run++;
      this.restoreFocus?.();
    });
    this.shadowRoot.querySelector("#search").oninput = () =>
      this.renderOptions();
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
  }
  api(action, extra = {}) {
    return this.hass.callWS({
      type: "ble_esl/designer",
      action,
      entry_id: this.entryId,
      ...extra,
    });
  }
  async show(hass, tag, anchor, restoreFocus) {
    this.hass = hass;
    this.entryId = tag.entry_id;
    this.restoreFocus = restoreFocus;
    this.shadowRoot.querySelector(".tag").textContent = tag.name || tag.title;
    this.shadowRoot.querySelector("#search").value = "";
    this.data = { linked: [], available: [] };
    this.busy = true;
    this.status("Loading automations…");
    this.render();
    if (!this.dialog.open) this.dialog.showModal();
    this.anchorRect = anchor.getBoundingClientRect();
    this.position();
    const run = (this.run = (this.run || 0) + 1);
    try {
      const data = await this.api("automations");
      if (run !== this.run) return;
      this.data = data;
      this.status("");
      this.dispatchEvent(
        new CustomEvent("automations-changed", {
          detail: { entry_id: this.entryId, data },
          bubbles: true,
          composed: true,
        }),
      );
    } catch (error) {
      if (run === this.run) this.status(error.message || String(error), true);
    } finally {
      if (run === this.run) {
        this.busy = false;
        this.render();
      }
    }
  }
  position() {
    if (!this.dialog.open || !this.anchorRect) return;
    const width = Math.min(440, window.innerWidth - 24);
    const height = Math.min(
      this.dialog.scrollHeight + 2,
      window.innerHeight - 24,
    );
    this.dialog.style.left = `${Math.max(12, Math.min(this.anchorRect.left, window.innerWidth - width - 12))}px`;
    this.dialog.style.top = `${Math.max(12, Math.min(this.anchorRect.bottom + 8, window.innerHeight - height - 12))}px`;
  }
  updateHass(hass) {
    this.hass = hass;
    if (
      this.dialog.open &&
      this.listSignature !==
        JSON.stringify(this.data.linked.map((item) => this.current(item)))
    ) {
      this.renderList();
      this.position();
    }
  }
  status(message, error = false) {
    const result = this.shadowRoot.querySelector(".result");
    result.textContent = message;
    result.classList.toggle("error", error);
  }
  current(item) {
    const state = !item.missing && this.hass.states[item.entity_id];
    return state
      ? {
          ...item,
          state: state.state,
          name: state.attributes.friendly_name || item.name,
        }
      : { ...item, state: "unavailable" };
  }
  renderList() {
    const focused = this.shadowRoot.activeElement;
    const focusKey = focused?.closest(".row")?.dataset.key;
    const focusSelector = focused?.matches("a")
      ? "a"
      : focused?.dataset.action
        ? `[data-action="${CSS.escape(focused.dataset.action)}"]`
        : null;
    this.listSignature = JSON.stringify(
      this.data.linked.map((item) => this.current(item)),
    );
    this.shadowRoot.querySelector(".list").innerHTML =
      this.data.linked
        .map((record, index) => {
          const item = this.current(record);
          const active = item.state === "on";
          const state = item.missing
            ? "Unavailable"
            : active
              ? "Active"
              : item.state === "off"
                ? "Inactive"
                : "Unavailable";
          const detected = item.source.includes("detected");
          // Missing references may share an entity_id with a different automation.
          // Do not offer an edit link for that removed association.
          const name =
            item.id && !item.missing
              ? `<a class="name" href="/config/automation/edit/${encodeURIComponent(item.id)}">${esc(item.name)} ↗</a>`
              : `<span class="name">${esc(item.name)}</span>`;
          return `<div class="row" data-key="${esc(item.link_id || item.entity_id)}"><div class="copy">${name}<div class="state ${active ? "on" : "off"}">${state}${detected ? " · References this ESL" : " · Linked manually"}</div></div>${item.source.includes("manual") ? `<button data-action="unlink" data-index="${index}" ${this.busy ? "disabled" : ""} aria-label="${detected ? "Remove manual link" : "Unlink"} ${esc(item.name)}">${detected ? "Remove manual link" : "Unlink"}</button>` : ""}</div>`;
        })
        .join("") ||
      `<div class="empty">${this.busy ? "Loading…" : "No connected automations"}</div>`;
    if (focusKey && focusSelector)
      this.shadowRoot
        .querySelector(
          `.row[data-key="${CSS.escape(focusKey)}"] ${focusSelector}`,
        )
        ?.focus();
  }
  renderOptions() {
    const search = this.shadowRoot
      .querySelector("#search")
      .value.toLocaleLowerCase()
      .trim();
    const select = this.shadowRoot.querySelector("#automation");
    const selected = select.value;
    const linked = new Set(
      this.data.linked
        .filter((item) => !item.missing)
        .map((item) => item.entity_id),
    );
    const options = this.data.available.filter(
      (item) =>
        !linked.has(item.entity_id) &&
        this.current(item).name.toLocaleLowerCase().includes(search),
    );
    select.innerHTML =
      `<option value="">${options.length ? "Choose an automation…" : "No matching automations"}</option>` +
      options
        .map(
          (item) =>
            `<option value="${esc(item.entity_id)}">${esc(this.current(item).name)}</option>`,
        )
        .join("");
    if (options.some((item) => item.entity_id === selected))
      select.value = selected;
    select.disabled = this.busy;
    this.shadowRoot.querySelector('[data-action="link"]').disabled =
      this.busy || !options.length;
  }
  render() {
    this.renderList();
    this.renderOptions();
    this.position();
  }
  async click(event) {
    const button = event.target.closest("[data-action]");
    if (!button || this.busy) return;
    let action, extra;
    if (button.dataset.action === "link") {
      const entity_id = this.shadowRoot.querySelector("#automation").value;
      if (!entity_id) {
        this.status("Choose an existing automation.", true);
        return;
      }
      action = "link_automation";
      extra = { entity_id };
    } else {
      const item = this.data.linked[Number(button.dataset.index)];
      action = "unlink_automation";
      extra = { entity_id: item.entity_id, link_id: item.link_id };
    }
    this.busy = true;
    this.render();
    const run = this.run;
    const entryId = this.entryId;
    try {
      const data = await this.api(action, extra);
      // A completed association must refresh cards even if the dialog was closed.
      this.dispatchEvent(
        new CustomEvent("automations-changed", {
          detail: { entry_id: entryId, data },
          bubbles: true,
          composed: true,
        }),
      );
      if (run === this.run) {
        this.data = data;
        this.status("");
      }
    } catch (error) {
      if (run === this.run) this.status(error.message || String(error), true);
    } finally {
      if (run === this.run) {
        this.busy = false;
        this.render();
        this.shadowRoot.querySelector("#automation").focus();
      }
    }
  }
}
customElements.define("ble-esl-automation-dialog", AutomationDialog);
