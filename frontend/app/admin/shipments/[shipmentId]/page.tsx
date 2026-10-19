import { notFound } from "next/navigation";
import { AdminPage } from "../../../../components/admin-page";
import { ShipmentDiscovery } from "../../../../components/shipment-discovery";
import { getLanguage } from "../../../../lib/i18n";
export default async function Page({params}:{params:Promise<{shipmentId:string}>}) {
 const {shipmentId}=await params;
 if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(shipmentId))notFound();
 return <AdminPage path="/admin/shipments" capability="fulfillment.manage"><ShipmentDiscovery ur={await getLanguage()==="ur"} shipmentId={shipmentId}/></AdminPage>;
}
