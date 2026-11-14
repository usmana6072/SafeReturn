import { AdminPage, AdminNotice } from '../../../components/admin-page';
import { AdminUsers } from '../../../components/admin-users';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Users & Accounts | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page() { return <AdminPage path="/admin/users" capability="users.manage">{(s, ur) => s.roles.includes('security_admin') ? <AdminUsers ur={ur}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
