import { AdminPage, AdminNotice } from '../../../../components/admin-page';
import { AdminOrders } from '../../../../components/admin-orders';
import { uuid } from '../../../../lib/qr-contract';
import { notFound } from 'next/navigation';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Order Details | SafeReturn', robots: { index: false, follow: false } };
export default async function Page({ params }: {
    params: Promise<{
        orderId: string;
    }>;
}) { const { orderId } = await params; if (!uuid(orderId)) notFound(); return <AdminPage path="/admin/orders" capability="orders.read">{(security, ur) => security.roles.some(r => ['operations', 'finance'].includes(r)) ? <AdminOrders orderId={orderId} ur={ur}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
