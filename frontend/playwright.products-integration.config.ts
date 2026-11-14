import {defineConfig} from '@playwright/test';
// Source-bundled UI and in-memory relay/upstream only: no Next server or legacy setup.
export default defineConfig({testDir:'./tests',testMatch:'products-integration.spec.ts',outputDir:'../test-results/products-integration',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
