import {guardedBackendFetch} from './quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { uuid, parsePage, parseDetail, parseTotal, type Filters } from '../users-contract';
const headers = { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
const codes = new Set(['AUTH_REQUIRED', 'FORBIDDEN', 'NOT_FOUND', 'INVALID_QUERY', 'INVALID_CURSOR']);
async function bounded(response: Response | NextRequest, max: number): Promise<unknown> {
    if (response.headers.get('content-type')?.split(';')[0].trim() !== 'application/json')
        throw Error();
    const reader = response.body?.getReader();
    if (!reader)
        throw Error();
    let size = 0, text = '';
    const decoder = new TextDecoder('utf-8', { fatal: true });
    try {
        for (;;) {
            const { done, value } = await reader.read();
            if (done)
                break;
            size += value.byteLength;
            if (size > max)
                throw Error();
            text += decoder.decode(value, { stream: true });
        }
        text += decoder.decode();
    }
    finally {
        await reader.cancel();
    }
    return JSON.parse(text);
}
export async function userDirectoryReadRelay(request: NextRequest) {
    const error = (status: number, code?: string) => NextResponse.json({ error: { code: code ?? (status === 401 ? 'AUTH_REQUIRED' : status === 403 ? 'FORBIDDEN' : status === 422 ? 'INVALID_QUERY' : 'SERVICE_UNAVAILABLE') } }, { status, headers });
    try {
        if (request.method !== 'GET')
            return error(405);
        const origin = authConfig().origin, incoming = request.headers.get('origin');
        if (request.headers.get('sec-fetch-site') === 'cross-site' || (incoming && incoming !== origin))
            return error(403);
        const session = await verifiedSession();
        if (!session)
            return error(401);
        const security = await staffState(session.token);
        if (!security.mfa_verified || !security.roles.includes('security_admin') || !security.capabilities.includes('users.manage'))
            return error(403);
        if (request.body || request.headers.has('content-encoding') || request.headers.has('transfer-encoding') || Number(request.headers.get('content-length') ?? 0) !== 0)
            return error(422);
        const p = request.nextUrl.searchParams, kind = p.get('kind');
        const allowed = kind === 'list' ? ['kind', 'user_id', 'email_verified', 'provider_access', 'limit', 'cursor'] : kind === 'count' ? ['kind', 'user_id', 'email_verified', 'provider_access'] : ['kind', 'user_id'];
        if ([...p.keys()].some(k => !allowed.includes(k) || p.getAll(k).length !== 1) || !['list', 'detail', 'count'].includes(kind ?? ''))
            return error(422);
        let id: string | null = null;
        try {
            id = p.has('user_id') ? uuid(p.get('user_id')) : null;
        }
        catch {
            return error(422);
        }
        if ((kind === 'detail') && !id)
            return error(422);
        const selected: Filters = { user_id: id, email_verified: null, provider_access: null };
        if (p.has('email_verified')) {
            if (!['true', 'false'].includes(p.get('email_verified')!))
                return error(422);
            selected.email_verified = p.get('email_verified') === 'true';
        }
        if (p.has('provider_access')) {
            if (!['banned', 'not_banned'].includes(p.get('provider_access')!))
                return error(422);
            selected.provider_access = p.get('provider_access') as Filters['provider_access'];
        }
        let path = '/api/v1/admin/users';
        let limit = 20;
        if (kind === 'detail')
            path += '/' + id + '?include=account_security';
        else {
            if (kind === 'count')
                path += '/count';
            const query = new URLSearchParams();
            for (const [k, v] of Object.entries(selected))
                if (v !== null)
                    query.set(k, String(v));
            if (kind === 'list') {
                const raw = p.get('limit') ?? '20';
                if (!/^[1-9][0-9]{0,2}$/.test(raw) || Number(raw) > 100)
                    return error(422);
                limit = Number(raw);
                query.set('limit', raw);
                if (p.has('cursor')) {
                    const cursor = p.get('cursor')!;
                    if (!/^[A-Za-z0-9_-]{1,1024}$/.test(cursor))
                        return error(422);
                    query.set('cursor', cursor);
                }
            }
            path += '?' + query.toString();
        }
        const response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '') + path, { method: 'GET', cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(10000), headers: { Authorization: `Bearer ${session.token}`, Accept: 'application/json', } });
        if (!response.ok) {
            const status = [401, 403, 404, 422, 429].includes(response.status) ? response.status : 503;
            let code: string | undefined;
            try {
                const v = await bounded(response, 4096) as {
                    error?: {
                        code?: string;
                    };
                };
                if (v?.error?.code && codes.has(v.error.code))
                    code = v.error.code;
            }
            catch { }
            return error(status, code);
        }
        if (response.status !== 200)
            return error(503);
        const value = await bounded(response, 65536);
        const result = kind === 'list' ? parsePage(value, limit) : kind === 'detail' ? parseDetail(value, id!) : parseTotal(value, selected);
        // Current roles/MFA are authoritative at relay completion as well as entry.
        const final = await staffState(session.token);
        if (!final.mfa_verified || !final.roles.includes('security_admin') || !final.capabilities.includes('users.manage'))
            return error(403);
        return NextResponse.json(result, { status: response.status, headers });
    }
    catch (e) {
        return error(e instanceof StaffAccessError && [401, 403].includes(e.status) ? e.status : 503);
    }
}
