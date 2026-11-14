import { test, expect as baseExpect } from "@playwright/test";
const expect = baseExpect.configure({ timeout: 20000 });
test("bounded synthetic restricted audit search, paging and response/RSC redaction", async ({ page, context, request }, testInfo) => {
  test.setTimeout(180000); page.setDefaultTimeout(20000);
  await page.goto('/admin/audit?view=live'); await expect(page).toHaveURL(/login/);
  expect((await page.request.get('/admin/audit/api')).status()).toBe(401);
  async function login(role: string) {
    await context.clearCookies(); await request.post('http://127.0.0.1:8115/fixture/support-role/' + role);
    await page.goto('/login'); await page.getByLabel('Email address').fill(role + '@synthetic.invalid');
    await page.locator('input[name=password]').fill('synthetic-password'); await page.getByRole('button', { name: 'Log in', exact: true }).click(); await expect(page).not.toHaveURL(/\/login/);
  }
  await login('finance'); await page.goto('/admin/audit?view=live'); await expect(page.getByRole('heading', { name: 'Access denied', exact: true })).toBeVisible();
  expect((await page.request.get('/admin/audit/api')).status()).toBe(403);
  expect(await (await page.request.get('/admin/audit', { headers: { RSC: '1' } })).text()).not.toContain('PRIVATE_');
  await login('security_admin'); await page.goto('/admin/audit?view=live');
  await page.getByLabel('Target UUID', { exact: true }).fill(process.env.AUDIT_TARGET!);
  await page.getByLabel('Exact approved action', { exact: true }).fill('support_case.read');
  await page.getByRole('button', { name: 'Search events', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'support_case.read', exact: true })).toHaveCount(20);
  await expect(page.locator('body')).not.toContainText('PRIVATE_');
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'support_case.read', exact: true })).toHaveCount(5);
  const r = await page.request.get('/admin/audit/api?target_id=' + process.env.AUDIT_TARGET);
  expect(r.status()).toBe(200); expect(await r.text()).not.toMatch(/CANARY|safe_details|request_id|"reason"|object_key|https?:\/\//);
  expect(r.headers()['cache-control']).toBe('private, no-store');
  expect((await page.request.get('/admin/audit/api?path=/admin/support-cases')).status()).toBe(400);
  expect((await page.request.get('/admin/audit/api?limit=20&limit=100')).status()).toBe(400);
  await page.getByLabel('Target UUID', { exact: true }).fill('00000000-0000-0000-0000-000000000000'); await page.getByRole('button', { name: 'Search events', exact: true }).click(); await expect(page.getByText('No matching events.', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  await context.addCookies([{ name: 'safereturn-language', value: 'ur', url: 'http://127.0.0.1:3100' }]); await page.setViewportSize({ width: 375, height: 900 }); await page.reload();
  await page.getByLabel('ہدف کی شناخت', { exact: true }).fill(process.env.AUDIT_TARGET!); await page.getByRole('button', { name: 'واقعات تلاش کریں', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'support_case.read', exact: true }).first()).toBeVisible(); await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('audit-rtl.png'), fullPage: true });
});
