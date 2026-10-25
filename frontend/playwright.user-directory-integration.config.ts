import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'user-directory-integration.spec.ts',outputDir:'../test-results/user-directory-integration',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
