import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs'; import path from 'node:path'; import vm from 'node:vm'; import ts from 'typescript';
import { INITIAL_SEED_DATA, INITIAL_SUPPORT_CASES, loadAdminMockData, resetAdminMockData, saveAdminMockData, updateDemoSupportCase } from '../lib/admin-mock-data';
import { demoSupportNextStates } from '../lib/admin-support-policy';
const bundle = require('./qa-browser-bundle.cjs');
const options = { componentPath: '../components/admin-support-cases.tsx', exportName: 'AdminSupportCases', cssClass: 'support-screen' };
async function open(page: Page, role = 'support', seed?: unknown, preview = 'authenticated', start = '/admin/support', customerDetailsAvailable = true) {
  const css = fs.readdirSync('.next/static/chunks').filter(f => f.endsWith('.css')).map(f => fs.readFileSync(path.join('.next/static/chunks', f), 'utf8')).join('\n') + fs.readFileSync('components/admin-support-cases.module.css', 'utf8').replaceAll('.screen', '.support-screen');
  await page.route('http://support-demo.test/**', route => {
    const pathname = new URL(route.request().url()).pathname;
    const caseId = pathname.startsWith('/admin/support/') ? decodeURIComponent(pathname.slice('/admin/support/'.length)) : undefined;
    return route.fulfill({ contentType: 'text/html; charset=utf-8', body: '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + css + '</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main><script>window.qaRole=' + JSON.stringify({ authenticatedRoles: [role], selectedRole: preview, effectiveRole: role }) + ';window.qaProps=' + JSON.stringify({ caseId, customerDetailsAvailable }) + ';' + bundle(options) + '</script></body></html>' });
  });
  if (seed !== undefined) await page.addInitScript(value => { if (!sessionStorage.getItem('seeded')) { localStorage.setItem('safereturn_demo_db', typeof value === 'string' ? value : JSON.stringify(value)); sessionStorage.setItem('seeded', '1'); } }, seed);
  await page.goto('http://support-demo.test' + start);
}
const input = { caseId: 'DEMO-CASE-001', expectedRevision: 1, action: 'note' as const, note: 'Synthetic internal context only', confirmed: true, authenticatedRoles: ['support'], previewRole: 'authenticated' };

test('service enforces explicit support, scope, validation, revision, transitions, hold and reset without unrelated changes', () => {
  resetAdminMockData(); const before = loadAdminMockData();
  for (const role of ['operations', 'finance', 'security_admin', 'superadmin']) expect(updateDemoSupportCase({ ...input, authenticatedRoles: [role] }).success).toBe(false);
  expect(updateDemoSupportCase({ ...input, previewRole: 'Support' }).success).toBe(false);
  for (const note of ['', '   ', 'abc', '12345', 'x'.repeat(2001)]) expect(updateDemoSupportCase({ ...input, note }).success).toBe(false);
  expect(updateDemoSupportCase({ ...input, confirmed: false }).success).toBe(false);
  expect(updateDemoSupportCase({ ...input, expectedRevision: 0 }).success).toBe(false);
  expect(updateDemoSupportCase({ ...input, caseId: 'missing' }).success).toBe(false);
  expect(updateDemoSupportCase({ ...input, caseId: 'DEMO-CASE-005' }).success).toBe(false);
  expect(updateDemoSupportCase({ ...input, action: 'assign' as any }).success).toBe(false);
  expect(updateDemoSupportCase({ ...input, action: 'status', nextStatus: 'closed' }).success).toBe(false);
  expect(updateDemoSupportCase(input).success).toBe(true);
  expect(updateDemoSupportCase(input).success).toBe(false);
  let db = loadAdminMockData(); expect(db.supportCases[0].notes).toHaveLength(1); expect(db.supportCases[0].activity).toHaveLength(1); expect(db.auditLogs[0].details).not.toContain(input.note);
  for (const key of ['users', 'orders', 'qaPairs', 'qrBatches', 'printJobs', 'shipments', 'products'] as const) expect(db[key]).toEqual(before[key]);
  for (const [revision, nextStatus] of [[2, 'investigating'], [3, 'resolved'], [4, 'closed']] as const) expect(updateDemoSupportCase({ ...input, action: 'status', expectedRevision: revision, nextStatus }).success).toBe(true);
  expect(updateDemoSupportCase({ ...input, expectedRevision: 5 }).success).toBe(false);
  expect(loadAdminMockData().supportCases[0].activity).toHaveLength(4);
  for (const category of ['payment', 'privacy', 'ownership_dispute']) {
    const sample = { ...INITIAL_SUPPORT_CASES[0], category, status: 'investigating' };
    expect(demoSupportNextStates(sample)).toEqual([]);
    db = loadAdminMockData(); db.supportCases[3] = { ...sample, id: 'DEMO-CASE-004' }; saveAdminMockData(db);
    expect(updateDemoSupportCase({ ...input, caseId: 'DEMO-CASE-004', action: 'status', nextStatus: 'resolved' }).success).toBe(false);
    expect(updateDemoSupportCase({ ...input, caseId: 'DEMO-CASE-004' }).success).toBe(true);
  }
  expect(demoSupportNextStates({ ...INITIAL_SUPPORT_CASES[1], hasActiveHold: true })).toEqual([]);
  expect(demoSupportNextStates({ ...INITIAL_SUPPORT_CASES[1], category: 'unknown' })).toEqual([]);
  resetAdminMockData(); expect(loadAdminMockData().supportCases).toEqual(INITIAL_SUPPORT_CASES);
});

test('search, combined filters, derived metrics, focus, clear, list/detail and customer link', async ({ page }) => {
  await open(page); await expect(page.locator('tbody tr')).toHaveCount(5); const requests: string[] = []; page.on('request', r => requests.push(r.url()));
  for (const query of ['DEMO-CASE-001', 'care guidance', 'amina']) { await page.getByRole('textbox', { name: 'Search Cases' }).fill(query); await expect(page.getByRole('textbox', { name: 'Search Cases' })).toBeFocused(); await expect(page.locator('tbody tr')).toHaveCount(query === 'amina' ? 2 : 1); }
  await page.getByRole('combobox', { name: 'Status', exact: true }).selectOption('investigating'); await page.getByRole('combobox', { name: 'Priority', exact: true }).selectOption('urgent'); await page.getByRole('combobox', { name: 'Category', exact: true }).selectOption('ownership_dispute'); await expect(page.locator('tbody tr')).toHaveCount(1); await expect(page.locator('tbody tr')).toContainText('DEMO-CASE-004');
  await page.getByRole('button', { name: 'Clear Filters' }).click(); await expect(page.locator('tbody tr')).toHaveCount(5); expect(requests).toEqual([]); expect(await page.evaluate(() => localStorage.getItem('safereturn_demo_db'))).toBeNull();
  await page.getByRole('link', { name: 'View Details for DEMO-CASE-001' }).click(); await expect(page.getByRole('heading', { name: 'Product care guidance', exact: true })).toBeVisible(); await expect(page.getByRole('link', { name: 'View Demo Customer' })).toHaveAttribute('href', '/admin/users/USR-8821'); await expect(page.getByText('No case activity recorded in this demo. Earlier fixture history was not recorded.', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Back to Support Cases' }).click(); await expect(page.locator('tbody tr')).toHaveCount(5);
});

test('notes and confirmed lifecycle persist, cancel leaves unchanged, closed disables, no communication or other mutation', async ({ page }) => {
  await open(page, 'support', undefined, 'authenticated', '/admin/support/DEMO-CASE-001'); await expect(page.getByRole('heading', { name: 'Internal Notes' })).toBeVisible(); const requests: string[] = []; page.on('request', r => requests.push(r.url()));
  await page.getByRole('button', { name: 'Update Demo Case Status', exact: true }).click(); await page.getByRole('button', { name: 'Cancel', exact: true }).click(); await expect(page.getByRole('button', { name: 'Update Demo Case Status', exact: true })).toBeFocused(); expect(await page.evaluate(() => localStorage.getItem('safereturn_demo_db'))).toBeNull();
  await page.getByRole('button', { name: 'Add Internal Note', exact: true }).click(); expect(await page.evaluate(() => localStorage.getItem('safereturn_demo_db'))).toBeNull();
  await page.getByRole('textbox', { name: 'Internal demo note', exact: true }).fill('Synthetic internal follow-up'); await page.getByRole('checkbox', { name: /reviewed this synthetic internal note/ }).check(); await page.getByRole('button', { name: 'Add Internal Note', exact: true }).click(); await expect(page.getByText('Internal demo note added.', { exact: true })).toBeVisible(); await expect(page.getByText('Synthetic internal follow-up', { exact: true })).toBeVisible();
  for (const state of ['Investigating', 'Resolved', 'Closed']) { await page.getByRole('button', { name: 'Update Demo Case Status', exact: true }).click(); await expect(page.getByRole('dialog')).toContainText('→ ' + state); await page.getByRole('dialog').getByRole('checkbox').check(); await page.getByRole('button', { name: 'Confirm Demo Status' }).click(); await expect(page.getByRole('dialog')).toHaveCount(0); }
  expect(requests).toEqual([]); await expect(page.getByRole('button', { name: 'Add Internal Note', exact: true })).toBeDisabled(); await expect(page.getByRole('button', { name: 'Update Demo Case Status', exact: true })).toBeDisabled();
  const db = await page.evaluate(() => JSON.parse(localStorage.getItem('safereturn_demo_db')!)); expect(db.supportCases[0].status).toBe('closed'); expect(db.supportCases[0].activity).toHaveLength(4); expect(db.supportCases[0].notes).toHaveLength(1); expect(db.users).toEqual(INITIAL_SEED_DATA.users); expect(db.qaPairs).toEqual(INITIAL_SEED_DATA.qaPairs); expect(db.orders).toEqual(INITIAL_SEED_DATA.orders);
  await page.reload(); await expect(page.getByText('Synthetic internal follow-up', { exact: true })).toBeVisible(); await page.getByRole('link', { name: 'Back to Support Cases' }).click(); await expect(page.locator('tbody tr').filter({ hasText: 'DEMO-CASE-001' })).toContainText('Closed');
});

test('sensitive, unassigned and other-handler scopes never grant unrestricted resolution or content access', async ({ page }) => {
  const seed = structuredClone(INITIAL_SEED_DATA); seed.supportCases[4] = { ...seed.supportCases[4], subject: 'HIDDEN SUBJECT', description: 'HIDDEN DESCRIPTION', customerId: 'USR-8821', notes: [{ id: 'hidden', text: 'HIDDEN NOTE', author: 'hidden', timestamp: '2026-10-23' }] }; seed.supportCases.push({ ...seed.supportCases[0], id: 'DEMO-OTHER', demoScope: 'other' });
  await open(page, 'support', seed, 'authenticated', '/admin/support/DEMO-CASE-004'); await expect(page.getByText(/Security-sensitive requests require/)).toBeVisible(); await expect(page.getByRole('button', { name: 'Update Demo Case Status', exact: true })).toBeDisabled(); await expect(page.getByRole('button', { name: 'Add Internal Note', exact: true })).toBeEnabled(); await expect(page.getByText('Case assignment is not configured in this demo.', { exact: true })).toBeVisible();
  await page.goto('http://support-demo.test/admin/support/DEMO-CASE-005'); await expect(page.getByText('Unassigned case — metadata only', { exact: true })).toBeVisible(); await expect(page.locator('body')).not.toContainText('HIDDEN'); await expect(page.getByRole('link', { name: 'View Demo Customer' })).toHaveCount(0);
  await page.goto('http://support-demo.test/admin/support/DEMO-OTHER'); await expect(page.getByText('This synthetic case is missing or outside the available demo scope.', { exact: true })).toBeVisible();
});

test('roles and preview do not inherit support mutation or visibility', async ({ page }) => {
  for (const role of ['superadmin', 'security_admin', 'finance', 'operations']) { await page.unrouteAll(); await open(page, role); await expect(page.getByText('Access denied', { exact: true })).toBeVisible(); await expect(page.locator('tbody tr')).toHaveCount(0); }
  await page.unrouteAll(); await open(page, 'support', undefined, 'Superadmin', '/admin/support/DEMO-CASE-001'); await expect(page.getByRole('button', { name: 'Add Internal Note', exact: true })).toBeDisabled(); await expect(page.getByRole('button', { name: 'Update Demo Case Status', exact: true })).toBeDisabled();
});

test('customer directory capability and malformed collection fail closed; older demo stores receive fixtures', async ({ page }) => {
  await open(page, 'support', { users: INITIAL_SEED_DATA.users }, 'authenticated', '/admin/support/DEMO-CASE-001', false);
  await expect(page.getByRole('link', { name: 'View Demo Customer' })).toHaveCount(0);
  await expect(page.getByText(/Customer Details requires separate users.manage access/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Add Internal Note', exact: true })).toBeEnabled();
  await page.evaluate(() => { localStorage.setItem('safereturn_demo_db', JSON.stringify({ supportCases: [null] })); window.dispatchEvent(new Event('storage')); });
  await expect(page.getByRole('alert')).toContainText('Browser case data is invalid or unavailable');
  await expect(page.getByRole('textbox', { name: 'Internal demo note', exact: true })).toHaveCount(0);
  await page.evaluate(() => localStorage.setItem('safereturn_demo_db', '{broken')); await page.reload();
  await expect(page.getByRole('alert')).toContainText('Browser case data is invalid or unavailable');
  await expect(page.getByRole('button', { name: 'Add Internal Note', exact: true })).toBeDisabled();
});

test('storage failures, empty data, missing customer, unknown values and invalid ID are explicit', async ({ page }) => {
  await open(page, 'support', { supportCases: [] }); await expect(page.getByText('No demo cases', { exact: true })).toBeVisible();
  await page.evaluate(seed => { localStorage.setItem('safereturn_demo_db', JSON.stringify(seed)); window.dispatchEvent(new Event('storage')); }, INITIAL_SEED_DATA); await expect(page.locator('tbody tr')).toHaveCount(5);
  await page.goto('http://support-demo.test/admin/support/unknown'); await expect(page.getByText('This synthetic case is missing or outside the available demo scope.', { exact: true })).toBeVisible();
  await page.evaluate(seed => { seed.supportCases[0].customerId = 'missing'; seed.supportCases[0].status = 'unknown'; seed.supportCases[0].priority = 'unrecognized'; localStorage.setItem('safereturn_demo_db', JSON.stringify(seed)); }, INITIAL_SEED_DATA); await page.goto('http://support-demo.test/admin/support/DEMO-CASE-001'); await expect(page.getByText(/Synthetic customer reference is missing/)).toBeVisible(); await expect(page.getByRole('button', { name: 'Add Internal Note', exact: true })).toBeDisabled(); await expect(page.getByText('unrecognized', { exact: true })).toBeVisible();
  await page.evaluate(() => localStorage.removeItem('safereturn_demo_db')); await page.reload(); await page.getByRole('textbox', { name: 'Internal demo note', exact: true }).fill('Synthetic failed persistence'); await page.getByRole('checkbox', { name: /reviewed this synthetic internal note/ }).check(); await page.evaluate(() => { Storage.prototype.setItem = () => { throw Error('quota'); }; }); await page.getByRole('button', { name: 'Add Internal Note', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Unable to save demo case change'); expect(await page.evaluate(() => localStorage.getItem('safereturn_demo_db'))).toBeNull();
  await page.addInitScript(() => { Storage.prototype.getItem = () => { throw Error('blocked'); }; }); await page.reload(); await expect(page.getByRole('alert')).toContainText('Browser case data is invalid or unavailable'); await expect(page.getByRole('button', { name: 'Add Internal Note', exact: true })).toBeDisabled();
});

test('stale note and status submissions cannot overwrite newer history', async ({ page }) => {
  await open(page, 'support', undefined, 'authenticated', '/admin/support/DEMO-CASE-001'); await page.getByRole('textbox', { name: 'Internal demo note', exact: true }).fill('Synthetic stale note'); await page.getByRole('checkbox', { name: /reviewed this synthetic internal note/ }).check(); await page.getByRole('button', { name: 'Update Demo Case Status', exact: true }).click();
  await page.evaluate(seed => { seed.supportCases[0].revision = 2; localStorage.setItem('safereturn_demo_db', JSON.stringify(seed)); window.dispatchEvent(new Event('storage')); }, INITIAL_SEED_DATA); await page.getByRole('dialog').getByRole('checkbox').check(); await page.getByRole('button', { name: 'Confirm Demo Status' }).click(); await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Case changed'); await page.keyboard.press('Escape'); await page.getByRole('button', { name: 'Add Internal Note', exact: true }).click(); await expect(page.getByRole('alert')).toContainText('Case changed');
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('safereturn_demo_db')!).supportCases[0].notes)).toEqual([]);
});

for (const width of [1366, 1440, 375]) test('support list/details responsive and keyboard ' + width, async ({ page }) => {
  await page.setViewportSize({ width, height: width === 1440 ? 900 : 768 }); await open(page); await expect(page.locator('tbody tr')).toHaveCount(5); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true); await page.screenshot({ path: `test-results/support-list-${width}.png`, fullPage: true });
  await page.getByRole('link', { name: 'View Details for DEMO-CASE-001' }).click(); await expect(page.getByRole('heading', { name: 'Case Information' })).toBeVisible(); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true); await page.screenshot({ path: `test-results/support-details-${width}.png`, fullPage: true }); await page.getByRole('button', { name: 'Update Demo Case Status', exact: true }).click(); expect(await page.getByRole('dialog').evaluate(el => el.getBoundingClientRect().width)).toBeLessThan(width); await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0); await expect(page.getByRole('button', { name: 'Update Demo Case Status', exact: true })).toBeFocused();
});

test('support routes preserve capability/MFA wrapper, explicit role, live console and UUID details', async () => {
  const AdminPage = () => null, AdminNotice = () => null, AdminSupportCases = () => null, SupportAdmin = () => null;
  function load(file: string) { const result = { exports: {} as any }; const source = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS } }).outputText; vm.runInNewContext(source, { exports: result.exports, require: (name: string) => { if (name === 'react/jsx-runtime') return require(name); if (name === 'next/link') return () => null; if (name.includes('admin-page')) return { AdminPage, AdminNotice }; if (name.includes('admin-support-cases')) return { AdminSupportCases }; if (name.includes('support-admin')) return { SupportAdmin }; throw Error(name); } }); return result.exports.default; }
  const list = load('app/admin/support/page.tsx'); const detail = load('app/admin/support/[caseId]/page.tsx');
  for (const role of ['support', 'security_admin', 'superadmin', 'operations', 'finance']) { const page = await list({ searchParams: Promise.resolve({}) }); expect(page.type).toBe(AdminPage); expect(page.props.capability).toBe('support.manage'); expect(page.props.children({ roles: [role], capabilities: [] }, false).type).toBe(role === 'support' ? AdminSupportCases : AdminNotice); }
  const live = await list({ searchParams: Promise.resolve({ view: 'live' }) }); expect(live.props.children({ roles: ['support'], capabilities: [] }, false).props.children[1].type).toBe(SupportAdmin);
  for (const [caseId, component] of [['DEMO-CASE-001', AdminSupportCases], ['00000000-0000-0000-0000-000000000001', SupportAdmin]] as const) { const page = await detail({ params: Promise.resolve({ caseId }) }); expect(page.props.capability).toBe('support.manage'); expect(page.props.children({ roles: ['support'], capabilities: [] }, false).type).toBe(component); expect(page.props.children({ roles: ['superadmin'], capabilities: [] }, false).type).toBe(AdminNotice); }
});
