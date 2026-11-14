import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:['item-checkout.spec.ts','allocation.spec.ts','independent-qr.spec.ts'],workers:1,use:{browserName:'chromium',headless:true},outputDir:'../test-results/customer-flow',reporter:'list'});
