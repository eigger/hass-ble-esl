import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/frontend",
  testMatch: "*.spec.js",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8765",
    viewport: { width: 1440, height: 1000 },
  },
  // WebKit stands in for Safari, which differs on shadow-tree selection.
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
    { name: "webkit", use: { browserName: "webkit" } },
  ],
  webServer: {
    command: `${process.env.DESIGNER_PYTHON || ".venv/bin/python"} scripts/designer_demo.py`,
    url: "http://127.0.0.1:8765",
    reuseExistingServer: !process.env.CI,
  },
});
