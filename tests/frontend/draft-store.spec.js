import { test, expect } from "@playwright/test";
import {
  DRAFT_KEY,
  hasStoredDraft,
  persistDrafts,
  readStoredDrafts,
  restoreStoredDrafts,
} from "../../custom_components/ble_esl/designer/frontend/editor/draft-store.js";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
    values,
  };
}

test("draft store writes the established session format and clears empty drafts", () => {
  const storage = memoryStorage();
  const document = { elements: [{ id: "text-1" }] };
  persistDrafts(
    new Map([
      ["tag-1", document],
      ["missing-tag", { elements: [] }],
    ]),
    [{ entry_id: "tag-1", width: 296, height: 128 }],
    storage,
  );

  expect(JSON.parse(storage.getItem(DRAFT_KEY))).toEqual({
    "tag-1": { width: 296, height: 128, document },
  });
  expect(hasStoredDraft("tag-1", storage)).toBe(true);
  expect(hasStoredDraft("tag-2", storage)).toBe(false);

  persistDrafts(new Map(), [], storage);
  expect(storage.getItem(DRAFT_KEY)).toBe(null);
});

test("restore removes the stored snapshot and only restores matching tag sizes", () => {
  const document = { elements: [{ id: "saved" }] };
  const storage = memoryStorage({
    [DRAFT_KEY]: JSON.stringify({
      match: { width: 296, height: 128, document },
      fresh: { width: 296, height: 128, document },
      resized: { width: 100, height: 40, document },
      missing: { width: 296, height: 128, document },
      malformed: { width: 296, height: 128 },
    }),
  });
  const drafts = new Map([["match", { elements: [{ id: "existing" }] }]]);

  restoreStoredDrafts(
    drafts,
    [
      { entry_id: "match", width: 296, height: 128 },
      { entry_id: "fresh", width: 296, height: 128 },
      { entry_id: "resized", width: 120, height: 40 },
    ],
    storage,
  );

  expect([...drafts]).toEqual([
    ["match", { elements: [{ id: "existing" }] }],
    ["fresh", document],
  ]);
  expect(storage.getItem(DRAFT_KEY)).toBe(null);
});

test("invalid or unavailable storage reads as no drafts and writes fail quietly", () => {
  const invalid = memoryStorage({ [DRAFT_KEY]: "not-json" });
  expect(readStoredDrafts(invalid)).toEqual({});
  expect(hasStoredDraft("tag-1", invalid)).toBe(false);

  const blockedStorage = {
    getItem() {
      throw new Error("blocked");
    },
    setItem() {
      throw new Error("blocked");
    },
    removeItem() {
      throw new Error("blocked");
    },
  };
  expect(readStoredDrafts(blockedStorage)).toEqual({});
  expect(() =>
    persistDrafts(new Map([["tag-1", {}]]), [], blockedStorage),
  ).not.toThrow();
  expect(() =>
    restoreStoredDrafts(new Map(), [], blockedStorage),
  ).not.toThrow();
});
