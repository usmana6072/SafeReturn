"use client";
import Link from "next/link";
import { useEffect, useRef, useState, useTransition, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import type { Catalog, CatalogProduct } from "../lib/catalog";
import { itemCartKey, readItemCart, type ItemCart } from "../lib/item-cart";
import { cartKey, readCart, type CopyRow } from "../lib/cart";
import { canOrder, checkoutUnavailableMessage } from "../lib/checkout-availability";
import { ShopImage } from "./shop-catalog";
import { CustomerIcon } from "./customer-icon";

type StoredCart = { items: ItemCart[]; pairs: CopyRow[] };
type Undo = { key: string; raw: string | null };
type Line = {
  key: string; product?: CatalogProduct; count: number; separate: boolean; legacy: boolean;
  options: { key: string; name: string; copies: number; min: number; change: (copies: number) => void; remove: () => void }[];
  remove: () => void;
};
const money = (cents: number) => "PKR " + (cents / 100).toFixed(2);

export function CartSkeleton() {
  return <div className="cart-screen cart-loading" role="status" aria-busy="true"><span className="sr-only">Loading cart / کارٹ لوڈ ہو رہا ہے</span><i className="cart-skeleton-title" aria-hidden="true"/>
    <div className="cart-layout" aria-hidden="true"><div>{[0,1].map(n => <div className="cart-card" key={n}><i/><i/><i/></div>)}</div><div className="cart-summary"><i/><i/><i/></div></div></div>;
}
export function ShoppingCart({ catalog, ur }: { catalog: Catalog; ur: boolean }) {
  const t = (en: string, translated: string) => ur ? translated : en;
  const router = useRouter();
  const [cart, setCart] = useState<StoredCart | null>(null), [undo, setUndo] = useState<Undo | null>(null);
  const [error, setError] = useState(""), [notice, setNotice] = useState(""), [leaving, setLeaving] = useState(false);
  const [retrying, startRetry] = useTransition();
  const [navSpace, setNavSpace] = useState(70);
  const root = useRef<HTMLDivElement>(null), snapshots = useRef<Record<string,string|null>>({});
  const navigating = useRef(false);
  function read() {
    snapshots.current = { [itemCartKey]: localStorage.getItem(itemCartKey), [cartKey]: localStorage.getItem(cartKey) };
    setCart({ items: readItemCart(), pairs: readCart() });
  }
  useEffect(() => {
    try { read(); } catch { setError(t("Your cart storage couldn’t be opened. Retry to load your selections.", "کارٹ کی محفوظ معلومات نہیں کھل سکیں۔ دوبارہ کوشش کریں۔")); }
    const sync = (event: StorageEvent) => {
      if (event.key === itemCartKey || event.key === cartKey || event.key === null) {
        try { read(); setUndo(null); setNotice(t("Your cart was updated in another tab.", "دوسرے ٹیب میں کارٹ تبدیل ہوا ہے۔")); } catch { setError(t("Your cart couldn’t be refreshed.", "کارٹ تازہ نہیں ہو سکا۔")); }
      }
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, [ur]);
  useEffect(() => {
    // Measure the shared navigation so enlarged text and Urdu labels cannot cover the checkout dock.
    const nav = root.current?.closest(".customer-portal")?.querySelector(".portal-nav");
    if (!nav) return;
    const observer = new ResizeObserver(() => setNavSpace(window.matchMedia("(max-width: 799px)").matches ? nav.getBoundingClientRect().height + 20 : 16));
    observer.observe(nav); return () => observer.disconnect();
  }, [cart !== null]);
  function write(key: string, value: ItemCart[] | CopyRow[], removed = false) {
    if (navigating.current) return;
    setError(""); setNotice("");
    try {
      const previous = localStorage.getItem(key);
      if (previous !== snapshots.current[key]) {
        read(); setUndo(null); setError(t("Your cart changed in another tab. Review the latest quantities and try again.", "دوسرے ٹیب میں کارٹ تبدیل ہوا ہے۔ نئی تعداد دیکھ کر دوبارہ کوشش کریں۔")); return;
      }
      localStorage.setItem(key, JSON.stringify(value));
      read();
      setUndo(removed ? { key, raw: previous } : null);
      if (removed) setNotice(t("Removed from your cart.", "کارٹ سے ہٹا دیا گیا۔"));
    } catch { setError(t("Your changes couldn’t be saved. Your previous selections are still shown. Please try again.", "تبدیلی محفوظ نہیں ہو سکی۔ پچھلی معلومات موجود ہیں۔ دوبارہ کوشش کریں۔")); }
  }
  function restore() {
    if (!undo) return;
    try {
      if (localStorage.getItem(undo.key) !== snapshots.current[undo.key]) { read(); setUndo(null); setError(t("Your cart changed. Review it before making another edit.", "کارٹ تبدیل ہوا ہے۔ دوبارہ ترمیم سے پہلے اسے دیکھیں۔")); return; }
      if (undo.raw === null) localStorage.removeItem(undo.key); else localStorage.setItem(undo.key, undo.raw);
      read(); setUndo(null); setNotice(t("Item restored.", "آئٹم بحال کر دیا گیا۔"));
    } catch { setError(t("The item couldn’t be restored. Please try again.", "آئٹم بحال نہیں ہو سکا۔ دوبارہ کوشش کریں۔")); }
  }
  const products = new Map(catalog.products.map(p => [p.product_id,p]));
  const variants = new Map(catalog.products.filter(p => p.commerce_model !== "single_qr").flatMap(p => p.variants.map(v => [v.variant_id, { product:p, variant:v }] as const)));
  const items = cart?.items ?? [], pairs = cart?.pairs ?? [];
  const lines: Line[] = items.map((item,index) => ({
    key: "item-" + index, product: products.get(item.product_id), count: item.sizes.reduce((n,s) => n+s.copies,0), separate: item.identity_group !== null, legacy:false,
    options: item.sizes.map((size,n) => ({
      key: size.variant_id, name: products.get(item.product_id)?.variants.find(v => v.variant_id === size.variant_id)?.name ?? t("Option unavailable", "اختیار دستیاب نہیں"), copies:size.copies, min:1,
      change: (copies:number) => write(itemCartKey,items.map((i,j) => j === index ? {...i,sizes:i.sizes.map((s,k) => k === n ? {...s,copies} : s)} : i)),
      remove: () => write(itemCartKey,items.map((i,j) => j === index ? {...i,sizes:i.sizes.filter((_,k) => k !== n)} : i).filter(i => i.sizes.length),true),
    })), remove: () => write(itemCartKey,items.filter((_,j) => j !== index),true),
  }));
  const pairGroups = new Map<string,{ product?: CatalogProduct; rows: CopyRow[] }>();
  for (const row of pairs) {
    const product = variants.get(row.variant_id)?.product, key = product?.product_id ?? row.variant_id;
    const group = pairGroups.get(key) ?? { product,rows:[] };
    group.rows.push(row); pairGroups.set(key,group);
  }
  for (const [key,group] of pairGroups) {
    const ids = new Set(group.rows.map(r => r.variant_id));
    lines.push({
      key: "pair-" + key, product:group.product, count:group.rows.reduce((n,r) => n+r.lost+r.ice,0), separate:false,legacy:true,
      options:group.rows.flatMap(row => (["lost","ice"] as const).map(tag => ({
        key: row.variant_id + tag, name:(variants.get(row.variant_id)?.variant.name ?? t("Option unavailable", "اختیار دستیاب نہیں")) + " · " + (tag === "lost" ? t("Lost", "گمشدہ") : t("Emergency", "ہنگامی")), copies:row[tag],min:0,
        change:(copies:number) => write(cartKey,pairs.map(r => r.variant_id === row.variant_id ? {...r,[tag]:copies} : r)),
        remove:() => write(cartKey,pairs.map(r => r.variant_id === row.variant_id ? {...r,[tag]:0} : r).filter(r => r.lost+r.ice>0),true),
      }))), remove:() => write(cartKey,pairs.filter(r => !ids.has(r.variant_id)),true),
    });
  }
  const missing = items.some(i => {
    const p = products.get(i.product_id);
    return !p || p.commerce_model !== "single_qr" || i.sizes.some(s => !p.variants.some(v => v.variant_id === s.variant_id));
  }) || pairs.some(r => !variants.has(r.variant_id));
  const exceeded = lines.some(l => l.product && l.count > l.product.max_order_copies) || items.reduce((n,i) => n+i.sizes.length,0)>50;
  const pairIncomplete = pairs.length > 0 && (pairs.reduce((n,r) => n+r.lost,0)<1 || pairs.reduce((n,r) => n+r.ice,0)<1);
  const paused = lines.some(l => l.product && !canOrder(l.product));
  const invalid = !lines.length || catalog.unavailable || missing || exceeded || pairIncomplete || paused;
  const estimated = missing || catalog.unavailable ? null : lines.reduce((n,l) => n + Number(l.product!.price_per_copy.replace(".","")) * l.count,0);
  function proceed() {
    if (invalid || navigating.current) return;
    try {
      if (localStorage.getItem(itemCartKey) !== snapshots.current[itemCartKey] || localStorage.getItem(cartKey) !== snapshots.current[cartKey]) {
        read(); setUndo(null); setError(t("Your cart changed. Review it before checkout.", "کارٹ تبدیل ہوا ہے۔ چیک آؤٹ سے پہلے اسے دیکھیں۔")); return;
      }
      navigating.current = true; setLeaving(true); router.push("/checkout");
    } catch { navigating.current = false; setLeaving(false); setError(t("Checkout couldn’t open. Please try again.", "چیک آؤٹ نہیں کھل سکا۔ دوبارہ کوشش کریں۔")); }
  }
  function retry() {
    setError("");
    startRetry(() => {
      try { read(); router.refresh(); } catch { setError(t("Your cart couldn’t be loaded. Please try again.", "کارٹ لوڈ نہیں ہو سکا۔ دوبارہ کوشش کریں۔")); }
    });
  }
  const checkoutButton = <button type="button" className="cart-primary" disabled={invalid || leaving} onClick={proceed}>{leaving ? t("Opening Checkout…", "چیک آؤٹ کھل رہا ہے…") : t("Proceed to Checkout", "چیک آؤٹ پر جائیں")}<CustomerIcon name="arrow"/></button>;
  return <div ref={root} className="cart-screen" dir={ur?"rtl":"ltr"} style={{"--cart-nav-space":navSpace+"px"} as CSSProperties}>
    <header className="cart-intro"><div><h1>{t("Shopping Cart", "خریداری کی ٹوکری")}</h1><p>{t("Review your items before checkout.", "چیک آؤٹ سے پہلے اپنے آئٹمز دیکھیں۔")}</p></div>
      {cart && <span className="cart-count">{lines.length} {t(lines.length === 1 ? "item" : "items", "آئٹمز")}</span>}</header>
    {error && <p className="cart-error" role="alert">{error}</p>}
    {notice && <div className="cart-feedback" role="status"><span>{notice}</span>{undo && <button onClick={restore}>{t("Undo", "واپس لائیں")}</button>}</div>}
    {!cart ? error ? <button className="cart-secondary" disabled={retrying} onClick={retry}>{t("Retry", "دوبارہ کوشش کریں")}</button> : <CartSkeleton/> :
      !lines.length ? <div className="cart-empty"><span><CustomerIcon name="cart"/></span><h2>{t("Your Cart Is Empty", "آپ کی ٹوکری خالی ہے")}</h2>
        <p>{t("Explore our QR tags and find the right way to protect your belongings.", "ہمارے QR ٹیگز دیکھیں اور اپنے سامان کی حفاظت کا مناسب طریقہ منتخب کریں۔")}</p><Link className="cart-primary" href="/shop">{t("Shop QR Tags", "QR ٹیگز خریدیں")}</Link></div> :
      <>
        {catalog.unavailable && <div className="cart-error" role="alert"><p>{t("Product details couldn’t be loaded. Your saved selections are retained.", "مصنوعات کی تفصیلات لوڈ نہیں ہو سکیں۔ آپ کے انتخابات محفوظ ہیں۔")}</p><button className="cart-secondary" onClick={retry} disabled={retrying}>{t("Retry", "دوبارہ کوشش کریں")}</button></div>}
        <div className="cart-layout"><section className="cart-items" aria-label={t("Items in Your Cart", "آپ کی ٹوکری میں آئٹمز")}>
          {lines.map(line => <CartCard key={line.key} line={line} ur={ur} disabled={leaving} unavailable={catalog.unavailable}/>)}
          {missing && !catalog.unavailable && <p className="cart-error" role="alert">{t("Some products or options are no longer available. Remove them before checkout.", "کچھ مصنوعات یا اختیارات دستیاب نہیں۔ چیک آؤٹ سے پہلے انہیں ہٹائیں۔")}</p>}
          {exceeded && <p className="cart-error" role="alert">{t("A product’s combined copy limit has been exceeded. Reduce its quantities before checkout.", "کاپیوں کی مشترکہ حد سے تجاوز ہے۔ چیک آؤٹ سے پہلے تعداد کم کریں۔")}</p>}
          {pairIncomplete && <p className="cart-error" role="alert">{t("Your paired tags need at least one Lost and one Emergency copy.", "جوڑے کے لیے کم از کم ایک Lost اور ایک Emergency کاپی ضروری ہے۔")}</p>}
          {items.length>0 && pairs.length>0 && <p className="cart-note">{t("Single QR tags and paired tags are checked out as separate orders in the next step.", "اگلے مرحلے میں سنگل QR ٹیگز اور جوڑے کے ٹیگز کے الگ آرڈرز ہوں گے۔")}</p>}
          <Link className="cart-shopping" href="/shop"><CustomerIcon name="shop"/>{t("Continue Shopping", "خریداری جاری رکھیں")}</Link>
        </section>
        <aside className="cart-summary"><h2>{t("Order Summary", "آرڈر کا خلاصہ")}</h2><dl><div><dt>{t("Product Subtotal", "مصنوعات کی قیمت")}</dt><dd>{estimated === null ? "—" : money(estimated)}</dd></div>
          <div><dt>{t("Delivery", "ترسیل")}</dt><dd>{t("Calculated at Checkout", "چیک آؤٹ پر حساب ہوگا")}</dd></div><div><dt>{t("Taxes", "ٹیکس")}</dt><dd>{t("Calculated at Checkout", "چیک آؤٹ پر حساب ہوگا")}</dd></div>
          <div className="cart-total"><dt>{t("Estimated Total", "تخمینی کل رقم")}</dt><dd>{estimated === null ? "—" : money(estimated)}</dd></div></dl>
          <p>{t("Delivery and tax will be included in your final checkout quote.", "ترسیل اور ٹیکس کی رقم حتمی چیک آؤٹ قیمت میں شامل ہوگی۔")}</p><div className="cart-desktop-checkout">{checkoutButton}</div></aside>
        </div>
        <div className="cart-checkout-dock"><div><span>{t("Estimated Total", "تخمینی کل رقم")}</span><strong>{estimated === null ? "—" : money(estimated)}</strong></div>{checkoutButton}</div>
      </>}
  </div>;
}
function CartCard({ line, ur, disabled, unavailable }: { line: Line; ur:boolean; disabled:boolean; unavailable:boolean }) {
  const t = (en:string,translated:string) => ur?translated:en, p=line.product;
  const href = p ? "/shop/" + encodeURIComponent(p.variants[0].sku) : null;
  const price = p ? Number(p.price_per_copy.replace(".","")) : null;
  return <article className="cart-card">
    <div className="cart-product">{p ? <div className="cart-thumbnail"><ShopImage product={p}/></div> : <div className="cart-thumbnail cart-fallback"><CustomerIcon name="tag"/></div>}
      <div className="cart-product-info"><h2>{href ? <Link href={href} prefetch={false}>{p!.name}</Link> : unavailable ? t("Product details loading", "مصنوعہ کی تفصیلات لوڈ ہو رہی ہیں") : t("Product unavailable", "مصنوعہ دستیاب نہیں")}</h2>
        {p && <p><bdi>{price === null ? "—" : money(price)}</bdi> {t("per copy", "فی کاپی")}</p>}
        <span className="cart-setup">{line.legacy ? t("Lost + Emergency Pair", "Lost اور Emergency جوڑا") : line.separate ? t("Separate QR for This Batch", "اس بیچ کے لیے الگ QR") : t("Combined Quantity · Shared QR", "مشترکہ تعداد، ایک QR")}</span></div></div>
    <details className="cart-qr-help"><summary>{t("QR Code Setup", "QR کوڈ کی ترتیب")}</summary><p>{line.legacy ? t("Lost and Emergency copies share their respective profiles within this pair.", "جوڑے میں Lost اور Emergency کی کاپیاں اپنے متعلقہ پروفائل استعمال کرتی ہیں۔") :
      t("All sizes and copies in this item share one QR. Separate batches keep their own QR.", "اس آئٹم کے تمام سائز اور کاپیاں ایک QR استعمال کرتی ہیں۔ الگ بیچ اپنا الگ QR رکھتے ہیں۔")}</p></details>
    <div className="cart-options">{line.options.map(option => {
      const max = p ? Math.min(100,p.max_order_copies-line.count+option.copies) : option.copies;
      return <div className="cart-option" key={option.key}><div className="cart-option-label"><label htmlFor={line.key+"-"+option.key}>{option.name}</label>
        <button className="cart-option-remove" disabled={disabled} aria-label={t("Remove Option, ", "اختیار ہٹائیں، ")+option.name} onClick={option.remove}>{t("Remove Option", "اختیار ہٹائیں")}</button></div>
        <div className="cart-stepper"><button disabled={disabled||option.copies<=option.min} aria-label={t("Decrease quantity, ", "تعداد کم کریں، ")+option.name} onClick={()=>option.change(option.copies-1)}>−</button>
          <input id={line.key+"-"+option.key} type="number" inputMode="numeric" min={option.min} max={Math.max(option.min,max)} value={option.copies} disabled={disabled||!p}
            onChange={e=>{const value=Number(e.target.value);if(e.target.value!==""&&Number.isInteger(value)&&value>=option.min&&value<=Math.max(option.min,max))option.change(value);}}/>
          <button disabled={disabled||!p||option.copies>=max} aria-label={t("Increase quantity, ", "تعداد بڑھائیں، ")+option.name} onClick={()=>option.change(option.copies+1)}>+</button></div>
      </div>;
    })}</div>
    {p&&!canOrder(p)&&<p className="cart-unavailable" role="status">{checkoutUnavailableMessage(p,ur?"ur":"en")}</p>}
    <div className="cart-card-footer"><div><span>{t("Item Subtotal", "آئٹم کی قیمت")}</span><strong>{price === null ? "—" : money(price*line.count)}</strong></div>
      <button className="cart-remove" disabled={disabled} aria-label={t("Remove Product, ", "مصنوعہ ہٹائیں، ")+(p?.name??"")} onClick={line.remove}><CustomerIcon name="close"/>{t("Remove Product", "مصنوعہ ہٹائیں")}</button></div>
  </article>;
}
