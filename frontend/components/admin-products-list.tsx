"use client";
import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { AdminCard, AdminEmptyState, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { productRequest, productError } from '../lib/admin-products-client';
import type { Product } from '../lib/admin-products-contract';
export function ProductsList({ ur = false }: {
    ur?: boolean;
}) {
    const [items, setItems] = useState<Product[]>([]), [next, setNext] = useState<string | null>(null), [cursor, setCursor] = useState<string | undefined>(), [history, setHistory] = useState<(string | undefined)[]>([]), [busy, setBusy] = useState(true), [error, setError] = useState(''), [revision, setRevision] = useState(0);
    const reload = useCallback(() => setRevision(n => n + 1), []);
    useEffect(() => { const controller = new AbortController(); setBusy(true); setError(''); setItems([]); setNext(null); productRequest<{
        items: Product[];
        next_cursor: string | null;
    }>('/admin/products', { cursor, signal: controller.signal }).then(v => { if (!controller.signal.aborted) {
        setItems(v.items);
        setNext(v.next_cursor);
    } }).catch(e => { if (!controller.signal.aborted)
        setError(productError(e, ur)); }).finally(() => { if (!controller.signal.aborted)
        setBusy(false); }); return () => controller.abort(); }, [cursor, revision, ur]);
    return <div className="space-y-4"><AdminPageHeader title={ur ? 'مصنوعات' : 'Products'} description={ur ? 'اصل کیٹلاگ — فی کاپی ایک PKR قیمت' : 'Manage the SafeReturn catalog. One PKR price per copy across all sizes.'} actions={<Link prefetch={false} href="/admin/products/new" className="rounded-lg bg-[#0A756E] text-white px-4 py-2 text-sm">{ur ? 'نئی مصنوعہ' : 'Add Product'}</Link>}/>
 <AdminCard><div className="p-4 flex flex-wrap gap-3 justify-between text-sm"><p>{ur ? 'سرور کرسر استعمال ہوتا ہے؛ عالمی تلاش اور کل تعداد دستیاب نہیں۔' : 'Cursor pagination is provided by the server. Global search, filters and total counts are unavailable.'}</p><button type="button" disabled={busy} onClick={reload}>{ur ? 'تازہ کریں' : 'Refresh products'}</button></div>
 {busy ? <p role="status" className="p-6">{ur ? 'لوڈ ہو رہا ہے…' : 'Loading products…'}</p> : error ? <p role="alert" className="p-6 text-red-800">{error}</p> : items.length === 0 ? <AdminEmptyState title={ur ? 'کوئی مصنوعات نہیں' : 'No products on this page'} description={ur ? 'نئی ڈرافٹ مصنوعہ شامل کریں یا پچھلے صفحے پر جائیں۔' : 'Create a draft product or return to the previous page.'}/> : <div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="bg-slate-50 text-slate-600"><tr>{['Product', 'Sizes', 'Price per copy (PKR)', 'Status', 'Actions'].map(t => <th key={t} scope="col" className="p-4">{t}</th>)}</tr></thead><tbody>{items.map(p => <tr key={p.id} className="border-t border-slate-100"><td className="p-4"><strong>{p.name}</strong><div className="text-xs text-slate-500 break-all">{p.slug}</div></td><td className="p-4">{p.variants.length}</td><td className="p-4">{p.price_per_copy === null ? 'Not configured' : `PKR ${p.price_per_copy}`}</td><td className="p-4"><AdminStatusBadge label={p.lifecycle_status} variant={p.lifecycle_status === 'published' ? 'success' : p.lifecycle_status === 'draft' ? 'warning' : 'neutral'}/></td><td className="p-4"><Link prefetch={false} href={'/admin/products/' + p.id} className="text-[#0A756E] font-semibold">{ur ? 'تفصیلات' : 'View details'}</Link></td></tr>)}</tbody></table></div>}
 <nav aria-label="Product pages" className="p-4 flex gap-4 border-t border-slate-100"><button disabled={busy || history.length === 0} onClick={() => { setCursor(history.at(-1)); setHistory(h => h.slice(0, -1)); }}>Previous page</button><button disabled={busy || !!error || !next} onClick={() => { setHistory(h => [...h, cursor]); setCursor(next ?? undefined); }}>Next page</button></nav></AdminCard></div>;
}
