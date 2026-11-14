"use client";
import { TemplateErrorNotice } from "./template-error-notice";
import React, { useEffect, useRef, useState } from 'react';
import { templateRequest, templateError, intentKeys } from '../lib/admin-templates-client';
import type { TemplateRecord, Revision, BindingPage, Binding, Receipt } from '../lib/admin-templates-contract';
import type { Product } from '../lib/admin-products-contract';
export function TemplateBindings({ template, revisions, canWrite, ur }: {
    template: TemplateRecord;
    revisions: Revision[];
    canWrite: boolean;
    ur: boolean;
}) {
    const [products, setProducts] = useState<Product[]>([]), [next, setNext] = useState<string | null>(null), [product, setProduct] = useState<Product | null>(null), [variantId, setVariantId] = useState(''), [bindings, setBindings] = useState<Binding[]>([]), [complete, setComplete] = useState(false), [rev, setRev] = useState(''), [confirmed, setConfirmed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
    const keys = useRef(intentKeys()), mutating = useRef(false);
    const variant = product?.variants.find(v => v.id === variantId), active = bindings.filter(b => b.is_active), published = revisions.filter(r => r.status === 'published');
    const selectedPublished = published.some(r => r.revision_id === rev);
    useEffect(() => {
        // Refresh/retirement must invalidate a selection that is no longer published.
        if (rev && !selectedPublished) { setRev(''); setConfirmed(false); setComplete(false); }
    }, [rev, selectedPublished]);
    async function catalog(cursor?: string) { setBusy(true); setError(''); try {
        const p = await templateRequest<{
            items: Product[];
            next_cursor: string | null;
        }>('/admin/products', { query: { limit: '50', ...(cursor ? { cursor } : {}) } });
        setProducts(old => cursor ? [...old, ...p.items] : p.items);
        setNext(p.next_cursor);
    }
    catch (e) {
        setError(templateError(e, ur));
    }
    finally {
        setBusy(false);
    } }
    async function selectProduct(id: string) { setProduct(null); setVariantId(''); setBindings([]); setComplete(false); setConfirmed(false); setNextBinding(null); setRev(''); setMessage(''); setError(''); if (!id)
        return; setBusy(true); try {
        setProduct(await templateRequest<Product>('/admin/products/' + id));
    }
    catch (e) {
        setError(templateError(e, ur));
    }
    finally {
        setBusy(false);
    } }
    async function loadBindings(cursor?: string) { if (!variant)
        return; setBusy(true); setComplete(false); setConfirmed(false); setError(''); try {
        const p = await templateRequest<BindingPage>('/admin/print-template-bindings', { query: { variant_id: variant.id, tag_type: template.purpose, limit: '50', ...(cursor ? { cursor } : {}) } });
        setBindings(old => cursor ? [...old, ...p.items] : p.items);
        setNextBinding(p.next_cursor);
        setComplete(p.next_cursor === null);
    }
    catch (e) {
        setError(templateError(e, ur));
    }
    finally {
        setBusy(false);
    } }
    const [nextBinding, setNextBinding] = useState<string | null>(null);
    async function bind() { if (!variant || !complete || !confirmed || !!rev && !selectedPublished || !rev && (variant.is_active || !active.length) || active.length > 1 || mutating.current)
        return; mutating.current = true; setBusy(true); setError(''); try {
        const path = '/admin/print-template-bindings', body = { variant_id: variant.id, tag_type: template.purpose, revision_id: rev || null, expected_variant_version: variant.catalog_version, expected_binding_id: active[0]?.binding_id ?? null, confirmed };
        await templateRequest<Receipt<{
            binding: Binding;
            variant_row_version: number;
        }>>(path, { method: 'POST', body, version: variant.catalog_version, key: keys.current(path, 'POST', body, variant.catalog_version) });
        setMessage('Binding command accepted. Reload product and binding metadata before another change.');
        setComplete(false);
        setConfirmed(false);
        setProduct(null);
        setVariantId('');
    }
    catch (e) {
        setError(templateError(e, ur));
        setComplete(false);
    }
    finally {
        mutating.current = false;
        setBusy(false);
    } }
    return <section className="rounded-xl border bg-white p-4 space-y-3"><h2 className="font-bold">Product variant bindings</h2><p>Metadata only. Select a catalog product and variant, then load all current bindings. The backend enforces published revision, purpose, size, material and template compatibility.</p><button disabled={busy} onClick={() => void catalog()}>Load product picker</button>{next && <button disabled={busy} onClick={() => void catalog(next)}>More products</button>}<label className="block">Product<select aria-label="Binding product" value={product?.id ?? ''} disabled={busy} onChange={e => void selectProduct(e.target.value)}><option value="">Select product</option>{products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>{product && <label className="block">Variant<select aria-label="Binding variant" value={variantId} disabled={busy} onChange={e => { setVariantId(e.target.value); setBindings([]); setComplete(false); setNextBinding(null); setRev(''); setConfirmed(false); setMessage(''); }}><option value="">Select variant</option>{product.variants.map(v => <option key={v.id} value={v.id}>{v.name} · {v.size_mm} · {v.material}</option>)}</select></label>}{variant && <><p>Variant version {variant.catalog_version} · {variant.is_active ? 'active' : 'inactive'}</p><button disabled={busy} onClick={() => void loadBindings()}>Load / refresh scoped bindings</button>{nextBinding && <button disabled={busy} onClick={() => void loadBindings(nextBinding)}>More scoped bindings</button>}{bindings.map(b => <p key={b.binding_id} className="break-all">{b.binding_id} · {b.is_active ? 'active' : 'historical'} · revision {b.revision_id}</p>)}{complete && <p>Complete binding snapshot loaded for this variant and purpose.</p>}{canWrite && <><label className="block">Published revision<select aria-label="Binding revision" value={rev} onChange={e => { setRev(e.target.value); setConfirmed(false); }}><option value="">Deactivate current binding (inactive variant only)</option>{published.map(r => <option key={r.revision_id} value={r.revision_id}>Revision {r.version}</option>)}</select></label><label className="block"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> Confirm binding replacement or deactivation.</label><button disabled={busy || !complete || !confirmed || !!rev && !selectedPublished || active.length > 1 || !rev && (variant.is_active || !active.length)} onClick={() => void bind()}>Apply binding</button></>}</>}<TemplateErrorNotice message={error} ur={ur}/>{message && <p role="status">{message}</p>}</section>;
}
