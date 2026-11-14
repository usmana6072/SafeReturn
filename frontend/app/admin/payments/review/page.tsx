import Link from 'next/link';
import { AdminPage, AdminNotice } from '../../../../components/admin-page';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Payment Review | SafeReturn', robots: { index: false, follow: false } };
export default async function Page() { return <AdminPage path="/admin/payments" capability="payments.review">{(s, ur) => s.roles.includes('finance') ? <section><h1>Payment review</h1><p>Select an order from the payment lookup to review pending attempts and record a verified bank match or rejection.</p><Link href="/admin/payments" prefetch={false}>Back to payment lookup</Link></section> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
