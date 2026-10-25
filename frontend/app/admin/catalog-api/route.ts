import { publishedTemplateChoices, PublishedTemplateError } from '../../../lib/api/published-template-choices';
import { parseTemplateChoices, templatePath } from '../../../lib/catalog-template-choices';
import {guardedBackendFetch} from '../../../lib/api/quarantine';
import { NextRequest, NextResponse } from 'next/server';
import { verifiedSession } from '../../../lib/auth/server';
import { staffState, StaffAccessError } from '../../../lib/auth/staff';
import { authConfig } from '../../../lib/auth/config';
import { validateOrigin } from '../../../lib/api/transport';
import { target, productBody, categoryBody, variantBody, imageBody, parseResult, uuid } from '../../../lib/admin-products-contract';
const headers = { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
const codes = new Set(['REAUTH_REQUIRED','TEMPLATE_VARIANT_MISMATCH','TEMPLATE_BINDING_UNAVAILABLE','TEMPLATE_QR_ORIGIN_REQUIRED','IDEMPOTENCY_KEY_REUSED', 'IDEMPOTENCY_KEY_REQUIRED', 'VERSION_MISMATCH', 'CATALOG_CONFLICT', 'CREATE_AS_DRAFT', 'QR_TYPE_REQUIRED', 'LEGACY_PRODUCT_TYPE', 'ARCHIVED_PRODUCT', 'PRODUCT_PRICE_REQUIRED', 'DUPLICATE_SIZE', 'FUTURE_PRODUCT_DISABLED', 'PHYSICAL_CATALOG_APPROVAL_REQUIRED', 'QR_TYPE_TEMPLATE_APPROVAL_REQUIRED', 'VERIFIED_PUBLIC_IMAGE_REQUIRED', 'INVALID_PUBLIC_ASSET', 'PUBLIC_ASSET_FOLDER_REQUIRED']);
async function bounded(message: Request | Response, max: number): Promise<unknown> {
    if (message.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json')
        throw Error('media');
    if (Number(message.headers.get('content-length') ?? 0) > max)
        throw Error('size');
    const reader = message.body?.getReader();
    if (!reader)
        throw Error('body');
    let size = 0, text = '';
    const decoder = new TextDecoder('utf-8', { fatal: true });
    try {
        for (;;) {
            const { done, value } = await reader.read();
            if (done)
                break;
            size += value.byteLength;
            if (size > max)
                throw Error('size');
            text += decoder.decode(value, { stream: true });
        }
        text += decoder.decode();
    }
    finally {
        await reader.cancel();
    }
    return JSON.parse(text);
}
async function relay(request: NextRequest) {
    const fail = (status: number, code?: string) => NextResponse.json({ error: { code: code ?? (status === 401 ? 'AUTH_REQUIRED' : status === 403 ? 'FORBIDDEN' : status === 422 ? 'INVALID_REQUEST' : 'UNAVAILABLE') } }, { status, headers });
    try {
        const origin = authConfig().origin, incoming = request.headers.get('origin');
        if (request.headers.get('sec-fetch-site') === 'cross-site' || (incoming && incoming !== origin) || (request.method === 'POST' && incoming !== origin))
            return fail(403);
        const session = await verifiedSession();
        if (!session)
            return fail(401);
        const security = await staffState(session.token);
        if (!security.mfa_verified || !security.capabilities.includes('catalog.manage') || !security.roles.some(r => ['operations', 'security_admin', 'superadmin'].includes(r)))
            return fail(403);
        let path: string, method: string, body: unknown, key: string | undefined, version: number | undefined, upload = false;
        const query = new URLSearchParams();
        if (request.method === 'GET') {
            const p = request.nextUrl.searchParams;
            if ([...p.keys()].some(k => !['path', 'limit', 'cursor'].includes(k) || p.getAll(k).length !== 1) || !p.has('path') || request.headers.get('transfer-encoding') || Number(request.headers.get('content-length') ?? 0) !== 0)
                return fail(422);
            path = p.get('path')!;
            method = 'GET';
            try {
                target(path, method);
                if (path !== '/admin/products' && (p.has('limit') || p.has('cursor')))
                    throw Error();
                if (p.has('limit')) {
                    const limit = p.get('limit')!;
                    if (!/^(?:[1-9][0-9]?|100)$/.test(limit))
                        throw Error();
                    query.set('limit', limit);
                }
                if (p.has('cursor'))
                    query.set('cursor', uuid(p.get('cursor')));
            }
            catch {
                return fail(422);
            }
        }
        else {
            if (request.nextUrl.search)
                return fail(422);
            let v: Record<string, unknown>;
            try {
                const value = await bounded(request, 32768);
                if (!value || typeof value !== 'object' || Array.isArray(value))
                    throw Error();
                v = value as Record<string, unknown>;
            }
            catch (e) {
                return fail(e instanceof Error && e.message === 'size' ? 413 : 422);
            }
            try {
                if (Object.keys(v).some(k => !['path', 'method', 'body', 'key', 'version', 'authorize_upload'].includes(k)))
                    throw Error();
                if (typeof v.path !== 'string' || typeof v.method !== 'string' || v.method === 'GET')
                    throw Error();
                path = v.path;
                method = v.method;
                const kind = target(path, method);
                if (typeof v.key !== 'string' || !/^[A-Za-z0-9._:-]{8,160}$/.test(v.key))
                    throw Error();
                key = v.key;
                const needsVersion = method !== 'POST' || kind === 'variant' || kind === 'image';
                if (needsVersion) {
                    if (!Number.isSafeInteger(v.version) || Number(v.version) < 1 || Number(v.version) > 2147483647)
                        throw Error();
                    version = v.version as number;
                }
                else if (v.version !== undefined)
                    throw Error();
                if (v.authorize_upload !== undefined) {
                    if (v.authorize_upload !== true || kind !== 'image' || method !== 'POST')
                        throw Error();
                    upload = true;
                    query.set('authorize_upload', 'true');
                }
                if (kind === 'product')
                    body = productBody(v.body, method === 'POST');
                else if (kind === 'category')
                    body = categoryBody(v.body);
                else if (kind === 'variant')
                    body = variantBody(v.body);
                else if (kind === 'image' && method !== 'DELETE')
                    body = imageBody(v.body, method === 'PATCH');
                else if (kind === 'image' && method === 'DELETE') {
                    if (v.body !== undefined)
                        throw Error();
                }
                else
                    throw Error();
            }
            catch {
                return fail(422);
            }
        }
        const backendOrigin = validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? '');
        const signal = AbortSignal.timeout(15000);
        const response = await guardedBackendFetch(backendOrigin + '/api/v1' + path + (query.size ? '?' + query : ''), { method, cache: 'no-store', redirect: 'error', signal, headers: { Authorization: `Bearer ${session.token}`, Accept: 'application/json', ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(key ? { 'Idempotency-Key': key } : {}), ...(version ? { 'If-Match': `"${version}"` } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
        if (!response.ok) {
            const status = [400, 401, 403, 404, 409, 412, 413, 415, 422, 429].includes(response.status) ? response.status : 503;
            let code: string | undefined;
            try {
                const v = await bounded(response, 8192) as {
                    detail?: {
                        code?: string;
                    };
                    error?: {
                        code?: string;
                    };
                };
                const c = v?.error?.code ?? v?.detail?.code;
                if (c && codes.has(c))
                    code = c;
            }
            catch { }
            return fail(status, code);
        }
        let value = parseResult(path, method, await bounded(response, 2 * 1024 * 1024), upload);
        if (method === 'GET' && path === templatePath) value = await publishedTemplateChoices(backendOrigin, session.token, parseTemplateChoices(value), signal);
        return NextResponse.json(value, { status: response.status, headers });
    }
    catch (error) {
        return fail((error instanceof StaffAccessError || error instanceof PublishedTemplateError) && [401, 403].includes(error.status) ? error.status : 503);
    }
}
export const GET = relay;
export const POST = relay;
const blocked = () => NextResponse.json({ error: { code: 'METHOD_NOT_ALLOWED' } }, { status: 405, headers: { ...headers, Allow: 'GET, POST' } });
export const PUT = blocked;
export const PATCH = blocked;
export const DELETE = blocked;
export const OPTIONS = blocked;
export const HEAD = blocked;
