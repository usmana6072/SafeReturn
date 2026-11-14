import { guardedBackendFetch } from './quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { paymentReview, uuid } from '../admin-payments-contract';

const headers = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
};

function failure(status: number, upstreamCode?: string) {
  const code = ['PAYMENT_CLOSED', 'SETTLEMENT_MISMATCH', 'ORDER_RECONCILIATION_REQUIRED', 'BANK_VERIFICATION_REQUIRED'].includes(upstreamCode ?? '')
    ? upstreamCode
    : status === 401 ? 'AUTH_REQUIRED'
    : status === 403 ? 'FORBIDDEN'
      : status === 404 ? 'NOT_FOUND'
      : status === 409 ? 'PAYMENT_CLOSED'
        : status === 400 || status === 422 ? 'VALIDATION_ERROR'
          : status === 429 ? 'RATE_LIMITED' : 'PROVIDER_UNAVAILABLE';
  return NextResponse.json({ error: { code } }, { status, headers });
}

async function upstreamFailure(response: Response) {
  try {
    const value: unknown = await response.json();
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const detail = (value as Record<string, unknown>).detail;
      if (typeof detail === 'string')
        return failure(response.status, detail);
      if (detail && typeof detail === 'object' && !Array.isArray(detail)
        && typeof (detail as Record<string, unknown>).code === 'string')
        return failure(response.status, (detail as Record<string, string>).code);
    }
  } catch {
    // Keep the upstream status mapping when the response is not JSON.
  }
  return failure(response.status);
}

function body(value: unknown) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error();
  const input = value as Record<string, unknown>;
  const keys = Object.keys(input).sort();
  const decision = input.decision;
  const reason = input.reason;
  if (decision !== 'verify' && decision !== 'reject'
    || !keys.every(key => ['decision', 'bank_verified', 'bank_match_reference', 'settled_amount', 'settled_currency', 'reason'].includes(key))
    || typeof reason !== 'string' || reason.length < 4 || reason.length > 1000
    || /[\u0000-\u001f\u007f]/.test(reason)) throw Error();
  if (decision === 'reject') {
    if (keys.some(key => !['decision', 'reason'].includes(key))) throw Error();
    return { decision, reason };
  }
  if (keys.length !== 6 || input.bank_verified !== true
    || typeof input.bank_match_reference !== 'string'
    || input.bank_match_reference.length < 4 || input.bank_match_reference.length > 120
    || /[\u0000-\u001f\u007f]/.test(input.bank_match_reference)
    || typeof input.settled_amount !== 'string' || !/^[0-9]{1,10}\.[0-9]{2}$/.test(input.settled_amount)
    || typeof input.settled_currency !== 'string' || !/^[A-Z]{3}$/.test(input.settled_currency)) throw Error();
  return {
    decision,
    bank_verified: true,
    bank_match_reference: input.bank_match_reference,
    settled_amount: input.settled_amount,
    settled_currency: input.settled_currency,
    reason,
  };
}

export async function paymentReviewRelay(request: NextRequest) {
  try {
    if (request.method !== 'POST'
      || request.headers.get('sec-fetch-site') === 'cross-site'
      || request.headers.has('origin') && request.headers.get('origin') !== authConfig().origin
      || Number(request.headers.get('content-length') ?? 0) > 16000) return failure(403);
    const session = await verifiedSession();
    if (!session) return failure(401);
    const access = await staffState(session.token);
    if (!access.mfa_verified || !access.roles.includes('finance') || !access.capabilities.includes('payments.review')) return failure(403);
    const attemptId = request.nextUrl.searchParams.get('attempt_id');
    if (request.nextUrl.searchParams.size !== 1 || !attemptId) return failure(422);
    uuid(attemptId);
    let payload: ReturnType<typeof body>;
    try {
      payload = body(await request.json());
    } catch {
      return failure(422);
    }
    const idempotencyKey = request.headers.get('idempotency-key');
    if (!idempotencyKey || !/^[A-Za-z0-9._:-]{8,160}$/.test(idempotencyKey)) return failure(422);
    const response = await guardedBackendFetch(
      `${validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '')}/api/v1/admin/payment-attempts/${attemptId}/reviews`,
      {
        method: 'POST',
        cache: 'no-store',
        redirect: 'error',
        signal: AbortSignal.timeout(20000),
        headers: {
          Authorization: `Bearer ${session.token}`,
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(payload),
      },
    );
    if (!response.ok) return upstreamFailure(response);
    return NextResponse.json(paymentReview(await response.json()), { headers });
  } catch (error) {
    return failure(error instanceof StaffAccessError && [401, 403].includes(error.status) ? error.status : 503);
  }
}
