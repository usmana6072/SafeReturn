"use client";
import { useEffect, useRef, useState } from 'react';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { fetchMetadata, metadataError, type OrderMetadata } from '../lib/admin-order-metadata';
import { readAttempts, readEvidence, paymentReadError } from '../lib/admin-payments-client';
import { uuid, type Attempt, type Evidence } from '../lib/admin-payments-contract';
import styles from './admin-payments.module.css';
export function AdminPayments({ ur = false, orderId, attemptId }: {
    ur?: boolean;
    orderId?: string;
    attemptId?: string;
    liveConsoleAvailable?: boolean;
}) {
    const { authenticatedRoles } = useAdminRole(), allowed = authenticatedRoles.includes('finance');
    const [number, setNumber] = useState(''), [orders, setOrders] = useState<OrderMetadata[] | null>(null), [selected, setSelected] = useState<OrderMetadata | null>(null), [currentOrder, setCurrentOrder] = useState<string | null>(null), [items, setItems] = useState<Attempt[] | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [preview, setPreview] = useState<{
        url: string;
        type: string;
        id: string;
    } | null>(null);
    const controller = useRef<AbortController | null>(null), sequence = useRef(0), url = useRef<string | null>(null);
    function closePreview() { if (url.current)
        URL.revokeObjectURL(url.current); url.current = null; setPreview(null); }
    function start() { controller.current?.abort(); const ctrl = new AbortController(); controller.current = ctrl; const id = ++sequence.current; closePreview(); setBusy(true); setError(''); setNotice(''); return { ctrl, id }; }
    async function lookup(e: React.FormEvent) { e.preventDefault(); const { ctrl, id } = start(); setOrders(null); setSelected(null); setCurrentOrder(null); setItems(null); try {
        if (!number.length || number.length > 40)
            throw Error();
        const page = await fetchMetadata(new URLSearchParams({ order_number: number, limit: '20' }), ctrl.signal);
        if (id !== sequence.current)
            return;
        if (page.next_cursor)
            throw Error();
        setOrders(page.items);
    }
    catch (e) {
        if (id === sequence.current && !ctrl.signal.aborted)
            setError(metadataError(e));
    }
    finally {
        if (id === sequence.current)
            setBusy(false);
    } }
    async function load(order: string, summary: OrderMetadata | null) { const { ctrl, id } = start(); setSelected(summary); setCurrentOrder(order); setItems(null); try {
        uuid(order);
        const result = await readAttempts(order, ctrl.signal);
        if (id !== sequence.current)
            return;
        if (attemptId) {
            uuid(attemptId);
            const match = result.items.find(a => a.attempt_id === attemptId);
            if (!match) {
                setNotice('Attempt is not present in the returned records for this order. The API returns at most 100 attempts.');
                setItems([]);
                return;
            }
            setItems([match]);
        }
        else
            setItems(result.items);
    }
    catch (e) {
        if (id === sequence.current && !ctrl.signal.aborted)
            setError(paymentReadError(e));
    }
    finally {
        if (id === sequence.current)
            setBusy(false);
    } }
    async function view(e: Evidence) { const { ctrl, id } = start(); try {
        const blob = await readEvidence(e, ctrl.signal);
        if (id !== sequence.current)
            return;
        if (e.content_type === 'application/pdf') {
            setNotice('PDF transport was validated, but inline PDF viewing is unavailable under the current safe-viewer policy. No file is stored or publicly linked.');
            return;
        }
        const next = URL.createObjectURL(blob);
        url.current = next;
        setPreview({ url: next, type: e.content_type, id: e.id });
    }
    catch (e) {
        if (id === sequence.current && !ctrl.signal.aborted)
            setError(paymentReadError(e));
    }
    finally {
        if (id === sequence.current)
            setBusy(false);
    } }
    useEffect(() => { if (allowed && orderId)
        void load(orderId, null); return () => { controller.current?.abort(); sequence.current++; if (url.current)
        URL.revokeObjectURL(url.current); }; }, [allowed, orderId, attemptId]);
    if (!allowed)
        return <p role="alert">Current Finance role and MFA are required for payment records.</p>;
    return <div className={styles.screen} dir={ur ? 'rtl' : 'ltr'}><AdminPageContainer><AdminPageHeader title={ur ? 'ادائیگیاں اور مالی مطابقت' : 'Payments & Reconciliation'} description="Recorded attempts and private evidence · read only" badge={<AdminStatusBadge label="Backend reads" variant="info"/>}/><p className={styles.notice}>An uploaded receipt or recorded verified state does not establish bank settlement. Amounts and currencies are stored backend values; no conversion or current catalog recalculation.</p>
 {!orderId && <AdminCard><form onSubmit={lookup} className={styles.toolbar}><label>Exact order number<input aria-label="Exact order number" required maxLength={40} value={number} onChange={e => setNumber(e.target.value)}/></label><button disabled={busy} className={styles.primary}>Find Payment by Order</button></form>{orders && <section className={styles.body}>{!orders.length ? <AdminEmptyState title="Order not found" description="No exact order-number match in the permitted metadata response."/> : orders.map(o => <div className={styles.actions} key={o.order_id}><span>{o.order_number} · {o.currency_code} {o.total_amount}</span><button disabled={busy} onClick={() => void load(o.order_id, o)}>View payment attempts</button></div>)}</section>}</AdminCard>}
 {busy && <p role="status">Loading protected payment records…</p>}{error && <p role="alert" className={styles.notice}>{error}</p>}{notice && <p role="status" className={styles.notice}>{notice}</p>}
 {currentOrder && <AdminCard><section className={styles.body}><h2>Payment attempts</h2><p className={styles.mono}>Order {selected?.order_number ?? currentOrder}</p>{selected && <p>Stored order total: {selected.currency_code} {selected.total_amount}</p>}<p>At most 100 attempts, newest first. This is not a global queue or a complete paginated history. No attempt timestamp, payment method or rejection reason is supplied by this API.</p><button disabled={busy} onClick={() => void load(currentOrder, selected)}>Refresh Records</button></section>{items && (!items.length ? <AdminEmptyState title="No payment attempts returned" description="No attempts are available in this bounded response; no settlement is inferred."/> : <div className={styles.scroll} tabIndex={0} role="region" aria-label="Payment attempts"><table><thead><tr>{['Attempt ID', 'Recorded state', 'Recorded amount', 'Evidence'].map(k => <th scope="col" key={k}>{k}</th>)}</tr></thead><tbody>{items.map(a => <tr key={a.attempt_id}><td className={styles.mono}>{a.attempt_id}</td><td><AdminStatusBadge label={a.state}/></td><td className={styles.amount}>{a.currency_code} {a.amount}</td><td>{!a.evidence.length ? 'No evidence returned' : a.evidence.map(e => <div key={e.id}><span className={styles.mono}>{e.id}</span><p>{e.content_type} · {e.bytes_size} bytes</p><button disabled={busy} onClick={() => void view(e)}>View evidence</button></div>)}</td></tr>)}</tbody></table></div>)}</AdminCard>}
 {preview && <AdminCard><section className={styles.body} aria-label="Private evidence preview"><h2>Private evidence · unverified receipt</h2><p className={styles.mono}>{preview.id}</p><img src={preview.url} alt="Private payment evidence; not proof of settlement" referrerPolicy="no-referrer" style={{ maxWidth: '100%', maxHeight: '65vh', objectFit: 'contain' }}/><button onClick={closePreview}>Close evidence</button><p>Preview remains in browser memory and is revoked when closed, refreshed or replaced.</p></section></AdminCard>}
 <AdminCard><section className={styles.body} aria-label="Reconciliation unavailable"><h2>Reconciliation unavailable</h2><p>Reconciliation signals and counts are excluded because their current backend implementation inspects QR-pair allocation. No reconciliation request is sent. Counts, filters, bank feeds and settlement actions are unavailable.</p></section></AdminCard>
 </AdminPageContainer></div>;
}
