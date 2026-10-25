import {defineConfig} from "@playwright/test";
export default defineConfig({testDir:"./tests",testMatch:"item-checkout.spec.ts",workers:1,use:{browserName:"chromium",channel:"msedge"},outputDir:"../tmp/phase4-checkout-browser"});
