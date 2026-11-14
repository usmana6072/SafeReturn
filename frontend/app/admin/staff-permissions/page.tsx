import {AdminPage} from '../../../components/admin-page';
import {AdminStaffPermissions} from '../../../components/admin-staff-permissions';
import {currentStaffSecurityAdmitted} from '../../../lib/phase13-gate';
export const dynamic='force-dynamic';
export const metadata={title:'staff-permissions | SafeReturn',robots:{index:false,follow:false},referrer:'no-referrer' as const};
export default async function Page(){return <AdminPage path="/admin/staff-permissions" >{(security,ur)=><AdminStaffPermissions ur={ur} admitted={currentStaffSecurityAdmitted()} />}</AdminPage>;}
