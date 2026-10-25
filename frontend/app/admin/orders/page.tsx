import { AdminPage, AdminNotice } from '../../../components/admin-page';
import { AdminOrders } from '../../../components/admin-orders';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Orders & Sales | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page() { return <AdminPage path="/admin/orders" capability="orders.read">{(security, ur) => security.roles.some(r => ['operations', 'finance'].includes(r)) ? <AdminOrders ur={ur}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
