import { AdminPage } from "../../../components/admin-page";
import { getLanguage } from "../../../lib/i18n";
import { FulfillmentAdmin } from "../../../components/fulfillment-admin";
export default async function Page() { return <AdminPage path="/admin/ready-to-ship" capability="fulfillment.manage"><FulfillmentAdmin ur={await getLanguage()==="ur"}/></AdminPage>; }
