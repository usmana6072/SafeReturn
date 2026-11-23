import type { BuyerShipment, Shipment } from "./fulfillment-workflow";
import { uuid } from "./qr-contract";
export type ShipmentSummary = BuyerShipment & {created_at?:string};
export type DeliveryAddress = {recipient_name:string;address:string;city:string;province:string|null;postal_code:string|null};
export const shipmentLabels:Record<string,[string,string]> = {
  preparing:["Preparing for Dispatch","روانگی کی تیاری"],packed:["Packed for Dispatch","روانگی کے لیے پیک"],
  dispatched:["Dispatched","روانہ ہو گیا"],delivered:["Delivered","پہنچ گیا"],
  exception:["Delivery Needs Attention","ترسیل پر توجہ درکار"],returned:["Returned","واپس آ گیا"],
};
export function shipmentLabel(value:string,ur:boolean){return shipmentLabels[value]?.[ur?1:0]??(ur?"حالت دستیاب نہیں":"Status Unavailable");}
export function shipmentTone(value:string){
  return value==="delivered"?"success":value==="dispatched"?"transit":value==="exception"||value==="returned"?"attention":["preparing","packed"].includes(value)?"waiting":"neutral";
}
export function shipmentDate(date:string,ur:boolean){
  return new Intl.DateTimeFormat(ur?"ur-PK":"en-GB",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Karachi"}).format(new Date(date));
}
const date=(value:unknown):value is string=>typeof value==="string"&&Number.isFinite(Date.parse(value));
export function shipmentRecord(value:unknown):Shipment {
  if(!value||typeof value!=="object")throw Error("Unavailable");
  const s=value as Shipment;
  if(typeof s.id!=="string"||!uuid(s.id)||typeof s.status!=="string"||
    ![s.carrier,s.tracking_reference].every(v=>v===null||typeof v==="string")||
    ![s.packed_at,s.dispatched_at,s.delivered_at].every(v=>v===null||date(v)))throw Error("Unavailable");
  return {id:s.id,status:s.status,carrier:s.carrier,tracking_reference:s.tracking_reference,
    packed_at:s.packed_at,dispatched_at:s.dispatched_at,delivered_at:s.delivered_at};
}
export function shipmentPage(value:unknown):{items:ShipmentSummary[];next_cursor:string|null}{
  if(!value||typeof value!=="object")throw Error("Unavailable");
  const page=value as {items:ShipmentSummary[];next_cursor:string|null};
  if(!Array.isArray(page.items)||page.items.length>100||!(page.next_cursor===null||typeof page.next_cursor==="string"))throw Error("Unavailable");
  return {next_cursor:page.next_cursor,items:page.items.map(raw=>{
    const s=shipmentRecord(raw);
    if(!uuid(raw.order_id)||typeof raw.order_number!=="string"||typeof raw.currency_code!=="string"||typeof raw.total_pkr!=="string"||
      !/^\d+\.\d{2}$/.test(raw.total_pkr)||!date(raw.created_at)||!Array.isArray(raw.order_items)||
      raw.order_items.some(p=>!p||typeof p.product_name_snapshot!=="string"||!Number.isInteger(p.quantity)||p.quantity<1))throw Error("Unavailable");
    return {...s,order_id:raw.order_id,order_number:raw.order_number,currency_code:raw.currency_code,total_pkr:raw.total_pkr,created_at:raw.created_at,
      order_items:raw.order_items.map(p=>({product_name_snapshot:p.product_name_snapshot,quantity:p.quantity}))};
  })};
}
