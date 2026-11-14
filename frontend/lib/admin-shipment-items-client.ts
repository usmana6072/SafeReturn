import { shipmentId, shipmentItems } from './admin-shipment-items-contract';
export class ShipmentItemsError extends Error {
    constructor(public status: number) { super('Shipment metadata unavailable'); }
}
export function shipmentError(e: unknown) { const s = e instanceof ShipmentItemsError ? e.status : 503; return s === 401 ? 'Sign in again to view shipment item metadata.' : s === 403 ? 'Current Operations role and MFA are required.' : s === 404 ? 'Shipment not found or not accessible.' : s === 422 ? 'Enter a valid backend shipment UUID. No lookup was performed for an invalid ID.' : s === 429 ? 'Request limit reached; wait before refreshing.' : 'Shipment item metadata unavailable or response invalid. No demo fallback or shipment state is assumed.'; }
export async function fetchShipmentItems(id: string, signal?: AbortSignal) { try {
    shipmentId(id);
}
catch {
    throw new ShipmentItemsError(422);
} const r = await fetch('/admin/shipments/items-api?' + new URLSearchParams({ shipment_id: id }), { method: 'GET', cache: 'no-store', redirect: 'error', signal: signal ?? AbortSignal.timeout(15000) }); if (!r.ok)
    throw new ShipmentItemsError(r.status); return shipmentItems(await r.json()); }
