import Link from "next/link";
import type { CustomerOrder, CustomerShipment, OrderDetail } from "../lib/customer-orders";
import { orderDate, mainOrderState, customerOrderLabel } from "../lib/customer-orders";
import { OrderBadge, OrderRetry } from "./customer-orders";
import { CustomerIcon } from "./customer-icon";
import { CancellationRequest } from "./cancellation-request";

export function CustomerOrderDetails({id,summary,detail,shipments,restricted,ur}:{id:string;summary:CustomerOrder|null;detail:OrderDetail|null;shipments:CustomerShipment[]|null;restricted:boolean;ur:boolean}) {
  const t=(en:string,u:string)=>ur?u:en,order=detail??summary,state=order?mainOrderState(order):null;
  const events:{key:string;label:string;at?:string}[]=[];
  if(order) {
    const at=order.placed_at||order.created_at;
    if(at)events.push({key:"placed",label:order.placed_at?t("Order Placed","آرڈر درج ہو گیا"):t("Order Created","آرڈر بنایا گیا"),at});
    if(order.payment_status==="verified")events.push({key:"payment",label:t("Payment Confirmed","ادائیگی کی تصدیق ہو گئی")});
  }
  for(const s of shipments??[])for(const [name,label,at] of [
    ["packed",t("Packed","پیک ہو گیا"),s.packed_at],["dispatched",t("Shipped","روانہ ہو گیا"),s.dispatched_at],["delivered",t("Delivered","پہنچ گیا"),s.delivered_at],
  ] as const)if(at)events.push({key:s.id+name,label,at});
  const restrictedMessage=t("Product, print and cancellation details are currently unavailable.","مصنوعات، پرنٹ اور منسوخی کی تفصیلات فی الحال دستیاب نہیں۔");
  return <section className="orders-screen orders-details"><Link className="orders-back" href="/orders"><CustomerIcon name="arrow"/>{t("Back to My Orders","میرے آرڈرز پر واپس")}</Link>
    <header className="orders-intro"><h1>{t("Order Details","آرڈر کی تفصیلات")}</h1>
      {order&&<p><bdi>{order.order_number}</bdi> · <time dateTime={order.created_at}>{orderDate(order.created_at,ur)}</time></p>}</header>
    <div className="orders-detail-grid"><div className="orders-detail-main">
      <section className="orders-panel orders-current"><h2>{t("Order Status","آرڈر کی حالت")}</h2>
        {order&&state?<><div className="orders-status-pair"><OrderBadge {...state} ur={ur}/><OrderBadge kind="order" value={order.order_status} ur={ur}/></div>
          <div className="orders-payment"><span>{t("Payment","ادائیگی")}</span><OrderBadge kind="payment" value={order.payment_status} ur={ur}/></div>
          {order.fulfillment_status==="unallocated"&&<p>{order.payment_status==="verified"?t("Payment is confirmed. QR preparation is awaiting assignment.","ادائیگی تصدیق شدہ ہے۔ QR کی تیاری کے لیے تخصیص کا انتظار ہے۔"):t("QR preparation is waiting for the required payment checks.","QR کی تیاری کے لیے ادائیگی کی ضروری جانچ باقی ہے۔")}</p>}
        </>:<><p role="alert">{t("Order status couldn’t be loaded.","آرڈر کی حالت لوڈ نہیں ہو سکی۔")}</p><OrderRetry ur={ur}/></>}
        {restricted&&<p className="orders-note">{restrictedMessage}</p>}
        {!restricted&&!detail&&<p className="orders-note">{t("Some order details couldn’t be loaded. Please try again.","آرڈر کی کچھ تفصیلات لوڈ نہیں ہو سکیں۔ دوبارہ کوشش کریں۔")}</p>}
      </section>
      <section className="orders-panel"><h2>{t("Order Progress","آرڈر کی پیش رفت")}</h2>
        {order?.order_status==="cancelled"&&<p className="orders-note">{t("This order is cancelled. Recorded events are shown below.","یہ آرڈر منسوخ ہے۔ درج شدہ واقعات نیچے موجود ہیں۔")}</p>}
        {events.length?<ol className="orders-timeline">{events.map(e=><li key={e.key}><span><CustomerIcon name="check"/></span><div><strong>{e.label}</strong>{e.at&&<time dateTime={e.at}>{orderDate(e.at,ur)}</time>}</div></li>)}</ol>:
          <p>{t("Order updates will appear here when available.","آرڈر کی پیش رفت دستیاب ہونے پر یہاں دکھائی دے گی۔")}</p>}
      </section>
      {detail&&<><section className="orders-panel"><h2>{t("Purchased Products","خریدی گئی مصنوعات")}</h2><ul className="orders-product-list">
        {detail.logical_items?.map(item=><li key={item.id}><span className="orders-art" aria-hidden="true"><CustomerIcon name={item.qr_type_snapshot==="ice"?"medical":"tag"}/></span><div>
          <h3><bdi>{item.product_name_snapshot}</bdi></h3><p>{item.quantity} {t("copies","کاپیاں")} · {item.qr_type_snapshot==="ice"?t("Emergency QR","ہنگامی QR"):t("Lost QR","گمشدہ QR")}</p>
          {item.sizes.map(s=><p className="orders-meta" key={s.id}>{s.variant_name_snapshot} · <bdi>{s.size_mm_snapshot} mm</bdi> · {s.copies} {t("copies","کاپیاں")}</p>)}
          <p className="orders-meta"><bdi>{detail.currency_code} {item.unit_price_snapshot}</bdi> {t("per copy","فی کاپی")}</p><strong><bdi>{detail.currency_code} {item.line_total}</bdi></strong>
        </div></li>)}
        {detail.items.map(item=><li key={item.id}><span className="orders-art" aria-hidden="true"><CustomerIcon name="tag"/></span><div>
          <h3><bdi>{item.product_name_snapshot}</bdi></h3><p>{item.quantity} {t("copies","کاپیاں")} · {item.variant_name_snapshot}</p><p className="orders-meta"><bdi>{item.size_mm_snapshot} mm</bdi>{item.material_snapshot&&<> · {item.material_snapshot}</>}</p>
          {detail.qr_uses.filter(q=>q.order_item_id===item.id).map(q=><p className="orders-meta" key={q.id}>{q.tag_type_snapshot==="ice"?t("Emergency","ہنگامی"):t("Lost","گمشدہ")} · {q.copies} {t("copies","کاپیاں")}</p>)}
          <p className="orders-meta"><bdi>{detail.currency_code} {item.unit_price_snapshot}</bdi> {t("per copy","فی کاپی")}</p><strong><bdi>{detail.currency_code} {item.line_total}</bdi></strong>
        </div></li>)}
      </ul></section>
      <section className="orders-panel"><h2>{t("QR Tag Preparation","QR ٹیگ کی تیاری")}</h2><div className="orders-status-pair"><OrderBadge kind="print" value={detail.print_status} ur={ur}/></div>
        {detail.allocation&&<><p>{detail.allocation.state==="allocated"?t("QR tags have been assigned to this order.","اس آرڈر کے لیے QR ٹیگز مختص ہو چکے ہیں۔"):
          detail.allocation.state==="reconciliation_pending"?t("Payment is confirmed. Your order needs an additional review before QR tags can be assigned.","ادائیگی تصدیق شدہ ہے۔ QR ٹیگز مختص کرنے سے پہلے آرڈر کا مزید جائزہ ضروری ہے۔"):t("QR tags will be assigned after payment verification.","ادائیگی کی تصدیق کے بعد QR ٹیگز مختص ہوں گے۔")}</p>
          <p>{t("Assigned QR codes","مختص QR کوڈز")} <bdi>{detail.allocation.allocated_count} / {detail.allocation.requested_count}</bdi></p></>}
        <Link className="orders-secondary" href="/my-qr">{t("View QR Codes","QR کوڈز دیکھیں")}</Link>
      </section></>}
      <section className="orders-panel"><h2>{t("Payment Information","ادائیگی کی معلومات")}</h2>
        {order&&<><OrderBadge kind="payment" value={order.payment_status} ur={ur}/><p><bdi>{order.currency_code} {order.total_pkr}</bdi></p>
          {["proof_submitted","under_review"].includes(order.payment_status)&&<p>{t("Your payment is awaiting review. Its status will update once verification is complete.","آپ کی ادائیگی جائزے کی منتظر ہے۔ تصدیق مکمل ہونے پر حالت تبدیل ہوگی۔")}</p>}</>}
        <Link className="orders-primary" prefetch={false} href={`/checkout?orderId=${id}`}>{t("View Payment Details","ادائیگی کی تفصیلات دیکھیں")}<CustomerIcon name="arrow"/></Link>
      </section>
      <section className="orders-panel"><h2>{t("Shipping & Delivery","ترسیل")}</h2>
        {shipments===null?<div role="alert"><p>{t("Shipping information couldn’t be loaded.","ترسیل کی معلومات لوڈ نہیں ہو سکیں۔")}</p><OrderRetry ur={ur}/></div>:
          shipments.length?<ul className="orders-shipment-list">{shipments.map(s=><li key={s.id}><OrderBadge kind="fulfillment" value={s.status} ur={ur}/>
            {s.carrier&&<p>{t("Courier","کوریئر")} · <bdi>{s.carrier}</bdi></p>}{s.tracking_reference&&<p>{t("Tracking Number","ٹریکنگ نمبر")} · <bdi>{s.tracking_reference}</bdi></p>}
            {s.dispatched_at&&<p>{t("Dispatched","روانہ ہوا")} · <time dateTime={s.dispatched_at}>{orderDate(s.dispatched_at,ur)}</time></p>}
            {s.delivered_at&&<p>{t("Delivered","پہنچ گیا")} · <time dateTime={s.delivered_at}>{orderDate(s.delivered_at,ur)}</time></p>}
            <Link className="orders-secondary" href="/shipments">{t("View Shipments","ترسیلات دیکھیں")}<CustomerIcon name="arrow"/></Link></li>)}</ul>:
          <p>{t("Shipment details will appear here once a shipment is recorded.","ترسیل درج ہونے پر تفصیلات یہاں دکھائی دیں گی۔")}</p>}
        {detail?.shipping_snapshot&&<address className="orders-address"><strong>{t("Delivery Address","ترسیل کا پتہ")}</strong><p>{detail.shipping_snapshot.recipient_name}</p>
          <p><bdi>{detail.shipping_snapshot.phone}</bdi></p><p>{detail.shipping_snapshot.address}</p><p>{detail.shipping_snapshot.city} {detail.shipping_snapshot.province} <bdi>{detail.shipping_snapshot.postal_code}</bdi></p></address>}
      </section>
      {detail&&<CancellationRequest orderId={id} revision={detail.order_revision} summary={detail.cancellation_request} ur={ur}/>}
    </div>
    <aside className="orders-panel orders-price-summary"><h2>{t("Price Summary","قیمت کا خلاصہ")}</h2>{order?<dl>
      {detail&&([[t("Subtotal","مصنوعات کی قیمت"),detail.subtotal_pkr],[t("Discount","رعایت"),detail.discount_pkr],[t("Delivery","ترسیل"),detail.shipping_pkr],[t("Tax","ٹیکس"),detail.tax_pkr]]).map(([label,value])=>value!==undefined&&<div key={label}><dt>{label}</dt><dd><bdi>{order.currency_code} {value}</bdi></dd></div>)}
      <div className="orders-total"><dt>{t("Order Total","آرڈر کی کل رقم")}</dt><dd><bdi>{order.currency_code} {order.total_pkr}</bdi></dd></div></dl>:<p>{t("Price details are currently unavailable.","قیمت کی تفصیلات فی الحال دستیاب نہیں۔")}</p>}
      {!detail&&<p className="orders-note">{t("The detailed price breakdown is currently unavailable.","قیمت کی مکمل تفصیل فی الحال دستیاب نہیں۔")}</p>}
      <Link className="orders-shopping" href="/orders">{t("View All Orders","تمام آرڈرز دیکھیں")}</Link>
    </aside></div>
  </section>;
}
