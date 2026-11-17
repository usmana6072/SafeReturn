import { notFound } from 'next/navigation';
import { AdminNotice, AdminPage } from '../../../../../components/admin-page';
import { OrderShipmentForm } from '../../../../../components/admin-order-workflow';
import { uuid } from '../../../../../lib/qr-contract';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Order Shipment | SafeReturn', robots: { index: false, follow: false } };

export default async function Page({ params }: { params: Promise<{ orderId: string }> }) {
  const { orderId } = await params;
  if (!uuid(orderId)) notFound();
  return <AdminPage path="/admin/shipments" capability="fulfillment.manage">{(staff, ur) =>
    staff.roles.includes('operations') ? <OrderShipmentForm key={orderId} orderId={orderId} ur={ur} /> : <AdminNotice ur={ur} denied />}
  </AdminPage>;
}
