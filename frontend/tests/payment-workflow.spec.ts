import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { Readable } from 'node:stream';
import path from 'node:path';

const bundle = require('./qa-browser-bundle.cjs');
const { harness } = require('./quarantine-fixture.cjs');
const { NextRequestAdapter } = require('next/dist/server/web/spec-extension/adapters/next-request');
const origin = 'https://payments.test';
const order = '00000000-0000-0000-0000-000000000701';
const attempt = '00000000-0000-0000-0000-000000000702';
const job = '00000000-0000-0000-0000-000000000703';
const artifact = '00000000-0000-0000-0000-000000000704';
const stamp = '2026-11-16T00:00:00Z';

async function mount(page: Page, componentPath: string, exportName: string, props: Record<string, string> = {}) {
    await page.route(`${origin}/test`, route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div id="root"></div>' }));
    await page.goto(`${origin}/test`);
    await page.evaluate((props) => Object.assign(window, { qaProps: props, qaRole: { authenticatedRoles: ['finance', 'operations'] } }), props);
    await page.addScriptTag({ content: bundle({ componentPath, exportName }) });
}

test('finance finds and approves a queued payment without an order search', async ({ page }) => {
    let verified = false;
    const keys: string[] = [];
    const allocation = () => ({ state: verified ? 'allocated' : 'awaiting_verified_payment', reason_code: null, allocated_count: verified ? 1 : 0, requested_count: 1 });
    await page.route('**/admin/orders/metadata-api?*', route => {
        const filters = new URL(route.request().url()).searchParams;
        expect(filters.get('payment_status')).toBe('pending');
        expect(filters.get('order_status')).toBe('placed');
        return route.fulfill({ json: { items: verified ? [] : [{ order_id: order, order_number: 'SR-PAYMENT', order_status: 'placed', payment_status: 'under_review', currency_code: 'PKR', total_amount: '15.00', created_at: stamp, placed_at: stamp }], next_cursor: null, as_of: stamp } });
    });
    await page.route('**/admin/payments/read-api?*', route => route.fulfill({ json: { items: [{ attempt_id: attempt, state: 'under_review', currency_code: 'PKR', amount: '15.00', evidence: [] }] } }));
    await page.route('**/payments/api?*', route => route.fulfill({ json: allocation() }));
    await page.route('**/admin/payments/review-api?*', route => {
        keys.push(route.request().headers()['idempotency-key']);
        expect(route.request().postDataJSON()).toMatchObject({ decision: 'verify', settled_amount: '15.00', settled_currency: 'PKR', bank_verified: true });
        verified = true;
        if (keys.length === 1) return route.fulfill({ status: 503, json: {} });
        return route.fulfill({ json: { attempt_id: attempt, order_id: order, review_id: artifact, state: 'verified', fulfillment_eligible: false, allocation: allocation() } });
    });
    await mount(page, '../components/admin-payments.tsx', 'AdminPayments');
    const queue = page.getByRole('region', { name: 'Awaiting payments' });
    await queue.getByRole('button', { name: 'View payment attempts for SR-PAYMENT' }).click();
    await page.getByRole('button', { name: 'Approve', exact: true }).click();
    await page.getByLabel('Bank match reference').fill('REF-12345');
    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'Confirm approval' }).click();
    await expect(page.getByRole('alert')).toHaveText(/No success or settlement is assumed/);
    await page.getByRole('button', { name: 'Confirm approval' }).click();
    expect(keys[0]).toBe(keys[1]);
    await expect(page.getByText(/Payment approved. QR identities allocated/)).toBeVisible();
    await expect(queue.getByText('No orders awaiting payment')).toBeVisible();
    await expect(page.getByRole('link', { name: 'View print jobs for this order' })).toHaveAttribute('href', `/admin/print-jobs?orderId=${order}`);
});

