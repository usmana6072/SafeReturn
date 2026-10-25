import { parseResult, target } from './admin-products-contract';
import { catalogCodeMessage } from './catalog-admin-feedback';
export class ProductApiError extends Error {
    constructor(public status: number, public code = 'UNAVAILABLE') { super('Product request failed'); }
}
export function productError(error: unknown, ur = false): string {
    const status = error instanceof ProductApiError ? error.status : 503;
    if (status === 401)
        return ur ? 'دوبارہ سائن ان کریں۔' : 'Your session expired. Sign in again.';
    if (status === 403)
        return ur ? 'موجودہ کردار یا MFA اس کارروائی کی اجازت نہیں دیتا۔' : 'Your role or MFA does not permit this action.';
    if (status === 404)
        return ur ? 'مصنوعہ دستیاب نہیں۔' : 'The requested record was not found.';
    if (status === 412 || status === 409)
        return ur ? 'ریکارڈ تبدیل ہو گیا یا درخواست متصادم ہے۔ ان پٹ محفوظ ہے؛ تازہ ورژن لوڈ کر کے دوبارہ تصدیق کریں۔' : 'The record changed or the request conflicts with its current state. Your input is preserved. Load the latest version, review it and confirm before saving again.';
    if (error instanceof ProductApiError && status < 500) {
        const message = catalogCodeMessage(error.code, ur);
        if (message)
            return message;
    }
    if (status === 400 || status === 422)
        return ur ? 'فیلڈز، قیمت اور اشاعت کے تقاضے چیک کریں۔' : 'Check the fields, decimal PKR price and publication requirements. Published products require approved sizes/templates and a verified main image.';
    return ur ? 'سرور دستیاب نہیں یا جواب کی تصدیق نہیں ہوئی۔ کوئی کامیابی فرض نہ کریں؛ اسی درخواست کو دوبارہ آزمائیں۔' : 'The server is unavailable or returned an invalid response. Success is not confirmed; retry the same request.';
}
export async function productRequest<T>(path: string, options: {
    method?: string;
    body?: unknown;
    version?: number;
    key?: string;
    upload?: boolean;
    cursor?: string;
    signal?: AbortSignal;
} = {}): Promise<T> {
    const method = options.method ?? 'GET';
    target(path, method);
    const query = new URLSearchParams({ path });
    if (options.cursor)
        query.set('cursor', options.cursor);
    const write = method !== 'GET';
    let response: Response;
    try {
        response = await fetch('/admin/catalog-api' + (write ? '' : '?' + query), { method: write ? 'POST' : 'GET', cache: 'no-store', redirect: 'error', signal: options.signal ?? AbortSignal.timeout(18000), headers: write ? { 'Content-Type': 'application/json' } : { Accept: 'application/json' }, body: write ? JSON.stringify({ path, method, body: options.body, key: options.key, version: options.version, ...(options.upload ? { authorize_upload: true } : {}) }) : undefined });
    }
    catch {
        throw new ProductApiError(503);
    }
    let value: unknown;
    try {
        value = await response.json();
    }
    catch {
        throw new ProductApiError(503);
    }
    if (!response.ok) {
        const code = (value as {
            error?: {
                code?: string;
            };
        })?.error?.code;
        throw new ProductApiError(response.status, typeof code === 'string' ? code : 'UNAVAILABLE');
    }
    try {
        return parseResult(path, method, value, options.upload) as T;
    }
    catch {
        throw new ProductApiError(503);
    }
}
// One stable key per exact user intent, including version and upload phase. Memory only.
export function intentKeys() { const keys = new Map<string, string>(); return (path: string, method: string, body: unknown, version?: number, upload = false) => { const signature = JSON.stringify([path, method, body, version, upload]); let key = keys.get(signature); if (!key) {
    key = crypto.randomUUID();
    keys.set(signature, key);
} return key; }; }
