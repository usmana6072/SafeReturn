// Products-only contract. No inventory, order, allocation or credential routes.
import type { Product as StoredProduct, Variant as StoredVariant, ProductImage } from './product-admin';
import { parseTemplateChoices } from './catalog-template-choices';
export type { ProductImage } from './product-admin';
export type Variant = Omit<StoredVariant, 'unit_price'> & {
    unit_price: string | null;
};
export type Product = Omit<StoredProduct, 'variants'> & {
    variants: Variant[];
};
export type Category = {
    id: string;
    name: string;
    slug: string;
    sort_order: number;
    is_active: boolean;
    catalog_version: number;
};
export type ProductBody = {
    name: string;
    slug: string;
    description: string | null;
    category_id: string | null;
    qr_type: 'lost' | 'ice' | null;
    price_per_copy: string;
    max_order_copies: number;
    lifecycle_status: 'draft' | 'published' | 'archived';
    is_featured: boolean;
    featured_sort_order: number;
};
export type VariantBody = Omit<Variant, 'id' | 'catalog_version' | 'currency_code' | 'unit_price'>;
export type CategoryBody = Omit<Category, 'id' | 'catalog_version'>;
export type ImageBody = {
    cloudinary_public_id: string;
    alt_text: string;
    sort_order: number;
    is_primary: boolean;
};
export type ImageEdit = Omit<ImageBody, 'cloudinary_public_id'>;
export const uuidPattern = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
export function uuid(v: unknown): string { if (typeof v !== 'string' || !uuidPattern.test(v))
    throw Error('contract'); return v; }
function obj(v: unknown): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v))
    throw Error('contract'); return v as Record<string, unknown>; }
function str(v: unknown, max: number, min = 1): string { if (typeof v !== 'string' || v.trim().length < min || v.length > max)
    throw Error('contract'); return v; }
function int(v: unknown, min: number, max = 2147483647): number { if (!Number.isSafeInteger(v) || Number(v) < min || Number(v) > max)
    throw Error('contract'); return v as number; }
function bool(v: unknown): boolean { if (typeof v !== 'boolean')
    throw Error('contract'); return v; }
function one<const T extends string>(v: unknown, values: readonly T[]): T { if (!values.includes(v as T))
    throw Error('contract'); return v as T; }
function nullable(v: unknown, max: number): string | null { return v === null ? null : str(v, max); }
export function money(v: unknown): string { const s = str(v, 14); if (!/^\d{1,10}(\.\d{1,2})?$/.test(s) || Number(s) > 9999999999.99)
    throw Error('contract'); return s; }
function exact(o: Record<string, unknown>, keys: string[]) { if (Object.keys(o).length !== keys.length || keys.some(k => !Object.hasOwn(o, k)))
    throw Error('contract'); }
function slug(v: unknown, max: number) { const s = str(v, max, 2); if (!/^[a-z0-9][a-z0-9-]+$/.test(s))
    throw Error('contract'); return s; }
