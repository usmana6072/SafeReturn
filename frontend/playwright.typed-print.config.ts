import {defineConfig} from "@playwright/test";
export default defineConfig({testDir:"./tests",testMatch:"typed-print.spec.ts",workers:1,use:{browserName:"chromium",channel:"msedge"},outputDir:"../tmp/phase6-typed-print-browser"});
