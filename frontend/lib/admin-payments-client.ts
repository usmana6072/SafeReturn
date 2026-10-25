import { attempts, paymentTarget, safeEvidence, type Evidence } from './admin-payments-contract';
export class PaymentReadError extends Error {
    constructor(public status: number) { super('Payment read unavailable'); }
}
export function paymentReadError(e: unknown) { const status = e instanceof PaymentReadError ? e.status : 503; return status === 401 ? 'Sign in again to view payment records.' : status === 403 ? 'Current Finance role and MFA are required.' : status === 404 ? 'Evidence is missing or unavailable.' : status === 422 ? 'Invalid request, evidence metadata or content.' : status === 429 ? 'Request limit reached; wait before retrying.' : 'Payment service or protected evidence unavailable. No success or settlement is assumed.'; }
export async function readAttempts(orderId: string, signal?: AbortSignal) { const query = new URLSearchParams({ kind: 'attempts', id: orderId }); paymentTarget(query); const r = await fetch('/admin/payments/read-api?' + query, { method: 'GET', cache: 'no-store', redirect: 'error', signal: signal ?? AbortSignal.timeout(20000) }); if (!r.ok)
    throw new PaymentReadError(r.status); return attempts(await r.json()); }
export async function readEvidence(e: Evidence, signal?: AbortSignal) { const query = new URLSearchParams({ kind: 'evidence', id: e.id }); paymentTarget(query); const r = await fetch('/admin/payments/read-api?' + query, { method: 'GET', cache: 'no-store', redirect: 'error', signal: signal ?? AbortSignal.timeout(20000) }); if (!r.ok)
    throw new PaymentReadError(r.status); if (r.headers.get('content-type')?.split(';')[0].trim() !== e.content_type)
    throw new PaymentReadError(422); const blob = await r.blob(); if (blob.size !== e.bytes_size)
    throw new PaymentReadError(422); safeEvidence(new Uint8Array(await blob.arrayBuffer()), e.content_type); return blob; }
