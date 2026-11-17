import { test, expect, type Page } from '@playwright/test';

const order = process.env.FULFILLMENT_ORDER;
const job = process.env.FULFILLMENT_JOB;

async function login(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Email address').fill(email);
  await page.locator('input[name="password"]').fill('fixture-password');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

test('staff fulfills a real stored order and the same buyer session observes all updates', async ({ page, browser }) => {
  test.skip(!order || !job, 'Run with the disposable PostgreSQL fulfillment browser controller');
  test.setTimeout(100000);
  page.setDefaultTimeout(15000);
  const buyerContext = await browser.newContext();
  try {
    const buyer = await buyerContext.newPage();
    buyer.setDefaultTimeout(15000);
    await login(buyer, 'buyer@fixture.test');
    await buyer.goto('/shipments');
    await expect(buyer.getByText('No shipments yet.')).toBeVisible();

    await login(page, 'operations@fixture.test');
    await page.goto('/admin/orders');
    const menu = page.getByRole('button', { name: /^Actions for SYN-/ });
    await menu.click();
    await expect(page.getByRole('link', { name: 'Verify Payment', exact: true })).toHaveAttribute('href', `/admin/payments?orderId=${order}`);
    await expect(page.getByRole('link', { name: 'View Order Details', exact: true })).toHaveAttribute('href', `/admin/orders/${order}`);
    await expect(page.getByRole('link', { name: 'Create Shipment', exact: true })).toHaveAttribute('href', `/admin/orders/${order}/shipment`);
    await page.getByRole('link', { name: 'View Order Details', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Ordered items' })).toBeVisible();
    await page.goto('/admin/orders');
    await menu.click();
    await page.getByRole('link', { name: 'Verify Payment', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Payment attempts' })).toBeVisible();
    await page.goto('/admin/orders');
    await menu.click();
    await page.getByRole('link', { name: 'View Print Job', exact: true }).click();
    await expect(page).toHaveURL(`/admin/print-jobs?orderId=${order}`);
    await page.goto(`/admin/print-jobs/${job}`);
    const qa = page.getByRole('region', { name: 'Physical print QA' });
    await expect(qa.getByText(/Expected 35(\.0+)? mm/).first()).toBeVisible();
    for (const field of await qa.getByLabel('Measured QR size (mm)').all()) await field.fill('35');
    for (const field of await qa.getByLabel('Printed copies counted').all()) await field.fill('3');
    for (const field of await qa.getByRole('checkbox').all()) await field.check();
    await qa.getByLabel('Inspection notes').fill('Isolated physical print workflow verification');
    await qa.getByRole('button', { name: 'Approve physical print' }).click();
    await expect(qa.getByText('Physical print QA passed.')).toBeVisible({ timeout: 10000 });
    await qa.getByRole('link', { name: 'Create shipment' }).click();

    await page.getByLabel('Shipping Service / Courier Name').fill('Independent courier');
    await page.getByLabel('Tracking Number', { exact: true }).fill('SR-2026-42');
    await page.getByRole('button', { name: 'Create shipment', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Manage shipment' })).toBeVisible();
    await buyer.bringToFront();
    await expect(buyer.getByText('SR-2026-42', { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(buyer.getByText('Independent courier', { exact: true })).toBeVisible();
    await expect(buyer.getByText('Preparing', { exact: true })).toBeVisible();

    for (const [status, label] of [['packed', 'Packed'], ['dispatched', 'Dispatched'], ['delivered', 'Delivered']]) {
      await page.bringToFront();
      await page.getByLabel('Next status').selectOption(status);
      if (status === 'packed') await page.getByRole('checkbox', { name: /packed the order/ }).check();
      await page.getByLabel('Reason').fill(`Isolated workflow status ${status}`);
      await page.getByRole('button', { name: 'Update shipment' }).click();
      await expect(page.getByRole('status').filter({ hasText: 'Shipment status updated.' })).toBeVisible();
      await buyer.bringToFront();
      await expect(buyer.getByText(label, { exact: true })).toBeVisible({ timeout: 15000 });
    }
    await expect(buyer).toHaveURL('/shipments');
    await expect(page.getByRole('button', { name: 'Update shipment' })).toHaveCount(0);
  } finally {
    await buyerContext.close();
  }
});