export function productBody(v: unknown, create = false): ProductBody {
    const o = obj(v);
    exact(o, ['name', 'slug', 'description', 'category_id', 'qr_type', 'price_per_copy', 'max_order_copies', 'lifecycle_status', 'is_featured', 'featured_sort_order']);
    const result: ProductBody = { name: str(o.name, 160), slug: slug(o.slug, 100), description: nullable(o.description, 4000), category_id: o.category_id === null ? null : uuid(o.category_id), qr_type: o.qr_type === null ? null : one(o.qr_type, ['lost', 'ice']), price_per_copy: money(o.price_per_copy), max_order_copies: int(o.max_order_copies, 1, 100), lifecycle_status: one(o.lifecycle_status, ['draft', 'published', 'archived']), is_featured: bool(o.is_featured), featured_sort_order: int(o.featured_sort_order, -100000, 100000) };
    if (create && (result.qr_type === null || result.lifecycle_status !== 'draft'))
        throw Error('contract');
    return result;
}
export function categoryBody(v: unknown): CategoryBody { const o = obj(v); exact(o, ['name', 'slug', 'sort_order', 'is_active']); return { name: str(o.name, 120), slug: slug(o.slug, 60), sort_order: int(o.sort_order, -100000, 100000), is_active: bool(o.is_active) }; }
export function variantBody(v: unknown): VariantBody {
    const o = obj(v);
    exact(o, ['sku', 'name', 'size_mm', 'material', 'color', 'fulfillment_method', 'template_key', 'template_version', 'is_active', 'sort_order']);
    const sku = str(o.sku, 60, 2);
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]+$/.test(sku))
        throw Error('contract');
    const size = o.size_mm === null ? null : str(o.size_mm, 12);
    if (size !== null && (!/^\d{1,5}(\.\d{1,2})?$/.test(size) || Number(size) <= 0 || Number(size) > 99999))
        throw Error('contract');
    return { sku, name: str(o.name, 160), size_mm: size, material: nullable(o.material, 120), color: nullable(o.color, 80), fulfillment_method: one(o.fulfillment_method, ['pdf_label', 'manufacturer_artwork', 'manual']), template_key: nullable(o.template_key, 120), template_version: int(o.template_version, 1, 100000), is_active: bool(o.is_active), sort_order: int(o.sort_order, -100000, 100000) };
}
export function imageBody(v: unknown, edit = false): ImageBody | ImageEdit { const o = obj(v); exact(o, edit ? ['alt_text', 'sort_order', 'is_primary'] : ['cloudinary_public_id', 'alt_text', 'sort_order', 'is_primary']); const data = { alt_text: str(o.alt_text, 240), sort_order: int(o.sort_order, -100000, 100000), is_primary: bool(o.is_primary) }; if (edit)
    return data; const id = str(o.cloudinary_public_id, 240); if (!/^[A-Za-z0-9/_-]+$/.test(id))
    throw Error('contract'); return { ...data, cloudinary_public_id: id }; }
export function parseCategory(v: unknown): Category { const o = obj(v); return { id: uuid(o.id), catalog_version: int(o.catalog_version, 1), ...categoryBody({ name: o.name, slug: o.slug, sort_order: o.sort_order, is_active: o.is_active }) }; }
export function parseVariant(v: unknown): Variant { const o = obj(v); return { id: uuid(o.id), catalog_version: int(o.catalog_version, 1), currency_code: (() => { const c = str(o.currency_code, 3, 3); if (!/^[A-Z]{3}$/.test(c))
        throw Error('contract'); return c; })(), unit_price: o.unit_price === null ? null : money(o.unit_price), ...variantBody(Object.fromEntries(['sku', 'name', 'size_mm', 'material', 'color', 'fulfillment_method', 'template_key', 'template_version', 'is_active', 'sort_order'].map(k => [k, o[k]]))) }; }
