import { attempts, paymentReview, paymentTarget, safeEvidence, uuid, type Evidence } from './admin-payments-contract';
export class PaymentReadError extends Error {
    constructor(public status: number, public code?: string) { super('Payment request failed'); }
}
export function paymentReadError(e: unknown) {
    const status = e instanceof PaymentReadError ? e.status : 503;
    const code = e instanceof PaymentReadError ? e.code : undefined;
    return status === 401 ? 'Sign in again to view payment records.'
        : status === 403 ? 'Current Finance role and MFA are required.'
            : status === 404 ? 'Evidence is missing or unavailable.'
                : status === 409 && code === 'PAYMENT_CLOSED' ? 'This payment has already been finalized. Refresh the records.'
                    : status === 409 && code === 'SETTLEMENT_MISMATCH' ? 'The settlement amount or currency does not match the payment.'
                        : status === 409 && code === 'ORDER_RECONCILIATION_REQUIRED' ? 'The order must be reconciled before approval.'
                            : status === 422 && code === 'BANK_VERIFICATION_REQUIRED' ? 'Confirm bank verification and provide a valid bank match reference.'
                                : status === 422 ? 'Invalid request, evidence metadata or content.'
                                    : status === 429 ? 'Request limit reached; wait before retrying.'
                                        : 'Payment service or protected evidence unavailable. No success or settlement is assumed.';
}
export async function readAttempts(orderId: string, signal?: AbortSignal) { const query = new URLSearchParams({ kind: 'attempts', id: orderId }); paymentTarget(query); const r = await fetch('/admin/payments/read-api?' + query, { method: 'GET', cache: 'no-store', redirect: 'error', signal: signal ?? AbortSignal.timeout(20000) }); if (!r.ok)
    throw new PaymentReadError(r.status); return attempts(await r.json()); }
export async function readEvidence(e: Evidence, signal?: AbortSignal) { const query = new URLSearchParams({ kind: 'evidence', id: e.id }); paymentTarget(query); const r = await fetch('/admin/payments/read-api?' + query, { method: 'GET', cache: 'no-store', redirect: 'error', signal: signal ?? AbortSignal.timeout(20000) }); if (!r.ok)
    throw new PaymentReadError(r.status); if (r.headers.get('content-type')?.split(';')[0].trim() !== e.content_type)
    throw new PaymentReadError(422); const blob = await r.blob(); if (blob.size !== e.bytes_size)
    throw new PaymentReadError(422); safeEvidence(new Uint8Array(await blob.arrayBuffer()), e.content_type); return blob; }
export async function reviewPayment(attemptId: string, payload: {
    decision: 'verify' | 'reject';
    reason: string;
    bank_verified?: boolean;
    bank_match_reference?: string;
    settled_amount?: string;
    settled_currency?: string;
}, signal?: AbortSignal) {
    const id = uuid(attemptId);
    const r = await fetch('/admin/payments/review-api?attempt_id=' + encodeURIComponent(id), {
        method: 'POST',
        cache: 'no-store',
        redirect: 'error',
        signal: signal ?? AbortSignal.timeout(20000),
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify(payload),
    });
    if (!r.ok) {
        let code: string | undefined;
        try {
            const value: unknown = await r.json();
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                const error = (value as Record<string, unknown>).error;
                if (error && typeof error === 'object' && !Array.isArray(error)
                    && typeof (error as Record<string, unknown>).code === 'string')
                    code = (error as Record<string, string>).code;
            }
        } catch {
            // The status remains useful when the upstream response is not JSON.
        }
        throw new PaymentReadError(r.status, code);
    }
    return paymentReview(await r.json());
}
