import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'admin-privacy-screen20.spec.ts',outputDir:'../test-results/privacy-metadata',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
