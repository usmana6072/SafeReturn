import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:8115/api/v1';
const auth = (token: string | undefined) => ({ Authorization: `Bearer ${token}` });

test('anonymous finance APIs deny access and admin landing requires login', async ({ page }) => {
  await page.goto('/admin/payments');
  await expect(page).toHaveURL(/login/);
  for (const path of ['/admin/finance/sheet-sync', '/admin/storage/artifacts']) {
    expect((await page.request.get(api + path)).status()).toBe(401);
  }
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
});

test('finance sees reporting status while operations cannot read it', async ({ page }) => {
  await page.goto('/');
  const response = await page.request.get(api + '/admin/finance/sheet-sync?limit=1', {
    headers: auth(process.env.TASK56_FINANCE_TOKEN),
  });
  expect(response.status()).toBe(200);
  expect(await response.text()).not.toMatch(/https?:\/\/|iban|activation_secret|medical|sender_account_ciphertext/i);
  expect((await page.request.get(api + '/admin/finance/sheet-sync', {
    headers: auth(process.env.TASK56_OPERATIONS_TOKEN),
  })).status()).toBe(403);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
});

test('artifact inventory is metadata only and finance cannot place legal holds', async ({ page }) => {
  await page.goto('/');
  const response = await page.request.get(api + '/admin/storage/artifacts', {
    headers: auth(process.env.TASK56_OPERATIONS_TOKEN),
  });
  expect(response.status()).toBe(200);
  expect(await response.text()).not.toMatch(/https?:\/\/|download_token|activation_secret/i);
  expect((await page.request.post(api + `/admin/storage/artifacts/${process.env.TASK56_ARTIFACT}/retention-holds`, {
    headers: auth(process.env.TASK56_FINANCE_TOKEN), data: { reason_code: 'SYNTHETIC' },
  })).status()).toBe(403);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
});
