import { clone, emptyDocument } from "../model.js";

// Owns the active editor document and the state that must move with it.
// Template and automation session metadata remains with the panel/manager.
export class EditorSession {
  constructor(document = emptyDocument()) {
    this.document = document;
    this.selected = null;
    this.undoStack = [];
    this.redoStack = [];
    this.dirty = false;
    // The document as last known saved (or loaded), so that undoing back to
    // it is no longer "unsaved". Unknown (null) for a restored draft.
    this.cleanSignature = JSON.stringify(document);
  }

  capture() {
    return {
      document: this.document,
      selected: this.selected,
      undoStack: this.undoStack,
      redoStack: this.redoStack,
      dirty: this.dirty,
      cleanSignature: this.cleanSignature,
    };
  }

  restore(state) {
    this.document = state.document;
    this.selected = state.selected;
    this.undoStack = state.undoStack;
    this.redoStack = state.redoStack;
    this.dirty = state.dirty;
    this.cleanSignature = state.cleanSignature ?? null;
  }

  reset(document, { selected = null, dirty = false } = {}) {
    this.document = document;
    this.selected = selected;
    this.dirty = dirty;
    this.cleanSignature = dirty ? null : JSON.stringify(document);
    this.clearHistory();
  }

  clearHistory() {
    this.undoStack = [];
    this.redoStack = [];
  }

  checkpoint(snapshot = this.document) {
    this.pushUndo(clone(snapshot));
  }

  pushUndo(snapshot) {
    // Callers pass snapshots they already detached before editing starts.
    this.undoStack.push(snapshot);
    if (this.undoStack.length > 100) this.undoStack.shift();
    this.redoStack = [];
  }

  markDirty(value = true) {
    this.dirty = value;
    this.cleanSignature = value ? this.cleanSignature : JSON.stringify(this.document);
  }

  // True when the document is exactly what was last saved or loaded.
  isClean() {
    return (
      this.cleanSignature !== null &&
      JSON.stringify(this.document) === this.cleanSignature
    );
  }

  stepHistory(direction) {
    const source = direction === "undo" ? this.undoStack : this.redoStack;
    const target = direction === "undo" ? this.redoStack : this.undoStack;
    if (!source.length) return false;
    target.push(clone(this.document));
    this.document = source.pop();
    return true;
  }
}
