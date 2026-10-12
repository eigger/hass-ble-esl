export const LOADING_STEPS = Object.freeze([
  ["fonts", "fonts"],
  ["icons", "icons"],
  ["templates", "tile styles"],
  ["specs", "component specs"],
  ["tags", "devices"],
]);

export function createLoadingSteps() {
  return LOADING_STEPS.map(([key, label]) => ({ key, label, done: false }));
}

export function renderLoadingContent(loading, { translate, escapeHtml }) {
  const { error, steps } = loading;
  if (error)
    return `<p class="error">${escapeHtml(error)}</p><button data-action="reload">${translate("Retry")}</button>`;
  const done = steps.filter((item) => item.done).length;
  const waiting = steps.find((item) => !item.done);
  return `<p>${escapeHtml(translate("Loading {step}… ({done}/{count})", { step: translate(waiting?.label || "designer"), done, count: steps.length }))}</p><progress aria-label="${translate("Loading designer")}" max="${steps.length}" value="${done}"></progress>`;
}
