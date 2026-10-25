import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: /admin-(add-product-screen4|product-details-screen5)\.spec\.ts/,
  workers: 1,
  outputDir: "../tmp/product-pricing-playwright",
});
