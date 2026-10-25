import "server-only";
import { validateOrigin } from "./api/transport";

export type CatalogProduct = {
  product_id: string; slug: string; name: string; description: string | null;
  commerce_model?: "legacy_pair"|"single_qr"; qr_type?: "lost"|"ice"|null;
  checkout_available?: boolean;
  featured: boolean; catalog_version: number;
  price_per_copy: string; max_order_copies: number;
  category: { id: string; slug: string; name: string };
  images: { url: string; alt_text: string; is_primary: boolean }[];
  variants: { variant_id: string; sku: string; name: string; currency_code: string; unit_price_pkr: string }[];
};
export type Catalog = { products: CatalogProduct[]; unavailable: boolean };
function record(v: unknown): v is Record<string, unknown> { return typeof v === "object" && v !== null; }
function isProduct(value: unknown): value is CatalogProduct {
  if (!record(value) || !record(value.category)) return false;
  if(value.checkout_available!==undefined&&typeof value.checkout_available!=="boolean")return false;
  if(value.commerce_model!==undefined&&value.commerce_model!=="legacy_pair"&&value.commerce_model!=="single_qr")return false;
  if(value.commerce_model==="single_qr"&&value.qr_type!=="lost"&&value.qr_type!=="ice")return false;
  return typeof value.product_id === "string" && typeof value.slug === "string" && /^[a-z0-9-]+$/.test(value.slug)
    && typeof value.name === "string" && (value.description === null || typeof value.description === "string")
    && typeof value.price_per_copy === "string" && /^\d{1,10}\.\d{2}$/.test(value.price_per_copy)
    && Number.isInteger(value.max_order_copies) && Number(value.max_order_copies) >= 1 && Number(value.max_order_copies) <= 100
    && typeof value.featured === "boolean" && Number.isInteger(value.catalog_version)
    && typeof value.category.name === "string" && typeof value.category.slug === "string"
    && Array.isArray(value.images) && value.images.every(i => record(i) && typeof i.url === "string"
      && /^https:\/\/res\.cloudinary\.com\/[a-z0-9-]+\/image\/upload\/v[0-9]+\/[A-Za-z0-9/_-]+\.(png|jpe?g|webp|avif)$/.test(i.url)
      && typeof i.alt_text === "string" && typeof i.is_primary === "boolean")
    && Array.isArray(value.variants) && value.variants.length > 0 && value.variants.every(v => record(v)
      && typeof v.sku === "string" && typeof v.name === "string" && v.currency_code === "PKR"
      && typeof v.unit_price_pkr === "string" && /^\d{1,10}\.\d{2}$/.test(v.unit_price_pkr));
}
export async function getCatalog(featured = false): Promise<Catalog> {
  try {
    const origin = validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "");
    const response = await fetch(`${origin}/api/v1/${featured ? "public/catalog/featured" : "public/products"}`, {
      headers: { Accept: "application/json" }, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) throw new Error("unavailable");
    const data: unknown = await response.json();
    const value = featured && record(data) ? data.items : data;
    if (!Array.isArray(value) || !value.every(isProduct)) throw new Error("contract");
    return { products: value, unavailable: false };
  } catch { return { products: [], unavailable: true }; }
}
export async function getProduct(sku: string): Promise<CatalogProduct | null | undefined> {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{1,59}$/.test(sku)) return null;
  try {
    const origin = validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "");
    const response = await fetch(`${origin}/api/v1/public/products/${encodeURIComponent(sku)}`, {
      cache: "no-store", redirect: "error", signal: AbortSignal.timeout(8000), headers: { Accept: "application/json" },
    });
    if (response.status === 404) return null;
    if (!response.ok) return undefined;
    const value: unknown = await response.json();
    return isProduct(value) ? value : undefined;
  } catch { return undefined; }
}