test('evidence form closes after the receipt and stays closed after reloading', async ({ page }) => {
    let submitted = false;
    await page.route('**/payments/api?*', route => {
        const path = new URL(route.request().url()).searchParams.get('path');
        return route.fulfill({ json: path?.endsWith('payment-attempts') ? {
            items: [{ id: attempt, state: submitted ? 'under_review' : 'initiated', evidence_received: submitted }],
            payment_open: true, payment_due: '15.00', currency_code: 'PKR',
        } : {} });
    });
    await page.route('**/payments/api', route => {
        if (route.request().postDataJSON().path.endsWith('evidence-finalize')) {
            submitted = true;
            return route.fulfill({ json: { received: true, evidence_id: artifact, payment_state: 'under_review' } });
        }
        return route.fulfill({ json: { upload_token: 'synthetic', upload_url: `${origin}/upload` } });
    });
    await page.route('**/upload', route => route.fulfill({ json: {} }));
    const render = () => mount(page, '../components/customer-payment.tsx', 'PaymentForm', { orderId: order, language: 'en' });
    await render();
    await expect(page.getByText(/Your payment details are saved/)).toBeVisible();
    await expect(page.getByLabel('Sender account')).toHaveCount(0);
    await page.getByLabel('Payment receipt (required)').setInputFiles({ name: 'receipt.png', mimeType: 'image/png', buffer: Buffer.from('synthetic') });
    await page.getByRole('button', { name: 'Submit payment for review' }).click();
    await expect(page.getByRole('status')).toHaveText('Payment details and receipt submitted. Your payment is under review.');
    await expect(page.getByLabel('Payment receipt (required)')).toHaveCount(0);
    await render();
    await expect(page.getByRole('status')).toHaveText('Payment details and receipt submitted. Your payment is under review.');
    await expect(page.getByRole('button', { name: 'Submit payment for review' })).toHaveCount(0);
});

test('the real download relay serves a ready PDF from an empty streamed POST', async ({ page }) => {
    let status = 'queued';
    let unavailable = true;
    const pdf = '%PDF-1.4\n%%EOF';
    const endpoint = `/admin/print-jobs/download-api?job=${job}&artifact=${artifact}`;
    const fixture = harness({ origin, respond(url: string, init: RequestInit) {
        expect(new URL(url).pathname).toBe(`/api/v1/admin/print-jobs/${job}/artifacts/${artifact}/download`);
        expect(init.method).toBe('POST');
        if (unavailable) return Response.json({}, { status: 503 });
        status = 'downloaded';
        return new Response(pdf, { headers: { 'content-type': 'application/pdf' } });
    } });
    const { POST } = fixture.load(path.resolve(__dirname, '../app/admin/print-jobs/download-api/route.ts'));
    function request(url: string, headers: Record<string, string>, bytes: Buffer[] = []) {
        return NextRequestAdapter.fromNodeNextRequest({ url, method: 'POST', headers, body: Readable.from(bytes) }, new AbortController().signal);
    }
    const withBody = await POST(request(origin + endpoint, { origin }, [Buffer.from('unexpected')]));
    expect(withBody.status).toBe(422);
    expect(fixture.state.calls).toHaveLength(0);

    await page.route('**/admin/print-jobs/metadata-api?*', route => route.fulfill({ json: {
        id: job, order_id: order, status, job_revision: 1, template_fingerprint: 'a'.repeat(64), attempt_count: 1, failure_category: null, typed_order: true,
        artifacts: status === 'queued' ? [] : [{ id: artifact, format: 'pdf', size_bytes: Buffer.byteLength(pdf), sha256_hex: 'a'.repeat(64), deleted_at: null }],
    } }));
    await page.route(`**${endpoint}`, async route => {
        const incoming = route.request();
        expect(incoming.method()).toBe('POST');
        const response = await POST(request(incoming.url(), await incoming.allHeaders()));
        return route.fulfill({ status: response.status, headers: Object.fromEntries(response.headers), body: Buffer.from(await response.arrayBuffer()) });
    });
    await mount(page, '../components/admin-print-jobs.tsx', 'AdminPrintJobs', { jobId: job });
    await expect(page.getByText('queued', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Download PDF' })).toHaveCount(0);
    status = 'ready';
    await page.getByRole('button', { name: 'Refresh Print Job' }).click();
    await page.getByRole('button', { name: 'Download PDF' }).click();
    await expect(page.getByRole('alert')).toHaveText('The print file could not be downloaded. Try again.');
    unavailable = false;
    const downloading = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download PDF' }).click();
    const saved = await downloading;
    expect(saved.suggestedFilename()).toBe('SR-print.pdf');
    expect(await readFile(await saved.path(), 'utf8')).toBe(pdf);
    await expect(page.getByRole('link', { name: 'Save PDF' })).toBeVisible();
    await expect(page.getByText('downloaded', { exact: true })).toBeVisible();
});
