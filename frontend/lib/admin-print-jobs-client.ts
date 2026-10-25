import { printTarget, printQuery, parsePage, parseCounts, parseOrder, parseDetail, type JobPage, type Counts, type OrderJob, type Detail } from './admin-print-jobs-contract';
export class PrintMetadataError extends Error {
    constructor(public status: number) { super('Print metadata unavailable'); }
}
export function printError(e: unknown) { const status = e instanceof PrintMetadataError ? e.status : 503; return status === 401 ? 'Sign in again to view print metadata.' : status === 403 ? 'Current Operations role and MFA are required.' : status === 404 ? 'Print job not found.' : status === 422 ? 'Invalid filters or cursor. Refresh the first page or check the UUID.' : status === 429 ? 'Request limit reached; wait before retrying.' : 'Print metadata unavailable or response invalid. No mock fallback or production success is assumed.'; }
export async function printRead(kind: 'jobs' | 'counts' | 'order' | 'detail', options: {
    query?: URLSearchParams;
    id?: string;
    signal?: AbortSignal;
} = {}): Promise<JobPage | Counts | {
    items: OrderJob[];
} | Detail> { let p: URLSearchParams; try {
    p = new URLSearchParams({ kind });
    if (options.id !== undefined)
        p.set('id', options.id);
    if (kind === 'jobs' || kind === 'counts') {
        for (const [k, v] of printQuery(options.query ?? new URLSearchParams(), kind === 'counts'))
            p.set(k, v);
    }
    printTarget(p);
}
catch {
    throw new PrintMetadataError(422);
} const r = await fetch('/admin/print-jobs/metadata-api?' + p, { method: 'GET', cache: 'no-store', redirect: 'error', signal: options.signal ?? AbortSignal.timeout(15000) }); if (!r.ok)
    throw new PrintMetadataError(r.status); const raw = await r.json(); return kind === 'jobs' ? parsePage(raw, Number(p.get('limit') ?? 20)) : kind === 'counts' ? parseCounts(raw) : kind === 'order' ? parseOrder(raw) : parseDetail(raw, options.id!); }
