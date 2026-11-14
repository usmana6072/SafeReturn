import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'print-jobs-integration.spec.ts',outputDir:'../test-results/print-jobs-integration',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
