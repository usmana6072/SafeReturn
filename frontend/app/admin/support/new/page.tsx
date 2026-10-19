import { AdminPage } from "../../../../components/admin-page";
import { SupportAdmin } from "../../../../components/support-admin";
import { getLanguage } from "../../../../lib/i18n";
export default async function Page(){return <AdminPage path="/admin/support" capability="support.manage"><SupportAdmin ur={await getLanguage()==="ur"} mode="new"/></AdminPage>;}
