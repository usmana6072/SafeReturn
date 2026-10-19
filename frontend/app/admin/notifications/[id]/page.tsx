import { notFound } from "next/navigation";
import { AdminPage } from "../../../../components/admin-page";
import { NotificationAdmin } from "../../../../components/notification-admin";
import { getLanguage } from "../../../../lib/i18n";
export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params;if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(id))notFound();return <AdminPage path="/admin/notifications" capability="notifications.manage"><NotificationAdmin ur={await getLanguage()==="ur"} id={id}/></AdminPage>;}
