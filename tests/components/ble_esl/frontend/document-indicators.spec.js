import { test, expect } from "@playwright/test";
import {
  markDocumentDirty,
  syncDocumentHistoryControls,
} from "../../../../custom_components/ble_esl/designer/frontend/editor/document-indicators.js";

test("document indicators retain save labels, dirty state, and history availability", () => {
  const undo = { disabled: false };
  const redo = { disabled: false };
  const save = {
    innerHTML: "",
    title: "",
    attributes: {},
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    getAttribute(name) {
      return this.attributes[name] ?? null;
    },
  };
  const badge = { hidden: true };
  const previewTitle = { textContent: "Exact preview" };
  const root = {
    querySelector(selector) {
      return (
        {
          '[data-action="undo"]': undo,
          '[data-action="redo"]': redo,
          '[data-action="save"]': save,
          "#dirty-badge": badge,
          ".canvas-wrap": {
            previousElementSibling: { querySelector: () => previewTitle },
          },
        }[selector] ?? null
      );
    },
  };
  const translate = (key) => key;
  syncDocumentHistoryControls(root, {
    undoCount: 1,
    redoCount: 0,
    busy: false,
  });
  const history = { undoDisabled: undo.disabled, redoDisabled: redo.disabled };
  markDocumentDirty(root, {
    undoCount: 1,
    redoCount: 0,
    busy: false,
    automationSaveMode: false,
    translate,
    saveIcon: '<svg aria-hidden="true"></svg>',
  });
  const regular = {
    label: save.getAttribute("aria-label"),
    title: save.title,
    badgeHidden: badge.hidden,
    previewTitle: previewTitle.textContent,
    hasIcon: save.innerHTML.includes('aria-hidden="true"'),
  };
  markDocumentDirty(root, {
    undoCount: 1,
    redoCount: 1,
    busy: true,
    automationSaveMode: true,
    translate,
    saveIcon: "",
  });
  const automation = {
    label: save.getAttribute("aria-label"),
    undoDisabled: undo.disabled,
    redoDisabled: redo.disabled,
  };

  expect(history).toEqual({ undoDisabled: false, redoDisabled: true });
  expect(regular).toEqual({
    label: "Save (unsaved changes)",
    title: "Save (unsaved changes) (⌘/Ctrl S)",
    badgeHidden: false,
    previewTitle: "Editing preview",
    hasIcon: true,
  });
  expect(automation).toEqual({
    label: "Save to automation",
    undoDisabled: true,
    redoDisabled: true,
  });
});
