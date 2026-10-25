"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { fetchShipmentItems, shipmentError } from '../lib/admin-shipment-items-client';
import type { ShipmentItems } from '../lib/admin-shipment-items-contract';
import styles from './admin-shipments.module.css';
export function AdminShipments({ shipmentId, ur = false }: {
    shipmentId?: string;
    ur?: boolean;
}) {
    const { authenticatedRoles } = useAdminRole(), allowed = authenticatedRoles.includes('operations');
    const [input, setInput] = useState(shipmentId ?? ''), [shown, setShown] = useState(''), [data, setData] = useState<ShipmentItems | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
    const controller = useRef<AbortController | null>(null), sequence = useRef(0);
    async function load(id: string) { controller.current?.abort(); const ctrl = new AbortController(); controller.current = ctrl; const seq = ++sequence.current; setBusy(true); setData(null); setError(''); try {
        const result = await fetchShipmentItems(id, ctrl.signal);
        if (seq !== sequence.current)
            return;
        setData(result);
        setShown(id);
    }
    catch (e) {
        if (seq === sequence.current && !ctrl.signal.aborted)
            setError(shipmentError(e));
    }
    finally {
        if (seq === sequence.current)
            setBusy(false);
    } }
    useEffect(() => { if (allowed && shipmentId !== undefined) {
        setInput(shipmentId);
        void load(shipmentId);
    } return () => { controller.current?.abort(); sequence.current++; }; }, [allowed, shipmentId]);
    if (!allowed)
        return <p role="alert">Current Operations role and MFA are required for shipment item metadata.</p>;
    return <div className={styles.screen} dir={ur ? 'rtl' : 'ltr'}><AdminPageContainer><AdminPageHeader title={ur ? 'ترسیل کی آئٹم معلومات' : 'Shipment Item Metadata'} description="Read-only metadata for an already-known shipment UUID" badge={<AdminStatusBadge label="Backend items only" variant="info"/>} actions={shipmentId !== undefined ? <Link href="/admin/shipments" prefetch={false}>Back to shipment lookup</Link> : undefined}/>
 <p className={styles.notice}>Shipment listing is unavailable because its current backend projection inspects prohibited QR-pair membership and fulfillment eligibility. No list request is sent.</p>
 <AdminCard><form className={styles.toolbar} onSubmit={e => { e.preventDefault(); void load(input); }}><label>Known shipment UUID<input aria-label="Known shipment UUID" required value={input} onChange={e => setInput(e.target.value)}/></label><button disabled={busy} className={styles.primary}>View Shipment Items</button>{shown && <button type="button" disabled={busy} onClick={() => void load(shown)}>Refresh Shipment Items</button>}</form></AdminCard>
 {busy && <p role="status">Loading shipment item metadata…</p>}{error && <p role="alert" className={styles.notice}>{error}</p>}
 {data && <AdminCard><section className={styles.body} aria-label="Shipment item summary"><h2>Shipment item context</h2><dl className={styles.facts}><div><dt>Shipment UUID</dt><dd>{shown}</dd></div><div><dt>Metadata scope</dt><dd>{data.commerce_model === 'single_qr' ? 'Logical shipment items' : 'Legacy shipment; logical item metadata is not a complete membership view'}</dd></div></dl><p>Shipment status, related order, carrier/tracking, customer delivery data, dispatch/delivery times and activity history are not supplied by this endpoint. They remain unavailable.</p><p>Recorded packing confirmation is not QR-pair QA approval, dispatch, delivery, readiness or permission to change any state. Print-job references are text only; no artwork is requested.</p></section>{data.commerce_model === 'legacy_pair' ? <AdminEmptyState title="Logical item view unavailable for this membership model" description="An empty logical item response does not establish that the shipment has no members. No pair membership is requested."/> : !data.items.length ? <AdminEmptyState title="No shipment item metadata returned" description="No status, physical quantity, readiness or identity count is inferred from an empty response."/> : <div className={styles.scroll} role="region" aria-label="Shipment items" tabIndex={0}><table><thead><tr>{['Logical item ID', 'Print-job reference', 'Recorded packing confirmation', 'Recorded packed at'].map(k => <th key={k} scope="col">{k}</th>)}</tr></thead><tbody>{data.items.map(i => <tr key={i.logical_item_id}><td className={styles.mono}>{i.logical_item_id}</td><td className={styles.mono}>{i.print_job_id}</td><td><AdminStatusBadge label={i.packed_qa_confirmed ? 'Confirmed (recorded)' : 'Not confirmed (recorded)'} variant="neutral"/></td><td>{i.packed_at ?? 'Not recorded'}</td></tr>)}</tbody></table></div>}</AdminCard>}
 </AdminPageContainer></div>;
}
