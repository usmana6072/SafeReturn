"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { printRead, printError } from '../lib/admin-print-jobs-client';
import { states, filterKeys, orderStates, paymentStates, fulfillmentStates, countLabel, type JobPage, type Counts, type Detail, type OrderJob } from '../lib/admin-print-jobs-contract';
import styles from './admin-print-jobs.module.css';
const blank = { job_id: '', order_id: '', order_number: '', job_status: '', order_status: '', payment_status: '', fulfillment_status: '', created_from: '', created_before: '', sort: 'oldest' };
export function AdminPrintJobs({ jobId, initialOrderId, ur = false }: {
    jobId?: string;
    initialOrderId?: string;
    ur?: boolean;
    liveConsoleAvailable?: boolean;
}) {
    const { authenticatedRoles } = useAdminRole(), allowed = authenticatedRoles.includes('operations');
    const initial = { ...blank, order_id: initialOrderId ?? '' };
    const [form, setForm] = useState(initial), [active, setActive] = useState(initial), [page, setPage] = useState<JobPage | null>(null), [counts, setCounts] = useState<Counts | null>(null), [detail, setDetail] = useState<Detail | null>(null), [history, setHistory] = useState<(string | undefined)[]>([undefined]), [error, setError] = useState(''), [countError, setCountError] = useState(''), [busy, setBusy] = useState(false), [order, setOrder] = useState(initialOrderId ?? ''), [orderJobs, setOrderJobs] = useState<OrderJob[] | null>(null), [orderShown, setOrderShown] = useState(''), [orderError, setOrderError] = useState(''), [orderBusy, setOrderBusy] = useState(false);
    const controller = useRef<AbortController | null>(null), sequence = useRef(0), orderController = useRef<AbortController | null>(null), orderSequence = useRef(0);
    function filters(f: typeof blank) { const q = new URLSearchParams(); for (const key of filterKeys)
        if (f[key])
            q.set(key, f[key]); return q; }
    async function load(f = active, cursor?: string, stack: (string | undefined)[] = [undefined], withCounts = true) { controller.current?.abort(); const ctrl = new AbortController(); controller.current = ctrl; const seq = ++sequence.current; setBusy(true); setError(''); setPage(null); if (withCounts) {
        setCounts(null);
        setCountError('');
    } const q = filters(f); q.set('sort', f.sort); q.set('limit', '20'); if (cursor)
        q.set('cursor', cursor); const result = await Promise.allSettled([printRead('jobs', { query: q, signal: ctrl.signal }), ...(withCounts ? [printRead('counts', { query: filters(f), signal: ctrl.signal })] : [])]); if (seq !== sequence.current)
        return; setActive(f); setHistory(stack); const jobs = result[0]; if (jobs.status === 'fulfilled')
        setPage(jobs.value as JobPage);
    else if (!ctrl.signal.aborted)
        setError(printError(jobs.reason)); if (withCounts) {
        const c = result[1];
        if (c.status === 'fulfilled')
            setCounts(c.value as Counts);
        else if (!ctrl.signal.aborted)
            setCountError(printError(c.reason));
    } setBusy(false); }
    async function loadDetail() { controller.current?.abort(); const ctrl = new AbortController(); controller.current = ctrl; const seq = ++sequence.current; setBusy(true); setError(''); setDetail(null); try {
        const d = await printRead('detail', { id: jobId, signal: ctrl.signal }) as Detail;
        if (seq === sequence.current)
            setDetail(d);
    }
    catch (e) {
        if (seq === sequence.current && !ctrl.signal.aborted)
            setError(printError(e));
    }
    finally {
        if (seq === sequence.current)
            setBusy(false);
    } }
    async function findOrder(e: React.FormEvent) { e.preventDefault(); orderController.current?.abort(); const ctrl = new AbortController(); orderController.current = ctrl; const seq = ++orderSequence.current; setOrderBusy(true); setOrderError(''); setOrderJobs(null); try {
        const p = await printRead('order', { id: order, signal: ctrl.signal }) as {
            items: OrderJob[];
        };
        if (seq !== orderSequence.current)
            return;
        setOrderJobs(p.items);
        setOrderShown(order);
    }
    catch (e) {
        if (seq === orderSequence.current && !ctrl.signal.aborted)
            setOrderError(printError(e));
    }
    finally {
        if (seq === orderSequence.current)
            setOrderBusy(false);
    } }
    useEffect(() => { if (allowed) {
        if (jobId !== undefined)
            void loadDetail();
        else
            void load(initial);
    } return () => { controller.current?.abort(); orderController.current?.abort(); sequence.current++; orderSequence.current++; }; }, [allowed, jobId, initialOrderId]);
    if (!allowed)
        return <p role="alert">Current Operations role and MFA are required for print metadata.</p>;
    const badge = (status: string) => <AdminStatusBadge label={status} variant={status === 'failed' ? 'danger' : status === 'qa_passed' ? 'success' : 'neutral'}/>;
    return <div className={styles.screen} dir={ur ? 'rtl' : 'ltr'}><AdminPageContainer><AdminPageHeader title={jobId === undefined ? 'Print Jobs' : 'Print Job Details'} description="Recorded metadata only · no artwork or production actions" badge={<AdminStatusBadge label="Backend metadata" variant="info"/>} actions={jobId !== undefined ? <Link href="/admin/print-jobs" prefetch={false}>Back to Print Jobs</Link> : undefined}/><p className={styles.notice}>Recorded job and order states are observations, not proof of physical QA or permission to print, download or dispatch. No production artwork, QR payloads or credentials are retrieved.</p>
 {jobId !== undefined ? <><button disabled={busy} onClick={() => void loadDetail()}>Refresh Print Job</button>{busy && <p role="status">Loading print metadata…</p>}{error && <p role="alert" className={styles.notice}>{error}</p>}{detail && <><AdminCard><section className={styles.body}><h2>Job metadata</h2><dl className={styles.facts}>{[['Job ID', detail.id], ['Order ID', detail.order_id], ['Revision', String(detail.job_revision)], ['Attempt count', String(detail.attempt_count)], ['Template fingerprint', detail.template_fingerprint], ['Recorded failure category', detail.failure_category ?? 'None recorded']].map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>{badge(detail.status)}<p>Creation/update timestamps and a template key/version are not supplied by this detail endpoint. Independent physical inspection evidence is not supplied by these reads.</p></section></AdminCard><AdminCard><section className={styles.body}><h2>Artifact metadata</h2><p>No artifact bytes, storage keys, private URLs or download controls.</p>{!detail.artifacts.length && <p>No artifact metadata returned.</p>}</section>{detail.artifacts.length > 0 && <div className={styles.scroll} role="region" tabIndex={0} aria-label="Artifact metadata"><table><thead><tr>{['Artifact ID', 'Format', 'Bytes', 'Checksum', 'Deleted at'].map(k => <th key={k} scope="col">{k}</th>)}</tr></thead><tbody>{detail.artifacts.map(a => <tr key={a.id}><td className={styles.mono}>{a.id}</td><td>{a.format}</td><td>{a.size_bytes}</td><td className={styles.mono}>{a.sha256_hex}</td><td>{a.deleted_at ?? 'Not recorded'}</td></tr>)}</tbody></table></div>}</AdminCard></>}</> : <>
 <AdminCard><form className={styles.toolbar} onSubmit={e => { e.preventDefault(); void load(form); }}>{(['job_id', 'order_id', 'order_number'] as const).map(k => <label key={k}>{k === 'job_id' ? 'Job UUID' : k === 'order_id' ? 'Order UUID' : 'Exact order number'}<input aria-label={k} value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}/></label>)}{([['job_status', states], ['order_status', orderStates], ['payment_status', paymentStates], ['fulfillment_status', fulfillmentStates]] as const).map(([k, values]) => <label key={k}>{k.replaceAll('_', ' ')}<select aria-label={k} value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}><option value="">All</option>{values.map(s => <option key={s}>{s}</option>)}</select></label>)}{(['created_from', 'created_before'] as const).map(k => <label key={k}>{k === 'created_from' ? 'Created from (inclusive RFC3339)' : 'Created before (exclusive RFC3339)'}<input aria-label={k} placeholder="2026-10-01T00:00:00Z" value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}/></label>)}<label>Sort<select aria-label="Sort" value={form.sort} onChange={e => setForm({ ...form, sort: e.target.value })}><option value="oldest">Oldest</option><option value="newest">Newest</option></select></label><button disabled={busy} className={styles.primary}>Apply filters</button><button type="button" disabled={busy} onClick={() => { setForm(blank); void load(blank); }}>Clear filters</button><button type="button" disabled={busy} onClick={() => void load(active)}>Refresh Print Jobs</button></form></AdminCard>
 {counts ? <><p>Counts as of {counts.as_of}. Matching the applied filters, independent of this page cursor.</p><div className={styles.metrics}>{[['Matching jobs', counts.matching_jobs], ['Affected orders', counts.affected_orders]].map(([label, c]) => <AdminCard key={label as string}><div className={styles.metric}><span>{label as string}</span><strong>{countLabel(c as Counts['matching_jobs'])}</strong></div></AdminCard>)}</div><AdminCard><section className={styles.body}><h2>Counts by recorded job status</h2><dl className={styles.facts}>{states.map(s => <div key={s}><dt>{s}</dt><dd>{countLabel(counts.by_job_status[s])}</dd></div>)}</dl><p>1000+ is a lower bound, including when exactly 1000. Counts are not summed into an exact total.</p></section></AdminCard></> : <p role={countError ? 'alert' : 'status'} className={styles.notice}>{countError ? 'Counts unavailable. ' + countError : 'Loading job counts…'}</p>}
 {busy && <p role="status">Loading print metadata…</p>}{error && <p role="alert" className={styles.notice}>{error}</p>}{page && <AdminCard><section className={styles.body}><h2>Print jobs</h2><p>List as of {page.as_of}. This is not the counts request timestamp or a transaction snapshot across pages.</p></section>{!page.items.length ? <AdminEmptyState title="No print jobs found" description="No records match the applied filters."/> : <div className={styles.scroll} role="region" aria-label="Print jobs table" tabIndex={0}><table><thead><tr>{['Job ID / revision', 'Order reference', 'Recorded job status', 'Created', 'Attempts', 'Failure category'].map(k => <th key={k} scope="col">{k}</th>)}</tr></thead><tbody>{page.items.map(j => <tr key={j.job_id}><td className={styles.mono}><Link href={'/admin/print-jobs/' + j.job_id} prefetch={false}>{j.job_id}</Link><p>Revision {j.job_revision}</p></td><td><p>{j.order_number}</p><p className={styles.mono}>{j.order_id}</p><p>Recorded order/payment/fulfillment: {j.order_status} / {j.payment_status} / {j.fulfillment_status}</p></td><td>{badge(j.job_status)}</td><td>{j.created_at}</td><td>{j.attempt_count}</td><td>{j.failure_category ?? 'None recorded'}</td></tr>)}</tbody></table></div>}<div className={styles.body}><div className={styles.actions}><button disabled={busy || history.length < 2} onClick={() => { const prior = history.slice(0, -1); void load(active, prior.at(-1), prior, false); }}>Previous</button><button disabled={busy || !page.next_cursor} onClick={() => void load(active, page.next_cursor!, [...history, page.next_cursor!], false)}>Next</button></div></div></AdminCard>}
 <AdminCard><section className={styles.body}><h2>Find Jobs by Order</h2><p>Use an already-known order UUID. This does not fetch order details, discover ownership or establish whether an order exists.</p><form onSubmit={findOrder} className={styles.actions}><label>Known order UUID<input aria-label="Known order UUID" required value={order} onChange={e => setOrder(e.target.value)}/></label><button disabled={orderBusy}>Find Jobs by Order</button></form>{orderBusy && <p role="status">Loading order-linked job metadata…</p>}{orderError && <p role="alert">{orderError}</p>}{orderJobs && <><p className={styles.mono}>Order context: {orderShown}</p>{!orderJobs.length ? <p>No print jobs returned for this order UUID. Order existence is not established by this response.</p> : <><p>Revision descending. This endpoint has no cursor/total; oversized history is unavailable rather than silently truncated.</p>{orderJobs.map(j => <div key={j.id} className={styles.actions}><Link href={'/admin/print-jobs/' + j.id} prefetch={false}>{j.id}</Link>{badge(j.status)}<span>Revision {j.job_revision}</span><span>{j.failure_category ?? 'No failure category recorded'}</span></div>)}</>}</>}</section></AdminCard>
 </>}</AdminPageContainer></div>;
}
