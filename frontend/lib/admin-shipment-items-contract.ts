// One metadata-only endpoint; no discovery, order, print or mutation clients.
export type ShipmentItem = {
    logical_item_id: string;
    print_job_id: string;
    packed_qa_confirmed: boolean;
    packed_at: string | null;
};
export type ShipmentItems = {
    commerce_model: 'single_qr' | 'legacy_pair';
    items: ShipmentItem[];
};
function bad(): never { throw Error('Invalid shipment metadata contract'); }
export function shipmentId(v: unknown) { if (typeof v !== 'string' || !(/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(v)))
    bad(); return v as string; }
function object(v: unknown, keys: string[]) { if (!v || typeof v !== 'object' || Array.isArray(v))
    bad(); const o = v as Record<string, unknown>; if (Object.keys(o).length !== keys.length || keys.some(k => !Object.hasOwn(o, k)))
    bad(); return o; }
export function shipmentItems(v: unknown): ShipmentItems { const p = object(v, ['commerce_model', 'items']); if (!['single_qr', 'legacy_pair'].includes(p.commerce_model as string) || !Array.isArray(p.items) || p.items.length > 1000)
    bad(); const items = p.items.map(v => { const i = object(v, ['logical_item_id', 'print_job_id', 'packed_qa_confirmed', 'packed_at']); if (typeof i.packed_qa_confirmed !== 'boolean')
    bad(); let at: string | null = null; if (i.packed_at !== null) {
    if (typeof i.packed_at !== 'string' || i.packed_at.length > 40 || !(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(i.packed_at)) || !Number.isFinite(Date.parse(i.packed_at)))
        bad();
    at = i.packed_at;
} if (i.packed_qa_confirmed && at === null)
    bad(); return { logical_item_id: shipmentId(i.logical_item_id), print_job_id: shipmentId(i.print_job_id), packed_qa_confirmed: i.packed_qa_confirmed as boolean, packed_at: at }; }); if (new Set(items.map(i => i.logical_item_id)).size !== items.length || p.commerce_model === 'legacy_pair' && items.length)
    bad(); return { commerce_model: p.commerce_model as ShipmentItems['commerce_model'], items }; }
