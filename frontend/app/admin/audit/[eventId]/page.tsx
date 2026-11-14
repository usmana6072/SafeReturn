import {AdminPage} from '../../../../components/admin-page';
import {AdminAuditLogs} from '../../../../components/admin-audit-logs';
import {auditEventsAdmitted} from '../../../../lib/phase13-gate';
export const dynamic='force-dynamic';
export const metadata={title:'audit | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page({params}:{params:Promise<{eventId:string}>}){const {eventId}=await params;return <AdminPage path="/admin/audit" capability="audit.search">{(security,ur)=><AdminAuditLogs ur={ur} admitted={auditEventsAdmitted()} eventId={eventId}/>}</AdminPage>;}
