import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:['customer-portal.spec.ts','independent-qr.spec.ts','item-checkout.spec.ts'],workers:1,use:{browserName:'chromium',headless:true},outputDir:'../test-results/customer-portal',reporter:'list'});
