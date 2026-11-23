"use client";
import { canOrder, checkoutUnavailableMessage } from "../lib/checkout-availability";
import { useEffect, useRef, useState } from "react";
import type { Catalog, CatalogProduct } from "../lib/catalog";
import { HomeIcon } from "./home-visual";
export function ProductCard({ product, language, home=false }: { product: CatalogProduct; language: "en" | "ur"; home?:boolean }) {
 const image = product.images.find(i => i.is_primary) ?? product.images[0];
 const detail = `/shop/${encodeURIComponent(product.variants[0].sku)}`;
 const ordering = canOrder(product);
 if(home){
  const ur=language==="ur";
  const cheapest=product.variants.reduce((current,variant)=>BigInt(variant.unit_price_pkr.replace(".",""))<BigInt(current.unit_price_pkr.replace(".",""))?variant:current);
  return <article className="catalog-card home-product"><a className="home-product-image" href={detail} aria-label={product.name}>{image?<img src={image.url} alt={image.alt_text} width="480" height="360" loading="lazy"/>:<span className="home-product-fallback"><HomeIcon name={product.qr_type==="ice"?"medical":"tag"}/><bdi>SafeReturn</bdi><small>{ur?"QR اسٹیکر":"QR sticker"}</small></span>}</a>
   <div className="home-product-body"><span className="home-product-type">{product.commerce_model==="single_qr"?(product.qr_type==="ice"?(ur?"ہنگامی / ICE":"Emergency / ICE"):(ur?"گمشدہ چیز":"Lost Item")):product.category.name}</span>
   <h3><a href={detail}>{product.name}</a></h3>{product.description&&<p className="home-product-description">{product.description}</p>}
   <div className="home-product-price"><strong><bdi>PKR {product.commerce_model==="single_qr"?product.price_per_copy:cheapest.unit_price_pkr}</bdi></strong><span>{product.commerce_model==="single_qr"?(ur?"فی کاپی":"per copy"):cheapest.name}</span></div>
   <details className="home-product-variants"><summary>{ur?"سائز اور قیمتیں":"Sizes & Prices"}</summary><ul>{product.variants.map(v=><li key={v.sku}><span>{v.name}</span><bdi>{v.currency_code} {v.unit_price_pkr}</bdi></li>)}</ul></details>
   <div className="home-product-actions"><a className="button secondary" href={detail}>{ur?"تفصیلات دیکھیں":"View details"}</a>{ordering?<a className="button" href={detail+'#order'}>{ur?"آرڈر کریں":"Order now"}<HomeIcon name="arrow"/></a>:<button className="button" disabled>{ur?"آرڈر کریں":"Order now"}</button>}</div>
   {!ordering&&<p className="home-product-availability">{checkoutUnavailableMessage(product,language)}</p>}</div></article>;
 }
 return <article className="catalog-card">{image && <img src={image.url} alt={image.alt_text} width="480" height="320" loading="lazy" />}<h3>{product.name}</h3>{product.commerce_model==="single_qr"&&<p><span className="pill">{product.qr_type==="ice"?(language==="ur"?"ہنگامی":"Emergency"):(language==="ur"?"گمشدہ":"Lost")}</span> <bdi>PKR {product.price_per_copy}</bdi> {language==="ur"?"فی کاپی":"per copy"}</p>}{product.description && <p>{product.description}</p>}<ul>{product.variants.map(v => <li key={v.sku}>{v.name}: <bdi>{v.currency_code} {v.unit_price_pkr}</bdi></li>)}</ul> <div style={{display:"flex",gap:"10px",alignItems:"center",flexWrap:"wrap",marginBlockStart:"1rem"}}><a className="button secondary" href={detail}>{language === "ur" ? "تفصیلات دیکھیں" : "View details"}</a><div className="catalog-order-action">{ordering ? <a className="button" href={detail + '#order'}>{language === 'ur' ? 'آرڈر کریں' : 'Order now'}</a> : <><button type="button" className="button" disabled>{language === 'ur' ? 'آرڈر کریں' : 'Order now'}</button><p>{checkoutUnavailableMessage(product, language)}</p></>}</div></div></article>;
}
export function FeaturedCatalog({ catalog, language, home=false,emptyText }: { catalog: Catalog; language: "en" | "ur"; home?:boolean;emptyText?:string }) {
 const ref = useRef<HTMLDivElement>(null), ur = language === "ur";
 const [scroll,setScroll]=useState({before:false,after:false,overflows:false});
 useEffect(()=>{
  const element=ref.current;if(!element||!home)return;
  const update=()=>{const maximum=element.scrollWidth-element.clientWidth,position=Math.abs(element.scrollLeft);setScroll({before:position>2,after:position<maximum-2,overflows:maximum>2});};
  const observer=new ResizeObserver(update);observer.observe(element);element.addEventListener('scroll',update,{passive:true});update();
  return()=>{observer.disconnect();element.removeEventListener('scroll',update);};
 },[home,catalog.products.length,ur]);
 if (!catalog.products.length) return <div className="empty-state" role="status"><p>{catalog.unavailable ? ur ? "مصنوعات ابھی لوڈ نہیں ہو سکیں۔ براہ کرم دوبارہ کوشش کریں۔" : "Products could not be loaded. Please try again." : emptyText??(ur ? "فی الحال کوئی نمایاں مصنوعات دستیاب نہیں۔" : "No featured products are available yet.")}</p><a href="/shop">{ur ? "تمام مصنوعات" : "All products"}</a></div>;
 function move(direction: number) { const el = ref.current; if (el) el.scrollBy({ left: direction * (ur ? -1 : 1) * el.clientWidth * .8, behavior: "instant" }); }
 return <><div className="catalog-controls">{(!home||scroll.overflows)&&<div className="home-carousel-buttons"><button type="button" disabled={home&&!scroll.before} onClick={() => move(-1)} aria-label={ur ? "پچھلی مصنوعات" : "Previous products"}>←</button><button type="button" disabled={home&&!scroll.after} onClick={() => move(1)} aria-label={ur ? "اگلی مصنوعات" : "Next products"}>→</button></div>}<a href="/shop">{ur ? "تمام مصنوعات" : "All products"}{home&&<HomeIcon name="arrow"/>}</a></div><div ref={ref} className="featured-scroll" tabIndex={0} role="region" aria-label={ur ? "نمایاں مصنوعات" : "Featured products"}>{catalog.products.map(p => <ProductCard key={p.product_id} product={p} language={language} home={home}/> )}</div></>;
}
