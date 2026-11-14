import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:['independent-finance.spec.ts','payments-read.spec.ts'],outputDir:'../test-results/independent-finance',workers:1,use:{browserName:'chromium',headless:true},reporter:'list'});
