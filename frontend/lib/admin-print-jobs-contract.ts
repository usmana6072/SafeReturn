// Closed metadata-only projections. No legacy printing/inventory/order clients.
export const states = ['queued', 'rendering', 'ready', 'downloaded', 'qa_passed', 'failed', 'superseded', 'deleted'] as const;
export const orderStates = ['draft', 'placed', 'processing', 'fulfilled', 'cancelled'] as const;
export const paymentStates = ['awaiting_transfer', 'proof_submitted', 'under_review', 'verified', 'rejected', 'refunded'] as const;
export const fulfillmentStates = ['unallocated', 'allocated', 'packed', 'dispatched', 'delivered', 'exception'] as const;
export const filterKeys = ['job_id', 'order_id', 'order_number', 'job_status', 'order_status', 'payment_status', 'fulfillment_status', 'created_from', 'created_before'] as const;
export type Failure = 'PHYSICAL_QA_FAILED' | 'PRINT_FAILURE_RECORDED' | null;
export type Job = {
    job_id: string;
    order_id: string;
    order_number: string;
    job_revision: number;
    job_status: string;
    created_at: string;
    order_status: string;
    payment_status: string;
    fulfillment_status: string;
    attempt_count: number;
    failure_category: Failure;
};
export type JobPage = {
    as_of: string;
    items: Job[];
    next_cursor: string | null;
};
export type Count = {
    value: number;
    is_exact: boolean;
};
export type Counts = {
    as_of: string;
    matching_jobs: Count;
    affected_orders: Count;
    by_job_status: Record<string, Count>;
};
export type OrderJob = {
    id: string;
    job_revision: number;
    status: string;
    template_fingerprint: string;
    failure_category: Failure;
};
export type Artifact = {
    id: string;
    format: string;
    size_bytes: number;
    sha256_hex: string;
    deleted_at: string | null;
};
export type Detail = OrderJob & {
    order_id: string;
    attempt_count: number;
    artifacts: Artifact[];
};
function bad(): never { throw Error('Invalid print metadata contract'); }
function object(v: unknown) { if (!v || typeof v !== 'object' || Array.isArray(v))
    bad(); return v as Record<string, unknown>; }
function exact(o: Record<string, unknown>, fields: string[]) { if (Object.keys(o).length !== fields.length || fields.some(k => !Object.hasOwn(o, k)))
    bad(); }
function text(v: unknown, max: number) { if (typeof v !== 'string' || !v.length || v.length > max || /[\x00-\x1f\x7f]/.test(v))
    bad(); return v as string; }
export function uuid(v: unknown) { const s = text(v, 36); if (!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(s))
    bad(); return s; }
function integer(v: unknown, min = 0, max = Number.MAX_SAFE_INTEGER) { if (!Number.isSafeInteger(v) || Number(v) < min || Number(v) > max)
    bad(); return v as number; }
function one(v: unknown, values: readonly string[]) { if (typeof v !== 'string' || !values.includes(v))
    bad(); return v as string; }
function date(v: unknown) { const s = text(v, 40); if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(s) || !Number.isFinite(Date.parse(s)))
    bad(); return s; }
function micros(s: string) { const f = s.match(/\.(\d{1,6})/)?.[1] ?? ''; return BigInt(Date.parse(s)) * BigInt(1000) + BigInt(f.padEnd(6, '0').slice(3)); }
function hash(v: unknown) { const s = text(v, 64); if (!/^[a-f0-9]{64}$/.test(s))
    bad(); return s; }
function cursor(v: unknown) { if (v === null)
    return null; const s = text(v, 4096); if (!/^[1-9][0-9]*\.[A-Za-z0-9_-]+={0,2}$/.test(s))
    bad(); return s; }
function failure(v: unknown, backend = false): Failure { if (v === null)
    return null; if (backend) {
    text(v, 80);
    return v === 'physical_qa_failed' ? 'PHYSICAL_QA_FAILED' : 'PRINT_FAILURE_RECORDED';
} return one(v, ['PHYSICAL_QA_FAILED', 'PRINT_FAILURE_RECORDED']) as Failure; }
export function printTarget(p: URLSearchParams) { const kind = p.get('kind'); if (!['jobs', 'counts', 'order', 'detail'].includes(kind ?? '') || p.getAll('kind').length !== 1)
    bad(); if (kind === 'order' || kind === 'detail') {
    if (p.size !== 2 || p.getAll('id').length !== 1)
        bad();
    const id = uuid(p.get('id'));
    return kind === 'order' ? '/admin/orders/' + id + '/print-jobs' : '/admin/print-jobs/' + id;
} return kind === 'counts' ? '/admin/print-jobs/counts' : '/admin/print-jobs'; }
export function printQuery(p: URLSearchParams, count = false) { const out = new URLSearchParams(); for (const [k, v] of p) {
    if (p.getAll(k).length !== 1 || ![...filterKeys, ...(count ? [] : ['limit', 'sort', 'cursor'])].includes(k))
        bad();
    if (k === 'job_id' || k === 'order_id')
        uuid(v);
    else if (k === 'order_number') {
        text(v, 40);
        if (v !== v.trim())
            bad();
    }
    else if (k === 'job_status')
        one(v, states);
    else if (k === 'order_status')
        one(v, orderStates);
    else if (k === 'payment_status')
        one(v, paymentStates);
    else if (k === 'fulfillment_status')
        one(v, fulfillmentStates);
    else if (k.startsWith('created_'))
        date(v);
    else if (k === 'sort')
        one(v, ['oldest', 'newest']);
    else if (k === 'cursor')
        cursor(v);
    else if (k === 'limit' && (!/^[1-9][0-9]{0,2}$/.test(v) || Number(v) > 100))
        bad();
    out.set(k, v);
} if (out.has('created_from') && out.has('created_before') && micros(out.get('created_from')!) >= micros(out.get('created_before')!))
    bad(); if (out.toString().length > 7800)
    bad(); return out; }
