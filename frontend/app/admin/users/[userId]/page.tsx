import { AdminPage, AdminNotice } from '../../../../components/admin-page';
import { AdminUsers } from '../../../../components/admin-users';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'User Details | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page({ params }: {
    params: Promise<{
        userId: string;
    }>;
}) { const { userId } = await params; return <AdminPage path="/admin/users" capability="users.manage">{(s, ur) => s.roles.includes('security_admin') ? <AdminUsers ur={ur} userId={userId}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