export function publicImage(v: unknown): string { const s = str(v, 2048); const u = new URL(s); if (u.protocol !== 'https:' || u.hostname !== 'res.cloudinary.com' || u.username || u.password || u.search || u.hash || !/^\/[a-z0-9-]+\/image\/upload\//i.test(u.pathname))
    throw Error('contract'); return s; }
export function parseImage(v: unknown): ProductImage { const o = obj(v); return { id: uuid(o.id), alt_text: str(o.alt_text, 240), sort_order: int(o.sort_order, -100000, 100000), is_primary: bool(o.is_primary), verified_public_url: o.verified_public_url === null ? null : publicImage(o.verified_public_url) }; }
export function parseProduct(v: unknown, expanded = true): Product {
    const o = obj(v);
    const fields = Object.fromEntries(['name', 'slug', 'description', 'category_id', 'qr_type', 'price_per_copy', 'max_order_copies', 'lifecycle_status', 'is_featured', 'featured_sort_order'].map(k => [k, o[k]]));
    const b = productBody({ ...fields, price_per_copy: o.price_per_copy === null ? '0' : o.price_per_copy });
    if (expanded && (!Array.isArray(o.variants) || !Array.isArray(o.images)))
        throw Error('contract');
    return { ...b, id: uuid(o.id), commerce_model: one(o.commerce_model, ['legacy_pair', 'single_qr']), price_per_copy: o.price_per_copy === null ? null : b.price_per_copy, catalog_version: int(o.catalog_version, 1), variants: expanded ? (o.variants as unknown[]).map(parseVariant) : [], images: expanded ? (o.images as unknown[]).map(parseImage) : [] };
}
export function parseGrant(v: unknown) {
    const o = obj(v), p = obj(o.upload_params);
    const url = str(o.upload_url, 2048);
    if (!/^https:\/\/api\.cloudinary\.com\/v1_1\/[a-z0-9-]+\/image\/upload$/.test(url))
        throw Error('contract');
    const params: Record<string, string> = {};
    exact(p, ['timestamp', 'public_id', 'overwrite', 'allowed_formats', 'type', 'upload_preset', 'signature', 'api_key']);
    for (const k of Object.keys(p))
        params[k] = str(p[k], 1024);
    if (params.overwrite !== 'false' || params.type !== 'upload' || params.allowed_formats !== 'png,jpg,jpeg,webp,avif' || !/^\d+$/.test(params.timestamp) || !/^\d+$/.test(params.api_key) || !(/^[a-f0-9]{64}$/.test(params.signature)))
        throw Error('contract');
    const id = uuid(o.id), public_id = str(o.public_id, 240);
    if (public_id !== params.public_id || !public_id.includes('/' + id + '/') || !/^\d+$/.test(String(o.expires_at)))
        throw Error('contract');
    return { id, catalog_version: int(o.catalog_version, 1), public_id, upload_url: url, upload_params: params, expires_at: int(o.expires_at, 1, Number.MAX_SAFE_INTEGER) };
}
export function target(path: string, method: string): 'products' | 'product' | 'categories' | 'category' | 'variant' | 'image' | 'choices' {
    const id = '[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}';
    if (path === '/admin/products' && ['GET', 'POST'].includes(method))
        return method === 'GET' ? 'products' : 'product';
    if (path === '/admin/catalog/categories' && ['GET', 'POST'].includes(method))
        return method === 'GET' ? 'categories' : 'category';
    if (path === '/admin/catalog/approved-templates' && method === 'GET')
        return 'choices';
    if (new RegExp('^/admin/products/' + id + '$').test(path) && ['GET', 'PATCH'].includes(method))
        return 'product';
    if (new RegExp('^/admin/catalog/categories/' + id + '$').test(path) && method === 'PATCH')
        return 'category';
    if ((new RegExp('^/admin/products/' + id + '/variants$').test(path) && method === 'POST') || (new RegExp('^/admin/product-variants/' + id + '$').test(path) && method === 'PATCH'))
        return 'variant';
    if ((new RegExp('^/admin/products/' + id + '/images$').test(path) && method === 'POST') || (new RegExp('^/admin/products/' + id + '/images/' + id + '$').test(path) && ['PATCH', 'DELETE'].includes(method)))
        return 'image';
    throw Error('route');
}
export function parseResult(path: string, method: string, value: unknown, upload = false): unknown {
    const kind = target(path, method);
    const o = obj(value);
    if (kind === 'choices')
        return parseTemplateChoices(value);
    if (kind === 'products') {
        exact(o, ['items', 'next_cursor']);
        if (!Array.isArray(o.items) || o.items.length > 100)
            throw Error('contract');
        return { items: o.items.map(v => parseProduct(v)), next_cursor: o.next_cursor === null ? null : uuid(o.next_cursor) };
    }
    if (kind === 'categories') {
        exact(o, ['items']);
        if (!Array.isArray(o.items) || o.items.length > 100)
            throw Error('contract');
        return { items: o.items.map(parseCategory) };
    }
    if (kind === 'product')
        return parseProduct(value, method === 'GET');
    if (kind === 'category')
        return parseCategory(value);
    if (kind === 'variant')
        return parseVariant(value);
    return upload ? parseGrant(value) : parseImage(value);
}
