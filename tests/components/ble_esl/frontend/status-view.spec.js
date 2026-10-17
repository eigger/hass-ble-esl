import { test, expect } from "@playwright/test";
import { sendButtonHint } from "../../../../custom_components/ble_esl/designer/frontend/editor/status-view.js";

test("send button hint reflects tag capability and busy status", () => {
  const translate = (message) => `translated: ${message}`;
  expect(
    sendButtonHint({
      tag: { writable: false },
      busy: true,
      status: "Sending…",
      translate,
    }),
  ).toBe(
    "translated: Discovery only: preview is available; sending is not supported yet.",
  );
  expect(
    sendButtonHint({
      tag: { writable: true },
      busy: true,
      status: "Sending…",
      translate,
    }),
  ).toBe("translated: Sending…");
  expect(
    sendButtonHint({ tag: null, busy: false, status: "Ready", translate }),
  ).toBe("translated: Send to tag");
});

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
      inlineText: root.querySelector(".status").textContent,
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
    inlineText: "",
  });
});
