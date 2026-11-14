// Closed read-only payments contract. No verification or reconciliation targets.
export const maxEvidenceBytes = 5000000;
export const evidenceTypes = ['image/png', 'image/jpeg', 'application/pdf'] as const;
export type Evidence = {
    id: string;
    content_type: string;
    bytes_size: number;
};
export type Attempt = {
    attempt_id: string;
    state: string;
    amount: string;
    currency_code: string;
    evidence: Evidence[];
};
function bad(): never { throw Error('Invalid payments contract'); }
export function uuid(v: unknown) { if (typeof v !== 'string' || !(/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(v)))
    bad(); return v as string; }
function object(v: unknown) { if (!v || typeof v !== 'object' || Array.isArray(v))
    bad(); return v as Record<string, unknown>; }
function exact(o: Record<string, unknown>, fields: string[]) { if (Object.keys(o).length !== fields.length || fields.some(k => !Object.hasOwn(o, k)))
    bad(); }
function str(v: unknown, max: number) { if (typeof v !== 'string' || !v.length || v.length > max || /[\x00-\x1f\x7f]/.test(v))
    bad(); return v as string; }
function evidence(v: unknown): Evidence { const o = object(v); exact(o, ['id', 'content_type', 'bytes_size']); if (!evidenceTypes.includes(o.content_type as typeof evidenceTypes[number]) || !Number.isSafeInteger(o.bytes_size) || Number(o.bytes_size) < 1 || Number(o.bytes_size) > maxEvidenceBytes)
    bad(); return { id: uuid(o.id), content_type: o.content_type as string, bytes_size: o.bytes_size as number }; }
export function attempts(raw: unknown, backend = false): {
    items: Attempt[];
} {
    const p = object(raw);
    exact(p, ['items']);
    if (!Array.isArray(p.items) || p.items.length > 100)
        bad();
    const items = p.items.map(v => {
        const o = object(v);
        exact(o, ['attempt_id', 'state', 'amount', 'currency_code', 'evidence', ...(backend ? ['sender_account', 'sender_holder'] : [])]);
        if (backend) {
            if (o.sender_account !== null)
                str(o.sender_account, 400);
            const holder = object(o.sender_holder);
            if (Object.keys(holder).some(k => !['holder', 'transfer_reference'].includes(k)))
                bad();
            for (const value of Object.values(holder))
                if (value !== null)
                    str(value, 1000);
        }
        const state = str(o.state, 32), amount = str(o.amount, 24), currency = str(o.currency_code, 3);
        if (!['initiated', 'submitted', 'under_review', 'verified', 'rejected', 'expired', 'refunded', 'disputed'].includes(state) || !/^\d{1,10}\.[0-9]{2}$/.test(amount) || !(/^[A-Z]{3}$/.test(currency)) || !Array.isArray(o.evidence) || o.evidence.length > 1000)
            bad();
        const ev = o.evidence.map(evidence);
        if (new Set(ev.map(e => e.id)).size !== ev.length)
            bad();
        return { attempt_id: uuid(o.attempt_id), state, amount, currency_code: currency, evidence: ev };
    });
    if (new Set(items.map(a => a.attempt_id)).size !== items.length)
        bad();
    return { items };
}
export function paymentTarget(p: URLSearchParams) { const kind = p.get('kind'); if (kind !== 'attempts' && kind !== 'evidence' || p.size !== 2 || p.getAll('kind').length !== 1 || p.getAll('id').length !== 1)
    bad(); const id = uuid(p.get('id')); return kind === 'attempts' ? '/admin/orders/' + id + '/payment-attempts' : '/admin/payment-evidence/' + id; }
export function safeEvidence(data: Uint8Array, type: string) {
    if (!data.length || data.length > maxEvidenceBytes || !evidenceTypes.includes(type as typeof evidenceTypes[number]))
        bad();
    const starts = (bytes: number[]) => bytes.every((b, i) => data[i] === b);
    const ends = (bytes: number[]) => bytes.every((b, i) => data[data.length - bytes.length + i] === b);
    if (type === 'image/png' && (!starts([137, 80, 78, 71, 13, 10, 26, 10]) || !ends([73, 69, 78, 68, 174, 66, 96, 130])))
        bad();
    if (type === 'image/jpeg' && (!starts([255, 216, 255]) || !ends([255, 217])))
        bad();
    if (type === 'application/pdf') {
        const text = new TextDecoder('latin1').decode(data);
        if (!text.startsWith('%PDF-') || !text.trimEnd().endsWith('%%EOF') || /\/(?:javascript|js|launch|embeddedfile|openaction|aa)/i.test(text))
            bad();
    }
}
