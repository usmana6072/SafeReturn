import { AdminPage } from "../../../components/admin-page";
import { getLanguage } from "../../../lib/i18n";
import { ShipmentDiscovery } from "../../../components/shipment-discovery";
export default async function Page() { return <AdminPage path="/admin/shipments" capability="fulfillment.manage"><ShipmentDiscovery ur={await getLanguage()==="ur"}/></AdminPage>; }
