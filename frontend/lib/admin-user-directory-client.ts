import { uuid, parsePage, parseDetail, parseTotal, type Filters } from './users-contract';
export class DirectoryError extends Error {
    constructor(public status: number) { super('Directory unavailable'); }
}
export function directoryError(e: unknown) { const s = e instanceof DirectoryError ? e.status : 503; return s === 401 ? 'Sign in again to view the user directory.' : s === 403 ? 'Current Security Admin role and MFA are required.' : s === 404 ? 'User not found or not accessible.' : s === 422 ? 'Invalid user UUID or directory filters.' : s === 429 ? 'Request limit reached; wait before refreshing.' : 'User directory unavailable or response invalid. No demo fallback.'; }
export function selectedFilters(raw: Record<string, string>): Filters { try {
    if (raw.email_verified && !['true', 'false'].includes(raw.email_verified) || raw.provider_access && !['banned', 'not_banned'].includes(raw.provider_access))
        throw Error();
    return { user_id: raw.user_id ? uuid(raw.user_id) : null, email_verified: raw.email_verified ? raw.email_verified === 'true' : null, provider_access: raw.provider_access ? raw.provider_access as Filters['provider_access'] : null };
}
catch {
    throw new DirectoryError(422);
} }
async function read(p: URLSearchParams, signal: AbortSignal) { const r = await fetch('/admin/users/directory-api?' + p, { method: 'GET', cache: 'no-store', redirect: 'error', signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]) }); if (!r.ok)
    throw new DirectoryError(r.status); return r.json(); }
function query(kind: string, f: Filters) { const p = new URLSearchParams({ kind }); for (const [k, v] of Object.entries(f))
    if (v !== null)
        p.set(k, String(v)); return p; }
export async function directoryPage(f: Filters, cursor: string | null, signal: AbortSignal) { const p = query('list', f); p.set('limit', '20'); if (cursor)
    p.set('cursor', cursor); return parsePage(await read(p, signal), 20); }
export async function directoryCount(f: Filters, signal: AbortSignal) { return parseTotal(await read(query('count', f), signal), f); }
export async function directoryDetail(id: string, signal: AbortSignal) { try {
    id = uuid(id);
}
catch {
    throw new DirectoryError(422);
} return parseDetail(await read(new URLSearchParams({ kind: 'detail', user_id: id }), signal), id); }
