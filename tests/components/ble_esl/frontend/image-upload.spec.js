import { test, expect } from "@playwright/test";
import { handleImageUpload } from "../../../../custom_components/ble_esl/designer/frontend/editor/image-upload.js";

test("image upload records one edit and clears its busy state", async () => {
  const previousReader = globalThis.FileReader;
  globalThis.FileReader = class {
    readAsDataURL() {
      this.result = "data:image/png;base64,abc";
      queueMicrotask(() => this.onload());
    }
  };
  const element = { id: "photo", image: null };
  const panel = {
    element,
    document: { elements: [element] },
    tag: { entry_id: "tag-1" },
    _automationSessionToken: null,
    pendingUploads: new Set(),
    checkpointCount: 0,
    editCount: 0,
    checkpoint() {
      this.checkpointCount++;
    },
    edited() {
      this.editCount++;
    },
    render() {},
  };
  const file = {
    slice: () => ({ arrayBuffer: async () => new ArrayBuffer(0) }),
  };

  try {
    handleImageUpload(panel, { files: [file] });
    await Promise.all([...panel.pendingUploads]);
    await Promise.resolve();

    expect(element.image).toBe("data:image/png;base64,abc");
    expect(panel.checkpointCount).toBe(1);
    expect(panel.editCount).toBe(1);
    expect(panel.status).toBe("Image added");
    expect(panel.busy).toBe(false);
    expect(panel.pendingUploads.size).toBe(0);
  } finally {
    globalThis.FileReader = previousReader;
  }
});

test("image upload does not apply to a document replaced while reading", async () => {
  const previousReader = globalThis.FileReader;
  let reader;
  globalThis.FileReader = class {
    constructor() {
      reader = this;
    }
    readAsDataURL() {
      this.result = "data:image/png;base64,abc";
    }
  };
  const element = { id: "photo", image: null };
  const originalDocument = { elements: [element] };
  const panel = {
    element,
    document: originalDocument,
    tag: { entry_id: "tag-1" },
    _automationSessionToken: null,
    pendingUploads: new Set(),
    checkpoint() {
      throw new Error("stale upload must not checkpoint");
    },
    edited() {
      throw new Error("stale upload must not edit");
    },
    render() {},
  };
  const file = {
    slice: () => ({ arrayBuffer: async () => new ArrayBuffer(0) }),
  };

  try {
    handleImageUpload(panel, { files: [file] });
    panel.document = { elements: [] };
    reader.onload();
    await Promise.all([...panel.pendingUploads]);
    await Promise.resolve();

    expect(element.image).toBeNull();
    expect(panel.pendingUploads.size).toBe(0);
  } finally {
    globalThis.FileReader = previousReader;
  }
});

test("image upload does not apply to a different automation session", async () => {
  const previousReader = globalThis.FileReader;
  let reader;
  globalThis.FileReader = class {
    constructor() {
      reader = this;
    }
    readAsDataURL() {
      this.result = "data:image/png;base64,abc";
    }
  };
  const element = { id: "photo", image: null };
  const panel = {
    element,
    document: { elements: [element] },
    tag: { entry_id: "tag-1" },
    _automationSessionToken: "session-a",
    pendingUploads: new Set(),
    checkpoint() {
      throw new Error("stale upload must not checkpoint");
    },
    edited() {
      throw new Error("stale upload must not edit");
    },
    render() {},
  };
  const file = {
    slice: () => ({ arrayBuffer: async () => new ArrayBuffer(0) }),
  };

  try {
    handleImageUpload(panel, { files: [file] });
    panel._automationSessionToken = "session-b";
    reader.onload();
    await Promise.all([...panel.pendingUploads]);
    await Promise.resolve();

    expect(element.image).toBeNull();
    expect(panel.busy).toBe(true);
    expect(panel.pendingUploads.size).toBe(0);
  } finally {
    globalThis.FileReader = previousReader;
  }
});
