"use client";
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AdminCard, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { AdminConfirmDialog } from './admin-confirm-dialog';
import { ProductCategories, ProductAssets, ProductVariants } from './admin-product-controls';
import { productRequest, productError, intentKeys, ProductApiError } from '../lib/admin-products-client';
import { productBody, uuid, type Product, type ProductBody, type Category } from '../lib/admin-products-contract';
export const productInput = 'w-full rounded-lg border border-slate-300 bg-white p-2 text-sm focus:outline-[#0A756E]';
export const productButton = 'rounded-lg bg-[#0A756E] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50';
const blank: ProductBody = { name: '', slug: '', description: null, category_id: null, qr_type: 'lost', price_per_copy: '', max_order_copies: 100, lifecycle_status: 'draft', is_featured: false, featured_sort_order: 0 };
export function productFields(p: Product): ProductBody { return { name: p.name, slug: p.slug, description: p.description, category_id: p.category_id, qr_type: p.qr_type, price_per_copy: p.price_per_copy ?? '', max_order_copies: p.max_order_copies, lifecycle_status: p.lifecycle_status, is_featured: p.is_featured, featured_sort_order: p.featured_sort_order }; }
// Refresh merges untouched server fields while retaining explicit user changes.
export function retainEdits<T extends object>(draft: T, base: T, fresh: T): T { const result = { ...fresh }; for (const k of Object.keys(draft) as (keyof T)[])
    if (JSON.stringify(draft[k]) !== JSON.stringify(base[k]))
        result[k] = draft[k]; return result; }
