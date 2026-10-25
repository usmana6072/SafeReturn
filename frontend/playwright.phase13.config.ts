import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'phase13.spec.ts',outputDir:'../test-results/phase13',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
