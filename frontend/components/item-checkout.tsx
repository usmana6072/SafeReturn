"use client";
import { canOrder, checkoutUnavailableMessage } from "../lib/checkout-availability";
import {useCallback,useEffect,useRef,useState} from "react";
import type {CatalogProduct} from "../lib/catalog";
import {itemCartKey,mergeItemCart,readItemCart,type ItemCart,type PaymentInstructions} from "../lib/item-cart";
import { uuid } from "../lib/qr-contract";
import {SavedAddressSelector,type SavedAddress} from "./shipping-addresses";

import { CustomerIcon } from "./customer-icon";

export function OfficialPaymentInstructions({value,ur}:{value:PaymentInstructions;ur:boolean}){
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copy = (key: string, text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        setCopiedKey(key);
        setTimeout(() => setCopiedKey(null), 2000);
      }).catch(() => {});
    }
  };

  const fields = [
    { key: "bank", label: ur ? "بینک" : "Bank Name", value: value.bank_name, copyable: false },
    { key: "title", label: ur ? "اکاؤنٹ کا عنوان" : "Account Title", value: value.account_title, copyable: false },
    { key: "account", label: ur ? "اکاؤنٹ نمبر" : "Account Number", value: value.account_number, copyable: true },
    { key: "raast", label: ur ? "راست آئی ڈی" : "Raast ID", value: value.raast_id, copyable: true },
  ];

  return (
    <div className="bank-instructions-card" aria-label={ur ? "ادائیگی کی سرکاری ہدایات" : "Official payment instructions"}>
      <h2>{ur ? "بینک / راست ادائیگی کی تفصیلات" : "Bank & Raast Payment Details"}</h2>
      <p className="bank-instructions-text">{ur ? value.instructions_ur : value.instructions_en}</p>
      <div className="bank-grid">
        {fields.map((f) => (
          <div className="bank-item" key={f.key}>
            <div>
              <span className="bank-item-label">{f.label}</span>
              <strong className="bank-item-value"><bdi>{f.value}</bdi></strong>
            </div>
            {f.copyable && (
              <button
                type="button"
                className="copy-badge-btn"
                onClick={() => copy(f.key, f.value)}
                aria-label={(ur ? "کاپی کریں " : "Copy ") + f.label}
              >
                <CustomerIcon name={copiedKey === f.key ? "check" : "copy"} />
                <span>{copiedKey === f.key ? (ur ? "کاپی ہو گیا!" : "Copied!") : (ur ? "کاپی" : "Copy")}</span>
              </button>
            )}
          </div>
        ))}
      </div>
      <p style={{ fontSize: "0.8rem", color: "var(--checkout-muted)", marginTop: "1rem", marginBottom: 0 }}>
        {ur ? "نوٹ: رقم بھیجنے کے بعد رسید کا اسکرین شاٹ محفوظ رکھیں اور نیچے فارم میں اپ لوڈ کریں۔" : "Note: Keep the screenshot after transferring funds and upload it in the form below."}
      </p>
    </div>
  );
}
export function ItemConfigurator({product,language,premium=false}:{product:CatalogProduct;language:"en"|"ur";premium?:boolean}){
 const ur=language==="ur",[sizes,setSizes]=useState(product.variants.map((v,index)=>({variant_id:v.variant_id,copies:premium&&index===0?1:0}))),[separate,setSeparate]=useState(false),[status,setStatus]=useState("");
 const submitting=useRef(false),[busy,setBusy]=useState(false);
 function handleAction(redirectUrl: string){try{
  if(submitting.current)return;
  if(!canOrder(product)){setStatus(checkoutUnavailableMessage(product,language));return;}
  if(sizes.some(s=>!Number.isInteger(s.copies)||s.copies<0||s.copies>product.max_order_copies)){setStatus(ur?"کاپیوں کی درست مکمل تعداد درج کریں۔":"Enter whole copy counts within the product limit.");return;}
  if(!sizes.some(s=>s.copies>0)){setStatus(ur?"کم از کم ایک کاپی منتخب کریں۔":"Select at least one copy.");return;}
  const next=mergeItemCart(readItemCart(),{product_id:product.product_id,identity_group:separate?crypto.randomUUID():null,sizes:sizes.filter(s=>s.copies>0)});
  if(next.length>50||next.reduce((n,i)=>n+i.sizes.length,0)>50||next.some(i=>i.product_id===product.product_id&&i.sizes.reduce((n,s)=>n+s.copies,0)>product.max_order_copies)){setStatus(ur?"تمام سائز کی مشترکہ حد سے تجاوز ہے۔":"Combined copies exceed the product limit.");return;}
  submitting.current=true;setBusy(true);localStorage.setItem(itemCartKey,JSON.stringify(next));location.href=redirectUrl;
 }catch{submitting.current=false;setBusy(false);setStatus(ur?"کارٹ محفوظ نہیں ہو سکا۔":"Cart could not be saved.");}}
 if(premium){
  const total=sizes.reduce((n,s)=>n+s.copies,0);
  const invalid=sizes.some(s=>!Number.isInteger(s.copies)||s.copies<0)||total<1||total>product.max_order_copies;
  const cents=Number(product.price_per_copy.replace(".",""));
  function update(index:number,value:number){setSizes(previous=>previous.map((s,i)=>i===index?{...s,copies:value}:s));setStatus("");}
  return <section className="shop-config" aria-label={ur?"اپنا ٹیگ منتخب کریں":"Customize your tag"}>
    <h2>{ur?"سائز اور کاپیاں":"Sizes & Copies"}</h2><p>{ur?"سائز کے مطابق کاپیوں کی تعداد منتخب کریں۔":"Choose how many copies you’d like in each size."}</p>
    <div className="shop-sizes">{sizes.map((s,i)=><div className="shop-size" key={s.variant_id}><label htmlFor={"copies-"+s.variant_id}>{product.variants[i].name}</label>
      <div className="shop-stepper"><button type="button" aria-label={(ur?"کم کریں، ":"Decrease copies for ")+product.variants[i].name} disabled={busy||s.copies<=0||total<=1} onClick={()=>update(i,s.copies-1)}>−</button>
      <input id={"copies-"+s.variant_id} type="number" inputMode="numeric" min={0} max={product.max_order_copies} step={1} disabled={busy} value={Number.isNaN(s.copies)?"":s.copies} onChange={e=>update(i,e.target.value===""?NaN:Number(e.target.value))}/>
      <button type="button" aria-label={(ur?"بڑھائیں، ":"Increase copies for ")+product.variants[i].name} disabled={busy||!Number.isInteger(total)||total>=product.max_order_copies} onClick={()=>update(i,s.copies+1)}>+</button></div></div>)}</div>
    <small>{ur?"تمام سائز ملا کر زیادہ سے زیادہ":"Maximum across all sizes"} {product.max_order_copies} {ur?"کاپیاں":"copies"}</small>
    {invalid&&<p role="alert">{ur?"کم از کم ایک کاپی اور حد کے اندر مکمل تعداد منتخب کریں۔":"Select at least one copy using whole numbers within the combined limit."}</p>}
    <fieldset className="shop-identity"><legend>{ur?"QR کوڈ کے اختیارات":"QR Code Options"}</legend>
      <label><input type="radio" name="identity" checked={!separate} onChange={()=>setSeparate(false)} disabled={busy}/><span><strong>{ur?"کارٹ میں موجود QR استعمال کریں":"Use This Product’s Cart QR"}</strong><small>{ur?"کاپیاں اس پروڈکٹ کے موجودہ کارٹ آئٹم میں شامل ہوں گی۔":"Copies join this product’s existing cart item. A new item is created if needed."}</small></span></label>
      <label><input type="radio" name="identity" checked={separate} onChange={()=>setSeparate(true)} disabled={busy}/><span><strong>{ur?"اس بیچ کے لیے نیا QR":"New QR for This Batch"}</strong><small>{ur?"تمام منتخب سائز اور کاپیاں ایک نیا QR استعمال کریں گی۔":"All selected sizes and copies share one new QR, separate from other cart items."}</small></span></label>
    </fieldset>
    <dl className="shop-price-summary"><div><dt>{ur?"فی کاپی":"Unit price"}</dt><dd>PKR {product.price_per_copy}</dd></div><div><dt>{ur?"کل کاپیاں":"Total copies"}</dt><dd>{Number.isFinite(total)?total:"—"}</dd></div>
      <div><dt>{ur?"مصنوعات کی کل قیمت":"Product subtotal"}</dt><dd>{invalid?"—":"PKR "+(cents*total/100).toFixed(2)}</dd></div></dl>
    <p className="shop-charge-note">{ur?"ترسیل اور ٹیکس کی تصدیق چیک آؤٹ پر ہوگی۔":"Delivery and tax are confirmed at checkout."}</p>
    <p role="status">{status}</p><div className="shop-buy-actions"><button className="shop-primary" disabled={busy||invalid} onClick={()=>handleAction("/cart")}>{ur?"کارٹ میں شامل کریں":"Add to Cart"}</button>
      <button className="shop-secondary" disabled={busy||invalid} onClick={()=>handleAction("/checkout")}>{ur?"ابھی خریدیں":"Buy Now"}</button></div>
  </section>;
 }
 return <section dir={ur?"rtl":"ltr"}><h2>{ur?"سائز اور کاپیاں":"Sizes and copies"}</h2><p>{product.qr_type==="ice"?(ur?"ایمرجنسی":"Emergency"):"Lost"} · PKR {product.price_per_copy} {ur?"فی کاپی، تمام سائز":"per copy, all sizes"}</p><p>{ur?"ہر آئٹم کے لیے ایک منفرد QR، تمام کاپیاں اسی QR کو استعمال کریں گی۔":"One distinct QR per item. Every selected size and copy shares that identity."}</p><p>{ur?"زیادہ سے زیادہ مشترکہ کاپیاں":"Maximum combined copies"}: {product.max_order_copies}</p>{sizes.map((s,i)=><label className="copy-count" key={s.variant_id}>{product.variants[i].name}<input type="number" min={0} max={product.max_order_copies} value={s.copies} onChange={e=>setSizes(sizes.map((row,n)=>n===i?{...row,copies:Number(e.target.value)}:row))}/></label>)}<label className="check-field"><input type="checkbox" checked={separate} onChange={e=>setSeparate(e.target.checked)}/>{ur?"اس مصنوعہ کے لیے الگ QR شناخت بنائیں":"Create a separate QR identity for this product"}</label><p>{ur?"ورنہ اس مصنوعہ کی کاپیاں کارٹ کے موجودہ آئٹم میں شامل ہوں گی۔":"By default, copies merge into the existing cart item for this product."}</p><div style={{display:"flex",gap:"12px",alignItems:"center",flexWrap:"wrap",marginBlockStart:"1rem"}}><button type="button" className="button secondary" onClick={()=>handleAction("/cart")}>{ur?"کارٹ میں شامل کریں":"Add to cart"}</button><button type="button" className="button" onClick={()=>handleAction("/checkout")}>{ur?"ابھی خریدیں":"Buy now"}</button></div><p role="status">{status}</p></section>;
}

