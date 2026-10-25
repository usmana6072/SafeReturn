"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useAdminRole } from './admin-shell';
import { TemplateErrorNotice } from './template-error-notice';
import { templateRequest, templateError, intentKeys, TemplateApiError } from '../lib/admin-templates-client';
import type { TemplatePage, Detail, Revision, TemplateRecord } from '../lib/admin-templates-contract';
import styles from './admin-templates.module.css';

type Entry = { template: TemplateRecord; revision: Revision };
export function TemplateQA({ ur = false }: { ur?: boolean }) {
    const { authenticatedRoles } = useAdminRole();
    const [entries, setEntries] = useState<Entry[]>([]), [selected, setSelected] = useState<Entry | null>(null);
    const [busy, setBusy] = useState(false), [loaded, setLoaded] = useState(false), [error, setError] = useState('');
    const [note, setNote] = useState(''), [preview, setPreview] = useState<{ url: string; fingerprint: string; bytes: number } | null>(null);
    const keys = useRef(intentKeys()), lock = useRef(false), url = useRef<string | null>(null), generation = useRef(0);
    function clearPreview() { if (url.current) URL.revokeObjectURL(url.current); url.current = null; setPreview(null); }
    async function load() {
        if (lock.current) return;
        lock.current = true; setBusy(true); setError(''); setLoaded(false); setSelected(null); clearPreview(); setEntries([]);
        try {
            const result: Entry[] = [];
            let cursor: string | null = null;
            do {
                const page: TemplatePage = await templateRequest('/admin/print-templates', { query: { limit: '50', ...(cursor ? { cursor } : {}) } });
                for (const template of page.items) {
                    let revisions_cursor: string | null = null;
                    do {
                        const detail: Detail = await templateRequest('/admin/print-templates/' + template.template_id, { query: { revisions_limit: '50', ...(revisions_cursor ? { revisions_cursor } : {}) } });
                        result.push(...detail.revisions.filter(r => r.status === 'pending_qa').map(revision => ({ template: detail.template, revision })));
                        revisions_cursor = detail.next_cursor;
                    } while (revisions_cursor);
                }
                cursor = page.next_cursor;
            } while (cursor);
            setEntries(result); setLoaded(true);
        } catch (e) { setError(templateError(e, ur)); }
        finally { lock.current = false; setBusy(false); }
    }
    useEffect(() => { void load(); return () => { generation.current++; if (url.current) URL.revokeObjectURL(url.current); }; }, []);
    async function generate() {
        if (!selected || lock.current) return;
        const run = generation.current;
        lock.current = true; setBusy(true); setError(''); clearPreview();
        const r = selected.revision, path = '/admin/print-templates/' + selected.template.template_id + '/revisions/' + r.revision_id + '/preview';
        const body = { expected_revision: r.row_version };
        try {
            const value = await templateRequest<{ blob: Blob; fingerprint: string }>(path, { method: 'POST', body, version: r.row_version, key: keys.current(path, 'POST', body, r.row_version) });
            if (run !== generation.current) return;
            if (value.fingerprint !== r.fingerprint_sha256) throw new TemplateApiError(409);
            url.current = URL.createObjectURL(value.blob);
            setPreview({ url: url.current, fingerprint: value.fingerprint, bytes: value.blob.size });
        } catch (e) { if (run === generation.current) setError(templateError(e, ur)); }
        finally { lock.current = false; setBusy(false); }
    }
    return <section className={styles.screen}>
        <h1 className="text-2xl font-bold">Template QA</h1>
        <p>QA approval, template publication and product assignment are separate steps. Template requests require genuine sign-in/MFA within 20 minutes.</p>
        <p>Decision service unavailable: the current backend accepts independently signed QA evidence through controlled import. It does not expose review-note approval, rejection, reviewer eligibility or QA decision history to this page. Approved and Rejected cannot be verified here.</p>
        <button disabled={busy} onClick={() => void load()}>Refresh submitted revisions</button>
        {busy && <p role="status">Loading template QA…</p>}
        <TemplateErrorNotice message={error} ur={ur}/>
        {loaded && !entries.length && <p role="status">No revisions pending QA.</p>}
        <div className="grid gap-5 lg:grid-cols-2">
            <section className="space-y-3" aria-label="Submitted revisions">{entries.map(entry => <button className="block w-full rounded border p-3 text-left break-all" key={entry.revision.revision_id} disabled={busy} onClick={() => { clearPreview(); setSelected(entry); setNote(''); setError(''); }}>
                {entry.template.name} · Revision {entry.revision.version} · Pending
            </button>)}</section>
            {selected && <section className="rounded-xl border p-4 space-y-3 min-w-0">
                <h2 className="font-bold">Revision {selected.revision.version} · Pending</h2>
                <p className="break-all">Template: {selected.template.template_id}<br/>Revision: {selected.revision.revision_id}<br/>Row version: {selected.revision.row_version}<br/>Submitted fingerprint: {selected.revision.fingerprint_sha256}</p>
                <Link prefetch={false} href={'/admin/templates/' + selected.template.template_id}>Open template details</Link>
                <details><summary>Revision design metadata</summary><pre className="overflow-auto text-xs">{JSON.stringify(selected.revision.content, null, 2)}</pre></details>
                <button disabled={busy || !authenticatedRoles.includes('operations')} onClick={() => void generate()}>Generate synthetic preview</button>
                {preview && <div className="break-all"><a href={preview.url} target="_blank" rel="noreferrer">Open synthetic PDF preview</a><p>Backend fingerprint: {preview.fingerprint}<br/>PDF size: {preview.bytes} bytes</p></div>}
                <p>Physical print quality, actual QR scans, measured label dimensions and signed reviewer evidence require independent verification. No QA decision timestamp or reviewer identity is available from this contract.</p>
                <label className="block">Short review note (local draft only)<textarea className="block w-full border rounded p-2" minLength={4} maxLength={500} value={note} onChange={e => setNote(e.target.value)}/></label>
                <p>Notes cannot be submitted or saved until a protected review contract is available.</p>
                <button disabled title="Protected decision API and verified reviewer authorization unavailable">Approve QA</button>{' '}
                <button disabled title="No backend rejection state or decision API available">Reject QA</button>
            </section>}
        </div>
    </section>;
}
