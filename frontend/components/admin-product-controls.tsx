"use client";
import { useRef, useState } from 'react';
import { AdminCard } from './admin-ui';
import { useTemplateChoices } from './catalog-template-picker';
import { productRequest, productError, intentKeys, ProductApiError } from '../lib/admin-products-client';
import { categoryBody, variantBody, imageBody, parseGrant, type Product, type Category, type CategoryBody, type Variant, type VariantBody, type ProductImage, type ImageEdit } from '../lib/admin-products-contract';
const input = 'w-full rounded-lg border border-slate-300 bg-white p-2 text-sm focus:outline-[#0A756E]';
const button = 'rounded-lg bg-[#0A756E] text-white px-4 py-2 text-sm font-semibold disabled:opacity-50';
function merge<T extends object>(draft: T, base: T, fresh: T): T { const result = { ...fresh }; for (const key of Object.keys(draft) as (keyof T)[])
    if (JSON.stringify(draft[key]) !== JSON.stringify(base[key]))
        result[key] = draft[key]; return result; }
function useCommand() {
    const keys = useRef(intentKeys()), running = useRef(false), [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [stale, setStale] = useState(false);
    async function run(work: () => Promise<void>) { if (running.current)
        return; running.current = true; setBusy(true); setError(''); setNotice(''); try {
        await work();
    }
    catch (e) {
        setError(productError(e));
        if (e instanceof ProductApiError && [409, 412].includes(e.status))
            setStale(true);
    }
    finally {
        running.current = false;
        setBusy(false);
    } }
    async function command<T>(path: string, method: string, body: unknown, version?: number, upload = false) { return productRequest<T>(path, { method, body, version, upload, key: keys.current(path, method, body, version, upload) }); }
    return { busy, error, notice, stale, setStale, setNotice, setError, run, command, resetKeys: () => { keys.current = intentKeys(); } };
}
function Feedback({ state }: {
    state: ReturnType<typeof useCommand>;
}) { return <>{state.error && <p role="alert" className="text-sm text-red-800">{state.error}</p>}{state.notice && <p role="status" className="text-sm text-emerald-800">{state.notice}</p>}</>; }
const blankCategory: CategoryBody = { name: '', slug: '', sort_order: 0, is_active: true };
function catFields(c: Category): CategoryBody { return { name: c.name, slug: c.slug, sort_order: c.sort_order, is_active: c.is_active }; }
export function ProductCategories({ categories, onChange, onSaved }: {
    categories: Category[];
    onChange: (c: Category[]) => void;
    onSaved?: (c: Category) => void;
}) {
    const state = useCommand(), [selected, setSelected] = useState<Category | null>(null), [form, setForm] = useState<CategoryBody>({ ...blankCategory });
    const base = useRef<CategoryBody>({ ...blankCategory });
    function select(c: Category | null) { setSelected(c); const f = c ? catFields(c) : { ...blankCategory }; base.current = f; setForm(f); state.setStale(false); }
    async function save() {
        if (state.stale)
            return;
        let body: CategoryBody;
        try {
            body = categoryBody(form);
        }
        catch {
            state.setError('Enter a category name, lowercase slug and valid sort order.');
            return;
        }
        if (selected?.is_active && !body.is_active && !window.confirm('Deactivate this category? Published products may become unavailable.'))
            return;
        await state.run(async () => { const saved = await state.command<Category>(selected ? '/admin/catalog/categories/' + selected.id : '/admin/catalog/categories', selected ? 'PATCH' : 'POST', body, selected?.catalog_version); onChange([...categories.filter(c => c.id !== saved.id), saved].sort((a, b) => a.sort_order - b.sort_order)); onSaved?.(saved); select(saved); state.setNotice('Category saved by the server.'); });
    }
    return <AdminCard><details className="p-5"><summary className="cursor-pointer font-semibold">Manage categories</summary><div className="mt-4 space-y-4"><Feedback state={state}/><form onSubmit={e => { e.preventDefault(); void save(); }}><fieldset disabled={state.busy} className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <label>Category to edit<select aria-label="Category to edit" className={input} value={selected?.id ?? ''} onChange={e => select(categories.find(c => c.id === e.target.value) ?? null)}><option value="">Create category</option>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
 <label>Category name<input className={input} required maxLength={120} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}/></label><label>Category slug<input className={input} required minLength={2} maxLength={60} pattern="[a-z0-9][a-z0-9\-]+" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })}/></label>
 <label>Category sort order<input className={input} type="number" required min={-100000} max={100000} value={form.sort_order} onChange={e => setForm({ ...form, sort_order: e.target.valueAsNumber })}/></label><label><input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })}/> Active category</label>
 <div><button className={button} disabled={state.stale} type="submit">{selected ? 'Save category' : 'Create category'}</button></div></fieldset></form>
 {state.stale && selected && <button disabled={state.busy} onClick={() => void state.run(async () => { const latest = await productRequest<{
        items: Category[];
    }>('/admin/catalog/categories'); const c = latest.items.find(c => c.id === selected.id); if (!c)
        throw new ProductApiError(404); setForm(merge(form, base.current, catFields(c))); base.current = catFields(c); setSelected(c); onChange(latest.items); state.setStale(false); state.setNotice('Latest category loaded; review retained edits before saving.'); })}>Load latest category (keep edits)</button>}
 <p className="text-xs text-slate-500">Publishing requires an active category whose category slug is exactly qr-stickers. The product slug is separate. Edit the existing qr-stickers category if present; otherwise create it with Active category checked. Saving that category selects it for this product; save the product to persist the selection. Other categories cannot be published. Category list is capped at 100. No delete operation is available.</p></div></details></AdminCard>;
}
const blankVariant: VariantBody = { sku: '', name: '', size_mm: '30', material: 'vinyl', color: null, fulfillment_method: 'pdf_label', template_key: null, template_version: 1, is_active: true, sort_order: 0 };
function varFields(v: Variant): VariantBody { return { sku: v.sku, name: v.name, size_mm: v.size_mm, material: v.material, color: v.color, fulfillment_method: v.fulfillment_method as VariantBody['fulfillment_method'], template_key: v.template_key, template_version: v.template_version, is_active: v.is_active, sort_order: v.sort_order }; }
export function ProductVariants({ product, reload }: {
    product: Product;
    reload: () => Promise<void>;
}) {
    const state = useCommand(), [editing, setEditing] = useState(false), [selected, setSelected] = useState<Variant | null>(null), [form, setForm] = useState<VariantBody>({ ...blankVariant }), [epoch, setEpoch] = useState(0), [version, setVersion] = useState<number | null>(null), [parentVersion, setParentVersion] = useState<number | null>(null), base = useRef<VariantBody>({ ...blankVariant });
    const choices = useTemplateChoices(editing, epoch);
    function select(v: Variant | null) { setSelected(v); const fields = v ? varFields(v) : { ...blankVariant }; base.current = fields; setForm(fields); setVersion(v?.catalog_version ?? null); setParentVersion(product.catalog_version); state.setStale(false); setEditing(true); setEpoch(n => n + 1); }
    async function save() {
        if (state.stale)
            return;
        let body: VariantBody;
        try {
            body = variantBody(form);
        }
        catch {
            state.setError('Check SKU, name, decimal size and variant attributes. No size-specific price is accepted.');
            return;
        }
        if (selected?.is_active && !body.is_active && !window.confirm('Deactivate this size? Existing purchases retain their saved attributes.'))
            return;
        await state.run(async () => { const saved = await state.command<Variant>(selected ? '/admin/product-variants/' + selected.id : '/admin/products/' + product.id + '/variants', selected ? 'PATCH' : 'POST', body, selected ? (version ?? selected.catalog_version) : (parentVersion ?? product.catalog_version)); setSelected(saved); setVersion(saved.catalog_version); base.current = body; state.setNotice('Size saved by the server.'); setEditing(false); try {
            await reload();
        }
        catch {
            state.setError('Size was saved, but refreshing failed. Refresh the page before another change.');
            state.setStale(true);
        } });
    }
    return <AdminCard><section className="p-5 space-y-4"><div className="flex flex-wrap gap-3 justify-between"><h2 style={{ fontSize: 16, margin: 0 }} className="font-semibold">Available sizes and variants</h2><button className={button} disabled={state.busy} onClick={() => select(null)}>Add variant</button></div><Feedback state={state}/><p className="text-xs text-slate-500">All sizes use the product price per copy. For Lost/Emergency products, saving a published template also binds it when QR type, exact size and material match.</p>
 <div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead><tr>{['Size / name', 'SKU', 'Material / color', 'Availability', 'Action'].map(t => <th key={t} className="p-2">{t}</th>)}</tr></thead><tbody>{product.variants.map(v => <tr key={v.id} className="border-t"><td className="p-2">{v.size_mm ?? 'Unspecified'} mm — {v.name}</td><td className="p-2">{v.sku}</td><td className="p-2">{v.material ?? 'Unspecified'} / {v.color ?? 'Unspecified'}</td><td className="p-2">{v.is_active ? 'Active' : 'Inactive'}</td><td className="p-2"><button disabled={state.busy} onClick={() => select(v)}>Edit size</button></td></tr>)}</tbody></table></div>{product.variants.length === 0 && <p>No variants yet.</p>}
 {editing && <form onSubmit={e => { e.preventDefault(); void save(); }}><fieldset disabled={state.busy} className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t pt-4"><legend className="font-semibold">{selected ? 'Edit variant' : 'New variant'}</legend>
 <label>Variant name<input className={input} required maxLength={160} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}/></label><label>SKU<input className={input} required minLength={2} maxLength={60} pattern="[A-Za-z0-9][A-Za-z0-9._\-]+" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })}/></label>
 <label>Size (mm)<input className={input} inputMode="decimal" value={form.size_mm ?? ''} onChange={e => setForm({ ...form, size_mm: e.target.value || null })}/></label><label>Material<input className={input} maxLength={120} value={form.material ?? ''} onChange={e => setForm({ ...form, material: e.target.value || null })}/></label><label>Color<input className={input} maxLength={80} value={form.color ?? ''} onChange={e => setForm({ ...form, color: e.target.value || null })}/></label>
 <label>Fulfillment method<select className={input} value={form.fulfillment_method} onChange={e => setForm({ ...form, fulfillment_method: e.target.value })}><option value="pdf_label">PDF label</option><option value="manufacturer_artwork">Manufacturer artwork</option><option value="manual">Manual</option></select></label>
 <label>Approved template reference<select aria-label="Approved template reference" disabled={!choices.fresh} className={input} value={form.template_key ? form.template_key + '@' + form.template_version : ''} onChange={e => { const value = e.target.value; if (!value)
            setForm({ ...form, template_key: null });
        else {
            const index = value.lastIndexOf('@');
            setForm({ ...form, template_key: value.slice(0, index), template_version: Number(value.slice(index + 1)) });
        } }}><option value="">Unassigned</option>{form.template_key && !choices.data?.items.some(c => c.template_key === form.template_key && c.template_version === form.template_version) && <option value={form.template_key + '@' + form.template_version}>{form.template_key}@{form.template_version} (current; availability unconfirmed)</option>}{choices.data?.items.map(c => <option key={c.template_key + '@' + c.template_version} value={c.template_key + '@' + c.template_version}>{c.template_key}@{c.template_version}</option>)}</select>{choices.mode === 'unavailable' && <small role="alert">Template choices unavailable. The current reference is preserved.</small>}{choices.mode === 'loading' && <small role="status">Loading published templates…</small>}{choices.fresh && !choices.data?.items.length && <small role="status">No published or configured templates available.</small>}<button type="button" disabled={state.busy || choices.mode === 'loading'} onClick={() => void choices.refresh()}>Refresh templates</button></label>
 <label>Variant sort order<input className={input} type="number" required min={-100000} max={100000} value={form.sort_order} onChange={e => setForm({ ...form, sort_order: e.target.valueAsNumber })}/></label><label><input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })}/> Active variant</label><div className="flex gap-4"><button type="submit" className={button} disabled={state.stale}>Save variant</button><button type="button" onClick={() => setEditing(false)}>Cancel variant edit</button></div></fieldset></form>}
 {state.stale && editing && <button disabled={state.busy} onClick={() => void state.run(async () => { const fresh = await productRequest<Product>('/admin/products/' + product.id); if (selected) {
        const v = fresh.variants.find(v => v.id === selected.id);
        if (!v)
            throw new ProductApiError(404);
        setForm(merge(form, base.current, varFields(v)));
        base.current = varFields(v);
        setVersion(v.catalog_version);
    } setParentVersion(fresh.catalog_version); await reload(); state.setStale(false); state.setNotice('Latest variant loaded. Review retained edits before saving.'); })}>Load latest variant (keep edits)</button>}
 </section></AdminCard>;
}
function imFields(i: ProductImage): ImageEdit { return { alt_text: i.alt_text, sort_order: i.sort_order, is_primary: i.is_primary }; }
export function ProductAssets({ product, reload }: {
    product: Product;
    reload: () => Promise<void>;
}) {
    const state = useCommand(), [file, setFile] = useState<File | null>(null), [alt, setAlt] = useState(''), [primary, setPrimary] = useState(false), [selected, setSelected] = useState<ProductImage | null>(null), [form, setForm] = useState<ImageEdit>({ alt_text: '', sort_order: 0, is_primary: false }), [version, setVersion] = useState<number | null>(null), inputRef = useRef<HTMLInputElement>(null), base = useRef<ImageEdit>(form);
    const progress = useRef<{
        signature: string;
        grant: ReturnType<typeof parseGrant>;
        uploaded: boolean;
    } | null>(null);
    async function upload() {
        if (state.stale)
            return;
        if (!file || !alt.trim() || file.size <= 0 || file.size > 5 * 1024 * 1024 || !['image/png', 'image/jpeg', 'image/webp', 'image/avif'].includes(file.type)) {
            state.setError('Select a public raster image up to 5 MB and enter its description.');
            return;
        }
        await state.run(async () => {
            const path = '/admin/products/' + product.id + '/images', body = { cloudinary_public_id: 'safereturn/catalog/pending', alt_text: alt, sort_order: product.images.length, is_primary: primary }, signature = JSON.stringify([file.name, file.type, file.size, file.lastModified, product.id, product.catalog_version, alt, primary]);
            if (progress.current?.signature !== signature) {
                const grant = await state.command<ReturnType<typeof parseGrant>>(path, 'POST', body, product.catalog_version, true);
                progress.current = { signature, grant, uploaded: false };
            }
            const p = progress.current;
            if (p.grant.id !== product.id || p.grant.catalog_version !== product.catalog_version)
                throw new ProductApiError(412);
            if (!p.uploaded) {
                if (Date.now() / 1000 >= p.grant.expires_at)
                    throw new ProductApiError(409);
                const data = new FormData();
                for (const [k, v] of Object.entries(p.grant.upload_params))
                    data.set(k, v);
                data.set('file', file);
                let response: Response;
                try {
                    response = await fetch(p.grant.upload_url, { method: 'POST', body: data, redirect: 'error', signal: AbortSignal.timeout(60000) });
                }
                catch {
                    throw new ProductApiError(503);
                }
                if (!response.ok && response.status !== 409)
                    throw new ProductApiError(503);
                p.uploaded = true;
            }
            await state.command<ProductImage>(path, 'POST', { ...body, cloudinary_public_id: p.grant.public_id }, product.catalog_version);
            progress.current = null;
            setFile(null);
            if (inputRef.current)
                inputRef.current.value = '';
            setAlt('');
            setPrimary(false);
            state.setNotice('Product image verified and attached by the server.');
            try {
                await reload();
            }
            catch {
                state.setError('Image was saved, but refreshing failed. Reload before another change.');
                state.setStale(true);
            }
        });
    }
    async function edit(remove = false) {
        if (!selected || state.stale)
            return;
        if (remove && !window.confirm('Remove this catalog image link? Publication requirements still apply.'))
            return;
        let body: ImageEdit | undefined;
        try {
            body = remove ? undefined : imageBody(form, true) as ImageEdit;
        }
        catch {
            state.setError('Enter valid image metadata.');
            return;
        }
        await state.run(async () => { await state.command<ProductImage>('/admin/products/' + product.id + '/images/' + selected.id, remove ? 'DELETE' : 'PATCH', body, version ?? product.catalog_version); setSelected(null); state.setNotice(remove ? 'Image link removed by the server.' : 'Image metadata saved by the server.'); try {
            await reload();
        }
        catch {
            state.setError('Image change saved, but refresh failed. Reload before another change.');
            state.setStale(true);
        } });
    }
    return <AdminCard><section className="p-5 space-y-4"><h2 style={{ fontSize: 16, margin: 0 }} className="font-semibold">Product images</h2><Feedback state={state}/><div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{[...product.images].sort((a, b) => a.sort_order - b.sort_order).map(i => <div className="rounded-lg border border-slate-200 p-3 space-y-2" key={i.id}>{i.verified_public_url && <img src={i.verified_public_url} alt={i.alt_text} loading="lazy" referrerPolicy="no-referrer" className="w-full h-32 object-contain"/>}<p className="text-sm">{i.alt_text}{i.is_primary ? ' — Main image' : ''}</p><button disabled={state.busy} onClick={() => { setSelected(i); const f = imFields(i); base.current = f; setForm(f); setVersion(product.catalog_version); state.setStale(false); }}>Edit image metadata</button></div>)}</div>
 {selected && <form onSubmit={e => { e.preventDefault(); void edit(); }}><fieldset disabled={state.busy} className="space-y-3 rounded-lg bg-slate-50 p-4"><legend>Edit image</legend><label className="block">Image alt text<input className={input} required maxLength={240} value={form.alt_text} onChange={e => setForm({ ...form, alt_text: e.target.value })}/></label><label className="block">Image sort order<input className={input} type="number" required min={-100000} max={100000} value={form.sort_order} onChange={e => setForm({ ...form, sort_order: e.target.valueAsNumber })}/></label><label><input type="checkbox" checked={form.is_primary} onChange={e => setForm({ ...form, is_primary: e.target.checked })}/> Main image</label><div className="flex flex-wrap gap-4"><button className={button} disabled={state.stale} type="submit">Save image metadata</button><button disabled={state.stale} type="button" onClick={() => void edit(true)}>Remove image</button><button type="button" onClick={() => setSelected(null)}>Cancel image edit</button></div></fieldset></form>}
 <form onSubmit={e => { e.preventDefault(); void upload(); }}><fieldset disabled={state.busy} className="space-y-3 border-t pt-4"><legend className="font-semibold">Add product image</legend><label className="block">Public raster file<input ref={inputRef} className={input} type="file" required accept="image/png,image/jpeg,image/webp,image/avif" onChange={e => { setFile(e.target.files?.[0] ?? null); progress.current = null; }}/></label><label className="block">New image description<input className={input} required maxLength={240} value={alt} onChange={e => setAlt(e.target.value)}/></label><label><input type="checkbox" checked={primary} onChange={e => setPrimary(e.target.checked)}/> Use as main image</label><div><button className={button} disabled={state.stale} type="submit">{state.busy ? 'Uploading…' : 'Upload and attach image'}</button></div><p className="text-xs text-slate-500">Public catalog artwork only, up to 5 MB. The server authorizes upload, verifies the provider asset and then attaches it.</p></fieldset></form>
 {state.stale && <button disabled={state.busy} onClick={() => void state.run(async () => { const fresh = await productRequest<Product>('/admin/products/' + product.id); if (selected) {
        const image = fresh.images.find(i => i.id === selected.id);
        if (!image)
            throw new ProductApiError(404);
        setForm(merge(form, base.current, imFields(image)));
        base.current = imFields(image);
    } setVersion(fresh.catalog_version); progress.current = null; state.resetKeys(); await reload(); state.setStale(false); state.setNotice('Latest image version loaded. Review retained inputs before saving.'); })}>Load latest images (keep edits)</button>}
 </section></AdminCard>;
}
