// Closed template metadata/synthetic-proof contract. No production print/QR paths.
import { uuid } from './admin-products-contract';
export { uuid };
export type Purpose = 'lost' | 'ice';
export type TemplateRecord = {
    template_id: string;
    key: string;
    name: string;
    purpose: Purpose;
    lifecycle_status: 'draft' | 'active' | 'retired';
    row_version: number;
    created_at: string;
};
export type Design = {
    schema_version: 1;
    renderer: 'safereturn-vector-v1';
    preset: 'fixed-footer-v1';
    symbol_mm: string;
    width_mm: string;
    height_mm: string;
    qr_x_mm: string;
    qr_y_mm: string;
    logo_mm: string;
    min_pitch_mm: string;
    font_pt: string;
    header: string;
    english_lines: string[];
    urdu_lines: string[];
    asset_set_id: string;
    material_codes: string[];
};
export type Revision = {
    revision_id: string;
    template_id: string;
    version: number;
    status: 'draft' | 'pending_qa' | 'published' | 'retired';
    row_version: number;
    content: Design;
    fingerprint_sha256: string | null;
    created_at: string;
    published_at: string | null;
};
export type Binding = {
    binding_id: string;
    variant_id: string;
    tag_type: Purpose;
    revision_id: string;
    is_active: boolean;
    row_version: number;
    created_at: string;
};
export type TemplatePage = {
    items: TemplateRecord[];
    next_cursor: string | null;
    as_of: string;
};
export type Detail = {
    template: TemplateRecord;
    revisions: Revision[];
    next_cursor: string | null;
};
export type BindingPage = {
    items: Binding[];
    next_cursor: string | null;
    as_of: string;
};
export type Receipt<T> = {
    command_id: string;
    result: T;
};
export class TemplateValidation extends Error {
    constructor(public field: string) { super('Invalid ' + field); }
}
function bad(field: string): never { throw new TemplateValidation(field); }
export function object(v: unknown): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v))
    bad('body'); return v as Record<string, unknown>; }
export function exact(o: Record<string, unknown>, keys: string[]) { if (Object.keys(o).length !== keys.length || keys.some(k => !Object.hasOwn(o, k)))
    bad('fields'); }
function text(v: unknown, field: string, max: number, min = 1) { if (typeof v !== 'string' || v.length > max || v.trim().length < min)
    bad(field); return v as string; }
