import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'template-qa.spec.ts',outputDir:'../test-results/template-qa',workers:1,use:{browserName:'chromium',headless:true},reporter:'list'});
