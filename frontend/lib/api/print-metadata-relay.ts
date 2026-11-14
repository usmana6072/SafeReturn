import {guardedBackendFetch} from './quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { printTarget, printQuery, parsePage, parseCounts, parseOrder, parseDetail } from '../admin-print-jobs-contract';
const headers = { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
export async function printMetadataRelay(r: NextRequest) {
    const fail = (s: number) => NextResponse.json({ error: { code: s === 401 ? 'AUTH_REQUIRED' : s === 403 ? 'FORBIDDEN' : s === 404 ? 'NOT_FOUND' : s === 422 ? 'VALIDATION_ERROR' : s === 429 ? 'RATE_LIMITED' : s === 405 ? 'METHOD_NOT_ALLOWED' : 'PROVIDER_UNAVAILABLE' } }, { status: s, headers });
    try {
        if (r.method !== 'GET')
            return fail(405);
        if (r.headers.get('sec-fetch-site') === 'cross-site' || r.headers.has('origin') && r.headers.get('origin') !== authConfig().origin)
            return fail(403);
        const session = await verifiedSession();
        if (!session)
            return fail(401);
        const permitted = (s: Awaited<ReturnType<typeof staffState>>) => s.mfa_verified && s.roles.includes('operations') && s.capabilities.includes('printing.manage');
        if (!permitted(await staffState(session.token)))
            return fail(403);
        let path: string, q = new URLSearchParams();
        const p = r.nextUrl.searchParams, kind = p.get('kind');
        try {
            if (r.body || r.headers.has('content-encoding') || r.headers.has('transfer-encoding') || Number(r.headers.get('content-length') ?? 0) !== 0)
                throw Error();
            path = printTarget(p);
            if (kind === 'jobs' || kind === 'counts') {
                const filters = new URLSearchParams(p);
                filters.delete('kind');
                q = printQuery(filters, kind === 'counts');
            }
        }
        catch {
            return fail(422);
        }
        const response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '') + '/api/v1' + path + (q.size ? '?' + q : ''), { method: 'GET', cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(10000), headers: { Authorization: 'Bearer ' + session.token, Accept: 'application/json' } });
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
                const { value, done } = await reader.read();
                if (done)
                    break;
                size += value.byteLength;
                if (size > 1048576)
                    throw Error();
                body += decoder.decode(value, { stream: true });
            }
            body += decoder.decode();
        }
        finally {
            await reader.cancel();
        }
        const raw = JSON.parse(body), result = kind === 'jobs' ? parsePage(raw, Number(q.get('limit') ?? 20)) : kind === 'counts' ? parseCounts(raw) : kind === 'order' ? parseOrder(raw, true) : parseDetail(raw, p.get('id')!, true);
        if (!permitted(await staffState(session.token)))
            return fail(403);
        return NextResponse.json(result, { headers });
    }
    catch (e) {
        return fail(e instanceof StaffAccessError && [401, 403].includes(e.status) ? e.status : 503);
    }
}