export function plain(v: unknown, field: string, max: number, min = 1) { const s = text(v, field, max, min); if (/[\x00-\x1f\x7f<>{}\\`]/.test(s) || /[a-z][a-z0-9+.-]*\s*:|javascript|@import|url\s*\(|\$\(/i.test(s))
    bad(field); return s; }
function one<const T extends string>(v: unknown, options: readonly T[], field = 'status'): T { if (!options.includes(v as T))
    bad(field); return v as T; }
export function positive(v: unknown) { if (!Number.isSafeInteger(v) || Number(v) < 1)
    bad('version'); return v as number; }
function stamp(v: unknown) { const s = text(v, 'timestamp', 40); if (!/^\d{4}-\d{2}-\d{2}T/.test(s) || !Number.isFinite(Date.parse(s)))
    bad('timestamp'); return s; }
export function cursor(v: unknown): string | null { if (v === null)
    return null; const s = text(v, 'cursor', 1024); if (!/^[A-Za-z0-9_-]+={0,2}$/.test(s))
    bad('cursor'); return s; }
export function design(v: unknown): Design {
    const o = object(v), dims = ['symbol_mm', 'width_mm', 'height_mm', 'qr_x_mm', 'qr_y_mm', 'logo_mm', 'min_pitch_mm', 'font_pt'];
    exact(o, ['schema_version', 'renderer', 'preset', ...dims, 'header', 'english_lines', 'urdu_lines', 'asset_set_id', 'material_codes']);
    if (o.schema_version !== 1 || o.renderer !== 'safereturn-vector-v1' || o.preset !== 'fixed-footer-v1')
        bad('renderer');
    const n: Record<string, number> = {};
    for (const key of dims) {
        if (typeof o[key] !== 'string' || !/^\d{1,3}\.\d{2}$/.test(o[key] as string))
            bad(key);
        n[key] = Number(o[key]);
        if (n[key] <= 0 || n[key] > 270)
            bad(key);
    }
    if (n.symbol_mm < 30 || n.symbol_mm > 100 || n.width_mm < 40 || n.width_mm > 190 || n.height_mm < 60 || n.qr_x_mm < 4 || n.qr_y_mm < 18 || n.logo_mm > 6 || n.min_pitch_mm < 0.3 || n.font_pt < 8 || n.font_pt > 14)
        bad('geometry');
    for (const key of ['english_lines', 'urdu_lines']) {
        if (!Array.isArray(o[key]) || (o[key] as unknown[]).length < 1 || (o[key] as unknown[]).length > 4)
            bad(key);
        (o[key] as unknown[]).forEach(v => plain(v, key, 120));
    }
    if ((o.urdu_lines as string[]).some(s => /[A-Za-z0-9]/.test(s)))
        bad('urdu_lines');
    if (n.qr_x_mm + n.symbol_mm > n.width_mm - 4 || n.qr_y_mm + n.symbol_mm > n.height_mm - 12 || n.logo_mm > n.symbol_mm * 0.15 || n.qr_y_mm - 4 - n.font_pt * 1.5 / 2.8346456693 * ((o.english_lines as string[]).length + (o.urdu_lines as string[]).length - 1) < 4)
        bad('geometry');
    if (!Array.isArray(o.material_codes) || o.material_codes.length < 1 || o.material_codes.length > 10 || o.material_codes.some(v => typeof v !== 'string' || !(/^[a-z0-9_-]{1,40}$/.test(v))) || JSON.stringify(o.material_codes) !== JSON.stringify([...new Set(o.material_codes)].sort()))
        bad('material_codes');
    uuid(o.asset_set_id);
    plain(o.header, 'header', 50);
    return { ...o } as unknown as Design;
}
export function createBody(v: unknown) { const o = object(v); exact(o, ['key', 'name', 'purpose']); const key = text(o.key, 'key', 80, 3); if (!/^[A-Za-z0-9._-]+$/.test(key))
    bad('key'); return { key, name: plain(o.name, 'name', 100), purpose: one(o.purpose, ['lost', 'ice'], 'purpose') }; }
export type Action = 'qa' | 'qa-decision' | 'list' | 'create' | 'detail' | 'revision' | 'edit' | 'preview' | 'submit' | 'retire' | 'bindings' | 'bind' | 'products' | 'product';
const id = '[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}';
export function templateTarget(path: string, method: string): Action {
    const qa = path.match(new RegExp('^/admin/print-templates/' + id + '/revisions/' + id + '/(qa|qa-decision)$'));
    if (qa && method === (qa[1] === 'qa' ? 'GET' : 'POST')) return qa[1] as Action;
    if (path === '/admin/print-templates' && ['GET', 'POST'].includes(method))
        return method === 'GET' ? 'list' : 'create';
    if (path === '/admin/print-template-bindings' && ['GET', 'POST'].includes(method))
        return method === 'GET' ? 'bindings' : 'bind';
    if (method === 'GET' && path === '/admin/products')
        return 'products';
    if (method === 'GET' && new RegExp('^/admin/products/' + id + '$').test(path))
        return 'product';
    if (method === 'GET' && new RegExp('^/admin/print-templates/' + id + '$').test(path))
        return 'detail';
    if (method === 'POST' && new RegExp('^/admin/print-templates/' + id + '/revisions$').test(path))
        return 'revision';
    const m = path.match(new RegExp('^/admin/print-templates/' + id + '/revisions/' + id + '(?:/(preview|submit-qa|retire))?$'));
    if (m && method === (m[1] ? 'POST' : 'PATCH'))
        return m[1] === 'preview' ? 'preview' : m[1] === 'submit-qa' ? 'submit' : m[1] === 'retire' ? 'retire' : 'edit';
    // Publish deliberately absent: no evidence/publisher discovery available to this UI.
    bad('route');
}
export function templateBody(action: Action, v: unknown) {
    if (action === 'create')
        return createBody(v);
    if (action === 'qa-decision') {
        const o = object(v); exact(o, ['decision', 'reason', 'expected_review_version', 'envelope', 'confirmed']);
        if (o.confirmed !== true || !Number.isSafeInteger(o.expected_review_version) || Number(o.expected_review_version) < 0) bad('confirmation');
        const decision = one(o.decision, ['approved', 'rejected']);
        if (decision === 'approved' ? !o.envelope : o.envelope !== null) bad('evidence');
        return { decision, reason: plain(o.reason, 'reason', 500, 4), expected_review_version: o.expected_review_version, envelope: o.envelope === null ? null : object(o.envelope), confirmed: true };
    }
    const o = object(v);
    if (action === 'revision' || action === 'edit') {
        exact(o, action === 'revision' ? ['content', 'version_note', 'base_revision_id'] : ['content', 'version_note']);
        const b = { content: design(o.content), version_note: plain(o.version_note, 'version_note', 500, 4) };
        return action === 'revision' ? { ...b, base_revision_id: o.base_revision_id === null ? null : uuid(o.base_revision_id) } : b;
    }
    if (action === 'preview') {
        exact(o, ['expected_revision']);
        return { expected_revision: positive(o.expected_revision) };
    }
    if (action === 'submit') {
        exact(o, ['reason']);
        return { reason: plain(o.reason, 'reason', 500, 4) };
    }
    if (action === 'retire') {
        exact(o, ['reason', 'confirmed']);
        if (o.confirmed !== true)
            bad('confirmed');
        return { reason: plain(o.reason, 'reason', 500, 4), confirmed: true };
    }
    if (action === 'bind') {
        exact(o, ['variant_id', 'tag_type', 'revision_id', 'expected_variant_version', 'expected_binding_id', 'confirmed']);
        if (o.confirmed !== true || o.revision_id === null && o.expected_binding_id === null)
            bad('confirmed');
        return { variant_id: uuid(o.variant_id), tag_type: one(o.tag_type, ['lost', 'ice']), revision_id: o.revision_id === null ? null : uuid(o.revision_id), expected_variant_version: positive(o.expected_variant_version), expected_binding_id: o.expected_binding_id === null ? null : uuid(o.expected_binding_id), confirmed: true };
    }
    bad('action');
}
export function templateRecord(v: unknown): TemplateRecord { const o = object(v); exact(o, ['template_id', 'key', 'name', 'purpose', 'lifecycle_status', 'row_version', 'created_at']); return { template_id: uuid(o.template_id), ...createBody({ key: o.key, name: o.name, purpose: o.purpose }), lifecycle_status: one(o.lifecycle_status, ['draft', 'active', 'retired']), row_version: positive(o.row_version), created_at: stamp(o.created_at) }; }
export function revisionRecord(v: unknown): Revision { const o = object(v); exact(o, ['revision_id', 'template_id', 'version', 'status', 'row_version', 'content', 'fingerprint_sha256', 'created_at', 'published_at']); if (o.fingerprint_sha256 !== null && (typeof o.fingerprint_sha256 !== 'string' || !(/^[a-f0-9]{64}$/.test(o.fingerprint_sha256))))
    bad('fingerprint'); const version = positive(o.version); if (version > 100000)
    bad('version'); return { revision_id: uuid(o.revision_id), template_id: uuid(o.template_id), version, status: one(o.status, ['draft', 'pending_qa', 'published', 'retired']), row_version: positive(o.row_version), content: design(o.content), fingerprint_sha256: o.fingerprint_sha256 as string | null, created_at: stamp(o.created_at), published_at: o.published_at === null ? null : stamp(o.published_at) }; }
export function bindingRecord(v: unknown): Binding { const o = object(v); exact(o, ['binding_id', 'variant_id', 'tag_type', 'revision_id', 'is_active', 'row_version', 'created_at']); if (typeof o.is_active !== 'boolean')
    bad('is_active'); return { binding_id: uuid(o.binding_id), variant_id: uuid(o.variant_id), tag_type: one(o.tag_type, ['lost', 'ice']), revision_id: uuid(o.revision_id), is_active: o.is_active, row_version: positive(o.row_version), created_at: stamp(o.created_at) }; }
function list<T>(v: unknown, parse: (v: unknown) => T): T[] { if (!Array.isArray(v) || v.length > 50)
    bad('items'); return v.map(parse); }
export function templateResult(action: Action, v: unknown): unknown {
    const o = object(v);
    if (action === 'qa') return qaRecord(v);
    if (action === 'qa-decision') { exact(o, ['command_id', 'result']); return { command_id: uuid(o.command_id), result: qaRecord(o.result) }; }
    if (action === 'list' || action === 'bindings') {
        exact(o, ['items', 'next_cursor', 'as_of']);
        return { items: action === 'list' ? list(o.items, templateRecord) : list(o.items, bindingRecord), next_cursor: cursor(o.next_cursor), as_of: stamp(o.as_of) };
    }
    if (action === 'detail') {
        exact(o, ['template', 'revisions', 'next_cursor']);
        const template = templateRecord(o.template), revisions = list(o.revisions, revisionRecord);
        if (revisions.some(r => r.template_id !== template.template_id))
            bad('template_id');
        return { template, revisions, next_cursor: cursor(o.next_cursor) };
    }
    exact(o, ['command_id', 'result']);
    const command_id = uuid(o.command_id), r = object(o.result);
    if (action === 'create')
        return { command_id, result: templateRecord(r) };
    if (action === 'edit')
        return { command_id, result: revisionRecord(r) };
    if (action === 'revision' || action === 'retire') {
        exact(r, ['template', 'revision']);
        const template = templateRecord(r.template), revision = revisionRecord(r.revision);
        if (template.template_id !== revision.template_id)
            bad('template_id');
        return { command_id, result: { template, revision } };
    }
    if (action === 'submit') {
        exact(r, ['revision', 'validation_status']);
        if (r.validation_status !== 'needs_independent_physical_qa')
            bad('validation_status');
        return { command_id, result: { revision: revisionRecord(r.revision), validation_status: r.validation_status } };
    }
    if (action === 'bind') {
        exact(r, ['binding', 'variant_row_version']);
        return { command_id, result: { binding: bindingRecord(r.binding), variant_row_version: positive(r.variant_row_version) } };
    }
    bad('result');
}
export function templateQuery(action: Action, p: URLSearchParams): URLSearchParams {
    const fields = action === 'list' ? ['purpose', 'status', 'limit', 'cursor'] : action === 'detail' ? ['revisions_limit', 'revisions_cursor'] : action === 'bindings' ? ['variant_id', 'tag_type', 'active', 'limit', 'cursor'] : action === 'products' ? ['limit', 'cursor'] : [];
    const out = new URLSearchParams();
    for (const [key, value] of p) {
        if (!fields.includes(key) || p.getAll(key).length !== 1)
            bad('query');
        if (key === 'limit' || key === 'revisions_limit') {
            if (!/^(?:[1-9][0-9]?|100)$/.test(value) || Number(value) > (action === 'products' ? 100 : 50))
                bad('limit');
        }
        else if (key === 'purpose' || key === 'tag_type')
            one(value, ['lost', 'ice']);
        else if (key === 'status')
            one(value, ['draft', 'active', 'retired']);
        else if (key === 'active')
            one(value, ['true', 'false']);
        else if (key === 'variant_id')
            uuid(value);
        else if (action === 'products')
            uuid(value);
        else
            cursor(value);
        out.set(key, value);
    }
    return out;
}

export type QAReview = { review_id: string; revision_id: string; revision_row_version: number; review_version: number; decision: 'approved' | 'rejected'; review_note: string; reviewer_user_id: string; reviewer_human_id: string; approval_id: string | null; decided_at: string };
export type QAState = { revision_id: string; revision_row_version: number; review_version: number; status: 'pending' | 'approved' | 'rejected'; can_review: boolean; history: QAReview[] };
export function qaRecord(value: unknown): QAState {
    const o = object(value); exact(o, ['revision_id', 'revision_row_version', 'review_version', 'status', 'can_review', 'history']);
    if (typeof o.can_review !== 'boolean' || !Number.isSafeInteger(o.review_version) || Number(o.review_version) < 0 || !Array.isArray(o.history) || o.history.length > 20) bad('qa');
    const revision_id = uuid(o.revision_id);
    const history = (o.history as unknown[]).map(value => {
        const r = object(value); exact(r, ['review_id', 'revision_id', 'revision_row_version', 'review_version', 'decision', 'review_note', 'reviewer_user_id', 'reviewer_human_id', 'approval_id', 'decided_at']);
        const decision = one(r.decision, ['approved', 'rejected']);
        if (r.revision_id !== revision_id || (decision === 'approved') !== (r.approval_id !== null)) bad('qa');
        return { review_id: uuid(r.review_id), revision_id, revision_row_version: positive(r.revision_row_version), review_version: positive(r.review_version), decision, review_note: plain(r.review_note, 'review_note', 500, 4), reviewer_user_id: uuid(r.reviewer_user_id), reviewer_human_id: uuid(r.reviewer_human_id), approval_id: r.approval_id === null ? null : uuid(r.approval_id), decided_at: stamp(r.decided_at) };
    });
    const status = one(o.status, ['pending', 'approved', 'rejected']);
    if ((history[0]?.review_version ?? 0) !== o.review_version || (history[0]?.decision ?? 'pending') !== status) bad('qa');
    return { revision_id, revision_row_version: positive(o.revision_row_version), review_version: o.review_version as number, status, can_review: o.can_review, history };
}
