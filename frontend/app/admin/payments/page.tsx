import { AdminPage, AdminNotice } from '../../../components/admin-page';
import { AdminPayments } from '../../../components/admin-payments';
import { notFound } from 'next/navigation';
import { uuid } from '../../../lib/qr-contract';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Payments & Reconciliation | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page({ searchParams }: { searchParams: Promise<{ orderId?: string | string[] }> }) {
    const { orderId } = await searchParams;
    if (orderId !== undefined && (typeof orderId !== 'string' || !uuid(orderId))) notFound();
    return <AdminPage path="/admin/payments" capability="payments.review">{(s, ur) => s.roles.includes('finance')
        ? <AdminPayments key={orderId ?? 'queue'} ur={ur} orderId={orderId}/> : <AdminNotice ur={ur} denied/>}</AdminPage>;
}
