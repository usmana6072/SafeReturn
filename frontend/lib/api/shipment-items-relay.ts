import {guardedBackendFetch} from './quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { shipmentId, shipmentItems } from '../admin-shipment-items-contract';
const headers = { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
export async function shipmentItemsRelay(r: NextRequest) {
    const fail = (s: number) => NextResponse.json({ error: { code: s === 401 ? 'AUTH_REQUIRED' : s === 403 ? 'FORBIDDEN' : s === 404 ? 'NOT_FOUND' : s === 422 ? 'VALIDATION_ERROR' : s === 429 ? 'RATE_LIMITED' : s === 405 ? 'METHOD_NOT_ALLOWED' : 'PROVIDER_UNAVAILABLE' } }, { status: s, headers });
    try {
        if (r.method !== 'GET')
            return fail(405);
        if (r.headers.get('sec-fetch-site') === 'cross-site' || r.headers.has('origin') && r.headers.get('origin') !== authConfig().origin)
            return fail(403);
        const session = await verifiedSession();
        if (!session)
            return fail(401);
        const permitted = (s: Awaited<ReturnType<typeof staffState>>) => s.mfa_verified && s.roles.includes('operations') && s.capabilities.includes('fulfillment.manage');
        if (!permitted(await staffState(session.token)))
            return fail(403);
        let id: string;
        try {
            if (r.nextUrl.searchParams.size !== 1 || r.nextUrl.searchParams.getAll('shipment_id').length !== 1 || r.body || r.headers.has('content-encoding') || r.headers.has('transfer-encoding') || Number(r.headers.get('content-length') ?? 0) !== 0)
                throw Error();
            id = shipmentId(r.nextUrl.searchParams.get('shipment_id'));
        }
        catch {
            return fail(422);
        }
        const response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '') + '/api/v1/admin/shipments/' + id + '/items', { method: 'GET', cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(10000), headers: { Authorization: 'Bearer ' + session.token, Accept: 'application/json' } });
        if (!response.ok)
            return fail([401, 403, 404, 422, 429].includes(response.status) ? response.status : 503);
        if (response.status !== 200 || response.headers.get('content-type')?.split(';')[0].trim() !== 'application/json')
            throw Error();
        const reader = response.body?.getReader();
        if (!reader)
            throw Error();
        let size = 0, body = '';
        const decoder = new TextDecoder('utf-8', { fatal: true });
        try {
            for (;;) {
                const { done, value } = await reader.read();
                if (done)
                    break;
                size += value.byteLength;
                if (size > 524288)
                    throw Error();
                body += decoder.decode(value, { stream: true });
            }
            body += decoder.decode();
        }
        finally {
            await reader.cancel();
        }
        const data = shipmentItems(JSON.parse(body));
        if (!permitted(await staffState(session.token)))
            return fail(403);
        return NextResponse.json(data, { headers });
    }
    catch (e) {
        return fail(e instanceof StaffAccessError && [401, 403].includes(e.status) ? e.status : 503);
    }
}
