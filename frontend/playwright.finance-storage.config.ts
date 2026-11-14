import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'phase12-finance-storage.spec.ts',outputDir:'../test-results/finance-storage',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
