import type { Allocation } from "./allocation";
import type { CancellationSummary } from "../components/cancellation-request";

export type CustomerOrder = {
  id:string; order_number:string; order_status:string; payment_status:string; fulfillment_status:string;
  currency_code:string; total_pkr:string; created_at:string; placed_at?:string|null;
};
export type CustomerShipment = {
  id:string; carrier:string|null; tracking_reference:string|null; status:string;
  packed_at:string|null; dispatched_at:string|null; delivered_at:string|null;
};
export type OrderDetail = CustomerOrder & {
  allocation?:Allocation; commerce_model?:"single_qr"|"legacy_pair"; identity_count?:number; pair_count:number;
  print_status:string; order_revision?:number; cancellation_request?:CancellationSummary|null;
  subtotal_pkr?:string; shipping_pkr?:string; tax_pkr?:string; discount_pkr?:string;
  logical_items?:{id:string;product_name_snapshot:string;qr_type_snapshot:string;quantity:number;unit_price_snapshot:string;line_total:string;
    sizes:{id:string;variant_name_snapshot:string;size_mm_snapshot:string;copies:number}[]}[];
  items:{id:string;product_name_snapshot:string;variant_name_snapshot:string;sku_snapshot:string;size_mm_snapshot:string;material_snapshot:string|null;quantity:number;unit_price_snapshot:string;line_total:string}[];
  qr_uses:{id:string;order_item_id:string;tag_type_snapshot:string;copies:number}[];
  shipping_snapshot:{recipient_name:string;phone:string;address:string;city:string;province:string|null;postal_code:string|null};
};
const payment:Record<string,[string,string]> = {
  awaiting_transfer:["Payment Pending","ادائیگی کا انتظار"],proof_submitted:["Payment Proof Submitted","ادائیگی کا ثبوت جمع ہو گیا"],
  under_review:["Payment Under Review","ادائیگی زیرِ جائزہ"],verified:["Paid","ادائیگی ہو گئی"],
  rejected:["Payment Rejected","ادائیگی مسترد"],refunded:["Refunded","رقم واپس"],
};
const fulfillment:Record<string,[string,string]> = {
  unallocated:["Awaiting QR Preparation","QR کی تیاری کا انتظار"],allocated:["QR Tags Assigned","QR ٹیگز مختص"],
  preparing:["Preparing Your Order","آپ کا آرڈر تیار ہو رہا ہے"],packed:["Packed","پیک ہو گیا"],
  dispatched:["Shipped","روانہ ہو گیا"],delivered:["Delivered","پہنچ گیا"],exception:["Delivery Needs Attention","ترسیل پر توجہ درکار"],
  returned:["Returned","واپس آ گیا"],
};
const order:Record<string,[string,string]> = {
  placed:["Order Placed","آرڈر درج ہو گیا"],processing:["Processing","کارروائی جاری"],fulfilled:["Fulfilled","مکمل"],cancelled:["Cancelled","منسوخ"],
};
const print:Record<string,[string,string]> = {
  not_requested:["Printing Not Started","پرنٹنگ شروع نہیں ہوئی"],queued:["Waiting for Printing","پرنٹنگ کا انتظار"],rendering:["Preparing Print File","پرنٹ فائل تیار ہو رہی ہے"],
  ready:["Print File Ready","پرنٹ فائل تیار"],downloaded:["Print File Downloaded","پرنٹ فائل حاصل کر لی گئی"],qa_passed:["Print Checked","پرنٹ کی جانچ مکمل"],
  failed:["Printing Needs Attention","پرنٹنگ پر توجہ درکار"],superseded:["Print File Replaced","پرنٹ فائل تبدیل ہو گئی"],draft:["Print Draft","پرنٹ کا مسودہ"],
};
export function customerOrderLabel(value:string,kind:"payment"|"fulfillment"|"order"|"print",ur:boolean) {
  return ({payment,fulfillment,order,print}[kind][value])?.[ur?1:0] ?? (ur?"حالت دستیاب نہیں":"Status Unavailable");
}
export function mainOrderState(value:CustomerOrder) {
  if(value.order_status==="cancelled")return {kind:"order" as const,value:"cancelled"};
  return {kind:"fulfillment" as const,value:value.fulfillment_status};
}
export function badgeTone(value:string) {
  if(["verified","delivered","fulfilled","qa_passed"].includes(value))return "success";
  if(["rejected","cancelled","failed","exception","returned"].includes(value))return "attention";
  if(["awaiting_transfer","under_review","proof_submitted","unallocated","not_requested","queued"].includes(value))return "waiting";
  return "neutral";
}
export function orderDate(stamp:string,ur:boolean) {
  return new Intl.DateTimeFormat(ur?"ur-PK":"en-GB",{dateStyle:"medium",timeZone:"Asia/Karachi"}).format(new Date(stamp));
}
export function orderPage(value:unknown):{items:CustomerOrder[];next_cursor:string|null} {
  if(!value || typeof value!=="object")throw Error("Unavailable");
  const page=value as {items:CustomerOrder[];next_cursor:string|null};
  if(!Array.isArray(page.items)||page.items.length>100||!(page.next_cursor===null||typeof page.next_cursor==="string")||
    page.items.some(item=>!item||["id","order_number","order_status","payment_status","fulfillment_status","currency_code","total_pkr","created_at"].some(key=>typeof item[key as keyof CustomerOrder]!=="string")||
      !/^[a-f0-9-]{36}$/i.test(item.id)||!/^\d+\.\d{2}$/.test(item.total_pkr)||!Number.isFinite(Date.parse(item.created_at))))throw Error("Unavailable");
  return {next_cursor:page.next_cursor,items:page.items.map(item=>({
    id:item.id,order_number:item.order_number,order_status:item.order_status,payment_status:item.payment_status,
    fulfillment_status:item.fulfillment_status,currency_code:item.currency_code,total_pkr:item.total_pkr,created_at:item.created_at,
    ...(typeof item.placed_at==="string"&&Number.isFinite(Date.parse(item.placed_at))?{placed_at:item.placed_at}:{}),
  }))};
}
