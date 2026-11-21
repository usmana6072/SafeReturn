import { test, expect, type Page } from '@playwright/test';
import { parseStaffSecurity, capabilities } from '../lib/auth/staff-contract';
import { ALL_ADMIN_MODULES } from '../lib/admin-navigation';

const bundle = require('./qa-browser-bundle.cjs');

async function open(page: Page, roles: string[], allowed: string[]) {
  const security = parseStaffSecurity({ roles, mfa_verified: true, capabilities: allowed });
  const source = bundle({ componentPath: '../components/admin-staff-permissions.tsx', exportName: 'AdminStaffPermissions', wrapperPath: '../components/admin-shell.tsx' });
  await page.route('http://owner-role.test/**', route => route.fulfill({ contentType: 'text/html', body:
    '<!doctype html><html><body><div id="root"></div><script>window.qaSecurity=' + JSON.stringify(security) + ';window.qaProps={};' + source + '</script></body></html>' }));
  await page.goto('http://owner-role.test/admin');
}

test('owner sees every module from database authorization without any role switch or demo controls', async ({ page }) => {
  await open(page, ['owner'], [...capabilities]);
  const navigation = page.getByRole('navigation', { name: 'Staff navigation' });
  await expect(navigation).toBeVisible();
  for (const item of ALL_ADMIN_MODULES) await expect(navigation.locator(`a[href="${item.path}"]`)).toBeVisible();
  await expect(page.getByRole('combobox')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Reset Demo|Change Role/i })).toHaveCount(0);
  await expect(page.getByText('Owner', { exact: true })).toBeVisible();
});

test('finance navigation follows its supplied capabilities and ignores local demo role data', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('safereturn_admin_role', 'owner');
    localStorage.setItem('safereturn_demo_db', JSON.stringify({ users: [{ role: 'owner' }] }));
  });
  await open(page, ['finance'], ['orders.read', 'payments.review', 'finance.mirror', 'storage.metadata']);
  const navigation = page.getByRole('navigation', { name: 'Staff navigation' });
  await expect(navigation.locator('a[href="/admin/payments"]')).toBeVisible();
  for (const path of ['/admin/support', '/admin/users', '/admin/shipments', '/admin/staff-permissions'])
    await expect(navigation.locator(`a[href="${path}"]`)).toHaveCount(0);
  await expect(page.getByRole('combobox')).toHaveCount(0);
});
