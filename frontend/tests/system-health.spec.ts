import { test, expect as baseExpect } from '@playwright/test';
const expect = baseExpect.configure({ timeout: 20000 });
test('bounded system process observation, unknown dependencies and stale evidence', async ({ page, context, request }, testInfo) => {
  test.setTimeout(180000); page.setDefaultTimeout(20000);
  await page.goto('/admin/system?view=live'); await expect(page).toHaveURL(/login/);
  expect((await page.request.get('/admin/system/api')).status()).toBe(401);
  async function login(role: string) {
    await context.clearCookies(); await request.post('http://127.0.0.1:8115/fixture/support-role/' + role);
    await page.goto('/login'); await page.getByLabel('Email address').fill(role + '@synthetic.invalid'); await page.locator('input[name=password]').fill('synthetic-password');
    await page.getByRole('button', { name: 'Log in', exact: true }).click(); await expect(page).not.toHaveURL(/\/login/);
  }
  await login('finance'); await page.goto('/admin/system?view=live'); await expect(page.getByRole('heading', { name: 'Access denied', exact: true })).toBeVisible();
  expect((await page.request.get('/admin/system/api')).status()).toBe(403);
  expect(await (await page.request.get('/admin/system?view=live', { headers: { RSC: '1' } })).text()).not.toContain('PRIVATE_CANARY');
  await login('operations'); await page.goto('/admin/system?view=live');
  await expect(page.getByRole('status')).toHaveText('Not observed');
  await expect(page.getByText('Unknown — observation contract unavailable', { exact: true })).toHaveCount(8);
  await expect(page.getByRole('link', { name: 'Finance mirror records', exact: true })).toHaveCount(0);
  async function check(mode: string, state: string) {
    await request.post('http://127.0.0.1:8115/fixture/system-mode/' + mode);
    await page.getByRole('button', { name: 'Check process liveness', exact: true }).click(); await expect(page.getByRole('status')).toHaveText(state);
  }
  await check('normal', 'Process answered');
  await check('down', 'Liveness check unavailable'); await expect(page.getByText(/Stale evidence: previous process response only/)).toBeVisible();
  await check('malformed', 'Unknown response'); await expect(page.locator('body')).not.toContainText('PRIVATE_CANARY');
  await check('slow', 'Liveness check unavailable');
  const response = await page.request.get('/admin/system/api'); expect(response.status()).toBe(200); expect(await response.text()).not.toMatch(/CANARY|https?:\/\/|token|credential|database/);
  expect(response.headers()['cache-control']).toBe('private, no-store');
  expect((await page.request.get('/admin/system/api?path=/health/ready')).status()).toBe(400);
  expect((await page.request.post('/admin/system/api', { data: {} })).status()).toBe(405);
  expect((await (await request.get('http://127.0.0.1:8115/fixture/system-stats')).json()).ready_calls).toBe(0);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  await request.post('http://127.0.0.1:8115/fixture/system-mode/normal'); await login('security_admin');
  await context.addCookies([{ name: 'safereturn-language', value: 'ur', url: 'http://127.0.0.1:3100' }]); await page.setViewportSize({ width: 375, height: 900 }); await page.goto('/admin/system?view=live');
  await page.getByRole('button', { name: 'عمل کی جانچ کریں', exact: true }).click(); await expect(page.getByRole('status')).toHaveText('عمل نے جواب دیا');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl'); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('system-rtl.png'), fullPage: true });
});

