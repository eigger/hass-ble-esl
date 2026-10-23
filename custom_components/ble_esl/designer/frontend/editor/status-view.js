import { materialIcon } from "./material-icons.js";
// Present editor status in the inline live region and, when appropriate, as
// a floating notice. The panel retains status state and notice timing.
export function sendButtonHint({ tag, busy, status, translate }) {
  if (tag && !tag.writable)
    return translate(
      "Discovery only: preview is available; sending is not supported yet.",
    );
  if (busy && status) return translate(status);
  return translate("Send to tag");
}

export function appendStatusDismiss(panel, node) {
  const dismiss = document.createElement("button");
  dismiss.dataset.action = "dismiss-status";
  dismiss.setAttribute("aria-label", panel.translate("Dismiss message"));
  dismiss.innerHTML = materialIcon("close");
  node.append(dismiss);
}

export function renderStatusView(panel) {
  const state = panel.getState();
  const node = panel.root.querySelector(".status");
  if (!node) return;
  const text = panel.translate(state.status);
  node.classList.toggle("error", !!state.error);
  node.setAttribute("role", state.error ? "alert" : "status");

  // Keep the inline region in the document flow while the floating notice is
  // visible, so status changes do not move the editor layout.
  const notice = state.notice !== null && state.notice === state.status;
  const toast =
    Boolean(state.status) &&
    ((state.error && state.errorSource !== "preview") || notice);
  // The floating toast carries the full message. Keep only the status
  // placeholder's minimum height here so wrapped messages cannot move the
  // canvas when the toast appears or disappears.
  node.textContent = toast ? "" : text;
  node.classList.toggle("toasting", toast);
  if (toast) node.setAttribute("aria-hidden", "true");
  else node.removeAttribute("aria-hidden");

  let host = panel.root.querySelector(".toast");
  if (!toast) host?.remove();
  else {
    if (!host) {
      host = document.createElement("div");
      host.className = "toast";
      host.append(document.createElement("span"));
      panel.root.append(host);
    }
    host.classList.toggle("error", !!state.error);
    host.classList.toggle("busy", !!state.busy);
    const message = host.firstElementChild;
    message.textContent = text;
    message.setAttribute("role", state.error ? "alert" : "status");
    host.querySelector("button")?.remove();
    // Keep the close control outside the live region to avoid duplicate speech.
    if (!state.busy) appendStatusDismiss(panel, host);
  }

  clearTimeout(panel.noticeTimer);
  panel.setNoticeTimer(undefined);
  if (toast && !state.error && !state.busy) {
    const shown = state.status;
    panel.setNoticeTimer(
      setTimeout(() => {
        if (panel.getState().status !== shown) return;
        panel.onNoticeTimeout();
      }, 6000),
    );
  }
  if (!toast && state.error && state.status) appendStatusDismiss(panel, node);
}