export interface AddProductFormProps {
    ur?: boolean;
}
export function AddProductForm({ ur = false }: AddProductFormProps) { return <ProductEditor ur={ur} initialEdit/>; }
export function ProductEditor({ productId, initialEdit = false, ur = false }: {
    productId?: string;
    initialEdit?: boolean;
    ur?: boolean;
}) {
    const router = useRouter(), [product, setProduct] = useState<Product | null>(null), [form, setForm] = useState<ProductBody>({ ...blank }), [categories, setCategories] = useState<Category[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(''), [notice, setNotice] = useState(''), [editing, setEditing] = useState(!productId || initialEdit), [busy, setBusy] = useState(false), [conflict, setConflict] = useState(false), [confirm, setConfirm] = useState(false);
    const base = useRef<ProductBody>({ ...blank }), keys = useRef(intentKeys()), running = useRef(false);
    useEffect(() => {
        const controller = new AbortController();
        setLoading(true);
        setError('');
        setProduct(null);
        setNotice('');
        setConflict(false);
        (async () => { try {
            if (productId)
                uuid(productId);
            const [cats, p] = await Promise.all([productRequest<{
                    items: Category[];
                }>('/admin/catalog/categories', { signal: controller.signal }), productId ? productRequest<Product>('/admin/products/' + productId, { signal: controller.signal }) : Promise.resolve(null)]);
            if (controller.signal.aborted)
                return;
            setCategories(cats.items);
            setProduct(p);
            const next = p ? productFields(p) : { ...blank };
            base.current = next;
            setForm(next);
        }
        catch (e) {
            if (!controller.signal.aborted)
                setError(productError(e, ur));
        }
        finally {
            if (!controller.signal.aborted)
                setLoading(false);
        } })();
        return () => controller.abort();
    }, [productId, ur]);
    const field = <K extends keyof ProductBody>(key: K, value: ProductBody[K]) => setForm(old => ({ ...old, [key]: value }));
    const stickerCategory = categories.find(c => c.slug === 'qr-stickers' && c.is_active);
    async function refresh(keep = false) { if (!productId)
        return; const fresh = await productRequest<Product>('/admin/products/' + productId); setProduct(fresh); const fields = productFields(fresh); const previous = base.current; setForm(old => keep ? retainEdits(old, previous, fields) : fields); base.current = fields; }
    async function rebase() { if (running.current)
        return; running.current = true; setBusy(true); setError(''); try {
        await refresh(true);
        setConflict(false);
        setNotice(ur ? 'تازہ ریکارڈ لوڈ ہوا۔ تبدیلیوں کا جائزہ لیں۔' : 'Latest version loaded. Your edits are retained; review the fields before saving.');
    }
    catch (e) {
        setError(productError(e, ur));
    }
    finally {
        running.current = false;
        setBusy(false);
    } }
    async function save() {
        if (running.current || conflict)
            return;
        let body: ProductBody;
        try {
            body = productBody(form, !productId);
        }
        catch {
            setError(ur ? 'درست فیلڈز اور PKR قیمت درج کریں۔' : 'Enter valid fields and a decimal PKR price. Slug requires 2–100 lowercase letters, digits or hyphens.');
            return;
        }
        if (body.lifecycle_status === 'published' && (!stickerCategory || body.category_id !== stickerCategory.id)) {
            setError('Publishing requires the active category with category slug qr-stickers. Select it below, or create/activate it in Manage categories. Changing the product slug does not change its category.');
            setConfirm(false);
            return;
        }
        running.current = true;
        setBusy(true);
        setError('');
        setNotice('');
        try {
            const path = productId ? '/admin/products/' + productId : '/admin/products', method = productId ? 'PATCH' : 'POST';
            const saved = await productRequest<Product>(path, { method, body, version: product?.catalog_version, key: keys.current(path, method, body, product?.catalog_version) });
            // A confirmed creation always navigates to the actual backend ID; no fixture write.
            if (!productId) {
                router.push('/admin/products/' + saved.id + '?edit=true');
                return;
            }
            base.current = { ...body };
            setProduct(old => old ? { ...old, ...saved, variants: old.variants, images: old.images } : saved);
            setNotice(ur ? 'سرور نے تبدیلی محفوظ کر دی۔' : 'Product saved by the server.');
            setEditing(false);
            try {
                await refresh();
            }
            catch (e) {
                setError(productError(e, ur));
                setNotice('Saved by the server, but refreshing the record failed. Reload before making further changes.');
                setConflict(true);
            }
        }
        catch (e) {
            setError(productError(e, ur));
            if (e instanceof ProductApiError && [409, 412].includes(e.status))
                setConflict(true);
        }
        finally {
            running.current = false;
            setBusy(false);
            setConfirm(false);
        }
    }
    const changed = JSON.stringify(form) !== JSON.stringify(base.current);
    useEffect(() => { const leave = (e: BeforeUnloadEvent) => { if (changed) {
        e.preventDefault();
        e.returnValue = '';
    } }; window.addEventListener('beforeunload', leave); return () => window.removeEventListener('beforeunload', leave); }, [changed]);
    return <div className="space-y-5"><AdminPageHeader title={productId ? (ur ? 'مصنوعہ کی تفصیلات' : 'Product Details') : (ur ? 'نئی مصنوعہ' : 'Add Product')} description={ur ? 'اصل کیٹلاگ؛ قیمت ہر سائز کے لیے یکساں ہے۔' : 'Catalog details, images, sizes and one PKR price per copy.'} actions={<Link prefetch={false} href="/admin/products" className="text-sm text-[#0A756E]">{ur ? 'مصنوعات' : 'Back to Products'}</Link>}/>
 {loading && <p role="status">{ur ? 'لوڈ ہو رہا ہے…' : 'Loading product and categories…'}</p>}{error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">{error}{loading ? null : !product && productId ? <button className="ml-3 underline" onClick={() => location.reload()}>Retry loading</button> : null}</div>}{notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-900">{notice}</p>}
 {!loading && (!productId || product) && <><AdminCard><form onSubmit={e => { e.preventDefault(); if (product && form.lifecycle_status !== product.lifecycle_status && ['published', 'archived'].includes(form.lifecycle_status))
            setConfirm(true);
        else
            void save(); }}><fieldset disabled={busy || !editing} className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
 <div className="md:col-span-2 flex flex-wrap gap-3 items-center"><h2 className="font-semibold text-slate-900">{product?.name || 'Product information'}</h2><AdminStatusBadge label={product?.lifecycle_status ?? 'draft'} variant={product?.lifecycle_status === 'published' ? 'success' : 'warning'}/></div>
 <label className="text-sm">Product name<input className={productInput} required maxLength={160} value={form.name} onChange={e => field('name', e.target.value)}/></label>
 <label className="text-sm">Slug<input className={productInput} required minLength={2} maxLength={100} pattern="[a-z0-9][a-z0-9\-]+" value={form.slug} onChange={e => field('slug', e.target.value)}/></label>
 <label className="text-sm md:col-span-2">Description<textarea aria-label="Description" className={productInput} maxLength={4000} value={form.description ?? ''} onChange={e => field('description', e.target.value || null)}/></label>
 <div className="text-sm"><label>Category<select aria-label="Category" className={productInput} value={form.category_id ?? ''} onChange={e => field('category_id', e.target.value || null)}><option value="">Unassigned</option>{categories.map(c => <option key={c.id} value={c.id} disabled={!c.is_active || c.slug !== 'qr-stickers'}>{c.name} — {c.slug}{!c.is_active ? ' (inactive)' : c.slug !== 'qr-stickers' ? ' (publishing unavailable)' : ''}</option>)}</select></label>{stickerCategory ? <><p className="text-xs text-slate-500 mt-1">Only the active qr-stickers category can be published. Product slug is separate.</p>{form.category_id !== stickerCategory.id && <button type="button" className="underline mt-1" onClick={() => { field('category_id', stickerCategory.id); setError(''); }}>Use QR Stickers category</button>}</> : <p role="status" className="text-xs text-amber-800 mt-1">No active qr-stickers category is available. In Manage categories below, edit the existing qr-stickers category and check Active category, or create it if missing. Save the category, then save this product.</p>}</div>
 {product?.commerce_model === 'legacy_pair' && <p role="status" className="md:col-span-2 text-sm">This is a legacy QR-pair product. To sell an independent Lost or Emergency QR, <Link href="/admin/products/new" className="underline">create a new product</Link>. This record cannot be converted.</p>}
 <label className="text-sm">QR type<select aria-label="QR type" className={productInput} required={!productId} disabled={product?.commerce_model === 'legacy_pair' || product?.lifecycle_status === 'published' || product?.lifecycle_status === 'archived'} value={form.qr_type ?? ''} onChange={e => field('qr_type', (e.target.value || null) as ProductBody['qr_type'])}><option value="">Unspecified (legacy)</option><option value="lost">Lost</option><option value="ice">Emergency (ICE)</option></select></label>
 <label className="text-sm">Price per copy (PKR)<input aria-label="Price per copy (PKR)" className={productInput} required inputMode="decimal" pattern="[0-9]{1,10}(\.[0-9]{1,2})?" value={form.price_per_copy} onChange={e => field('price_per_copy', e.target.value)}/><span className="block text-xs text-slate-500 mt-1">One price applies to every size. Historical purchases keep their original prices.</span></label>
 <label className="text-sm">Maximum combined copies<input className={productInput} type="number" required min={1} max={100} step={1} value={form.max_order_copies} onChange={e => field('max_order_copies', e.target.valueAsNumber)}/></label>
 <label className="text-sm">Product status<select aria-label="Product status" className={productInput} disabled={!productId || product?.lifecycle_status === 'archived'} value={form.lifecycle_status} onChange={e => field('lifecycle_status', e.target.value as ProductBody['lifecycle_status'])}><option value="draft">Draft</option><option value="published">Published</option><option value="archived">Archived</option></select></label>
 <label className="text-sm">Featured sort order<input className={productInput} type="number" required min={-100000} max={100000} value={form.featured_sort_order} onChange={e => field('featured_sort_order', e.target.valueAsNumber)}/></label>
 <label className="text-sm flex gap-2"><input type="checkbox" checked={form.is_featured} onChange={e => field('is_featured', e.target.checked)}/>Featured product</label>
 <p className="md:col-span-2 text-xs text-slate-500">{product ? 'Publishing requires approved print-template bindings, sizes and a verified main image. Availability is decided by the backend.' : 'Create a draft first. Add sizes and verified product images on the saved record.'} <Link prefetch={false} href="/admin/templates" className="underline">Manage print templates</Link>. A draft template does not satisfy publication; the published revision must be bound to the applicable size/variant.</p>
 </fieldset><div className="p-5 border-t border-slate-100 flex flex-wrap gap-3 items-center">{editing ? <><button className={productButton} disabled={busy || conflict} type="submit">{busy ? 'Saving…' : productId ? 'Save changes' : 'Create draft'}</button>{product && <button type="button" disabled={busy} onClick={() => { if (!changed || window.confirm('Discard unsaved product edits?')) {
            setForm(base.current);
            setEditing(false);
        } }}>Cancel editing</button>}</> : <button type="button" className={productButton} disabled={busy} onClick={() => setEditing(true)}>Edit product</button>}{conflict && <button type="button" disabled={busy} onClick={() => void rebase()}>Load latest version (keep edits)</button>}{product && <small>Version {product.catalog_version}</small>}</div></form></AdminCard>
 <ProductCategories categories={categories} onChange={setCategories} onSaved={c => { if (c.slug === 'qr-stickers' && c.is_active) { field('category_id', c.id); setEditing(true); setError(''); setNotice('QR Stickers category selected. Save the product to apply this selection.'); } }}/>
 {product && <><ProductVariants product={product} reload={async () => refresh(true)}/><ProductAssets product={product} reload={async () => refresh(true)}/></>}
 </>}
 <AdminConfirmDialog isOpen={confirm} title="Confirm product status change" message={'Save this product as ' + form.lifecycle_status + '? This affects catalog availability. Backend publication checks still apply.'} confirmLabel="Confirm and save" loading={busy} variant={form.lifecycle_status === 'archived' ? 'danger' : 'primary'} onConfirm={() => void save()} onCancel={() => setConfirm(false)}/>
 </div>;
}
