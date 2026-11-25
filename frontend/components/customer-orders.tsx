"use client";
import Link from "next/link";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import type { CustomerOrder } from "../lib/customer-orders";
import { badgeTone, customerOrderLabel, mainOrderState, orderDate } from "../lib/customer-orders";
import { CustomerIcon } from "./customer-icon";

export function OrderRetry({ur}:{ur:boolean}) {
  const router=useRouter(),[pending,start]=useTransition();
  return <button className="orders-secondary" disabled={pending} onClick={()=>start(()=>router.refresh())}>
    {pending?(ur?"کوشش جاری ہے…":"Retrying…"):(ur?"دوبارہ کوشش کریں":"Retry")}</button>;
}
export function OrderBadge({value,kind,ur}:{value:string;kind:"order"|"payment"|"fulfillment"|"print";ur:boolean}) {
  return <span className={"orders-badge "+badgeTone(value)}>{customerOrderLabel(value,kind,ur)}</span>;
}
export function OrdersSkeleton() {
  return <div className="orders-screen orders-loading" role="status" aria-busy="true"><span className="sr-only">Loading orders / آرڈرز لوڈ ہو رہے ہیں</span>
    <i className="orders-skeleton-title" aria-hidden="true"/><i className="orders-skeleton-search" aria-hidden="true"/><div className="orders-grid" aria-hidden="true">{[0,1,2].map(i=><div className="orders-card" key={i}><i/><i/><i/></div>)}</div></div>;
}
export function OrdersList({items,next,older,cursor,ur,unavailable=false}:{items:CustomerOrder[];next:string|null;older:boolean;cursor?:string;ur:boolean;unavailable?:boolean}) {
  const [query,setQuery]=useState(""),[filter,setFilter]=useState("all");
  const t=(en:string,u:string)=>ur?u:en,complete=!next&&!older;
  const matches=(o:CustomerOrder,key:string)=>{
    if(key==="awaiting")return o.order_status!=="cancelled"&&["awaiting_transfer","rejected"].includes(o.payment_status);
    if(key==="processing")return o.order_status!=="cancelled"&&["unallocated","allocated","preparing","packed"].includes(o.fulfillment_status);
    if(key==="shipped")return o.order_status!=="cancelled"&&o.fulfillment_status==="dispatched";
    if(key==="delivered")return o.order_status!=="cancelled"&&o.fulfillment_status==="delivered";
    if(key==="cancelled")return o.order_status==="cancelled";
    return true;
  };
  const filters=[["all","All Orders","تمام آرڈرز"],["awaiting","Awaiting Payment","ادائیگی کا انتظار"],["processing","Processing","کارروائی جاری"],["shipped","Shipped","روانہ"],["delivered","Delivered","پہنچ گیا"],["cancelled","Cancelled","منسوخ"]];
  const result=items.filter(o=>matches(o,filter)&&(!query.trim()||o.order_number.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())));
  function clear(){setQuery("");setFilter("all");}
  return <section className="orders-screen">
    <header className="orders-intro"><h1>{t("My Orders","میرے آرڈرز")}</h1><p>{t("Track your purchases, payments, and deliveries.","اپنی خریداری، ادائیگیوں اور ترسیل پر نظر رکھیں۔")}</p></header>
    {!unavailable&&items.length>0&&complete&&<>
      <div className="orders-search"><CustomerIcon name="search"/><input type="search" value={query} onChange={e=>setQuery(e.target.value)} autoComplete="off" enterKeyHint="search"
        aria-label={t("Search your orders","اپنے آرڈرز تلاش کریں")} placeholder={t("Search your orders","اپنے آرڈرز تلاش کریں")}/>
        {query&&<button aria-label={t("Clear search","تلاش صاف کریں")} onClick={()=>setQuery("")}><CustomerIcon name="close"/></button>}</div>
      <div className="orders-filters" role="group" aria-label={t("Filter orders","آرڈرز فلٹر کریں")}>{filters.map(([key,en,u])=><button key={key} className={filter===key?"selected":""} aria-pressed={filter===key} onClick={()=>setFilter(key)}>{ur?u:en}{key==="all"&&<span>{items.length}</span>}</button>)}</div>
      {(filter!=="all"||query)&&<button className="orders-clear" onClick={clear}>{t("Clear Filters","فلٹر صاف کریں")}</button>}
    </>}
    {!complete&&!unavailable&&<p className="orders-note">{t("Showing a page of your order history. Search and filters are available when your complete history fits on one page.","آرڈر ہسٹری کا ایک صفحہ دکھایا جا رہا ہے۔ مکمل ہسٹری ایک صفحے پر ہونے پر تلاش اور فلٹر دستیاب ہوں گے۔")}</p>}
    {unavailable?<div className="orders-empty" role="alert"><CustomerIcon name="refresh"/><h2>{t("Your orders couldn’t be loaded.","آپ کے آرڈرز لوڈ نہیں ہو سکے۔")}</h2><p>{t("Please try again in a moment.","تھوڑی دیر بعد دوبارہ کوشش کریں۔")}</p><OrderRetry ur={ur}/></div>:
      !result.length?<div className="orders-empty"><CustomerIcon name="orders"/><h2>{items.length?t("No Matching Orders","کوئی مماثل آرڈر نہیں"):older?t("No More Orders","مزید آرڈرز نہیں"):t("No Orders Yet","ابھی کوئی آرڈر نہیں")}</h2>
        <p>{items.length?t("Try another filter to find your order.","اپنا آرڈر تلاش کرنے کے لیے فلٹر تبدیل کریں۔"):older?t("Return to your latest orders.","تازہ ترین آرڈرز پر واپس جائیں۔"):t("Your QR tag purchases will appear here.","آپ کی QR ٹیگ کی خریداری یہاں دکھائی دے گی۔")}</p>
        {items.length?<button className="orders-secondary" onClick={clear}>{t("Clear Filters","فلٹر صاف کریں")}</button>:<Link className="orders-primary" href={older?"/orders":"/shop"}>{older?t("Latest Orders","تازہ ترین آرڈرز"):t("Shop QR Tags","QR ٹیگز خریدیں")}</Link>}
      </div>:<div className="orders-grid">{result.map(o=>{
        const state=mainOrderState(o);
        return <article className="orders-card" key={o.id}><div className="orders-card-top"><time dateTime={o.created_at}>{orderDate(o.created_at,ur)}</time><OrderBadge {...state} ur={ur}/></div>
          <div className="orders-purchase"><span className="orders-art" aria-hidden="true"><CustomerIcon name="box"/></span><div><h2><bdi>{o.order_number.length>24?"…"+o.order_number.slice(-16):o.order_number}</bdi></h2>
            <span className="orders-meta">{t("Order Total","آرڈر کی کل رقم")}</span><strong><bdi>{o.currency_code} {o.total_pkr}</bdi></strong></div></div>
          {o.order_status==="cancelled"&&<p className="orders-meta">{customerOrderLabel(o.fulfillment_status,"fulfillment",ur)}</p>}
          <div className="orders-payment"><span>{t("Payment","ادائیگی")}</span><OrderBadge kind="payment" value={o.payment_status} ur={ur}/></div>
          <Link className="orders-primary" prefetch={false} href={`/orders/${o.id}`+(cursor?"?cursor="+encodeURIComponent(cursor):"")}>{t("View Order Details","آرڈر کی تفصیلات دیکھیں")}<CustomerIcon name="arrow"/></Link>
          <Link className="orders-payment-link" prefetch={false} href={`/checkout?orderId=${o.id}`}>{t("View Payment Details","ادائیگی کی تفصیلات دیکھیں")}</Link>
        </article>;
      })}</div>}
    <div className="orders-pagination">{older&&<Link className="orders-secondary" href="/orders">{t("Latest Orders","تازہ ترین آرڈرز")}</Link>}
      {next&&<Link className="orders-secondary" href={"/orders?cursor="+encodeURIComponent(next)}>{t("Older Orders","پرانے آرڈرز")}</Link>}
      <Link className="orders-shopping" href="/portal/shop">{t("Continue Shopping","خریداری جاری رکھیں")}</Link></div>
  </section>;
}
