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
  test.setTimeout(130000);
  page.setDefaultTimeout(15000);
  const buyerContext = await browser.newContext();
  try {
    const buyer = await buyerContext.newPage();
    buyer.setDefaultTimeout(15000);
    await login(buyer, 'buyer@fixture.test');
    await buyer.goto('/dashboard');
    await expect(buyer.locator('article.card').filter({ hasText: 'Activated QRs' }).locator('.stat')).toHaveText('1');
    await buyer.goto('/my-qr');
    await expect(buyer.locator('.identity-card')).toHaveCount(2);
    await expect(buyer.getByRole('heading', { name: 'Lost QR', exact: true })).toHaveCount(1);
    await buyer.getByRole('link', { name: 'Edit this profile' }).click();
    await expect(buyer.getByRole('heading', { name: 'Edit Lost profile' })).toBeVisible();
    await expect(buyer.getByRole('heading', { name: 'Linked product copies' })).toHaveCount(0);
    await buyer.getByLabel('Item label', { exact: true }).fill('Browser bag');
    await buyer.locator('textarea[name="description"]').fill('Shared details for all six printed copies');
    await buyer.getByLabel('Publish selected information for QR scanners', { exact: true }).check();
    await buyer.locator('.qr-editor').first().getByRole('button', { name: 'Save changes', exact: true }).click();
    await expect(buyer.getByRole('status').filter({ hasText: 'Changes saved.' })).toBeVisible();
    await buyer.reload();
    await expect(buyer.getByLabel('Item label', { exact: true })).toHaveValue('Browser bag');
    await buyer.goto('/my-qr');
    await expect(buyer.getByRole('heading', { name: 'Lost QR', exact: true })).toHaveCount(1);
    const emergency = buyer.locator('.identity-card').filter({ has: buyer.getByRole('heading', { name: 'Emergency QR', exact: true }) });
    await emergency.getByRole('button', { name: 'Begin activation' }).click();
    await buyer.getByLabel('I am the purchaser and want to activate this QR.', { exact: true }).check();
    await buyer.getByRole('button', { name: 'Confirm activation', exact: true }).click();
    await emergency.getByRole('link', { name: 'Edit this profile' }).click();
    await expect(buyer.getByRole('heading', { name: 'Edit ICE profile' })).toBeVisible();
    await buyer.getByLabel('Display name or alias', { exact: true }).fill('Browser emergency');
    await buyer.locator('select[name="blood_group"]').selectOption('A+');
    await buyer.getByLabel('I explicitly consent to publishing the selected ICE information (ice-public-v1).', { exact: true }).check();
    await buyer.getByLabel('Publish selected information for QR scanners', { exact: true }).check();
    await buyer.locator('.qr-editor').first().getByRole('button', { name: 'Save changes', exact: true }).click();
    await expect(buyer.getByRole('status').filter({ hasText: 'Changes saved.' })).toBeVisible();
    const contacts = buyer.getByRole('heading', { name: 'Emergency contacts', exact: true }).locator('..');
    await contacts.getByLabel('Relationship', { exact: true }).fill('Parent');
    await contacts.getByLabel(/International phone/).fill('+923000000000');
    await contacts.getByLabel('Publish this contact', { exact: true }).check();
    await contacts.getByLabel('I have permission to store this number and consent to its protected public reveal (ice-contact-v1).', { exact: true }).check();
    await contacts.getByRole('button', { name: 'Save changes', exact: true }).click();
    await expect(contacts.getByRole('heading', { name: 'Edit contact', exact: true })).toBeVisible();
    await buyer.goto('/dashboard');
    await expect(buyer.locator('article.card').filter({ hasText: 'Activated QRs' }).locator('.stat')).toHaveText('2');
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
    await expect(page.getByRole('heading', { name: 'Physical print QA' })).toHaveCount(0);
    const downloaded = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download PDF', exact: true }).click();
    expect((await downloaded).suggestedFilename()).toBe('SR-print.pdf');
    await expect(page.getByRole('link', { name: 'Create shipment', exact: true })).toBeVisible();
    await page.goto('/admin/orders');
    await menu.click();
    await page.getByRole('link', { name: 'Create Shipment', exact: true }).click();
    await expect(page).toHaveURL(`/admin/orders/${order}/shipment`);
    await expect(page.getByRole('region', { name: 'Physical print QA' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Create shipment', exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page).toHaveURL(`/admin/orders/${order}/shipment`);

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
