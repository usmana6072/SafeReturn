"use client";
import Link from "next/link";
import { useRef, useState, useTransition, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Catalog, CatalogProduct } from "../lib/catalog";
import { canOrder } from "../lib/checkout-availability";
import { readItemCart } from "../lib/item-cart";
import { readCart } from "../lib/cart";
import { CustomerDialog } from "./customer-dialog";
import { CustomerIcon } from "./customer-icon";

export function ShopCartLink({ ur }: { ur: boolean }) {
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => {
    const update = () => setCount(readItemCart().length + readCart().filter(row => row.lost + row.ice > 0).length);
    update(); window.addEventListener("pageshow", update); window.addEventListener("storage", update);
    return () => { window.removeEventListener("pageshow", update); window.removeEventListener("storage", update); };
  }, []);
  return <Link className="shop-cart" href="/cart"><CustomerIcon name="cart"/>{ur ? "کارٹ" : "Cart"}{count !== null && count > 0 && <span>{count}</span>}</Link>;
}
export function ShopImage({ product }: { product: CatalogProduct }) {
  const [failed, setFailed] = useState(false);
  const image = product.images.find(i => i.is_primary) ?? product.images[0];
  return <div className="shop-image">{image && !failed ? <img src={image.url} alt={image.alt_text || product.name} width="600" height="450" loading="lazy" onError={() => setFailed(true)}/>
    : <div className="shop-image-fallback"><CustomerIcon name="tag"/><span>{product.name}</span></div>}</div>;
}
export function shopPrice(product: CatalogProduct) {
  return Number(product.price_per_copy);
}
export function ShopProductCard({ product, ur, shopPath }: { product: CatalogProduct; ur: boolean; shopPath: string }) {
  const href = shopPath + "/" + encodeURIComponent(product.variants[0].sku);
  return <article className="shop-card"><Link href={href} prefetch={false} aria-label={(ur ? "تفصیلات دیکھیں، " : "View details for ") + product.name}><ShopImage product={product}/></Link>
    <div className="shop-card-content"><span className="shop-category">{product.category.name}</span><h2><Link href={href} prefetch={false}>{product.name}</Link></h2>
      {product.description && <p className="shop-summary">{product.description}</p>}
      <div className="shop-price"><strong><bdi>{product.variants[0].currency_code} {shopPrice(product).toFixed(2)}</bdi></strong><small>{ur ? "فی کاپی" : "per copy"}</small></div>
      <p className="shop-options">{product.variants.length} {ur ? "سائز کے اختیارات" : product.variants.length === 1 ? "size option" : "size options"}{product.qr_type && <> · {product.qr_type === "ice" ? (ur ? "ہنگامی QR" : "Emergency QR") : (ur ? "گمشدہ QR" : "Lost QR")}</>}</p>
      <Link className="shop-primary" href={href + (canOrder(product) ? "#order" : "")} prefetch={false}>{canOrder(product) ? (ur ? "اپنی پسند کا آرڈر" : "Customize & Order") : (ur ? "تفصیلات دیکھیں" : "View Details")}<CustomerIcon name="arrow"/></Link>
    </div></article>;
}
export function ShopRetry({ ur }: { ur: boolean }) {
  const router = useRouter(), [pending, start] = useTransition();
  return <button className="shop-secondary" disabled={pending} onClick={() => start(() => router.refresh())}>{pending ? (ur ? "کوشش جاری ہے…" : "Retrying…") : (ur ? "دوبارہ کوشش کریں" : "Retry")}</button>;
}
export function ShopCatalog({ catalog, ur, initialQuery = "", initialCategory = "", shopPath = "/shop" }: { catalog: Catalog; ur: boolean; initialQuery?: string; initialCategory?: string; shopPath?: string }) {
  const [query, setQuery] = useState(initialQuery), [category, setCategory] = useState(initialCategory);
  const [availability, setAvailability] = useState("all"), [sort, setSort] = useState("featured"), [open, setOpen] = useState(false);
  const search = useRef<HTMLInputElement>(null), trigger = useRef<HTMLButtonElement>(null);
  const categories = [...new Map(catalog.products.map(p => [p.category.slug, p.category])).values()];
  const term = query.trim().toLocaleLowerCase();
  const products = catalog.products.filter(p => (!category || p.category.slug === category) &&
    (availability === "all" || canOrder(p) === (availability === "available")) &&
    (!term || (p.name + " " + (p.description ?? "")).toLocaleLowerCase().includes(term)));
  products.sort((a,b) => sort === "low" ? shopPrice(a)-shopPrice(b) : sort === "high" ? shopPrice(b)-shopPrice(a) : sort === "name" ? a.name.localeCompare(b.name, ur ? "ur" : "en") : Number(b.featured)-Number(a.featured));
  const filters = Number(!!category) + Number(availability !== "all");
  function clear() { setQuery(""); setCategory(""); setAvailability("all"); setSort("featured"); }
  function close() { setOpen(false); requestAnimationFrame(() => trigger.current?.focus()); }
  return <section className="shop-screen">
    <header className="shop-intro"><div><h1>{ur ? "QR ٹیگز خریدیں" : "Shop QR Tags"}</h1><p>{ur ? "اپنے سامان کی حفاظت کے لیے مناسب QR ٹیگ منتخب کریں۔" : "Find the right QR tag to help protect your belongings."}</p></div><ShopCartLink ur={ur}/></header>
    <div className="shop-search"><CustomerIcon name="search"/><input ref={search} type="search" autoComplete="off" enterKeyHint="search" maxLength={120} value={query} onChange={e => setQuery(e.target.value)}
      aria-label={ur ? "QR ٹیگز اور مصنوعات تلاش کریں" : "Search QR tags and products"} placeholder={ur ? "QR ٹیگز اور مصنوعات تلاش کریں" : "Search QR tags and products"}/>
      {query && <button aria-label={ur ? "تلاش صاف کریں" : "Clear search"} onClick={() => {setQuery("");search.current?.focus();}}><CustomerIcon name="close"/></button>}</div>
    <div className="shop-toolbar"><button ref={trigger} className="shop-secondary" aria-haspopup="dialog" onClick={() => setOpen(true)}><CustomerIcon name="filter"/>{ur ? "فلٹر" : "Filter"}{filters > 0 && <span>{filters}</span>}</button>
      <label className="shop-sort"><span>{ur ? "ترتیب" : "Sort"}</span><select aria-label={ur ? "ترتیب" : "Sort"} value={sort} onChange={e => setSort(e.target.value)}>
        <option value="featured">{ur ? "نمایاں" : "Featured"}</option><option value="low">{ur ? "کم سے زیادہ قیمت" : "Price Low to High"}</option>
        <option value="high">{ur ? "زیادہ سے کم قیمت" : "Price High to Low"}</option><option value="name">{ur ? "نام کے لحاظ سے" : "Name A–Z"}</option></select></label>
      {!catalog.unavailable && <span className="shop-count" role="status">{products.length} {ur ? "مصنوعات" : "products"}</span>}
    </div>
    {(filters > 0 || term) && <button className="shop-clear" onClick={clear}>{ur ? "فلٹر صاف کریں" : "Clear Filters"}</button>}
    {catalog.unavailable ? <div className="shop-empty" role="status"><CustomerIcon name="refresh"/><h2>{ur ? "مصنوعات لوڈ نہیں ہو سکیں۔" : "Products couldn’t be loaded."}</h2><p>{ur ? "تھوڑی دیر بعد دوبارہ کوشش کریں۔" : "Please try again in a moment."}</p><ShopRetry ur={ur}/></div>
      : products.length ? <div className="shop-grid">{products.map(p => <ShopProductCard key={p.product_id} product={p} ur={ur} shopPath={shopPath}/>)}</div>
      : <div className="shop-empty"><CustomerIcon name={catalog.products.length ? "search" : "shop"}/><h2>{catalog.products.length ? (ur ? "کوئی مماثل مصنوعہ نہیں" : "No Matching Products") : (ur ? "مصنوعات دستیاب نہیں" : "No Products Available")}</h2>
        <p>{catalog.products.length ? (ur ? "تلاش یا فلٹر تبدیل کریں۔" : "Try another search or adjust your filters.") : (ur ? "نئے QR ٹیگز اور لوازمات دستیاب ہونے پر یہاں دکھائی دیں گے۔" : "New QR tags and accessories will appear here when available.")}</p>
        {catalog.products.length > 0 && <button className="shop-secondary" onClick={clear}>{ur ? "فلٹر صاف کریں" : "Clear Filters"}</button>}</div>}
    {open && <CustomerDialog title={ur ? "فلٹر" : "Filter Products"} ur={ur} busy={false} onClose={close} dismissOnBackdrop>
      <label>{ur ? "قسم" : "Category"}<select aria-label={ur ? "قسم" : "Category"} value={category} onChange={e => setCategory(e.target.value)}><option value="">{ur ? "تمام اقسام" : "All Categories"}</option>{categories.map(c => <option key={c.slug} value={c.slug}>{c.name}</option>)}</select></label>
      <label>{ur ? "خریداری" : "Ordering"}<select aria-label={ur ? "خریداری" : "Ordering"} value={availability} onChange={e => setAvailability(e.target.value)}><option value="all">{ur ? "تمام مصنوعات" : "All Products"}</option><option value="available">{ur ? "آرڈر کے لیے دستیاب" : "Available to Order"}</option><option value="paused">{ur ? "صرف دیکھنے کے لیے" : "Browse Only"}</option></select></label>
      <div className="shop-dialog-actions"><button className="shop-secondary" onClick={clear}>{ur ? "فلٹر صاف کریں" : "Clear Filters"}</button><button className="shop-primary" onClick={close}>{ur ? "مکمل" : "Done"}</button></div>
    </CustomerDialog>}
  </section>;
}
