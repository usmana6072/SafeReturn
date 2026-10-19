import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3100", browserName: "chromium", channel: process.env.PLAYWRIGHT_CHANNEL || undefined },
  webServer: process.env.PLAYWRIGHT_EXTERNAL_SERVER ? undefined : { command: "node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100", url: "http://127.0.0.1:3100", reuseExistingServer: false, timeout: 60000 },
});
