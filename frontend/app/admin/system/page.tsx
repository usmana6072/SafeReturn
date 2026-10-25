import {AdminPage} from '../../../components/admin-page';
import {AdminSystemMonitoring} from '../../../components/admin-system-monitoring';
import {backendLivenessAdmitted} from '../../../lib/phase13-gate';
export const dynamic='force-dynamic';
export const metadata={title:'system | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page(){return <AdminPage path="/admin/system" capability="notifications.manage">{(security,ur)=><AdminSystemMonitoring ur={ur} admitted={backendLivenessAdmitted()} />}</AdminPage>;}
