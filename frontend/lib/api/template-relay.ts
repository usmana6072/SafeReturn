import {guardedBackendFetch} from './quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { object, templateTarget, templateBody, templateQuery, templateResult, positive, type Action } from '../admin-templates-contract';
import { parseResult as productResult } from '../admin-products-contract';
const headers = { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
const codes = new Set(['PREVIEW_TIMEOUT', 'PREVIEW_BUSY', 'PREVIEW_WORKER_FAILED','AUTH_REQUIRED', 'FORBIDDEN', 'REAUTH_REQUIRED', 'NOT_FOUND', 'CONFLICT', 'IDEMPOTENCY_KEY_REUSED', 'VERSION_MISMATCH', 'FILE_TOO_LARGE', 'VALIDATION_ERROR', 'RATE_LIMITED', 'PROVIDER_UNAVAILABLE', 'TEMPLATE_MANAGEMENT_DISABLED', 'TEMPLATE_ASSETS_UNAVAILABLE', 'PREVIEW_ISOLATION_UNAVAILABLE', 'TEMPLATE_ORIGIN_MISMATCH']);
async function bytes(message: Request | Response, max: number) { const reader = message.body?.getReader(); if (!reader)
    throw Error(); let size = 0; const parts: Uint8Array[] = []; try {
    for (;;) {
        const { done, value } = await reader.read();
        if (done)
            break;
        size += value.byteLength;
        if (size > max)
            throw Error('size');
        parts.push(value);
    }
}
finally {
    await reader.cancel();
} const result = new Uint8Array(size); let offset = 0; for (const p of parts) {
    result.set(p, offset);
    offset += p.byteLength;
} return result; }
async function json(message: Request | Response, max: number) { if (message.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json')
    throw Error(); return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(await bytes(message, max))); }
export async function templateRelay(request: NextRequest) {
    const fail = (status: number, code?: string) => NextResponse.json({ error: { code: code ?? (status === 401 ? 'AUTH_REQUIRED' : status === 403 ? 'FORBIDDEN' : status === 422 ? 'VALIDATION_ERROR' : 'PROVIDER_UNAVAILABLE') } }, { status, headers });
    try {
        if (!['GET', 'POST'].includes(request.method))
            return fail(405, 'METHOD_NOT_ALLOWED');
        const origin = authConfig().origin, incoming = request.headers.get('origin');
        if (request.headers.get('sec-fetch-site') === 'cross-site' || incoming && incoming !== origin || request.method === 'POST' && incoming !== origin)
            return fail(403);
        const session = await verifiedSession();
        if (!session)
            return fail(401);
        const security = await staffState(session.token);
        if (!security.mfa_verified || !security.roles.some(r => ['operations', 'security_admin', 'superadmin'].includes(r)))
            return fail(403);
        let path: string, method: string, action: Action, body: unknown, key: string | undefined, version: number | undefined, query = new URLSearchParams();
        try {
            if (request.method === 'GET') {
                const p = request.nextUrl.searchParams;
                if (p.getAll('path').length !== 1 || Number(request.headers.get('content-length') ?? 0) !== 0 || request.headers.get('transfer-encoding'))
                    throw Error();
                path = p.get('path')!;
                method = 'GET';
                action = templateTarget(path, method);
                const raw = new URLSearchParams(p);
                raw.delete('path');
                query = templateQuery(action, raw);
            }
            else {
                if (request.nextUrl.search || request.headers.get('content-encoding'))
                    throw Error();
                const v = object(await json(request, 164000));
                if (Object.keys(v).some(k => !['path', 'method', 'body', 'key', 'version'].includes(k)) || typeof v.path !== 'string' || typeof v.method !== 'string' || v.method === 'GET')
                    throw Error();
                path = v.path;
                method = v.method;
                action = templateTarget(path, method);
                if (action === 'qa-decision' ? !security.roles.includes('security_admin') : !security.roles.includes('operations') || !security.capabilities.includes('printing.manage'))
                    return fail(403);
                if (typeof v.key !== 'string' || !/^[A-Za-z0-9._:-]{8,160}$/.test(v.key))
                    throw Error();
                key = v.key;
                if (action === 'create') {
                    if (v.version !== undefined)
                        throw Error();
                }
                else
                    version = positive(v.version);
                body = templateBody(action, v.body);
                if (action === 'preview' && (body as {
                    expected_revision: number;
                }).expected_revision !== version)
                    throw Error();
                if (action === 'bind' && (body as {
                    expected_variant_version: number;
                }).expected_variant_version !== version)
                    throw Error();
            }
        }
        catch (e) {
            return fail(e instanceof Error && e.message === 'size' ? 413 : 422);
        }
        // No auth_time is synthesized: backend requires a genuine recent authentication (1200s).
        const response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '') + '/api/v1' + path + (query.size ? '?' + query : ''), { method, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(action === 'preview' || action === 'submit' ? 75000 : 10000), headers: { Authorization: `Bearer ${session.token}`, Accept: action === 'preview' ? 'application/pdf' : 'application/json', ...(method !== 'GET' ? { 'Content-Type': 'application/json', Origin: origin, 'Idempotency-Key': key! } : {}), ...(version ? { 'If-Match': `"${version}"` } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
        if (!response.ok) {
            const status = [400, 401, 403, 404, 409, 412, 413, 422, 429].includes(response.status) ? response.status : 503;
            let code: string | undefined;
            try {
                const v = object(await json(response, 8192)), e = object(v.error);
                if (typeof e.code === 'string' && codes.has(e.code))
                    code = e.code;
            }
            catch { }
            if(process.env.NODE_ENV==='development'&&action==='preview')console.info(JSON.stringify({event:'template.preview.rejected',status:response.status,code:code??'UNRECOGNIZED',request_id:/^[a-f0-9]{32}$/.test(response.headers.get('x-request-id')??'')?response.headers.get('x-request-id'):null}));
            return fail(status, code);
        }
        if (action === 'preview') {
            if(process.env.NODE_ENV==='development')console.info(JSON.stringify({event:'template.preview.received',status:response.status,pdf_content_type:response.headers.get('content-type')?.split(';')[0].trim()==='application/pdf',fingerprint_valid:/^[a-f0-9]{64}$/.test(response.headers.get('x-template-fingerprint')??'')}));
            if (response.headers.get('content-type')?.split(';')[0].trim() !== 'application/pdf')
                throw Error();
            const fingerprint = response.headers.get('x-template-fingerprint');
            if (!fingerprint || !/^[a-f0-9]{64}$/.test(fingerprint))
                throw Error();
            const pdf = await bytes(response, 2 * 1024 * 1024);
            if (new TextDecoder().decode(pdf.slice(0, 5)) !== '%PDF-')
                throw Error();
            return new Response(pdf, { headers: { ...headers, 'Content-Type': 'application/pdf', 'Content-Disposition': 'inline; filename="synthetic-template-preview.pdf"', 'Content-Security-Policy': "sandbox; default-src 'none'", 'X-Template-Fingerprint': fingerprint } });
        }
        const raw = await json(response, 2 * 1024 * 1024), value = action === 'products' || action === 'product' ? productResult(path, 'GET', raw) : templateResult(action, raw);
        const etag = response.headers.get('etag');
        return NextResponse.json(value, { status: response.status, headers: { ...headers, ...(action === 'detail' && etag && /^"[1-9][0-9]{0,15}"$/.test(etag) ? { ETag: etag } : {}) } });
    }
    catch (e) {
        return fail(e instanceof StaffAccessError && [401, 403].includes(e.status) ? e.status : 503);
    }
}
