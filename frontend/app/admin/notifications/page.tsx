import { AdminPage, AdminNotice } from '../../../components/admin-page';
import { AdminNotifications } from '../../../components/admin-notifications';
import { canReadNotifications } from '../../../lib/admin-notification-contract';
import { notificationReadAdmitted, notificationRetryAdmitted } from '../../../lib/notification-gate';
export const dynamic = 'force-dynamic';
export const metadata = {title:'Notifications | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page(){
  return <AdminPage path="/admin/notifications" capability="notifications.manage">{(security,ur)=>canReadNotifications(security.roles)?<AdminNotifications ur={ur} admitted={notificationReadAdmitted()} retryAdmitted={notificationRetryAdmitted()}/>:<AdminNotice ur={ur} denied/>}</AdminPage>;
}
