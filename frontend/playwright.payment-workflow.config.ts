import { defineConfig } from '@playwright/test';

export default defineConfig({
    testDir: './tests',
    testMatch: 'payment-workflow.spec.ts',
    outputDir: '../test-results/payment-workflow',
    workers: 1,
    use: { browserName: 'chromium', headless: true },
});
