"use client";
import { TemplateErrorNotice } from "./template-error-notice";
import styles from './admin-templates.module.css';
import React, { useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAdminRole } from './admin-shell';
import { templateRequest, templateError, intentKeys } from '../lib/admin-templates-client';
import { createBody, TemplateValidation, type TemplateRecord, type Receipt } from '../lib/admin-templates-contract';
export function CreateTemplateKeyForm({ ur = false, onSuccess, onCancel }: {
    ur?: boolean;
    isModal?: boolean;
    onSuccess?: (t: TemplateRecord) => void;
    onCancel?: () => void;
}) {
    const router = useRouter(), { authenticatedRoles } = useAdminRole(), keys = useRef(intentKeys()), submitting = useRef(false);
    const [key, setKey] = useState(''), [name, setName] = useState(''), [purpose, setPurpose] = useState('lost'), [busy, setBusy] = useState(false), [error, setError] = useState(''), [field, setField] = useState('');
    async function submit(e: React.FormEvent) { e.preventDefault(); if (submitting.current)
        return; submitting.current = true; setError(''); setField(''); setBusy(true); try {
        const body = createBody({ key, name, purpose }), path = '/admin/print-templates';
        const r = await templateRequest<Receipt<TemplateRecord>>(path, { method: 'POST', body, key: keys.current(path, 'POST', body) });
        if (onSuccess)
            onSuccess(r.result);
        else
            router.push('/admin/templates/' + r.result.template_id);
    }
    catch (e) {
        if (e instanceof TemplateValidation)
            setField(e.field);
        setError(templateError(e, ur));
    }
    finally {
        submitting.current = false;
        setBusy(false);
    } }
    if (!authenticatedRoles.includes('operations'))
        return <p role="alert">Operations role required to create a template.</p>;
    return <form onSubmit={submit} className="max-w-xl space-y-4"><p>This creates design metadata with no revisions. An enrolled asset-set ID is required when adding design content.</p><label className="block">Template key<input aria-invalid={field === 'key'} required minLength={3} maxLength={80} pattern="[A-Za-z0-9._-]+" value={key} onChange={e => setKey(e.target.value)} className="block w-full rounded border p-2"/></label><label className="block">Name<input aria-invalid={field === 'name'} required maxLength={100} value={name} onChange={e => setName(e.target.value)} className="block w-full rounded border p-2"/></label><label className="block">Purpose<select value={purpose} onChange={e => setPurpose(e.target.value)} className="block border p-2"><option value="lost">Lost</option><option value="ice">ICE</option></select></label><TemplateErrorNotice message={error} ur={ur}/><button disabled={busy} className="rounded bg-teal-700 px-4 py-2 text-white">{busy ? 'Creating…' : 'Create template'}</button>{onCancel && <button type="button" onClick={onCancel}>Cancel</button>}</form>;
}
export function CreatePrintTemplatePage({ ur = false }: {
    ur?: boolean;
}) { return <section className={styles.screen}><Link prefetch={false} href="/admin/templates">Back to templates</Link><h1 className="text-2xl font-bold">Create print template</h1><CreateTemplateKeyForm ur={ur}/></section>; }
