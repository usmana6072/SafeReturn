"use client";
import { TemplateErrorNotice } from "./template-error-notice";
import { TemplateDesignFields } from "./template-design-fields";
import styles from './admin-templates.module.css';
import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useAdminRole } from './admin-shell';
import { AdminStatusBadge } from './admin-ui';
import { TemplateBindings } from './admin-template-bindings';
import { templateRequest, templateError, intentKeys, TemplateApiError } from '../lib/admin-templates-client';
import { uuid, design, type Detail, type Revision, type Receipt } from '../lib/admin-templates-contract';
export interface AdminTemplateDetailsProps {
    keyParam: string;
    ur?: boolean;
}
export function AdminTemplateDetails({ keyParam, ur = false }: AdminTemplateDetailsProps) {
    const { authenticatedRoles } = useAdminRole(), canWrite = authenticatedRoles.includes('operations'), keys = useRef(intentKeys()), mutating = useRef(false);
    const [detail, setDetail] = useState<Detail | null>(null), [revision, setRevision] = useState<Revision | null>(null), [base, setBase] = useState(''), [content, setContent] = useState('{}'), [note, setNote] = useState(''), [reason, setReason] = useState(''), [conflict, setConflict] = useState(false), [confirmed, setConfirmed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState(''), [preview, setPreview] = useState<{
        url: string;
        fingerprint: string;
        version: number;
        id: string;
    } | null>(null);
    const previewRef = useRef<string | null>(null), path = '/admin/print-templates/' + keyParam;
    const dirty = revision ? content !== JSON.stringify(revision.content, null, 2) : content !== '{}';
    function clearPreview() { if (previewRef.current)
        URL.revokeObjectURL(previewRef.current); previewRef.current = null; setPreview(null); }
    async function load(more = false) { setBusy(true); setError(''); try {
        try {
            uuid(keyParam);
        }
        catch {
            throw new TemplateApiError(404);
        }
        const d = await templateRequest<Detail>(path, { query: more && detail?.next_cursor ? { revisions_cursor: detail.next_cursor } : {} });
        setDetail(old => more && old ? { ...d, revisions: [...old.revisions, ...d.revisions] } : d);
        if (!more && revision) {
            const fresh = d.revisions.find(r => r.revision_id === revision.revision_id);
            if (fresh) {
                if (fresh.row_version !== revision.row_version || fresh.status !== revision.status || JSON.stringify(fresh.content) !== JSON.stringify(revision.content)) {
                    clearPreview(); setConfirmed(false);
                }
                setRevision(fresh);
                setConflict(false);
            }
            else {
                clearPreview(); setConfirmed(false);
                setConflict(true);
                setMessage('Selected revision is outside this page. Load its history and select it before editing.');
                return;
            }
        }
        else if (!revision) {
            clearPreview(); setConfirmed(false);
            setConflict(false);
            if (!more && content === '{}' && !note && d.revisions.length) {
                const latest = d.revisions[0]; setRevision(latest); setBase(latest.revision_id); setContent(JSON.stringify(latest.content, null, 2));
            }
        }
        setMessage('Latest server data loaded. Unsaved editor text is retained; compare before saving.');
    }
    catch (e) {
        setError(templateError(e, ur));
    }
    finally {
        setBusy(false);
    } }
    useEffect(() => { void load(); return () => { if (previewRef.current)
        URL.revokeObjectURL(previewRef.current); }; }, [keyParam]);
    useEffect(() => {
        const refresh = () => { if (!busy && !dirty && !note && !mutating.current) void load(); };
        window.addEventListener('focus', refresh);
        return () => window.removeEventListener('focus', refresh);
    }, [busy, dirty, note, revision?.revision_id, keyParam]);
    function choose(r: Revision | null) { if ((dirty || note) && !window.confirm('Discard unsaved editor changes?'))
        return; clearPreview(); setRevision(r); setBase(r?.revision_id ?? ''); setContent(r ? JSON.stringify(r.content, null, 2) : '{}'); setNote(''); setReason(''); setConfirmed(false); setConflict(false); setError(''); setMessage(''); }
    async function mutate(action: 'save' | 'preview' | 'submit-qa' | 'retire') {
        if (!detail || mutating.current || conflict)
            return;
        mutating.current = true;
        setBusy(true);
        setError('');
        setMessage('');
        try {
            let target = path, method = 'POST', body: unknown, version: number;
            if (action === 'save') {
                const parsed = design(JSON.parse(content));
                body = { content: parsed, version_note: note, ...(!revision ? { base_revision_id: base || null } : {}) };
                target += revision ? '/revisions/' + revision.revision_id : '/revisions';
                method = revision ? 'PATCH' : 'POST';
                version = revision?.row_version ?? detail.template.row_version;
            }
            else {
                if (!revision)
                    throw Error();
                target += '/revisions/' + revision.revision_id + '/' + action;
                version = revision.row_version;
                body = action === 'preview' ? { expected_revision: version } : action === 'submit-qa' ? { reason } : { reason, confirmed };
            }
            const result = await templateRequest<any>(target, { method, body, version, key: keys.current(target, method, body, version) });
            if (action === 'preview') {
                clearPreview();
                const url = URL.createObjectURL(result.blob);
                previewRef.current = url;
                setPreview({ url, fingerprint: result.fingerprint, version: revision!.row_version, id: revision!.revision_id });
                setMessage('Synthetic PDF ready. This is not physical QA approval.');
            }
            else {
                clearPreview();
                const r: Revision = action === 'save' && revision ? result.result : result.result.revision;
                setRevision(r);
                setBase(r.revision_id);
                setContent(JSON.stringify(r.content, null, 2));
                setNote('');
                setConfirmed(false);
                setReason('');
                setDetail(d => d ? { ...d, template: result.result.template ?? d.template, revisions: [r, ...d.revisions.filter(x => x.revision_id !== r.revision_id)] } : d);
                setMessage(action === 'submit-qa' ? 'Submitted for physical QA. Approval on Template QA will publish this revision automatically.' : action === 'retire' ? 'Revision retired; history retained.' : 'Draft saved.');
            }
        }
        catch (e) {
            if (e instanceof TemplateApiError && [409, 412].includes(e.status))
                setConflict(true);
            setError(templateError(e, ur));
        }
        finally {
            mutating.current = false;
            setBusy(false);
        }
    }
    const previewCurrent = !!preview && preview.id === revision?.revision_id && preview.version === revision.row_version && !dirty;
    const submissionHint = conflict ? 'Load the latest revision before submitting.' : dirty ? 'Save your design changes before generating the PDF.' : !previewCurrent ? 'Generate the saved revision PDF, then open it for review.' : !confirmed ? 'Confirm that you reviewed this PDF.' : reason.trim().length < 4 ? 'Add a review note of at least 4 characters.' : '';
    return <section className={styles.screen}><Link prefetch={false} href="/admin/templates">Back to templates</Link><h1 className="text-2xl font-bold">{detail?.template.name ?? 'Template details'}</h1><button disabled={busy} onClick={() => void load()}>Load latest record (keep edits)</button>{conflict && <p>Load the latest record and compare edits before retrying.</p>}{busy && <p role="status">Working…</p>}<TemplateErrorNotice message={error} ur={ur}/>{message && <p role="status">{message}</p>}{detail && <><p className="break-all">{detail.template.key} · {detail.template.purpose} · template version {detail.template.row_version}</p><p className="break-all">Template ID: {detail.template.template_id} · Created: {detail.template.created_at}</p><AdminStatusBadge label={detail.template.lifecycle_status}/><div className="grid gap-5 lg:grid-cols-2"><section className="rounded-xl border bg-white p-4 space-y-3"><h2 className="font-bold">Revision history</h2>{!detail.revisions.length && <p>No revisions yet.</p>}{detail.revisions.map(r => <button key={r.revision_id} disabled={busy} onClick={() => choose(r)} className="block w-full text-left border rounded p-3">Revision {r.version} · {r.status} · row version {r.row_version}</button>)}{detail.next_cursor && <button disabled={busy} onClick={() => void load(true)}>Load more revisions</button>}{canWrite && <button disabled={busy || detail.template.lifecycle_status === 'retired'} onClick={() => choose(null)}>New draft revision</button>}</section>
 <section className="rounded-xl border bg-white p-4 space-y-3"><h2 className="font-bold">{revision ? 'Revision ' + revision.version : 'New draft revision'}</h2><p className="text-sm">{revision && <>Created: {revision.created_at} · Published: {revision.published_at ?? 'Not published'} · Fingerprint: {revision.fingerprint_sha256 ?? 'Not submitted'}</>}</p><p className="text-sm">Use the form below to configure the sticker. Only enrolled font/logo assets are supported; arbitrary files and URLs are unavailable.</p>{!revision && <label className="block">Base revision<select aria-label="Base revision" value={base} onChange={e => { setBase(e.target.value); const r = detail.revisions.find(r => r.revision_id === e.target.value); if (r)
            setContent(JSON.stringify(r.content, null, 2)); }} className="block max-w-full"><option value="">None (first revision only)</option>{detail.revisions.map(r => <option key={r.revision_id} value={r.revision_id}>Revision {r.version} · {r.status}</option>)}</select></label>}
 <TemplateDesignFields content={content} onChange={value=>{setContent(value);clearPreview();}} readOnly={!canWrite || !!revision && revision.status!=='draft'} purpose={detail.template.purpose}/>
 <details><summary>Advanced design JSON</summary><label className="block">Content JSON<textarea aria-label="Content JSON" rows={6} value={content} readOnly={!canWrite || !!revision && revision.status !== 'draft'} onChange={e => { setContent(e.target.value); clearPreview(); }} className="block w-full font-mono text-xs border rounded p-2"/></label></details>{revision && <details><summary>Latest server content for comparison</summary><pre className="overflow-auto text-xs">{JSON.stringify(revision.content, null, 2)}</pre></details>}
 {canWrite && (!revision || revision.status === 'draft') && <><label className="block">Version note<input minLength={4} maxLength={500} value={note} onChange={e => setNote(e.target.value)} className="block w-full border p-2"/></label><button disabled={busy || conflict || note.trim().length < 4 || !revision && detail.revisions.length > 0 && !base} onClick={() => void mutate('save')}>Save draft</button></>}
 {canWrite && revision?.status === 'draft' && <><button disabled={busy || conflict || dirty} onClick={() => void mutate('preview')}>Generate synthetic PDF preview</button><label className="block">QA / retirement reason<input value={reason} maxLength={500} onChange={e => setReason(e.target.value)} className="block w-full border p-2"/></label><label className="block"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> I reviewed the current revision and confirm this lifecycle action.</label><button disabled={busy || conflict || !previewCurrent || !confirmed || reason.trim().length < 4} onClick={() => void mutate('submit-qa')}>Submit for independent QA</button>{submissionHint && <p role="status">{submissionHint}</p>}<p className="text-sm">After submission, print and review the PDF on Template QA. Approve QA will publish the same revision automatically.</p></>}
 {revision?.status === 'pending_qa' && <p role="status">Awaiting physical QA. <Link prefetch={false} href="/admin/template-qa">Open Template QA</Link> to review the PDF. Approval publishes this revision automatically.</p>}
 {revision?.status === 'published' && <><p role="status">This revision is published. No additional QA submission or PDF generation is required. Product assignment is a separate action.</p>{canWrite && <><label className="block">QA / retirement reason<input value={reason} maxLength={500} onChange={e => setReason(e.target.value)} className="block w-full border p-2"/></label><label className="block"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> I reviewed the current revision and confirm this lifecycle action.</label><button disabled={busy || conflict || dirty || !confirmed || reason.trim().length < 4} onClick={() => void mutate('retire')}>Retire published revision</button><p className="text-sm">Retirement requires backend publisher authorization and no active bindings. Rejections retain input.</p></>}</>}

 {previewCurrent && <div className="break-all"><p>Fingerprint: {preview!.fingerprint}</p><a href={preview!.url} target="_blank" rel="noreferrer">Open synthetic PDF preview</a></div>}</section></div><TemplateBindings template={detail.template} revisions={detail.revisions} canWrite={canWrite} ur={ur}/></>}</section>;
}
