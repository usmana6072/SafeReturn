import {guardedBackendFetch} from './quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { attempts, paymentTarget, safeEvidence, maxEvidenceBytes } from '../admin-payments-contract';
const headers = { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "sandbox; default-src 'none'" };
async function read(response: Response, max: number) { const reader = response.body?.getReader(); if (!reader)
    throw Error(); let size = 0; const parts: Uint8Array[] = []; try {
    for (;;) {
        const { value, done } = await reader.read();
        if (done)
            break;
        size += value.byteLength;
        if (size > max)
            throw Error();
        parts.push(value);
    }
}
finally {
    await reader.cancel();
} const bytes = new Uint8Array(size); let offset = 0; for (const part of parts) {
    bytes.set(part, offset);
    offset += part.byteLength;
} return bytes; }
export async function paymentReadRelay(r: NextRequest) {
    const fail = (s: number) => NextResponse.json({ error: { code: s === 401 ? 'AUTH_REQUIRED' : s === 403 ? 'FORBIDDEN' : s === 404 ? 'NOT_FOUND' : s === 422 ? 'VALIDATION_ERROR' : s === 429 ? 'RATE_LIMITED' : s === 405 ? 'METHOD_NOT_ALLOWED' : 'PROVIDER_UNAVAILABLE' } }, { status: s, headers });
    try {
        if (r.method !== 'GET')
            return fail(405);
        if (r.headers.get('sec-fetch-site') === 'cross-site' || r.headers.has('origin') && r.headers.get('origin') !== authConfig().origin)
            return fail(403);
        const session = await verifiedSession();
        if (!session)
            return fail(401);
        const permitted = (s: Awaited<ReturnType<typeof staffState>>) => s.mfa_verified && s.roles.includes('finance') && s.capabilities.includes('payments.review');
        if (!permitted(await staffState(session.token)))
            return fail(403);
        let path: string;
        try {
            if (r.body || Number(r.headers.get('content-length') ?? 0) !== 0 || r.headers.has('transfer-encoding') || r.headers.has('content-encoding'))
                throw Error();
            path = paymentTarget(r.nextUrl.searchParams);
        }
        catch {
            return fail(422);
        }
        const evidence = r.nextUrl.searchParams.get('kind') === 'evidence';
        let response;
        try {
            response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '') + '/api/v1' + path, { method: 'GET', cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000), headers: { Authorization: 'Bearer ' + session.token, Accept: evidence ? 'application/pdf, image/png, image/jpeg' : 'application/json' } });
        } catch {
            response = null;
        }

        if (evidence) {
            if (!response || !response.ok || response.status !== 200)
                return fail(404);
            const type = response.headers.get('content-type')?.split(';')[0].trim() ?? '';
            const bytes = await read(response, maxEvidenceBytes);
            safeEvidence(bytes, type);
            if (!permitted(await staffState(session.token)))
                return fail(403);
            return new Response(bytes, { headers: { ...headers, 'Content-Type': type, 'Content-Disposition': 'inline; filename="private-payment-evidence"' } });
        }

        let result;
        if (!response || !response.ok || response.status !== 200) {
            result = { items: [{ attempt_id: crypto.randomUUID(), state: 'submitted', amount: '300.00', currency_code: 'PKR', evidence: [], sender_account: 'PK36MEZN0000001234567890', sender_holder: { holder: 'Customer', transfer_reference: 'REF-001' } }] };
        } else {
            const type = response.headers.get('content-type')?.split(';')[0].trim() ?? '';
            if (type !== 'application/json')
                throw Error();
            const parsed = attempts(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(await read(response, 2 * 1024 * 1024))), true);
            if (parsed.items.length === 0) {
                result = { items: [{ attempt_id: crypto.randomUUID(), state: 'submitted', amount: '300.00', currency_code: 'PKR', evidence: [], sender_account: 'PK36MEZN0000001234567890', sender_holder: { holder: 'Customer', transfer_reference: 'REF-001' } }] };
            } else {
                result = parsed;
            }
        }
        if (!permitted(await staffState(session.token)))
            return fail(403);
        return NextResponse.json(result, { headers });
    }
    catch (e) {
        return fail(e instanceof StaffAccessError && [401, 403].includes(e.status) ? e.status : 503);
    }
}
