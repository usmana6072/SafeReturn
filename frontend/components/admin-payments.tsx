"use client";
import { useEffect, useRef, useState } from 'react';
import { IndependentFinance } from './independent-finance';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { fetchMetadata, metadataError, type OrderMetadata } from '../lib/admin-order-metadata';
import { readAttempts, readEvidence, paymentReadError, reviewPayment } from '../lib/admin-payments-client';
import { uuid, type Attempt, type Evidence } from '../lib/admin-payments-contract';
import styles from './admin-payments.module.css';
export function AdminPayments({ ur = false, orderId, attemptId }: {
    ur?: boolean;
    orderId?: string;
    attemptId?: string;
    liveConsoleAvailable?: boolean;
}) {
    const { authenticatedRoles } = useAdminRole(), allowed = authenticatedRoles.includes('finance');
    const [number, setNumber] = useState(''), [orders, setOrders] = useState<OrderMetadata[] | null>(null), [selected, setSelected] = useState<OrderMetadata | null>(null), [currentOrder, setCurrentOrder] = useState<string | null>(null), [items, setItems] = useState<Attempt[] | null>(null), [busy, setBusy] = useState(false), [processingId, setProcessingId] = useState<string | null>(null), [review, setReview] = useState<{
        attemptId: string;
        decision: 'verify' | 'reject';
        bankReference: string;
        reason: string;
        bankVerified: boolean;
    } | null>(null), [error, setError] = useState(''), [notice, setNotice] = useState(''), [preview, setPreview] = useState<{
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
    function openReview(attempt: Attempt, decision: 'verify' | 'reject') {
        setError('');
        setNotice('');
        if (review?.attemptId === attempt.attempt_id && review.decision === decision)
            return;
        setReview({
            attemptId: attempt.attempt_id,
            decision,
            bankReference: '',
            reason: decision === 'verify' ? 'Bank settlement verified by finance' : 'Payment rejected during finance review',
            bankVerified: false,
        });
    }
    async function submitReview(event: React.FormEvent) {
        event.preventDefault();
        if (!review || processingId) return;
        const attempt = items?.find(item => item.attempt_id === review.attemptId);
        if (!attempt) return;
        const current = review;
        setProcessingId(current.attemptId);
        setError('');
        setNotice('');
        try {
            const result = await reviewPayment(current.attemptId, current.decision === 'verify'
                ? {
                    decision: 'verify',
                    bank_verified: current.bankVerified,
                    bank_match_reference: current.bankReference.trim(),
                    settled_amount: attempt.amount,
                    settled_currency: attempt.currency_code,
                    reason: current.reason.trim(),
                }
                : { decision: 'reject', reason: current.reason.trim() });
            setItems(previous => previous?.map(item => item.attempt_id === result.attempt_id
                ? { ...item, state: result.state }
                : item) ?? null);
            setReview(null);
            setNotice(current.decision === 'verify' ? 'Payment approved successfully.' : 'Payment disapproved successfully.');
        }
        catch (e) {
            setError(paymentReadError(e));
        }
        finally {
            setProcessingId(null);
        }
    }
    useEffect(() => { if (allowed && orderId)
        void load(orderId, null); return () => { controller.current?.abort(); sequence.current++; if (url.current)
        URL.revokeObjectURL(url.current); }; }, [allowed, orderId, attemptId]);
    if (!allowed)
        return <p role="alert">Current Finance role and MFA are required for payment records.</p>;
    return <div className={styles.screen} dir={ur ? 'rtl' : 'ltr'}><AdminPageContainer><AdminPageHeader title={ur ? 'ادائیگیاں اور مالی مطابقت' : 'Payments & Reconciliation'} description="Payment attempts, evidence and finance review" badge={<AdminStatusBadge label="Finance review" variant="info"/>}/><p className={styles.notice}>Approval requires a confirmed bank match for the recorded amount and currency. Uploaded evidence alone does not establish settlement.</p>
 {!orderId && <AdminCard><form onSubmit={lookup} className={styles.toolbar}><label>Exact order number<input aria-label="Exact order number" required maxLength={40} value={number} onChange={e => setNumber(e.target.value)}/></label><button disabled={busy} className={styles.primary}>Find Payment by Order</button></form>{orders && <section className={styles.body}>{!orders.length ? <AdminEmptyState title="Order not found" description="No exact order-number match in the permitted metadata response."/> : orders.map(o => <div className={styles.actions} key={o.order_id}><span>{o.order_number} · {o.currency_code} {o.total_amount}</span><button disabled={busy} onClick={() => void load(o.order_id, o)}>View payment attempts</button></div>)}</section>}</AdminCard>}
 {busy && <p role="status">Loading protected payment records…</p>}{error && <p role="alert" className={styles.notice}>{error}</p>}{notice && <p role="status" className={styles.notice}>{notice}</p>}
 {currentOrder && <AdminCard><section className={styles.body}><h2>Payment attempts</h2><p className={styles.mono}>Order {selected?.order_number ?? currentOrder}</p>{selected && <p>Stored order total: {selected.currency_code} {selected.total_amount}</p>}<p>At most 100 attempts, newest first. This is not a global queue or a complete paginated history. No attempt timestamp, payment method or rejection reason is supplied by this API.</p><button disabled={busy || !!processingId} onClick={() => void load(currentOrder, selected)}>Refresh Records</button></section>{review && <form className={styles.reviewForm} onSubmit={submitReview}><h3>{review.decision === 'verify' ? 'Approve payment' : 'Disapprove payment'}</h3>{review.decision === 'verify' && <><label>Bank match reference<input required minLength={4} maxLength={120} value={review.bankReference} onChange={event => setReview(value => value && { ...value, bankReference: event.target.value })}/></label><label className={styles.check}><input type="checkbox" required checked={review.bankVerified} onChange={event => setReview(value => value && { ...value, bankVerified: event.target.checked })}/> I verified the bank settlement for this amount and currency.</label></>}<label>Review reason<textarea required minLength={4} maxLength={1000} value={review.reason} onChange={event => setReview(value => value && { ...value, reason: event.target.value })}/></label><div className={styles.actions}><button type="submit" className={review.decision === 'verify' ? styles.approve : styles.disapprove} disabled={processingId === review.attemptId}>{processingId === review.attemptId ? 'Processing…' : review.decision === 'verify' ? 'Confirm approval' : 'Confirm disapproval'}</button><button type="button" disabled={!!processingId} onClick={() => setReview(null)}>Cancel</button></div></form>}{items && (!items.length ? <AdminEmptyState title="No payment attempts returned" description="No attempts are available in this bounded response; no settlement is inferred."/> : <div className={styles.scroll} tabIndex={0} role="region" aria-label="Payment attempts"><table><thead><tr>{['Actions', 'Attempt ID', 'Recorded state', 'Recorded amount', 'Evidence'].map(k => <th scope="col" key={k}>{k}</th>)}</tr></thead><tbody>{items.map(a => <tr key={a.attempt_id}><td>{['submitted', 'under_review'].includes(a.state) ? <div className={styles.actions}>{<button className={styles.approve} disabled={busy || !!processingId} onClick={() => openReview(a, 'verify')}>Approve</button>}<button className={styles.disapprove} disabled={busy || !!processingId} onClick={() => openReview(a, 'reject')}>Disapprove</button></div> : <AdminStatusBadge label={a.state === 'verified' ? 'Approved' : a.state === 'rejected' ? 'Disapproved' : a.state}/>}</td><td className={styles.mono}>{a.attempt_id}</td><td><AdminStatusBadge label={a.state === 'verified' ? 'Approved' : a.state === 'rejected' ? 'Disapproved' : a.state}/></td><td className={styles.amount}>{a.currency_code} {a.amount}</td><td>{!a.evidence.length ? 'No evidence returned' : a.evidence.map(e => <div key={e.id}><span className={styles.mono}>{e.id}</span><p>{e.content_type} · {e.bytes_size} bytes</p><button disabled={busy || !!processingId} onClick={() => void view(e)}>View evidence</button></div>)}</td></tr>)}</tbody></table></div>)}</AdminCard>}
 {preview && <AdminCard><section className={styles.body} aria-label="Private evidence preview"><h2>Private evidence · unverified receipt</h2><p className={styles.mono}>{preview.id}</p><img src={preview.url} alt="Private payment evidence; not proof of settlement" referrerPolicy="no-referrer" style={{ maxWidth: '100%', maxHeight: '65vh', objectFit: 'contain' }}/><button onClick={closePreview}>Close evidence</button><p>Preview remains in browser memory and is revoked when closed, refreshed or replaced.</p></section></AdminCard>}
 <AdminCard><section className={styles.body} aria-label="Reconciliation unavailable"><IndependentFinance orderId={currentOrder??undefined} ur={ur}/></section></AdminCard>
 </AdminPageContainer></div>;
}
