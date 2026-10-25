import {defineConfig} from "@playwright/test";
export default defineConfig({
  testDir:"./tests",testMatch:"product-admin-live.spec.ts",workers:1,
  use:{browserName:"chromium",channel:"msedge"},
  outputDir:"../tmp/phase3-catalog-browser",
});
