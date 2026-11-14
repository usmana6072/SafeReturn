import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'quarantine.spec.ts',outputDir:'../test-results/quarantine',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
