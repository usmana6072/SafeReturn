import { ownerSession } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { PaymentForm } from "../../../components/payments";
import { notFound } from "next/navigation";
export default async function Payment({params}:{params:Promise<{orderId:string}>}){await ownerSession();const {orderId}=await params;if(!/^[a-f0-9-]{36}$/.test(orderId))notFound();return <PaymentForm orderId={orderId} language={await getLanguage()}/>;}
