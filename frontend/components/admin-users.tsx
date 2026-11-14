"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { AdminUserDetails } from './admin-user-details';
import { directoryPage, directoryCount, directoryDetail, selectedFilters, directoryError, DirectoryError } from '../lib/admin-user-directory-client';
import type { Page, Total, Detail, Filters } from '../lib/users-contract';
import styles from './admin-users.module.css';
const empty = { user_id: '', email_verified: '', provider_access: '' };
const noFilters: Filters = { user_id: null, email_verified: null, provider_access: null };
export function AdminUsers({ userId, ur = false }: {
    userId?: string;
    ur?: boolean;
}) {
    const { authenticatedRoles } = useAdminRole(), allowed = authenticatedRoles.includes('security_admin');
    const [raw, setRaw] = useState(empty), [filters, setFilters] = useState(noFilters), [cursors, setCursors] = useState<(string | null)[]>([null]), [page, setPage] = useState<Page | null>(null), [count, setCount] = useState<Total | null>(null), [detail, setDetail] = useState<Detail | null>(null), [error, setError] = useState(''), [countError, setCountError] = useState(''), [busy, setBusy] = useState(false), [tick, setTick] = useState(0), [visible, setVisible] = useState(true);
    const seq = useRef(0);
    useEffect(() => { const change = () => setVisible(document.visibilityState !== 'hidden'); document.addEventListener('visibilitychange', change); return () => document.removeEventListener('visibilitychange', change); }, []);
    useEffect(() => {
        const n = ++seq.current, ctrl = new AbortController();
        setPage(null);
        setCount(null);
        setDetail(null);
        setError('');
        setCountError('');
        if (!allowed || !visible) {
            setBusy(false);
            return () => ctrl.abort();
        }
        setBusy(true);
        const current = () => seq.current === n && !ctrl.signal.aborted;
        async function load() { try {
            if (userId !== undefined) {
                const d = await directoryDetail(userId, ctrl.signal);
                if (current())
                    setDetail(d);
            }
            else {
                const results = await Promise.allSettled([directoryPage(filters, cursors.at(-1) ?? null, ctrl.signal), directoryCount(filters, ctrl.signal)]);
                if (!current())
                    return;
                for (const r of results)
                    if (r.status === 'rejected' && r.reason instanceof DirectoryError && [401, 403].includes(r.reason.status))
                        throw r.reason;
                const [p, c] = results;
                if (p.status === 'fulfilled')
                    setPage(p.value);
                else
                    setError(directoryError(p.reason));
                if (c.status === 'fulfilled')
                    setCount(c.value);
                else
                    setCountError(directoryError(c.reason));
            }
        }
        catch (e) {
            if (current()) {
                setPage(null);
                setCount(null);
                setDetail(null);
                setError(directoryError(e));
            }
        }
        finally {
            if (current())
                setBusy(false);
        } }
        void load();
        return () => { ctrl.abort(); seq.current++; };
    }, [allowed, visible, userId, filters, cursors, tick]);
    function apply(clear = false) { try {
        const f = clear ? noFilters : selectedFilters(raw);
        if (clear)
            setRaw(empty);
        setFilters(f);
        setCursors([null]);
    }
    catch (e) {
        setError(directoryError(e));
    } }
    if (!allowed)
        return <p role="alert">Current Security Admin role and MFA are required.</p>;
    return <div className={styles.screen} dir={ur ? 'rtl' : 'ltr'}><AdminPageContainer><AdminPageHeader title={userId !== undefined ? 'User Details' : 'Users & Accounts'} description="Authorized minimal account metadata" badge={<AdminStatusBadge variant="info" label="Backend directory"/>} actions={userId !== undefined ? <Link prefetch={false} href="/admin/users">Back to Users</Link> : undefined}/>
 <p className={styles.notice}>Only retained, non-anonymous registrations are included. No private contact/profile data or QR ownership is requested. Provider access and application suspension are separate states.</p>
 <div><button disabled={busy} type="button" onClick={() => { setCursors([null]); setTick(t => t + 1); }}>Refresh {userId !== undefined ? 'User' : 'Users'}</button></div>
 {userId === undefined && <AdminCard><form className={styles.toolbar} onSubmit={e => { e.preventDefault(); apply(); }}><label>Exact user UUID<input aria-label="Exact user UUID" value={raw.user_id} onChange={e => setRaw({ ...raw, user_id: e.target.value })}/></label><label>Email verified<select aria-label="Email verified" value={raw.email_verified} onChange={e => setRaw({ ...raw, email_verified: e.target.value })}><option value="">Any</option><option value="true">Verified</option><option value="false">Not verified</option></select></label><label>Provider access<select aria-label="Provider access" value={raw.provider_access} onChange={e => setRaw({ ...raw, provider_access: e.target.value })}><option value="">Any</option><option value="banned">banned</option><option value="not_banned">not_banned</option></select></label><button disabled={busy}>Apply filters</button><button disabled={busy} type="button" onClick={() => apply(true)}>Clear filters</button></form></AdminCard>}
 {busy && <p role="status">Loading user metadata…</p>}{error && <p role="alert" className={styles.notice}>{error}</p>}
 {userId === undefined && <><AdminCard><section className={styles.details}><h2>Matching registrations</h2>{count ? <><strong>{count.count.is_exact ? count.count.value : '1000+ (lower bound)'}</strong><p>Count as of {count.as_of}</p></> : <p>Count unavailable</p>}{countError && <p role="alert">{countError}</p>}<p>Definition: retained non-anonymous auth registrations. Count is independent of the current page; separate requests are not one snapshot.</p></section></AdminCard>{page && <AdminCard><p className={styles.count}>List as of {page.as_of} · Registered newest first, UUID descending for ties.</p>{page.items.length ? <div className={styles.scroll} role="region" aria-label="User directory" tabIndex={0}><table><thead><tr>{['User ID', 'Registered at', 'Email verified', 'Provider access', 'Actions'].map(k => <th key={k} scope="col">{k}</th>)}</tr></thead><tbody>{page.items.map(u => <tr key={u.user_id}><td className={styles.mono}>{u.user_id}</td><td>{u.registered_at}</td><td>{u.email_verified ? 'Verified' : 'Not verified'}</td><td><AdminStatusBadge label={u.provider_access} variant="neutral"/></td><td><Link prefetch={false} href={'/admin/users/' + u.user_id} aria-label={'View Details for ' + u.user_id}>View Details</Link></td></tr>)}</tbody></table></div> : <AdminEmptyState title="No matching users" description="No records returned for the applied directory filters."/>}<div className={styles.toolbar}><button type="button" disabled={busy || cursors.length === 1} onClick={() => setCursors(c => c.slice(0, -1))}>Previous</button><button type="button" disabled={busy || !page.next_cursor} onClick={() => setCursors(c => [...c, page.next_cursor])}>Next</button></div></AdminCard>}</>}
 {detail && <AdminUserDetails detail={detail}/>}
 </AdminPageContainer></div>;
}
