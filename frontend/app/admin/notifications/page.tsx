import { AdminPage } from "../../../components/admin-page";
import { NotificationAdmin } from "../../../components/notification-admin";
import { getLanguage } from "../../../lib/i18n";
export default async function Page(){return <AdminPage path="/admin/notifications" capability="notifications.manage"><NotificationAdmin ur={await getLanguage()==="ur"}/></AdminPage>;}
