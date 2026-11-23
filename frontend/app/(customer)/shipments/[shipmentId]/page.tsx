import { notFound } from "next/navigation";
import { ownerApi, ownerSession } from "../../../../lib/qr-server";
import { getLanguage } from "../../../../lib/i18n";
import { uuid } from "../../../../lib/qr-contract";
import { ApiError } from "../../../../lib/api/transport";
import { customerOperationAvailable } from "../../../../lib/customer-capabilities";
import { shipmentPage, shipmentRecord, type DeliveryAddress, type ShipmentSummary } from "../../../../lib/customer-shipments";
import type { Shipment } from "../../../../lib/fulfillment-workflow";
import { ShipmentDetails } from "../../../../components/customer-shipments";

export const metadata={title:"Shipment Details | SafeReturn"};
export default async function Page({params,searchParams}:{params:Promise<{shipmentId:string}>;searchParams:Promise<{orderId?:string|string[];cursor?:string|string[]}>}){
  const {shipmentId}=await params;
  if(!uuid(shipmentId))notFound();
  const [session,language,query]=await Promise.all([ownerSession(),getLanguage(),searchParams]);
  if(query.orderId!==undefined&&(typeof query.orderId!=="string"||!uuid(query.orderId)))notFound();
  if(query.cursor!==undefined&&(typeof query.cursor!=="string"||query.cursor.length>2048))notFound();
  const cursor=typeof query.cursor==="string"?query.cursor:undefined;
  const api=ownerApi(session.token),pageQuery=new URLSearchParams({limit:"100"});
  if(cursor)pageQuery.set("cursor",cursor);
  let summary:ShipmentSummary|null=null,shipment:Shipment|null=null,address:DeliveryAddress|null=null;
  let orderId=typeof query.orderId==="string"?query.orderId:null;
  let summaryFailed=false;
  const summaryPromise=api<unknown>("/me/shipments?"+pageQuery).then(shipmentPage).then(page=>page.items.find(s=>s.id===shipmentId)??null).catch(()=>{summaryFailed=true;return null;});
  async function readShipment(ownerOrderId:string){
    let candidates:Shipment[];
    try{
      const value=await api<{items:unknown[]}>(`/me/orders/${ownerOrderId}/shipments`);
      if(!Array.isArray(value.items))throw Error();
      candidates=value.items.map(shipmentRecord);
    }catch(error){
      if(error instanceof ApiError&&[403,404].includes(error.status??0))notFound();
      return null;
    }
    const result=candidates.find(s=>s.id===shipmentId);
    if(!result)notFound();
    return result;
  }
  if(orderId){
    [summary,shipment]=await Promise.all([summaryPromise,readShipment(orderId)]);
    if(summary?.order_id!==orderId)summary=null;
  }else{
    summary=await summaryPromise;
    if(summary){orderId=summary.order_id;shipment=await readShipment(orderId);}
  }
  if(!orderId){
    if(!summaryFailed)notFound();
    return <ShipmentDetails shipment={null} summary={null} orderId={null} address={null} backHref="/shipments" ur={language==="ur"}/>;
  }
  if(shipment&&customerOperationAvailable("GET",`/me/orders/${orderId}`)){
    try{
      const value=await api<{shipping_snapshot:DeliveryAddress}>(`/me/orders/${orderId}`);
      const s=value.shipping_snapshot;
      if(s&&typeof s.recipient_name==="string"&&typeof s.address==="string"&&typeof s.city==="string"&&
        (s.province===null||typeof s.province==="string")&&(s.postal_code===null||typeof s.postal_code==="string")){
        address={recipient_name:s.recipient_name,address:s.address,city:s.city,province:s.province,postal_code:s.postal_code};
      }
    }catch{ /* The recorded shipment remains useful when the historical address is unavailable. */ }
  }
  return <ShipmentDetails shipment={shipment} summary={summary} orderId={orderId} address={address} backHref={cursor?"/shipments?cursor="+encodeURIComponent(cursor):"/shipments"} ur={language==="ur"}/>;
}
