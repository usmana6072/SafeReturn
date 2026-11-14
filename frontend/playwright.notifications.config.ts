import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'admin-notifications-screen19.spec.ts',outputDir:'../test-results/notifications',workers:1,timeout:30000,use:{browserName:'chromium',headless:true},reporter:'list'});
