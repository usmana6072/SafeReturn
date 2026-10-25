import { templateTarget, templateQuery, templateBody, templateResult, object, TemplateValidation } from './admin-templates-contract';
import { parseResult as productResult } from './admin-products-contract';
export { intentKeys } from './admin-products-client';
export class TemplateApiError extends Error {
    constructor(public status: number, public code = 'PROVIDER_UNAVAILABLE') { super('Template request failed'); }
}
export function templateError(e: unknown, ur = false) {
    if (e instanceof TemplateValidation)
        return (ur ? 'فیلڈ چیک کریں: ' : 'Check field: ') + e.field;
    if (e instanceof SyntaxError)
        return ur ? 'درست JSON درج کریں۔' : 'Content JSON is invalid. Correct the JSON syntax before saving.';
    const error = e instanceof TemplateApiError ? e : new TemplateApiError(503);
    if (error.status === 401)
        return ur ? 'دوبارہ سائن ان کریں؛ درج شدہ ڈیزائن برقرار ہے۔' : 'Sign in again. Your unsaved design is retained.';
    if (error.code === 'REAUTH_REQUIRED')
        return ur ? 'حساس کارروائی کے لیے دوبارہ تصدیق درکار ہے۔' : 'Recent authentication is required: all Print Template actions require authentication within 20 minutes. Reauthenticate using the existing sign-in/MFA flow, then review and retry. Your input is retained.';
    if (error.code === 'PREVIEW_TIMEOUT') return 'The isolated preview worker exceeded its 60-second elapsed-time limit. Retry the same intent once; if repeated, inspect Render CPU/memory and worker logs. No preview or approval was produced.';
    if (error.code === 'PREVIEW_BUSY') return 'Another preview is running. Wait for it to finish, then retry the same intent.';
    if (error.code === 'PREVIEW_WORKER_FAILED') return 'The isolated preview worker failed. Check the deployed worker/assets and Render logs; no preview or approval was produced.';
    if (error.code === 'TEMPLATE_MANAGEMENT_DISABLED')
        return 'Print Template Management is disabled in this backend environment. Reauthentication will not enable it.';
    if (error.code === 'TEMPLATE_ASSETS_UNAVAILABLE')
        return 'Preview requires an enrolled font/logo asset set and a configured asset root. Draft metadata is independent; no approval was granted.';
    if (error.code === 'PREVIEW_ISOLATION_UNAVAILABLE')
        return 'Synthetic preview requires the supported isolated Linux worker. This runtime cannot preview or submit for QA. Draft metadata remains available.';
    if (error.code === 'TEMPLATE_ORIGIN_MISMATCH')
        return 'The backend template web origin does not match this frontend. The request was rejected; no change was confirmed.';
    if (error.status === 403)
        return ur ? 'مجاز کردار، MFA یا پبلشر اجازت درکار ہے۔' : 'Your role, MFA or enrolled publisher authorization does not permit this action.';
    if (error.status === 404)
        return ur ? 'ٹیمپلیٹ دستیاب نہیں۔' : 'Template or revision not found.';
    if (error.status === 409 || error.status === 412)
        return ur ? 'ریکارڈ بدل گیا یا تقاضے پورے نہیں۔ ان پٹ محفوظ ہے؛ تازہ ریکارڈ کا جائزہ لیں۔' : 'Version conflict or lifecycle prerequisite rejected. Your input is retained. Load the latest record, compare your edits and confirm before retrying.';
    if (error.status === 400 || error.status === 422)
        return ur ? 'ڈیزائن، ورژن اور لازمی فیلڈز چیک کریں۔' : 'Check the structured design, required fields, version and lifecycle prerequisites. Only plain text and enrolled asset-set IDs are supported.';
    if (error.status === 429)
        return ur ? 'حد پوری ہوئی؛ بعد میں دوبارہ کوشش کریں۔' : 'Preview/request budget exhausted. Wait before retrying; no approval was granted.';
    return ur ? 'ٹیمپلیٹ سروس یا منظور شدہ وسائل دستیاب نہیں۔' : 'Template service unavailable or response invalid. Check the management flag, configured web origin, enrolled assets and platform isolation. Success is not confirmed; retry the same intent.';
}
export async function templateRequest<T>(path: string, options: {
    method?: string;
    body?: unknown;
    version?: number;
    key?: string;
    query?: Record<string, string>;
    signal?: AbortSignal;
} = {}): Promise<T> {
    const method = options.method ?? 'GET', action = templateTarget(path, method), write = method !== 'GET';
    const q = new URLSearchParams({ path, ...options.query });
    if (!write)
        templateQuery(action, new URLSearchParams(options.query));
    else
        templateBody(action, options.body);
    let response: Response;
    try {
        response = await fetch('/admin/templates/api' + (write ? '' : '?' + q), { method: write ? 'POST' : 'GET', cache: 'no-store', redirect: 'error', signal: options.signal ?? AbortSignal.timeout(action === 'preview' || action === 'submit' ? 90000 : 25000), headers: write ? { 'Content-Type': 'application/json' } : { Accept: 'application/json' }, body: write ? JSON.stringify({ path, method, body: options.body, key: options.key, version: options.version }) : undefined });
    }
    catch {
        throw new TemplateApiError(503);
    }
    if (action === 'preview' && response.ok) {
        if (response.headers.get('content-type')?.split(';')[0].trim() !== 'application/pdf')
            throw new TemplateApiError(503);
        const blob = await response.blob(), fingerprint = response.headers.get('x-template-fingerprint');
        if (blob.size > 2 * 1024 * 1024 || !fingerprint || !/^[a-f0-9]{64}$/.test(fingerprint) || (await blob.slice(0, 5).text()) !== '%PDF-')
            throw new TemplateApiError(503);
        return { blob, fingerprint } as T;
    }
    let raw: unknown;
    try {
        raw = await response.json();
    }
    catch {
        throw new TemplateApiError(503);
    }
    if (!response.ok) {
        let code = 'PROVIDER_UNAVAILABLE';
        try {
            const e = object(object(raw).error);
            if (typeof e.code === 'string')
                code = e.code;
        }
        catch { }
        throw new TemplateApiError(response.status, code);
    }
    try {
        return (action === 'products' || action === 'product' ? productResult(path, 'GET', raw) : templateResult(action, raw)) as T;
    }
    catch {
        throw new TemplateApiError(503);
    }
}
