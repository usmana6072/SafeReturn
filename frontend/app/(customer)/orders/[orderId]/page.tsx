import { notFound } from "next/navigation";
import { ownerApi, ownerSession } from "../../../../lib/qr-server";
import { getLanguage } from "../../../../lib/i18n";
import { customerOperationAvailable } from "../../../../lib/customer-capabilities";
import { uuid } from "../../../../lib/qr-contract";
import { ApiError } from "../../../../lib/api/transport";
import { orderPage, type CustomerOrder, type OrderDetail, type CustomerShipment } from "../../../../lib/customer-orders";
import { CustomerOrderDetails } from "../../../../components/customer-order-details";

export const metadata = { title: "Order Details | SafeReturn" };
export default async function OrderPage({params,searchParams=Promise.resolve({})}:{params:Promise<{orderId:string}>;searchParams?:Promise<{cursor?:string|string[]}>}) {
  const {orderId}=await params;
  if(!uuid(orderId))notFound();
  const [session,language]=await Promise.all([ownerSession(),getLanguage()]);
  const api=ownerApi(session.token),restricted=!customerOperationAvailable("GET",`/me/orders/${orderId}`);
  const {cursor}=await searchParams;
  const summaryQuery=new URLSearchParams({limit:"100"});
  if(typeof cursor==="string"&&cursor.length<=2048)summaryQuery.set("cursor",cursor);
  const [orderResult,shippingResult]=await Promise.allSettled([
    restricted?api<unknown>("/me/orders?"+summaryQuery).then(orderPage).then(page=>page.items.find(o=>o.id===orderId)??null):
      api<OrderDetail>(`/me/orders/${orderId}`),
    api<{items:CustomerShipment[]}>(`/me/orders/${orderId}/shipments`),
  ]);
  for(const result of [orderResult,shippingResult])if(result.status==="rejected"&&result.reason instanceof ApiError&&result.reason.status===404)notFound();
  const order=orderResult.status==="fulfilled"?orderResult.value:null;
  const shipments=shippingResult.status==="fulfilled"&&Array.isArray(shippingResult.value.items)?shippingResult.value.items:null;
  const detail=!restricted?order as OrderDetail|null:null;
  return <CustomerOrderDetails id={orderId} summary={order as CustomerOrder|null} detail={detail} shipments={shipments} restricted={restricted} ur={language==="ur"}/>;
}
