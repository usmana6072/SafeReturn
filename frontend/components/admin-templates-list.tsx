"use client";
import { TemplateErrorNotice } from "./template-error-notice";
import styles from './admin-templates.module.css';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAdminRole } from './admin-shell';
import { AdminStatusBadge } from './admin-ui';
import { templateRequest, templateError } from '../lib/admin-templates-client';
import type { TemplateRecord, TemplatePage } from '../lib/admin-templates-contract';
export function TemplateRevisionBadge({ template }: {
    template: TemplateRecord;
    ur?: boolean;
}) { return <AdminStatusBadge label={template.lifecycle_status}/>; }
export function PrintTemplatesList({ ur = false }: {
    ur?: boolean;
}) {
    const { authenticatedRoles } = useAdminRole(), canWrite = authenticatedRoles.includes('operations');
    const [page, setPage] = useState<TemplatePage | null>(null), [purpose, setPurpose] = useState(''), [status, setStatus] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
    async function load(cursor?: string) { setBusy(true); setError(''); try {
        const query: Record<string, string> = { limit: '20' };
        if (purpose)
            query.purpose = purpose;
        if (status)
            query.status = status;
        if (cursor)
            query.cursor = cursor;
        setPage(await templateRequest<TemplatePage>('/admin/print-templates', { query }));
    }
    catch (e) {
        setPage(null);
        setError(templateError(e, ur));
    }
    finally {
        setBusy(false);
    } }
    useEffect(() => { void load(); }, []);
    return <section className={styles.screen}><header className="flex flex-wrap justify-between gap-3"><div><h1 className="text-2xl font-bold">{ur ? 'پرنٹ ٹیمپلیٹس' : 'Print templates'}</h1><p>Design metadata and synthetic proofs. A template key identifies a design.</p></div>{canWrite && <Link prefetch={false} href="/admin/templates/new" className="px-4 py-2 rounded bg-teal-700 text-white">Create template</Link>}</header>
 <form onSubmit={e => { e.preventDefault(); void load(); }} className="flex flex-wrap gap-3"><label>Purpose <select aria-label="Purpose filter" value={purpose} onChange={e => setPurpose(e.target.value)}><option value="">All</option><option value="lost">Lost</option><option value="ice">ICE</option></select></label><label>Status <select aria-label="Status filter" value={status} onChange={e => setStatus(e.target.value)}><option value="">All</option>{['draft', 'active', 'retired'].map(s => <option key={s}>{s}</option>)}</select></label><button disabled={busy}>Apply filters / Refresh</button></form>
 <TemplateErrorNotice message={error} ur={ur}/>{busy && <p role="status">Loading templates…</p>}{page && <><p className="text-sm">As of {page.as_of}</p>{!page.items.length && <p>No templates match these filters.</p>}<div className="grid gap-4 md:grid-cols-2">{page.items.map(t => <article key={t.template_id} className="rounded-xl border bg-white p-5 space-y-2"><h2 className="font-semibold">{t.name}</h2><p className="break-all">{t.key} · {t.purpose}</p><TemplateRevisionBadge template={t}/><p>Template version {t.row_version}</p><Link prefetch={false} href={'/admin/templates/' + t.template_id}>View revisions</Link></article>)}</div>{page.next_cursor && <button disabled={busy} onClick={() => void load(page.next_cursor!)}>Next page</button>}</>}</section>;
}