type QuotedItem={product_name:string;qr_type:string;quantity:number;unit_price:string;line_total:string;sizes:{name:string;copies:number}[]};
type Quote={quote_id:string;expires_at:string;subtotal_pkr:string;shipping_pkr:string;tax_pkr:string;total_pkr:string;currency_code:"PKR";items:QuotedItem[];identity_count:number;payment_instructions:PaymentInstructions};
export function ItemCheckoutCart({products,language,checkout=false}:{products:CatalogProduct[];language:"en"|"ur";checkout?:boolean}){
 const ur=language==="ur",[items,setItems]=useState<ItemCart[]>([]),[loaded,setLoaded]=useState(false),[busy,setBusy]=useState(false),[status,setStatus]=useState(""),[quote,setQuote]=useState<Quote|null>(null),[accepted,setAccepted]=useState(false),[confirmed,setConfirmed]=useState(false),[now,setNow]=useState(Date.now());
 const [address,setAddress]=useState({recipient_name:"",phone:"",address:"",city:"",province:"",postal_code:""}),[saved,setSaved]=useState<SavedAddress|null>(null);
 const keys=useRef(new Map<string,string>()),running=useRef(false),generation=useRef(0);
 useEffect(()=>{setItems(readItemCart());setLoaded(true);const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[]);
 function invalidate(){generation.current++;setQuote(null);setAccepted(false);setStatus("");}
 const selectAddress=useCallback((value:SavedAddress|null)=>{setSaved(value);generation.current++;setQuote(null);setAccepted(false);setConfirmed(false);},[]);
 const catalog=new Map(products.filter(p=>p.commerce_model==="single_qr").map(p=>[p.product_id,p]));
 const unavailable=items.some(i=>{const p=catalog.get(i.product_id);return !p||!canOrder(p)||i.sizes.some(s=>!p.variants.some(v=>v.variant_id===s.variant_id))||i.sizes.reduce((n,s)=>n+s.copies,0)>p.max_order_copies;});
 function save(next:ItemCart[]){invalidate();try{localStorage.setItem(itemCartKey,JSON.stringify(next));setItems(next);}catch{setStatus(ur?"کارٹ محفوظ نہیں ہو سکا۔":"Cart could not be saved.");}}
 async function send(path:string,body:unknown){const signature=JSON.stringify({path,body});if(!keys.current.has(signature))keys.current.set(signature,crypto.randomUUID());const response=await fetch("/checkout/api",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path,body,key:keys.current.get(signature)})});const data=await response.json();if(!response.ok)throw Error(data.error?.code??"UNAVAILABLE");return data;}
 function renewQuoteKey(){for(const signature of keys.current.keys())if(JSON.parse(signature).path==="/me/checkout/item-quotes")keys.current.delete(signature);}
 function failure(error:unknown){const code=error instanceof Error?error.message:"";if(code==="QUOTE_STALE"||code==="QUOTE_UNAVAILABLE"){renewQuoteKey();setQuote(null);setAccepted(false);}setStatus(code==="QUOTE_STALE"||code==="QUOTE_UNAVAILABLE"?(ur?"قیمت تبدیل یا ختم ہو گئی۔ نئی قیمت حاصل کریں۔":"Quote changed or expired. Request a fresh quote."):code==="AUTH_REQUIRED"||code==="UNAUTHENTICATED"?(ur?"دوبارہ سائن ان کریں۔ کارٹ محفوظ ہے۔":"Please sign in again. Your cart is preserved."):code==="FORBIDDEN"?(ur?"آپ کو اس کارروائی کی اجازت نہیں۔ کارٹ محفوظ ہے۔":"You do not have permission to complete this action. Your cart is preserved."):code==="CHECKOUT_CHARGES_UNCONFIGURED"?(ur?"ترسیل اور ٹیکس کی رقم مقرر نہیں۔ کارٹ محفوظ ہے۔":"Delivery and tax amounts are not configured. Your cart is preserved."):code==="CHECKOUT_RUNTIME_DISABLED"?(ur?"سرور پر چیک آؤٹ فعال نہیں۔ کارٹ محفوظ ہے۔":"Checkout is not enabled on the server. Your cart is preserved."):code==="PROVIDER_UNAVAILABLE"?(ur?"چیک آؤٹ سروس عارضی طور پر دستیاب نہیں۔ کارٹ محفوظ ہے۔":"The checkout service is temporarily unavailable. Your cart is preserved."):code==="VALIDATION_ERROR"?(ur?"پتے اور کاپیوں کی تعداد چیک کریں۔ کارٹ محفوظ ہے۔":"Check the address and copy quantities. Your cart is preserved."):code==="MAX_ORDER_COPIES_EXCEEDED"?(ur?"مشترکہ کاپیوں کی حد سے تجاوز ہے۔":"Combined copies exceed the product limit."):code==="SINGLE_QR_CHECKOUT_NOT_RELEASED"?(ur?"آن لائن خریداری ابھی فعال نہیں۔ کارٹ محفوظ ہے۔":"Online purchasing has not been enabled. Your cart is preserved."):code==="PAYMENT_INSTRUCTIONS_UNAVAILABLE"?(ur?"منظور شدہ بینک / راست ہدایات دستیاب نہیں۔ کارٹ محفوظ ہے۔":"Approved Bank / Raast payment instructions are unavailable. Your cart is preserved."):ur?"درخواست مکمل نہیں ہوئی۔ کارٹ محفوظ ہے۔":"Request could not be completed. Your cart is preserved.");}
 async function getQuote(e:React.FormEvent){e.preventDefault();if(running.current||unavailable||!confirmed)return;if(!saved&&!/^\+[1-9][0-9]{7,14}$/.test(address.phone)){setStatus(ur?"فون نمبر ملک کے کوڈ کے ساتھ درج کریں، مثلاً +923001234567۔":"Enter the phone number with its country code, for example +923001234567.");return;}running.current=true;setBusy(true);setStatus("");const revision=generation.current;if(quote&&Date.parse(quote.expires_at)<=Date.now())renewQuoteKey();try{const result=await send("/me/checkout/item-quotes",{commerce_model:"single_qr",items,...(saved?{shipping_address_id:saved.id,shipping_address_version:saved.version}:{address:{...address,province:address.province||null,postal_code:address.postal_code||null}}),contact_phone_confirmation:confirmed});if(revision===generation.current){setQuote(result);setAccepted(false);setNow(Date.now());}}catch(e){failure(e);}finally{running.current=false;setBusy(false);}}
 async function continueToPayment() {
  if (running.current || !quote || !accepted || Date.parse(quote.expires_at) <= Date.now()) return;
  running.current = true;
  setBusy(true);
  setStatus("");
  try {
   const result = await send(`/me/checkout/item-quotes/${quote.quote_id}/confirm`, { accept_total: quote.total_pkr, accept_currency: "PKR" });
   if (typeof result.order_id !== 'string' || !uuid(result.order_id)) throw Error("PROVIDER_UNAVAILABLE");
   try { localStorage.removeItem(itemCartKey); } catch { /* My Orders can resume the confirmed order. */ }
   location.replace(`/checkout?orderId=${result.order_id}`);
   return;
  } catch (error) {
   failure(error);
   running.current = false;
   setBusy(false);
  }
 }
 if(!loaded)return <p role="status" style={{ padding: "1.5rem 0", color: "var(--checkout-muted)" }}>{ur?"کارٹ لوڈ ہو رہا ہے۔":"Loading cart…"}</p>;
 if(!items.length)return <div className="checkout-panel"><p style={{ margin: 0, color: "var(--checkout-muted)" }}>{ur?"الگ QR کارٹ خالی ہے۔":"Your independent QR cart is empty."}</p></div>;

 if(!checkout){
  return (
   <section dir={ur?"rtl":"ltr"} aria-label={ur?"الگ QR کارٹ":"Independent QR cart"}>
    <div className="checkout-panel">
     <h2>{ur?"QR آئٹمز":"QR items"}</h2>
     <p style={{ color: "var(--checkout-muted)", fontSize: "0.9rem", margin: "0 0 1rem" }}>
      {ur?"ہر آئٹم کا ایک QR، کاپیوں کی تعداد سے قطع نظر۔":"Each item receives one distinct QR after verified payment, regardless of copy count."}
     </p>
     {items.map((item,index)=><div className="checkout-item-card" key={`${item.product_id}:${item.identity_group}`}>
      <div className="checkout-item-thumb"><CustomerIcon name="tag"/></div>
      <div className="checkout-item-info">
       <h3>{catalog.get(item.product_id)?.name??(ur?"مصنوعہ دستیاب نہیں":"Product unavailable")}</h3>
       <p className="checkout-item-meta">{item.identity_group?(ur?"الگ شناخت":"Separate identity"):(ur?"مشترکہ آئٹم":"Merged item")}</p>
       {item.sizes.map((s,n)=><div style={{display:"flex",alignItems:"center",gap:"0.5rem",margin:"0.4rem 0"}} key={s.variant_id}>
        <span className="checkout-item-meta">{catalog.get(item.product_id)?.variants.find(v=>v.variant_id===s.variant_id)?.name??(ur?"سائز دستیاب نہیں":"Size unavailable")}:</span>
        <input type="number" min={1} max={100} value={s.copies} disabled={busy} style={{width:"4rem",padding:"0.2rem 0.5rem",borderRadius:"6px",border:"1px solid var(--checkout-line)"}} onChange={e=>save(items.map((i,j)=>j===index?{...i,sizes:i.sizes.map((row,k)=>k===n?{...row,copies:Math.max(1,Math.min(100,Math.trunc(Number(e.target.value))||1))}:row)}:i))}/>
        <button type="button" className="button secondary" style={{padding:"0.2rem 0.6rem",minHeight:"32px",fontSize:"0.75rem"}} onClick={()=>save(items.map((i,j)=>j===index?{...i,sizes:i.sizes.filter((_,k)=>k!==n)}:i).filter(i=>i.sizes.length))}>{ur?"سائز ہٹائیں":"Remove size"}</button>
       </div>)}
       <button type="button" className="button secondary" style={{padding:"0.3rem 0.8rem",minHeight:"34px",fontSize:"0.8rem",marginTop:"0.5rem"}} onClick={()=>save(items.filter((_,j)=>j!==index))}>{ur?"آئٹم ہٹائیں":"Remove item"}</button>
      </div>
     </div>)}
     <div style={{ marginTop: "1rem" }}>
      <a className="button" href="/checkout">{ur?"چیک آؤٹ":"Continue to checkout"}</a>
     </div>
    </div>
   </section>
  );
 }

 return (
  <section dir={ur?"rtl":"ltr"} aria-label={ur?"چیک آؤٹ تفصیلات":"Checkout details"}>
   <div className="checkout-layout">
    <div className="checkout-main">
     <div className="checkout-panel">
      <h2>{ur?"منتخب کردہ آئٹمز":"Selected Items"}</h2>
      {items.map((item,index)=><div className="checkout-item-card" key={`${item.product_id}:${item.identity_group}`}>
       <div className="checkout-item-thumb"><CustomerIcon name="tag"/></div>
       <div className="checkout-item-info">
        <h3>{catalog.get(item.product_id)?.name??(ur?"مصنوعہ دستیاب نہیں":"Product unavailable")}</h3>
        <p className="checkout-item-meta">{item.identity_group?(ur?"الگ شناخت":"Separate identity"):(ur?"مشترکہ آئٹم":"Merged item")}</p>
        <div style={{display:"flex",flexWrap:"wrap",gap:"0.75rem",margin:"0.4rem 0"}}>
         {item.sizes.map(s=><span key={s.variant_id} style={{fontSize:"0.85rem",background:"#f5eee6",padding:"0.2rem 0.6rem",borderRadius:"8px"}}>
          {catalog.get(item.product_id)?.variants.find(v=>v.variant_id===s.variant_id)?.name}: <strong>{s.copies} {ur?"کاپیاں":"copies"}</strong>
         </span>)}
        </div>
       </div>
      </div>)}
      {items.map(i=>catalog.get(i.product_id)).filter((p):p is CatalogProduct=>!!p&&!canOrder(p)).map(p=><p role="status" style={{color:"var(--danger)",fontSize:"0.875rem"}} key={p.product_id}>{p.name}: {checkoutUnavailableMessage(p,language)}</p>)}
      {unavailable&&<div className="checkout-notice-box" style={{background:"#fff4ef",borderColor:"#e6c2b8",color:"#7c372a"}} role="alert">
       <p style={{margin:0}}>{ur?"دستیاب سائز اور مشترکہ حد چیک کریں۔":"Some selected products are unavailable for ordering, or their size/copy limits changed. Your cart is preserved."}</p>
      </div>}
     </div>

     <div className="checkout-panel">
      <h2>{ur?"ترسیل کا پتہ":"Shipping Address"}</h2>
      <SavedAddressSelector ur={ur} onSelect={selectAddress} disabled={busy}/>
      <form onSubmit={getQuote} style={{ marginTop: "1rem" }}>
       <fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0 }}>
        {!saved&&<div className="checkout-form-grid" style={{ marginBottom: "1rem" }}>
         <div className="checkout-field">
          <label htmlFor="chk-name">{ur?"وصول کنندہ کا پورا نام":"Recipient Full Name"}</label>
          <input id="chk-name" value={address.recipient_name} required maxLength={160} onChange={e=>{setAddress({...address,recipient_name:e.target.value});setConfirmed(false);invalidate();}} placeholder={ur?"مثلاً محمد عثمان":"e.g. Muhammad Usman"}/>
         </div>
         <div className="checkout-field">
          <label htmlFor="chk-phone">{ur?"رابطہ فون نمبر":"Contact Phone Number"}</label>
          <input id="chk-phone" value={address.phone} type="tel" required pattern="\+[1-9][0-9]{7,14}" maxLength={16} aria-describedby="checkout-phone-help" onChange={e=>{setAddress({...address,phone:e.target.value});setConfirmed(false);invalidate();}} placeholder="+923001234567"/>
          <small id="checkout-phone-help" className="checkout-phone-help">{ur?"ملک کا کوڈ ضروری ہے (+92)، پھر ابتدائی 0 کے بغیر 10 ہندسے۔ مثال: +923001234567۔":"Include country code (+92) followed by 10 digits without leading 0. Example: +923001234567."}</small>
         </div>
         <div className="checkout-field">
          <label htmlFor="chk-addr">{ur?"مکمل گلی / گھر کا پتہ":"Street Address & House / Flat No."}</label>
          <input id="chk-addr" value={address.address} required maxLength={500} onChange={e=>{setAddress({...address,address:e.target.value});setConfirmed(false);invalidate();}} placeholder={ur?"گھر / فلیٹ نمبر، گلی، علاقہ":"House/apartment, street, area"}/>
         </div>
         <div className="checkout-form-grid two-col">
          <div className="checkout-field">
           <label htmlFor="chk-city">{ur?"شہر":"City"}</label>
           <input id="chk-city" value={address.city} required maxLength={100} onChange={e=>{setAddress({...address,city:e.target.value});setConfirmed(false);invalidate();}} placeholder={ur?"مثلاً لاہور / کراچی":"e.g. Lahore, Karachi"}/>
          </div>
          <div className="checkout-field">
           <label htmlFor="chk-prov">{ur?"صوبہ (اختیاری)":"Province (optional)"}</label>
           <input id="chk-prov" value={address.province} maxLength={100} onChange={e=>{setAddress({...address,province:e.target.value});setConfirmed(false);invalidate();}} placeholder={ur?"مثلاً پنجاب / سندھ":"e.g. Punjab, Sindh"}/>
          </div>
         </div>
         <div className="checkout-field">
          <label htmlFor="chk-postal">{ur?"پوسٹل کوڈ (اختیاری)":"Postal Code (optional)"}</label>
          <input id="chk-postal" value={address.postal_code} maxLength={20} onChange={e=>{setAddress({...address,postal_code:e.target.value});setConfirmed(false);invalidate();}} placeholder="54000"/>
         </div>
        </div>}

        <label className="checkout-notice-box" style={{ cursor: "pointer" }}>
         <input type="checkbox" required checked={confirmed} onChange={e=>{setConfirmed(e.target.checked);invalidate();}}/>
         <span>{ur?"میں ترسیل کے فون اور پتے کی درستگی کی تصدیق کرتا ہوں۔":"I confirm that the shipping phone number and address are complete and correct."}</span>
        </label>

        <button className="button" style={{ minHeight: "48px" }} disabled={unavailable||!confirmed||busy} type="submit">
         {busy ? (ur?"قیمت حاصل ہو رہی ہے…":"Calculating…") : quote ? (ur?"نئی قیمت حاصل کریں":"Refresh Final Quote") : (ur?"حتمی قیمت حاصل کریں":"Get Final Quote")}
        </button>
       </fieldset>
      </form>
     </div>
    </div>

    <aside className="checkout-sidebar checkout-summary-sticky">
     <div className="checkout-panel">
      <h2>{ur?"آرڈر کا خلاصہ":"Order Summary"}</h2>
      {quote ? (
       <div>
        <div style={{ marginBottom: "1rem" }}>
         {quote.items.map((i,n)=><div style={{display:"flex",justifyContent:"space-between",fontSize:"0.85rem",marginBottom:"0.4rem"}} key={n}>
          <span>{i.product_name} ({i.quantity}x)</span>
          <strong><bdi>PKR {i.line_total}</bdi></strong>
         </div>)}
        </div>
        <dl className="checkout-summary-dl">
         <div>
          <dt>{ur?"مصنوعات کی قیمت":"Subtotal"}</dt>
          <dd><bdi>PKR {quote.subtotal_pkr}</bdi></dd>
         </div>
         <div>
          <dt>{ur?"ترسیل (ڈلیوری)":"Delivery"}</dt>
          <dd><bdi>PKR {quote.shipping_pkr}</bdi></dd>
         </div>
         {Number(quote.tax_pkr) > 0 && <div>
          <dt>{ur?"ٹیکس":"Tax"}</dt>
          <dd><bdi>PKR {quote.tax_pkr}</bdi></dd>
         </div>}
         <div className="checkout-summary-total">
          <dt>{ur?"کل واجب الادا رقم":"Total Amount"}</dt>
          <dd><bdi>PKR {quote.total_pkr}</bdi></dd>
         </div>
        </dl>

        <p style={{ fontSize: "0.8rem", color: "var(--checkout-muted)", marginTop: "0.75rem" }}>
         {Date.parse(quote.expires_at)<=now?(ur?"قیمت کی میعاد ختم۔ نئی قیمت حاصل کریں۔":"Quote expired. Please refresh quote."):(ur?"قیمت کی میعاد جاری ہے۔":"Quote is locked for checkout.")}
        </p>

        <label className="checkout-notice-box" style={{ cursor: "pointer", fontSize: "0.85rem", margin: "1rem 0" }}>
         <input type="checkbox" checked={accepted} disabled={busy} onChange={e=>setAccepted(e.target.checked)}/>
         <span>{ur?"میں کل رقم اور ترسیل کی شرائط قبول کرتا ہوں۔":"I accept the order total and delivery terms."}</span>
        </label>

        <button className="button" style={{ width: "100%", minHeight: "50px", fontSize: "1rem" }} disabled={busy||!accepted||Date.parse(quote.expires_at)<=now} onClick={()=>void continueToPayment()}>
         {busy ? (ur?"پروسیسنگ…":"Processing…") : (ur?"ادائیگی کے لیے آگے بڑھیں":"Continue to Payment")}
        </button>
       </div>
      ) : (
       <div style={{ textAlign: "center", padding: "1.5rem 0", color: "var(--checkout-muted)" }}>
        <CustomerIcon name="cart" />
        <p style={{ fontSize: "0.875rem", margin: "0.75rem 0 0" }}>
         {ur?"ترسیل کا پتہ تصدیق کر کے حتمی قیمت حاصل کریں تاکہ کل رقم دیکھی جا سکے۔":"Confirm shipping address and request quote to see final total with delivery charges."}
        </p>
       </div>
      )}

      <div className="checkout-trust-badge">
       <CustomerIcon name="shield"/>
       <span>{ur?"بینک / راست تصدیق شدہ آرڈر":"Bank & Raast Verified Checkout"}</span>
      </div>
     </div>
    </aside>
   </div>
   {status && <div className="checkout-notice-box" style={{background:"#fff4ef",borderColor:"#e6c2b8",color:"#7c372a",marginTop:"1rem"}} role="status"><p style={{margin:0}}>{status}</p></div>}
  </section>
 );
}
