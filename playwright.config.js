import { defineConfig } from "@playwright/test";
const port = process.env.DESIGNER_PORT || "8765";
export default defineConfig({
  testDir: "tests/components/ble_esl/frontend",
  testMatch: "*.spec.js",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    viewport: { width: 1440, height: 1000 },
  },
  // CI logs only show complete lines; the default "dot" reporter looks hung.
  reporter: "list",
  // WebKit stands in for Safari (shadow-tree selection differs) but hangs on
  // the Linux CI runners, so it is opt-in: `npm run test:webkit`.
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
    ...(process.env.WEBKIT
      ? [{ name: "webkit", use: { browserName: "webkit" } }]
      : []),
  ],
  webServer: {
    command: `${process.env.DESIGNER_PYTHON || ".venv/bin/python"} scripts/designer_demo.py`,
    url: `http://127.0.0.1:${port}`,
    env: { DESIGNER_PORT: port },
    reuseExistingServer: !process.env.CI,
  },
});
