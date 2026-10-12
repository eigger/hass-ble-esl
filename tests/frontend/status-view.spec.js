import { test, expect } from "@playwright/test";

test("status view keeps routine, preview error, and operation toast semantics", async ({
  page,
}) => {
  await page.goto("/");
  const states = await page.evaluate(async () => {
    const { renderStatusView } =
      await import("/frontend/editor/status-view.js");
    const root = document.createElement("div");
    root.innerHTML = '<div class="status"></div>';
    document.body.append(root);
    let state = {
      status: "Preview updating",
      error: false,
      errorSource: null,
      notice: null,
      busy: false,
    };
    let timer;
    const panel = {
      root,
      getState: () => state,
      translate: (value) => value,
      setNoticeTimer: (value) => (timer = value),
      onNoticeTimeout: () => {},
    };
    renderStatusView(panel);
    const routine = {
      role: root.querySelector(".status").getAttribute("role"),
      hidden: root.querySelector(".status").getAttribute("aria-hidden"),
      toast: !!root.querySelector(".toast"),
    };
    state = {
      status: "Preview failed",
      error: true,
      errorSource: "preview",
      notice: null,
      busy: false,
    };
    renderStatusView(panel);
    const previewError = {
      role: root.querySelector(".status").getAttribute("role"),
      toast: !!root.querySelector(".toast"),
      dismiss: !!root.querySelector(".status [data-action=dismiss-status]"),
    };
    state = {
      status: "Display saved",
      error: false,
      errorSource: null,
      notice: "Display saved",
      busy: false,
    };
    renderStatusView(panel);
    const successToast = {
      role: root.querySelector(".toast span").getAttribute("role"),
      text: root.querySelector(".toast span").textContent,
      dismiss: !!root.querySelector(".toast [data-action=dismiss-status]"),
      inlineHidden: root.querySelector(".status").getAttribute("aria-hidden"),
    };
    clearTimeout(timer);
    root.remove();
    return { routine, previewError, successToast };
  });

  expect(states.routine).toEqual({
    role: "status",
    hidden: null,
    toast: false,
  });
  expect(states.previewError).toEqual({
    role: "alert",
    toast: false,
    dismiss: true,
  });
  expect(states.successToast).toEqual({
    role: "status",
    text: "Display saved",
    dismiss: true,
    inlineHidden: "true",
  });
});
