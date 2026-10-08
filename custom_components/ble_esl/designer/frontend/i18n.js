// Translate UI copy only. Entity names, design content and payloads stay untouched.
import { messages } from "./locales/index.js";
export const supportedLanguages = Object.keys(messages);
export function language(hass) {
  const requested = String(hass?.locale?.language || hass?.language || "en")
    .toLowerCase()
    .replaceAll("_", "-");
  const exact = supportedLanguages.find((code) => {
    const normalized = code.toLowerCase();
    return requested === normalized || requested.startsWith(normalized + "-");
  });
  if (exact) return exact;
  if (requested === "zh" || requested.startsWith("zh-"))
    return /^zh-(tw|hk|mo)(-|$)/.test(requested) ? "zh-Hant" : "zh-Hans";
  if (requested === "pt" || requested.startsWith("pt-")) return "pt-BR";
  return "en";
}
export function t(hass, key, values = {}) {
  if (key && typeof key === "object") return t(hass, key.key, key.values);
  const text = messages[language(hass)][key] || key;
  return text.replace(/\{(\w+)\}/g, (match, name) =>
    Object.hasOwn(values, name)
      ? values[name] && typeof values[name] === "object"
        ? t(hass, values[name])
        : String(values[name])
      : match,
  );
}
// These bindings are captured only from constructor markup, before user data is inserted.
const bindings = new WeakMap();
export function bindStatic(root) {
  const copy = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const key = node.textContent.trim();
    if (Object.hasOwn(messages.en, key)) copy.push({ node, key });
  }
  for (const node of root.querySelectorAll("*"))
    for (const attr of ["title", "aria-label", "placeholder", "alt"])
      if (Object.hasOwn(messages.en, node.getAttribute(attr)))
        copy.push({ node, attr, key: node.getAttribute(attr) });
  bindings.set(root, copy);
}
export function localize(root, hass) {
  for (const { node, attr, key } of bindings.get(root) || [])
    if (attr) node.setAttribute(attr, t(hass, key));
    else node.textContent = t(hass, key);
}

// Preserve modal hosts and their drafts when the surrounding markup changes language.
export function rerenderWithDialogs(root, hass, render) {
  const selector =
    "ble-esl-component-editor, ble-esl-dynamic-fields, ble-esl-import-dialog, ble-esl-yaml-dialog, ble-esl-preview-parameters-dialog";
  const hosts = [...root.querySelectorAll(selector)];
  const opened = [];
  const inspect = (host) => {
    const dialog = host.shadowRoot.querySelector("dialog");
    if (dialog?.open) {
      const active = host.shadowRoot.activeElement;
      opened.push({
        host,
        activeId: active?.id,
        selectionStart: active?.selectionStart,
        selectionEnd: active?.selectionEnd,
      });
    }
    for (const child of host.shadowRoot.querySelectorAll(selector))
      inspect(child);
  };
  for (const host of hosts) inspect(host);
  for (const { host } of [...opened].reverse())
    host.shadowRoot.querySelector("dialog").close();
  for (const host of hosts) host.remove();
  render();
  for (const host of hosts) {
    root.append(host);
    host.updateHass?.(hass);
  }
  for (const { host, activeId, selectionStart, selectionEnd } of opened) {
    const dialog = host.shadowRoot.querySelector("dialog");
    if (!dialog.open) dialog.showModal();
    const active = activeId ? host.shadowRoot.getElementById(activeId) : null;
    active?.focus({ preventScroll: true });
    if (typeof selectionStart === "number")
      active?.setSelectionRange(selectionStart, selectionEnd);
  }
}
