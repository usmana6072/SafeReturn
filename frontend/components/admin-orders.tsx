"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { fetchMetadata, historicalAmount, metadataError, orderStates, paymentStates, type OrderMetadata, type MetadataPage } from '../lib/admin-order-metadata';
import styles from './admin-orders.module.css';
export function OrderStateBadge({ value }: {
    value?: string;
    payment?: boolean;
}) { return <AdminStatusBadge label={value ?? 'Unknown'} variant={value === 'verified' || value === 'fulfilled' ? 'success' : 'neutral'}/>; }
const empty = { order_number: '', order_status: '', payment_status: '', created_from: '', created_before: '', sort: 'newest' };
export function AdminOrders({ orderId, ur = false }: {
    orderId?: string;
    ur?: boolean;
    liveConsoleAvailable?: boolean;
}) {
    const { authenticatedRoles } = useAdminRole(), allowed = authenticatedRoles.some(r => ['operations', 'finance'].includes(r));
    const [form, setForm] = useState(empty), [active, setActive] = useState(empty), [page, setPage] = useState<MetadataPage | null>(null), [history, setHistory] = useState<(string | undefined)[]>([undefined]), [selected, setSelected] = useState<OrderMetadata | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
    const request = useRef<AbortController | null>(null), sequence = useRef(0);
    async function load(filters = active, cursor?: string, stack: (string | undefined)[] = [undefined]) { request.current?.abort(); const ctrl = new AbortController(); request.current = ctrl; const seq = ++sequence.current; setBusy(true); setError(''); setPage(null); setSelected(null); try {
        const q = new URLSearchParams({ limit: '20' });
        for (const [k, v] of Object.entries(filters))
            if (v)
                q.set(k, v);
        if (cursor)
            q.set('cursor', cursor);
        const data = await fetchMetadata(q, ctrl.signal);
        if (seq !== sequence.current)
            return;
        setPage(data);
        setHistory(stack);
        setActive(filters);
    }
    catch (e) {
        if (seq === sequence.current && !ctrl.signal.aborted)
            setError(metadataError(e));
    }
    finally {
        if (seq === sequence.current)
            setBusy(false);
    } }
    useEffect(() => { if (orderId === undefined && allowed)
        void load(empty); return () => { request.current?.abort(); sequence.current++; }; }, [orderId, allowed]);
    const t = (en: string, u: string) => ur ? u : en;
    if (!allowed)
        return <p role="alert">Your authenticated role cannot view order metadata.</p>;
    if (orderId !== undefined)
        return <AdminPageContainer><h1>Order details unavailable</h1><p>Detailed order information is unavailable through the currently approved admin API integration.</p><p>Return to Orders and use an exact order-number lookup to view permitted summary fields.</p><Link href="/admin/orders" prefetch={false}>Back to Orders</Link></AdminPageContainer>;
    return <div className={styles.screen} dir={ur ? 'rtl' : 'ltr'}><AdminPageContainer><AdminPageHeader title={t('Orders & Sales', 'آرڈرز اور فروخت')} description="Stored order metadata · read only" badge={<AdminStatusBadge label="Backend metadata" variant="info"/>}/><p className={styles.notice}>Historical totals use stored amounts and explicit currency. Payment status is recorded state, not proof of settlement. Detailed order information is unavailable through the currently approved admin API integration.</p><AdminCard><form className={styles.toolbar} onSubmit={e => { e.preventDefault(); void load(form); }}>
 <label>Exact order number<input aria-label="Exact order number" value={form.order_number} maxLength={40} onChange={e => setForm({ ...form, order_number: e.target.value })}/></label>
 <label>Order status<select aria-label="Order status" value={form.order_status} onChange={e => setForm({ ...form, order_status: e.target.value })}><option value="">All</option>{orderStates.map(s => <option key={s}>{s}</option>)}</select></label><label>Payment status<select aria-label="Payment status" value={form.payment_status} onChange={e => setForm({ ...form, payment_status: e.target.value })}><option value="">All</option>{paymentStates.map(s => <option key={s}>{s}</option>)}</select></label>
 {(['created_from', 'created_before'] as const).map(k => <label key={k}>{k === 'created_from' ? 'Created from (inclusive RFC3339)' : 'Created before (exclusive RFC3339)'}<input aria-label={k} placeholder="2026-10-01T00:00:00Z" value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}/></label>)}
 <label>Sort<select aria-label="Sort" value={form.sort} onChange={e => setForm({ ...form, sort: e.target.value })}><option value="newest">Newest</option><option value="oldest">Oldest</option></select></label><button disabled={busy}>Apply filters</button><button type="button" disabled={busy} onClick={() => { setForm(empty); void load(empty); }}>Clear filters</button><button type="button" disabled={busy} onClick={() => void load(active)}>Refresh Orders</button></form>
 {busy && <p role="status">Loading order metadata…</p>}{error && <p role="alert" className={styles.notice}>{error}</p>}{page && <><p className={styles.footer}>Creation watermark: {page.as_of}. Statuses can change between pages.</p>{!page.items.length ? <AdminEmptyState title="No orders found" description="No records match the current filters."/> : <div className={styles.scroll} role="region" tabIndex={0} aria-label="Orders table"><table className={styles.ordersTable}><thead><tr>{['Order number / ID', 'Created', 'Order status', 'Payment status', 'Historical total', 'Actions'].map(s => <th key={s} scope="col">{s}</th>)}</tr></thead><tbody>{page.items.map(o => <tr key={o.order_id}><td className={styles.mono}><span>{o.order_number}</span><br />{o.order_id}</td><td>{o.created_at}</td><td><OrderStateBadge value={o.order_status}/></td><td><OrderStateBadge value={o.payment_status}/></td><td className={styles.money}>{historicalAmount(o)}</td><td><button onClick={() => setSelected(o)}>View summary</button></td></tr>)}</tbody></table></div>}<div className={styles.footer}><button disabled={busy || history.length < 2} onClick={() => { const previous = history.slice(0, -1); void load(active, previous.at(-1), previous); }}>Previous</button><button disabled={busy || !page.next_cursor} onClick={() => void load(active, page.next_cursor!, [...history, page.next_cursor!])}>Next</button></div></>}</AdminCard>
 {selected && <AdminCard><section className={styles.cardBody} aria-label="Order summary"><h2>Limited order summary</h2><dl className={styles.facts}>{[['Order ID', selected.order_id], ['Order number', selected.order_number], ['Created', selected.created_at], ['Placed', selected.placed_at ?? 'Not placed'], ['Order status', selected.order_status], ['Payment status', selected.payment_status], ['Historical total', historicalAmount(selected)]].map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl><p>Detailed order information is unavailable through the currently approved admin API integration.</p><button onClick={() => setSelected(null)}>Close summary</button></section></AdminCard>}</AdminPageContainer></div>;
}
