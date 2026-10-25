"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useAdminRole } from './admin-shell';
import { TemplateErrorNotice } from './template-error-notice';
import { templateRequest, templateError, intentKeys, TemplateApiError } from '../lib/admin-templates-client';
import type { TemplatePage, Detail, Revision, TemplateRecord, QAState, Receipt } from '../lib/admin-templates-contract';
import styles from './admin-templates.module.css';

type Entry = { template: TemplateRecord; revision: Revision };
export function TemplateQA({ ur = false }: { ur?: boolean }) {
    const { authenticatedRoles } = useAdminRole();
    const [entries, setEntries] = useState<Entry[]>([]), [selected, setSelected] = useState<Entry | null>(null);
    const [busy, setBusy] = useState(false), [loaded, setLoaded] = useState(false), [error, setError] = useState('');
    const [note, setNote] = useState(''), [preview, setPreview] = useState<{ url: string; fingerprint: string; bytes: number } | null>(null);
    const [qa, setQA] = useState<Record<string, QAState>>({}), [qaError, setQAError] = useState('');
    const keys = useRef(intentKeys()), lock = useRef(false), url = useRef<string | null>(null), generation = useRef(0);
    function clearPreview() { if (url.current) URL.revokeObjectURL(url.current); url.current = null; setPreview(null); }
    async function load() {
        if (lock.current) return;
        lock.current = true; setBusy(true); setError(''); setLoaded(false); clearPreview(); setEntries([]); setQA({}); setQAError('');
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
            setEntries(result); setSelected(old => old ? result.find(e => e.revision.revision_id === old.revision.revision_id) ?? null : null); setLoaded(true);
            const states: Record<string, QAState> = {};
            for (const entry of result) {
                try { states[entry.revision.revision_id] = await templateRequest<QAState>('/admin/print-templates/' + entry.template.template_id + '/revisions/' + entry.revision.revision_id + '/qa'); }
                catch (e) { setQAError(e instanceof TemplateApiError && e.status === 503 ? 'QA reviews are temporarily unavailable. Contact a portal administrator, then refresh.' : templateError(e, ur)); break; }
            }
            setQA(states);
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
            const download = document.createElement('a'); download.href = url.current; download.download = 'template-revision-' + r.version + '.pdf'; download.click();
        } catch (e) { if (run === generation.current) setError(templateError(e, ur)); }
        finally { lock.current = false; setBusy(false); }
    }
    const current = selected ? qa[selected.revision.revision_id] : undefined;
    async function decide(decision: 'approved' | 'rejected') {
        if (!selected || !current?.can_review || !preview || lock.current) return;
        lock.current = true; setBusy(true); setError('');
        try {
            const body = { decision, reason: note.trim() || (decision === 'approved' ? 'Staff confirmed manual review of the printed PDF' : 'Staff rejected the printed PDF'), expected_review_version: current.review_version, preview_fingerprint: preview.fingerprint, confirmed: true };
            const path = '/admin/print-templates/' + selected.template.template_id + '/revisions/' + selected.revision.revision_id + '/qa-decision';
            const result = await templateRequest<Receipt<QAState>>(path, { method: 'POST', body, version: selected.revision.row_version, key: keys.current(path, 'POST', body, selected.revision.row_version) });
            if (result.result.revision_id !== selected.revision.revision_id) throw new TemplateApiError(503);
            const latest = await templateRequest<QAState>(path.replace(/qa-decision$/, 'qa'));
            if (latest.revision_id !== selected.revision.revision_id) throw new TemplateApiError(503);
            setQA(old => ({ ...old, [latest.revision_id]: latest })); setNote('');
        } catch (e) {
            if (e instanceof TemplateApiError && [409, 412].includes(e.status)) setQA(old => { const copy = { ...old }; delete copy[selected.revision.revision_id]; return copy; });
            setError(templateError(e, ur));
        } finally { lock.current = false; setBusy(false); }
    }
    return <section className={styles.screen}>
        <h1 className="text-2xl font-bold">Template QA</h1>
        <p>Get the PDF, print it and inspect the result. Then click Approve QA or Reject QA. Approval also publishes this revision. Product assignment remains separate.</p>
        {qaError && <p role="alert">{qaError}</p>}
        <button disabled={busy} onClick={() => void load()}>Refresh submitted revisions</button>
        {busy && <p role="status">Loading template QA…</p>}
        <TemplateErrorNotice message={error} ur={ur}/>
        {loaded && !entries.length && <p role="status">No revisions pending QA.</p>}
        <div className="grid gap-5 lg:grid-cols-2">
            <section className="space-y-3" aria-label="Submitted revisions">{entries.map(entry => <button className="block w-full rounded border p-3 text-left break-all" key={entry.revision.revision_id} disabled={busy} onClick={() => { clearPreview(); setSelected(entry); setNote(''); setError(''); }}>
                {entry.template.name} · Revision {entry.revision.version} · {qa[entry.revision.revision_id]?.status ?? 'Review status unavailable'}
            </button>)}</section>
            {selected && <section className="rounded-xl border p-4 space-y-3 min-w-0">
                <h2 className="font-bold">Revision {selected.revision.version} · {current?.status ?? 'Review status unavailable'}</h2>
                {current?.publication_status === 'published' && <p role="status">QA approved and template published · {current.published_at}</p>}
                <p className="break-all">Template: {selected.template.template_id}<br/>Revision: {selected.revision.revision_id}<br/>Row version: {current?.revision_row_version ?? selected.revision.row_version}<br/>Submitted fingerprint: {selected.revision.fingerprint_sha256}</p>
                <Link prefetch={false} href={'/admin/templates/' + selected.template.template_id}>Open template details</Link>
                <details><summary>Revision design metadata</summary><pre className="overflow-auto text-xs">{JSON.stringify(selected.revision.content, null, 2)}</pre></details>
                <button disabled={busy || !authenticatedRoles.includes('operations')} onClick={() => void generate()}>Get PDF for printing</button>
                {preview && <div className="break-all"><a href={preview.url} target="_blank" rel="noreferrer">Open PDF to print</a><p>Backend fingerprint: {preview.fingerprint}<br/>PDF size: {preview.bytes} bytes</p></div>}
                <p>Clicking Approve QA confirms that you printed and checked this PDF, and publishes this exact revision. No evidence upload is required.</p>
                <details><summary>Add a note (optional)</summary><label className="block">Review note<textarea className="block w-full border rounded p-2" maxLength={500} value={note} onChange={e => setNote(e.target.value)}/></label></details>
                {current && !current.can_review && current.publication_status !== 'published' && <p>{current.status === 'rejected' ? 'This revision was rejected. Submit a new revision to review changes.' : 'Your current account is not permitted to review this revision.'}</p>}
                <button disabled={busy || !current?.can_review || !preview || (!!note.trim() && note.trim().length < 4)} onClick={() => void decide('approved')}>Approve QA</button>{' '}
                <button disabled={busy || !current?.can_review || !preview || (!!note.trim() && note.trim().length < 4)} onClick={() => void decide('rejected')}>Reject QA</button>
                {current && <section aria-label="QA decision history"><h3 className="font-bold">QA decision history</h3>{!current.history.length && <p>No QA decisions recorded.</p>}{current.history.map(review => <article key={review.review_id} className="border rounded p-3 break-all"><p>{review.decision} · {review.decided_at}</p><p>Reviewer: {review.reviewer_user_id}</p><p>{review.review_note}</p><p>{review.evidence_kind === 'manual_print' ? 'Manual print review' : 'Signed evidence review'}</p>{review.approval_id && <p>Evidence approval: {review.approval_id}. Publication separately rechecks evidence validity.</p>}</article>)}</section>}

            </section>}
        </div>
    </section>;
}
