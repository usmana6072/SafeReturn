import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'independent-qr.spec.ts',workers:1,use:{browserName:'chromium',channel:'msedge'},outputDir:'../tmp/phase7-independent-qr-browser'});