export function parsePage(raw: unknown, limit = 20): JobPage { const p = object(raw); exact(p, ['as_of', 'items', 'next_cursor']); if (!Array.isArray(p.items) || p.items.length > limit)
    bad(); const as_of = date(p.as_of), next = cursor(p.next_cursor); const items = p.items.map(v => { const o = object(v); exact(o, ['job_id', 'order_id', 'order_number', 'job_revision', 'job_status', 'created_at', 'order_status', 'payment_status', 'fulfillment_status', 'attempt_count', 'failure_category']); return { job_id: uuid(o.job_id), order_id: uuid(o.order_id), order_number: text(o.order_number, 40), job_revision: integer(o.job_revision, 1), job_status: one(o.job_status, states), created_at: date(o.created_at), order_status: one(o.order_status, orderStates), payment_status: one(o.payment_status, paymentStates), fulfillment_status: one(o.fulfillment_status, fulfillmentStates), attempt_count: integer(o.attempt_count), failure_category: failure(o.failure_category) }; }); if (new Set(items.map(j => j.job_id)).size !== items.length || next && !items.length || items.some(j => micros(j.created_at) > micros(as_of)))
    bad(); return { as_of, items, next_cursor: next }; }
export function parseCounts(raw: unknown): Counts { const p = object(raw); exact(p, ['as_of', 'matching_jobs', 'affected_orders', 'by_job_status']); const groups = object(p.by_job_status); exact(groups, [...states]); const count = (v: unknown): Count => { const o = object(v); exact(o, ['value', 'is_exact']); const value = integer(o.value, 0, 1000); if (typeof o.is_exact !== 'boolean' || o.is_exact === (value === 1000))
    bad(); return { value, is_exact: o.is_exact as boolean }; }; return { as_of: date(p.as_of), matching_jobs: count(p.matching_jobs), affected_orders: count(p.affected_orders), by_job_status: Object.fromEntries(states.map(s => [s, count(groups[s])])) }; }
function orderJob(v: unknown, backend: boolean, extra: string[] = []): OrderJob { const o = object(v); exact(o, ['id', 'job_revision', 'status', 'template_fingerprint', backend ? 'failure_code' : 'failure_category', ...extra]); return { id: uuid(o.id), job_revision: integer(o.job_revision, 1), status: one(o.status, states), template_fingerprint: hash(o.template_fingerprint), failure_category: failure(o[backend ? 'failure_code' : 'failure_category'], backend) }; }
export function parseOrder(raw: unknown, backend = false) { const p = object(raw); exact(p, ['items']); if (!Array.isArray(p.items) || p.items.length > 1000)
    bad(); const items = p.items.map(v => orderJob(v, backend)); if (new Set(items.map(j => j.id)).size !== items.length)
    bad(); return { items }; }
export function parseDetail(raw: unknown, target: string, backend = false): Detail { const o = object(raw), inspection = backend && Object.hasOwn(o, 'inspection_items'); const base = orderJob(o, backend, ['order_id', 'attempt_count', 'artifacts', ...(inspection ? ['inspection_items'] : [])]); if (base.id !== uuid(target) || !Array.isArray(o.artifacts) || o.artifacts.length > 100)
    bad(); if (inspection) {
    if (!Array.isArray(o.inspection_items) || o.inspection_items.length > 50)
        bad();
    for (const v of o.inspection_items) {
        const i = object(v);
        exact(i, ['id', 'product_name_snapshot', 'qr_type_snapshot']);
        uuid(i.id);
        text(i.product_name_snapshot, 500);
        one(i.qr_type_snapshot, ['lost', 'ice']);
    }
} const artifacts = o.artifacts.map(v => { const a = object(v); exact(a, ['id', 'format', 'size_bytes', 'sha256_hex', 'deleted_at']); return { id: uuid(a.id), format: one(a.format, ['pdf', 'svg', 'other_approved']), size_bytes: integer(a.size_bytes, 1), sha256_hex: hash(a.sha256_hex), deleted_at: a.deleted_at === null ? null : date(a.deleted_at) }; }); if (new Set(artifacts.map(a => a.id)).size !== artifacts.length)
    bad(); return { ...base, order_id: uuid(o.order_id), attempt_count: integer(o.attempt_count), artifacts }; }
export function countLabel(c: Count) { return c.is_exact ? String(c.value) : c.value + '+ (lower bound)'; }
