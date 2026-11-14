// Independent closed projections from backend/app/services/support_metadata.py.
export const caseTypes = ['activation', 'lost_tag', 'payment', 'privacy', 'ownership_dispute', 'other'] as const;
export const caseStatuses = ['open', 'investigating', 'resolved', 'closed'] as const;
export const casePriorities = ['low', 'normal', 'high', 'urgent'] as const;
export type CaseMetadata = { case_id: string; case_type: typeof caseTypes[number]; status: typeof caseStatuses[number]; priority: typeof casePriorities[number]; case_revision: number; created_at: string; assignment: 'mine' | 'unassigned'; assigned_to_me: boolean };
export type CaseDetail = CaseMetadata & { content_available: false };
export type CaseEvent = { event_id: string; case_revision: number; event_type: 'created' | 'claimed' | 'updated'; from_status: typeof caseStatuses[number] | null; to_status: typeof caseStatuses[number]; priority: typeof casePriorities[number]; created_at: string };
export type CasePage = { as_of: string; items: CaseMetadata[]; next_cursor: string | null };
export type CaseHistory = { case_id: string; case_revision: number; items: CaseEvent[]; next_cursor: string | null };
export type MetadataKind = 'list' | 'detail' | 'history';
function invalid(): never { throw Error('Invalid support metadata'); }
function object(v: unknown, keys: string[]): Record<string, unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) invalid();
  const o = v as Record<string, unknown>;
  if (Object.keys(o).length !== keys.length || keys.some(k => !Object.hasOwn(o, k))) invalid();
  return o;
}
function one<const T extends readonly string[]>(v: unknown, values: T): T[number] { if (typeof v !== 'string' || !values.includes(v)) invalid(); return v as T[number]; }
export function caseId(v: unknown): string { if (typeof v !== 'string' || !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(v)) invalid(); return v.toLowerCase(); }
function revision(v: unknown): number { if (typeof v !== 'number' || !Number.isInteger(v) || v < 1 || v > 2147483647) invalid(); return v; }
function date(v: unknown): string { if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v) || !Number.isFinite(Date.parse(v))) invalid(); return v; }
function cursor(v: unknown): string | null { if (v === null) return null; if (typeof v !== 'string' || !/^[A-Za-z0-9_-]{40,2000}$/.test(v)) invalid(); return v; }
const fields = ['case_id','case_type','status','priority','case_revision','created_at','assignment','assigned_to_me'];
function row(raw: unknown, detail = false): CaseMetadata {
  const o = object(raw, detail ? [...fields, 'content_available'] : fields);
  const assignment = one(o.assignment, ['mine','unassigned']) as CaseMetadata['assignment'];
  if (typeof o.assigned_to_me !== 'boolean' || o.assigned_to_me !== (assignment === 'mine') || detail && o.content_available !== false) invalid();
  return {case_id: caseId(o.case_id), case_type: one(o.case_type, caseTypes), status: one(o.status, caseStatuses), priority: one(o.priority, casePriorities), case_revision: revision(o.case_revision), created_at: date(o.created_at), assignment, assigned_to_me: o.assigned_to_me};
}
export function supportDetail(raw: unknown): CaseDetail { return {...row(raw, true), content_available: false}; }
export function supportPage(raw: unknown, limit = 20): CasePage {
  const o = object(raw, ['as_of','items','next_cursor']);
  if (!Array.isArray(o.items) || o.items.length > limit) invalid();
  const items = o.items.map(i => row(i)), next = cursor(o.next_cursor);
  if (new Set(items.map(i => i.case_id)).size !== items.length || next && !items.length) invalid();
  return {as_of: date(o.as_of), items, next_cursor: next};
}
export function supportHistory(raw: unknown, limit = 20): CaseHistory {
  const o = object(raw, ['case_id','case_revision','items','next_cursor']);
  if (!Array.isArray(o.items) || o.items.length > limit) invalid();
  const current = revision(o.case_revision);
  const items = o.items.map(raw => {
    const e = object(raw, ['event_id','case_revision','event_type','from_status','to_status','priority','created_at']);
    return {event_id: caseId(e.event_id), case_revision: revision(e.case_revision), event_type: one(e.event_type, ['created','claimed','updated']), from_status: e.from_status === null ? null : one(e.from_status, caseStatuses), to_status: one(e.to_status, caseStatuses), priority: one(e.priority, casePriorities), created_at: date(e.created_at)};
  });
  const next = cursor(o.next_cursor);
  if (new Set(items.map(e => e.event_id)).size !== items.length || items.some((e,i) => e.case_revision > current || i > 0 && e.case_revision >= items[i-1].case_revision) || next && !items.length) invalid();
  return {case_id: caseId(o.case_id), case_revision: current, items, next_cursor: next};
}
export function supportQuery(p: URLSearchParams, kind: MetadataKind = 'list') {
  if (p.toString().length > 4096) invalid();
  const q = new URLSearchParams();
  for (const [k,v] of p) {
    if (p.getAll(k).length !== 1 || kind === 'detail') invalid();
    if (k === 'limit') { if (!/^[1-9][0-9]{0,2}$/.test(v) || Number(v) > 100) invalid(); }
    else if (k === 'cursor') cursor(v);
    else if (kind !== 'list') invalid();
    else if (k === 'case_id') caseId(v);
    else if (k === 'case_type') one(v, caseTypes);
    else if (k === 'status') one(v, caseStatuses);
    else if (k === 'priority') one(v, casePriorities);
    else if (k === 'queue') one(v, ['all','mine','unassigned']);
    else invalid();
    q.set(k,v);
  }
  return q;
}
export class SupportMetadataError extends Error { constructor(public status: number) { super('Support metadata unavailable'); } }
export function supportError(error: unknown) {
  const status = error instanceof SupportMetadataError ? error.status : 503;
  return status === 401 ? 'Sign in again to view support metadata.' : status === 403 ? 'Access denied. Explicit Support role, verified email and MFA are required.' : status === 404 ? 'Case not found or outside your assignment scope.' : status === 409 ? 'Case revision changed. Refresh to restart history.' : status === 400 || status === 422 ? 'Invalid filters or cursor. Refresh from the first page.' : status === 429 ? 'Request limit reached. Wait before refreshing.' : 'Support metadata unavailable or response invalid. Try again later.';
}
// This calls only the same-origin relay. Its independent server gate is authoritative.
export async function fetchSupport(kind: MetadataKind, params: URLSearchParams, id?: string, signal?: AbortSignal): Promise<CasePage | CaseDetail | CaseHistory> {
  let q: URLSearchParams, path = '/admin/support/metadata-api';
  try { q = supportQuery(params,kind); if (kind !== 'list') path += '/' + caseId(id) + (kind === 'history' ? '/history' : ''); }
  catch { throw new SupportMetadataError(422); }
  const r = await fetch(path + (q.size ? '?' + q : ''), {method: 'GET', cache: 'no-store', redirect: 'error', signal: signal ?? AbortSignal.timeout(15000)});
  if (!r.ok) throw new SupportMetadataError(r.status);
  const raw: unknown = await r.json(), limit = Number(q.get('limit') ?? 20);
  const result = kind === 'list' ? supportPage(raw,limit) : kind === 'detail' ? supportDetail(raw) : supportHistory(raw,limit);
  if (kind !== 'list' && 'case_id' in result && result.case_id !== caseId(id)) throw new SupportMetadataError(503);
  return result;
}
