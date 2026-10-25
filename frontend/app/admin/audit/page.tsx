import {AdminPage} from '../../../components/admin-page';
import {AdminAuditLogs} from '../../../components/admin-audit-logs';
import {auditEventsAdmitted} from '../../../lib/phase13-gate';
export const dynamic='force-dynamic';
export const metadata={title:'audit | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page(){return <AdminPage path="/admin/audit" capability="audit.search">{(security,ur)=><AdminAuditLogs ur={ur} admitted={auditEventsAdmitted()} />}</AdminPage>;}
