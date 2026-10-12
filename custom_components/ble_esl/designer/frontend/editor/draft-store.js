// Session-scoped persistence for unsaved display documents. The editor owns
// which documents are drafts; this module owns their storage format/lifetime.
export const DRAFT_KEY = "ble_esl_designer_drafts";

export function readStoredDrafts(storage) {
  try {
    const stored = JSON.parse(
      (storage ?? globalThis.sessionStorage).getItem(DRAFT_KEY) || "{}",
    );
    return stored && typeof stored === "object" ? stored : {};
  } catch {
    return {};
  }
}

export function hasStoredDraft(entryId, storage) {
  return Object.hasOwn(readStoredDrafts(storage), entryId);
}

export function persistDrafts(drafts, tags, storage) {
  const stored = {};
  for (const [entryId, document] of drafts) {
    const tag = tags.find((item) => item.entry_id === entryId);
    if (tag)
      stored[entryId] = { width: tag.width, height: tag.height, document };
  }
  try {
    if (Object.keys(stored).length)
      (storage ?? globalThis.sessionStorage).setItem(
        DRAFT_KEY,
        JSON.stringify(stored),
      );
    else (storage ?? globalThis.sessionStorage).removeItem(DRAFT_KEY);
  } catch {
    // Storage may be full or blocked; the draft is then simply not kept.
  }
}

export function restoreStoredDrafts(drafts, tags, storage) {
  const stored = readStoredDrafts(storage);
  try {
    (storage ?? globalThis.sessionStorage).removeItem(DRAFT_KEY);
  } catch {
    // Nothing to clean up.
  }
  for (const [entryId, draft] of Object.entries(stored)) {
    const tag = tags.find((item) => item.entry_id === entryId);
    if (
      tag &&
      draft?.document &&
      tag.width === draft.width &&
      tag.height === draft.height &&
      !drafts.has(entryId)
    )
      drafts.set(entryId, draft.document);
  }
}
