import { test, expect } from '@playwright/test';
const bundle = require('./qa-browser-bundle.cjs');
import fs from 'node:fs';
import path from 'node:path';

async function openQA(page: any) {
  const cssDir = path.resolve('.next/static/chunks');
  const css = fs.readdirSync(cssDir).filter(f => f.endsWith('.css')).map(f => fs.readFileSync(path.join(cssDir, f), 'utf8')).join('\n') + fs.readFileSync('components/admin-qa.module.css','utf8').replaceAll('.screen','.qa-screen');
  await page.route('http://qa-demo.test/**', (route: any) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><html><head><style>'+css+'</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main></body></html>' }));
  await page.goto('http://qa-demo.test/');
  await page.evaluate(() => { (window as any).qaRole = { selectedRole: 'authenticated', effectiveRole: 'Operations', authenticatedRoles: ['operations'] }; });
  await page.addScriptTag({content: bundle()});
  await expect(page.getByRole('heading', {name: 'QR Quality Assurance', exact: true})).toBeVisible();
}

test('QA browser: lookup, stale input, pass, quarantine, filters, persistence and details', async ({page}) => {
  await openQA(page);
  const requests: string[] = [];
  page.on('request', request => requests.push(request.url()));
  await page.getByRole('textbox', {name:'Pair Tag ID',exact:true}).fill('unknown');
  await page.getByRole('button',{name:'Lookup Demo Pair'}).click();
  await expect(page.getByText(/not found. Select an existing/)).toBeVisible();
  await page.getByRole('combobox',{name:'Batch',exact:true}).selectOption('BATCH-2026-09');
  await page.getByRole('textbox',{name:'Pair Tag ID',exact:true}).fill('PAIR-2026-004');
  await page.getByRole('button',{name:'Lookup Demo Pair'}).click();
  await expect(page.getByText(/not the currently selected batch/)).toBeVisible();
  await page.getByRole('combobox',{name:'Batch',exact:true}).selectOption('all');
  await page.getByRole('button',{name:'PAIR-2026-004',exact:true}).click();
  await page.getByRole('textbox',{name:'Pair Tag ID',exact:true}).fill('PAIR-2026-005');
  await expect(page.getByRole('button',{name:'Pass QA',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Lookup Demo Pair'}).click();
  await page.getByRole('button',{name:'Pass QA',exact:true}).click();
  await expect(page.getByText('Demo QA result recorded as Passed.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Pass QA',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'PAIR-2026-004',exact:true}).click();
  await page.getByRole('button',{name:'Reject & Quarantine',exact:true}).click();
  const dialog = page.getByRole('dialog');
  await page.getByRole('button',{name:'Confirm Quarantine'}).click();
  await expect(dialog.getByText('Please select a rejection reason.')).toBeVisible();
  await page.getByRole('combobox',{name:'Rejection reason'}).selectOption('Physical damage');
  await page.getByRole('textbox',{name:'Inspection notes'}).fill('Synthetic corner damage');
  await page.getByRole('button',{name:'Confirm Quarantine'}).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByText('Demo pair marked as Quarantined.')).toBeVisible();
  await page.getByRole('combobox',{name:'Inspection outcome'}).selectOption('Quarantined');
  await page.getByRole('textbox',{name:'Search inspection pair ID'}).fill('004');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await page.getByRole('button',{name:'View Details',exact:true}).click();
  await expect(page.getByRole('dialog').getByText('Synthetic corner damage')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('safereturn_demo_db')!));
  expect(stored.qaInspections).toHaveLength(5);
  expect(stored.qrBatches[1].status).toBe('In QA');
  expect(requests).toEqual([]);
  await page.reload();
  await page.evaluate(() => { (window as any).qaRole = { selectedRole:'authenticated',effectiveRole:'Operations',authenticatedRoles:['operations'] }; });
  await page.addScriptTag({content:bundle()});
  await expect(page.locator('tbody tr')).toHaveCount(5);
});

for (const width of [1366,1440,375]) test('QA responsive '+width, async ({page}) => {
  await page.setViewportSize({width,height:width===1440?900:768});
  await openQA(page);
  await page.getByRole('button',{name:'PAIR-2026-004',exact:true}).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button',{name:'Reject & Quarantine',exact:true}).click();
  expect(await page.getByRole('dialog').evaluate(el => el.getBoundingClientRect().width)).toBeLessThan(width);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.screenshot({path:'test-results/qa-'+width+'.png',fullPage:true});
});

test('QA preview cannot grant inspection rights and storage failures are visible',async ({page})=>{
 await openQA(page);
 await page.getByRole('button',{name:'PAIR-2026-004',exact:true}).click();
 await page.evaluate(()=>{(window as any).qaRole={selectedRole:'Operations',effectiveRole:'Operations',authenticatedRoles:['finance']};});
 await page.getByRole('button',{name:'PAIR-2026-005',exact:true}).click();
 await expect(page.getByRole('button',{name:'Pass QA',exact:true})).toBeDisabled();
 await page.evaluate(()=>{(window as any).qaRole={selectedRole:'authenticated',effectiveRole:'Operations',authenticatedRoles:['operations']};});
 await page.getByRole('button',{name:'PAIR-2026-004',exact:true}).click();
 await page.evaluate(()=>{Storage.prototype.setItem=()=>{throw new Error('quota');};});
 await page.getByRole('button',{name:'Pass QA',exact:true}).click();
 await expect(page.getByText(/Unable to save demo inspection/)).toBeVisible();
 await expect(page.getByRole('button',{name:'Pass QA',exact:true})).toBeEnabled();
});
