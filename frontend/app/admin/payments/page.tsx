import { AdminPage, AdminNotice } from '../../../components/admin-page';
import { AdminPayments } from '../../../components/admin-payments';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Payments & Reconciliation | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page() { return <AdminPage path="/admin/payments" capability="payments.review">{(s, ur) => s.roles.includes('finance') ? <AdminPayments ur={ur}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
