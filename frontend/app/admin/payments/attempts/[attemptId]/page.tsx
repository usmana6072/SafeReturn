import { AdminPage, AdminNotice } from '../../../../../components/admin-page';
import { AdminPayments } from '../../../../../components/admin-payments';
import { uuid } from '../../../../../lib/admin-payments-contract';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Payment Attempt | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page({ params, searchParams }: {
    params: Promise<{
        attemptId: string;
    }>;
    searchParams: Promise<{
        orderId?: string | string[];
    }>;
}) { let attempt: string, order: string; try {
    attempt = uuid((await params).attemptId);
    order = uuid((await searchParams).orderId);
}
catch {
    return <AdminPage path="/admin/payments" capability="payments.review">{(_s, ur) => <AdminNotice ur={ur}/>}</AdminPage>;
} return <AdminPage path="/admin/payments" capability="payments.review">{(s, ur) => s.roles.includes('finance') ? <AdminPayments ur={ur} orderId={order} attemptId={attempt}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
