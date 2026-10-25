"use client";
import { useRef } from "react";
import type { Catalog, CatalogProduct } from "../lib/catalog";
export function ProductCard({ product, language }: { product: CatalogProduct; language: "en" | "ur" }) {
 const image = product.images.find(i => i.is_primary) ?? product.images[0];
 const detail = `/shop/${encodeURIComponent(product.variants[0].sku)}`;
 const ordering = product.checkout_available !== false;
 return <article className="catalog-card">{image && <img src={image.url} alt={image.alt_text} width="480" height="320" loading="lazy" />}<h3>{product.name}</h3>{product.description && <p>{product.description}</p>}<ul>{product.variants.map(v => <li key={v.sku}>{v.name}: <bdi>{v.currency_code} {v.unit_price_pkr}</bdi></li>)}</ul><a className="button secondary" href={detail}>{language === "ur" ? "تفصیلات دیکھیں" : "View details"}</a><div className="catalog-order-action">{ordering ? <a className="button" href={detail + '#order'}>{language === 'ur' ? 'آرڈر کریں' : 'Order now'}</a> : <><button type="button" className="button" disabled>{language === 'ur' ? 'آرڈر کریں' : 'Order now'}</button><p>{language === 'ur' ? 'آن لائن آرڈر ابھی دستیاب نہیں۔' : 'Online ordering is not available yet.'}</p></>}</div></article>;
}
export function FeaturedCatalog({ catalog, language }: { catalog: Catalog; language: "en" | "ur" }) {
 const ref = useRef<HTMLDivElement>(null), ur = language === "ur";
 if (!catalog.products.length) return <div className="empty-state" role="status"><p>{catalog.unavailable ? ur ? "مصنوعات ابھی لوڈ نہیں ہو سکیں۔ براہ کرم دوبارہ کوشش کریں۔" : "Products could not be loaded. Please try again." : ur ? "فی الحال کوئی نمایاں مصنوعات دستیاب نہیں۔" : "No featured products are available yet."}</p><a href="/shop">{ur ? "تمام مصنوعات" : "All products"}</a></div>;
 function move(direction: number) { const el = ref.current; if (el) el.scrollBy({ left: direction * (ur ? -1 : 1) * el.clientWidth * .8, behavior: "instant" }); }
 return <><div className="catalog-controls"><button type="button" onClick={() => move(-1)} aria-label={ur ? "پچھلی مصنوعات" : "Previous products"}>←</button><button type="button" onClick={() => move(1)} aria-label={ur ? "اگلی مصنوعات" : "Next products"}>→</button><a href="/shop">{ur ? "تمام مصنوعات" : "All products"}</a></div><div ref={ref} className="featured-scroll" tabIndex={0} role="region" aria-label={ur ? "نمایاں مصنوعات" : "Featured products"}>{catalog.products.map(p => <ProductCard key={p.product_id} product={p} language={language} />)}</div></>;
}
