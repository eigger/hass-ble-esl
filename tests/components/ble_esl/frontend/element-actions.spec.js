import { expect, test } from "@playwright/test";
import {
  ELEMENT_ACTIONS,
  renderElementActionBar,
  renderElementActionMenu,
} from "../../../../custom_components/ble_esl/designer/frontend/editor/element-actions.js";

const renderOptions = {
  t: (message) => message,
  icon: (name) => `<svg data-icon="${name}"></svg>`,
  toolIcon: (name) => `<svg data-icon="${name}"></svg>`,
};

test("context menu and action bar expose the same actions and icons", () => {
  const menu = renderElementActionMenu(renderOptions);
  const bar = renderElementActionBar({ ...renderOptions, busy: false });

  for (const [action, label, shortcut] of ELEMENT_ACTIONS) {
    expect(menu).toContain(`role="menuitem" data-action="${action}"`);
    expect(menu).toContain(`<span>${label}</span><kbd>${shortcut}</kbd>`);
    expect(bar).toContain(`data-action="${action}"`);
    expect(bar).toContain(`aria-label="${label}"`);
    expect(bar).toContain(
      `title="${label}${shortcut ? ` (${shortcut})` : ""}"`,
    );
  }
  expect(menu).toContain('data-icon="delete"');
  expect(bar).toContain('aria-label="Element actions"');
  expect(bar).toContain('role="toolbar"');
});

test("action bar disables every action while the editor is busy", () => {
  const bar = renderElementActionBar({ ...renderOptions, busy: true });

  expect((bar.match(/ disabled /g) || []).length).toBe(ELEMENT_ACTIONS.length);
});
