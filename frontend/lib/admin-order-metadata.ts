// Independent metadata contract; no legacy order/fulfillment imports.
export const orderStates = ['draft', 'placed', 'processing', 'fulfilled', 'cancelled'] as const;
export const paymentStates = ['awaiting_transfer', 'proof_submitted', 'under_review', 'verified', 'rejected', 'refunded'] as const;
export type OrderMetadata = {
    order_id: string;
    order_number: string;
    order_status: string;
    payment_status: string;
    currency_code: string;
    total_amount: string;
    created_at: string;
    placed_at: string | null;
};
export type MetadataPage = {
    items: OrderMetadata[];
    next_cursor: string | null;
    as_of: string;
};
function bad(): never { throw Error('Invalid metadata contract'); }
function obj(v: unknown, keys: string[]): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v))
    bad(); const o = v as Record<string, unknown>; if (Object.keys(o).length !== keys.length || keys.some(k => !Object.hasOwn(o, k)))
    bad(); return o; }
function str(v: unknown, max: number) { if (typeof v !== 'string' || !v.length || v.length > max || /[\x00-\x1f\x7f]/.test(v))
    bad(); return v as string; }
function one(v: unknown, options: readonly string[]) { if (typeof v !== 'string' || !options.includes(v))
    bad(); return v as string; }
function date(v: unknown) { const s = str(v, 40); if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(s) || !Number.isFinite(Date.parse(s)))
    bad(); return s; }
function cursor(v: unknown) { if (v === null)
    return null; const s = str(v, 2048); if (!/^[A-Za-z0-9_-]+={0,2}$/.test(s))
    bad(); return s; }
// Preserve PostgreSQL microseconds when comparing filter bounds in the browser.
function micros(s: string) {
    const fraction = s.match(/\.(\d{1,6})/)?.[1] ?? '';
    return BigInt(Date.parse(s)) * BigInt(1000) + BigInt(fraction.padEnd(6, '0').slice(3));
}
export function metadataQuery(p: URLSearchParams) { const out = new URLSearchParams(); for (const [k, v] of p) {
    if (p.getAll(k).length !== 1)
        bad();
    switch (k) {
        case 'order_number':
            str(v, 40);
            break;
        case 'order_status':
            one(v, orderStates);
            break;
        case 'payment_status':
            one(v, paymentStates);
            break;
        case 'created_from':
        case 'created_before':
            date(v);
            break;
        case 'sort':
            one(v, ['newest', 'oldest']);
            break;
        case 'limit':
            if (!/^[1-9][0-9]{0,2}$/.test(v) || Number(v) > 100)
                bad();
            break;
        case 'cursor':
            cursor(v);
            break;
        default: bad();
    }
    out.set(k, v);
} if (out.has('created_from') && out.has('created_before') && micros(out.get('created_from')!) >= micros(out.get('created_before')!))
    bad(); if (out.toString().length > 7800)
    bad(); return out; }
export function metadataPage(raw: unknown, limit = 20): MetadataPage { const p = obj(raw, ['items', 'next_cursor', 'as_of']); if (!Array.isArray(p.items) || p.items.length > limit)
    bad(); const items = p.items.map(raw => { const o = obj(raw, ['order_id', 'order_number', 'order_status', 'payment_status', 'currency_code', 'total_amount', 'created_at', 'placed_at']); const id = str(o.order_id, 36); if (!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(id))
    bad(); const currency = str(o.currency_code, 3), amount = str(o.total_amount, 13); if (!/^[A-Z]{3}$/.test(currency) || !/^(0|[1-9][0-9]{0,9})\.[0-9]{2}$/.test(amount))
    bad(); return { order_id: id, order_number: str(o.order_number, 40), order_status: one(o.order_status, orderStates), payment_status: one(o.payment_status, paymentStates), currency_code: currency, total_amount: amount, created_at: date(o.created_at), placed_at: o.placed_at === null ? null : date(o.placed_at) }; }); if (new Set(items.map(i => i.order_id)).size !== items.length)
    bad(); const next = cursor(p.next_cursor); if (next && !items.length)
    bad(); return { items, next_cursor: next, as_of: date(p.as_of) }; }
export function historicalAmount(o: OrderMetadata) { return o.currency_code + ' ' + o.total_amount; }
export class MetadataError extends Error {
    constructor(public status: number) { super('Metadata request failed'); }
}
export function metadataError(e: unknown) { const s = e instanceof MetadataError ? e.status : 503; return s === 429 ? 'Request limit reached. Wait before refreshing.' : s === 401 ? 'Sign in again to view order metadata.' : s === 403 ? 'Your current role or MFA does not permit this view.' : s === 422 ? 'Invalid filters or expired cursor. Refresh from the first page.' : 'Order metadata service unavailable or response invalid. No demo fallback is shown.'; }
export async function fetchMetadata(params: URLSearchParams, signal?: AbortSignal) { let q: URLSearchParams; try {
    q = metadataQuery(params);
}
catch {
    throw new MetadataError(422);
} const r = await fetch('/admin/orders/metadata-api?' + q, { method: 'GET', cache: 'no-store', redirect: 'error', signal: signal ?? AbortSignal.timeout(15000) }); if (!r.ok)
    throw new MetadataError(r.status); return metadataPage(await r.json(), Number(q.get('limit') ?? 20)); }
