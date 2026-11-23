"use client";
import Link from "next/link";
import { useState } from "react";
import type { Shipment } from "../lib/fulfillment-workflow";
import { type ShipmentSummary, type DeliveryAddress, shipmentLabel, shipmentTone, shipmentDate } from "../lib/customer-shipments";
import { CustomerIcon } from "./customer-icon";
import { ShipmentRefresh } from "./shipment-refresh";

export function TrackingNumber({value,ur}:{value:string|null;ur:boolean}){
  const [feedback,setFeedback]=useState(""),[copying,setCopying]=useState(false);
  async function copy(){
    if(!value||copying)return;
    setCopying(true);setFeedback("");
    try{await navigator.clipboard.writeText(value);setFeedback(ur?"ٹریکنگ نمبر کاپی ہو گیا۔":"Tracking number copied.");}
    catch{setFeedback(ur?"کاپی نہیں ہو سکا۔ نمبر منتخب کر کے کاپی کریں۔":"Copy couldn’t complete. Select the tracking number to copy it.");}
    finally{setCopying(false);}
  }
  return <div className="ship-tracking"><span className="ship-label">{ur?"ٹریکنگ نمبر":"Tracking Number"}</span>
    {value?<div className="ship-tracking-value"><bdi>{value}</bdi><button type="button" disabled={copying} aria-label={ur?"ٹریکنگ نمبر کاپی کریں":"Copy Tracking Number"} title={ur?"ٹریکنگ نمبر کاپی کریں":"Copy Tracking Number"} onClick={copy}>
      <CustomerIcon name="copy"/></button></div>:<p className="ship-muted">{ur?"ٹریکنگ نمبر ابھی دستیاب نہیں۔":"Tracking number not available yet."}</p>}
    {feedback&&<p className="ship-copy-feedback" role="status">{feedback}</p>}
  </div>;
}
export function ShipmentBadge({status,ur}:{status:string;ur:boolean}){return <span className={"ship-badge "+shipmentTone(status)}>{shipmentLabel(status,ur)}</span>;}
export function ShipmentSkeleton(){
  return <div className="ship-screen ship-loading" role="status" aria-busy="true"><span className="sr-only">Loading shipments / ترسیلات لوڈ ہو رہی ہیں</span><i className="ship-skeleton-title" aria-hidden="true"/>
    <div className="ship-grid" aria-hidden="true">{[0,1,2].map(i=><div className="ship-card" key={i}><i/><i/><i/></div>)}</div></div>;
}
export function ShipmentsList({items,next,cursor,ur,failed=false}:{items:ShipmentSummary[];next:string|null;cursor?:string;ur:boolean;failed?:boolean}){
  const [filter,setFilter]=useState("all"),t=(en:string,u:string)=>ur?u:en;
  const complete=!cursor&&!next;
  const filters=[["all","All","تمام"],["preparing","Preparing","تیاری"],["dispatched","Dispatched","روانہ"],["delivered","Delivered","پہنچ گیا"],["exception","Needs Attention","توجہ درکار"],["returned","Returned","واپس"]];
  const result=items.filter(s=>filter==="all"||(filter==="preparing"?["preparing","packed"].includes(s.status):s.status===filter));
  return <section className="ship-screen"><header className="ship-intro"><div><h1>{t("My Shipments","میری ترسیلات")}</h1><p>{t("Track your QR tag deliveries in one place.","اپنے QR ٹیگز کی ترسیل ایک جگہ دیکھیں۔")}</p></div><ShipmentRefresh ur={ur}/></header>
    {!failed&&items.length>0&&<><div className="ship-filters" role="group" aria-label={t("Filter shipments","ترسیلات فلٹر کریں")}>{filters.map(([key,en,u])=><button key={key} aria-pressed={filter===key} className={filter===key?"selected":""} onClick={()=>setFilter(key)}>{ur?u:en}{key==="all"&&complete&&<span>{items.length}</span>}</button>)}</div>
      {!complete&&<p className="ship-note">{t("Filters apply to this page of shipment history.","فلٹر ترسیل کی ہسٹری کے اس صفحے پر لاگو ہیں۔")}</p>}
      {filter!=="all"&&<button className="ship-clear" onClick={()=>setFilter("all")}>{t("Clear Filters","فلٹر صاف کریں")}</button>}</>}
    {failed?<div className="ship-empty" role="alert"><CustomerIcon name="refresh"/><h2>{t("Shipments couldn’t be loaded.","ترسیلات لوڈ نہیں ہو سکیں۔")}</h2><p>{t("Refresh to try again.","دوبارہ کوشش کے لیے تازہ کریں۔")}</p><ShipmentRefresh ur={ur} automatic={false} retry/></div>:
    !result.length?<div className="ship-empty"><span className="ship-empty-icon"><CustomerIcon name="truck"/></span><h2>{items.length?t("No Matching Shipments","کوئی مماثل ترسیل نہیں"):cursor?t("No More Shipments","مزید ترسیلات نہیں"):t("No Shipments Yet","ابھی کوئی ترسیل نہیں")}</h2>
      <p>{items.length?t("Try another filter to find your delivery.","ترسیل تلاش کرنے کے لیے فلٹر تبدیل کریں۔"):t("Your shipment details will appear here once your orders are prepared for delivery.","آپ کے آرڈرز ترسیل کے لیے تیار ہونے پر تفصیلات یہاں دکھائی دیں گی۔")}</p>
      {items.length?<button className="ship-secondary" onClick={()=>setFilter("all")}>{t("Clear Filters","فلٹر صاف کریں")}</button>:<Link className="ship-primary" href="/orders">{t("View My Orders","میرے آرڈرز دیکھیں")}</Link>}</div>:
      <div className="ship-grid">{result.map(s=>{
        const query=new URLSearchParams({orderId:s.order_id});if(cursor)query.set("cursor",cursor);
        const first=s.order_items[0];
        return <article className="ship-card" key={s.id}><div className="ship-card-top"><ShipmentBadge status={s.status} ur={ur}/>{(s.dispatched_at||s.created_at)&&<time dateTime={s.dispatched_at||s.created_at}>{shipmentDate((s.dispatched_at||s.created_at)!,ur)}</time>}</div>
          <div className="ship-product"><span className="ship-art" aria-hidden="true"><CustomerIcon name="box"/></span><div><h2><bdi>{s.order_number}</bdi></h2>
            {first&&<p><bdi>{first.product_name_snapshot}</bdi> × {first.quantity}</p>}
            {s.order_items.length>1&&<span className="ship-muted">+ {s.order_items.length-1} {t("more order items","مزید آرڈر آئٹمز")}</span>}
            <span className="ship-label">{t("Order contents","آرڈر میں شامل مصنوعات")}</span></div></div>
          <div className="ship-carrier"><CustomerIcon name="truck"/><span>{s.carrier||t("Delivery service not available yet.","ترسیل کی سروس ابھی دستیاب نہیں۔")}</span></div>
          <TrackingNumber key={s.tracking_reference??"missing"} value={s.tracking_reference} ur={ur}/>
          <Link className="ship-primary" prefetch={false} href={`/shipments/${s.id}?${query}`}>{t("View Shipment Details","ترسیل کی تفصیلات دیکھیں")}<CustomerIcon name="arrow"/></Link>
          <Link className="ship-order-link" prefetch={false} href={`/orders/${s.order_id}`}>{t("View Related Order","متعلقہ آرڈر دیکھیں")}</Link>
        </article>;
      })}</div>}
    <div className="ship-pagination">{cursor&&<Link className="ship-secondary" href="/shipments">{t("Latest Shipments","تازہ ترین ترسیلات")}</Link>}
      {next&&<Link className="ship-secondary" href={"/shipments?cursor="+encodeURIComponent(next)}>{t("Older Shipments","پرانی ترسیلات")}</Link>}</div>
  </section>;
}
export function ShipmentDetails({shipment,summary,orderId,address,backHref,ur}:{shipment:Shipment|null;summary:ShipmentSummary|null;orderId:string|null;address:DeliveryAddress|null;backHref:string;ur:boolean}){
  const t=(en:string,u:string)=>ur?u:en;
  const milestones:{name:string;at:string}[]=[];
  if(summary?.created_at)milestones.push({name:t("Shipment Created","ترسیل درج ہو گئی"),at:summary.created_at});
  if(shipment)for(const [label,at] of [
    [t("Packed for Dispatch","روانگی کے لیے پیک"),shipment.packed_at],
    [t("Dispatched","روانہ ہو گیا"),shipment.dispatched_at],
    [t("Delivery Recorded","ترسیل کی تصدیق درج"),shipment.delivered_at],
  ] as const)if(at)milestones.push({name:label,at});
  milestones.sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  return <section className="ship-screen ship-details"><Link className="ship-back" href={backHref}><CustomerIcon name="arrow"/>{t("Back to My Shipments","میری ترسیلات پر واپس")}</Link>
    <header className="ship-intro"><div><h1>{t("Shipment Details","ترسیل کی تفصیلات")}</h1>{summary&&<p><bdi>{summary.order_number}</bdi></p>}</div><ShipmentRefresh ur={ur}/></header>
    {!shipment?<div className="ship-empty" role="alert"><h2>{t("Shipment information couldn’t be loaded.","ترسیل کی معلومات لوڈ نہیں ہو سکیں۔")}</h2><p>{t("Refresh to try again.","دوبارہ کوشش کے لیے تازہ کریں۔")}</p><ShipmentRefresh ur={ur} automatic={false} retry/></div>:
      <div className="ship-detail-grid"><div className="ship-detail-main">
        <section className={"ship-status-card "+shipmentTone(shipment.status)}><span className="ship-status-icon"><CustomerIcon name={shipment.status==="delivered"?"check":"truck"}/></span>
          <div><span className="ship-label">{t("Current Shipment Status","ترسیل کی موجودہ حالت")}</span><h2>{shipmentLabel(shipment.status,ur)}</h2>
            {shipment.dispatched_at&&<p>{t("Dispatched","روانہ ہوا")} · {shipmentDate(shipment.dispatched_at,ur)}</p>}</div></section>
        <section className="ship-panel"><h2>{t("Tracking Information","ٹریکنگ کی معلومات")}</h2><TrackingNumber key={shipment.tracking_reference??"missing"} value={shipment.tracking_reference} ur={ur}/>
          <div className="ship-service"><span className="ship-label">{t("Delivery Service","ترسیل کی سروس")}</span><strong>{shipment.carrier||t("Not available yet","ابھی دستیاب نہیں")}</strong></div>
          <p className="ship-note">{t("Updates reflect the shipment records saved with SafeReturn.","یہ معلومات SafeReturn میں محفوظ ترسیل کے ریکارڈ پر مبنی ہیں۔")}</p></section>
        <section className="ship-panel"><h2>{t("Shipment Progress","ترسیل کی پیش رفت")}</h2>
          {milestones.length?<ol className="ship-timeline">{milestones.map((e,i)=><li key={e.name+e.at} className={i===milestones.length-1?"latest":""}><span><CustomerIcon name="check"/></span><div><strong>{e.name}</strong><time dateTime={e.at}>{shipmentDate(e.at,ur)}</time></div></li>)}</ol>:
            <p>{t("Milestone dates are not available yet. The current recorded status is shown above.","اہم مراحل کی تاریخیں ابھی دستیاب نہیں۔ موجودہ درج شدہ حالت اوپر دکھائی گئی ہے۔")}</p>}
          {["returned","exception"].includes(shipment.status)&&<p className="ship-note">{t("The current shipment status needs attention. Earlier recorded milestones are shown above.","ترسیل کی موجودہ حالت پر توجہ درکار ہے۔ پہلے سے درج مراحل اوپر دکھائے گئے ہیں۔")}</p>}
        </section>
        {address&&<section className="ship-panel"><h2>{t("Delivery Address","ترسیل کا پتہ")}</h2><address><strong>{address.recipient_name}</strong><p>{address.address}</p><p>{address.city} {address.province} <bdi>{address.postal_code}</bdi></p></address></section>}
      </div><aside className="ship-panel ship-related"><h2>{t("Related Order","متعلقہ آرڈر")}</h2>
        {summary?<><h3><bdi>{summary.order_number}</bdi></h3><ul className="ship-order-products">{summary.order_items.map((p,i)=><li key={i}><span className="ship-art"><CustomerIcon name="tag"/></span><div><strong><bdi>{p.product_name_snapshot}</bdi></strong><small>{t("Order quantity","آرڈر کی تعداد")} · {p.quantity}</small></div></li>)}</ul>
          <dl className="ship-order-total"><dt>{t("Order Total","آرڈر کی کل رقم")}</dt><dd><bdi>{summary.currency_code} {summary.total_pkr}</bdi></dd></dl>
          <p className="ship-note">{t("Order contents and total may cover more than one shipment.","آرڈر کی مصنوعات اور کل رقم ایک سے زیادہ ترسیلات پر مشتمل ہو سکتی ہیں۔")}</p></>:
          <p>{t("Open your order to view its purchase information.","خریداری کی معلومات کے لیے اپنا آرڈر کھولیں۔")}</p>}
        {orderId&&<Link className="ship-primary" prefetch={false} href={`/orders/${orderId}`}>{t("View Order Details","آرڈر کی تفصیلات دیکھیں")}<CustomerIcon name="arrow"/></Link>}
      </aside></div>}
  </section>;
}
