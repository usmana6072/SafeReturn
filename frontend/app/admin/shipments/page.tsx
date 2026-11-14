import { AdminPage, AdminNotice } from '../../../components/admin-page';
import { AdminShipments } from '../../../components/admin-shipments';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Shipment Item Metadata | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page() { return <AdminPage path="/admin/shipments" capability="fulfillment.manage">{(s, ur) => s.roles.includes('operations') ? <AdminShipments ur={ur}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
