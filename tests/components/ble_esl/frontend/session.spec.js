import { test, expect } from "@playwright/test";
import { EditorSession } from "../../../../custom_components/ble_esl/designer/frontend/editor/session.js";

const documentWith = (value) => ({
  version: 1,
  background: "white",
  elements: [{ id: String(value) }],
});

test("editor session owns document history, selection and dirty state", () => {
  const session = new EditorSession(documentWith(1));
  session.selected = "1";
  session.checkpoint();
  session.document = documentWith(2);
  session.selected = "2";
  session.markDirty();

  expect(session.stepHistory("undo")).toBe(true);
  expect(session.document.elements[0].id).toBe("1");
  expect(session.redoStack).toHaveLength(1);
  expect(session.stepHistory("redo")).toBe(true);
  expect(session.document.elements[0].id).toBe("2");

  session.checkpoint();
  expect(session.redoStack).toHaveLength(0);
  expect(session.dirty).toBe(true);
});

test("editor session reset and restore keep history policy bounded", () => {
  const session = new EditorSession(documentWith(0));
  for (let value = 0; value < 102; value++) {
    session.document = documentWith(value);
    session.checkpoint();
  }
  expect(session.undoStack).toHaveLength(100);

  const saved = session.capture();
  session.reset(documentWith("fresh"), { selected: "fresh", dirty: false });
  expect(session.undoStack).toHaveLength(0);
  expect(session.redoStack).toHaveLength(0);
  session.restore(saved);
  expect(session.document.elements[0].id).toBe("101");
  expect(session.undoStack).toHaveLength(100);
});

test("pushUndo adopts detached snapshots while checkpoint clones live state", () => {
  const session = new EditorSession(documentWith("live"));
  const snapshot = documentWith("before-edit");
  session.pushUndo(snapshot);
  expect(session.undoStack[0]).toBe(snapshot);

  session.checkpoint();
  expect(session.undoStack[1]).not.toBe(session.document);
  expect(session.undoStack[1]).toEqual(session.document);
});

test("undoing back to the saved state is clean, a restored draft never is", () => {
  const session = new EditorSession(documentWith(1));
  session.checkpoint();
  session.document = documentWith(2);
  session.markDirty();
  expect(session.isClean()).toBe(false);
  session.stepHistory("undo");
  expect(session.isClean()).toBe(true);
  session.stepHistory("redo");
  expect(session.isClean()).toBe(false);
  // Saving makes the current document the clean one.
  session.markDirty(false);
  expect(session.isClean()).toBe(true);

  session.reset(documentWith(3), { dirty: true });
  expect(session.isClean()).toBe(false);
  const state = session.capture();
  session.reset(documentWith(4));
  session.restore(state);
  expect(session.isClean()).toBe(false);
});

test("a save of an older snapshot becomes the clean reference", () => {
  const session = new EditorSession(documentWith(1));
  session.checkpoint();
  session.document = documentWith(2);
  session.markDirty();
  session.checkpoint();
  session.document = documentWith(3);
  session.markSaved(documentWith(2));
  expect(session.isClean()).toBe(false);
  session.stepHistory("undo");
  expect(session.isClean()).toBe(true);
  session.stepHistory("undo");
  expect(session.isClean()).toBe(false);
});
