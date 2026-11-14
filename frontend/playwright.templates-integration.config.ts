import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'templates-integration.spec.ts',outputDir:'../test-results/templates-integration',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
