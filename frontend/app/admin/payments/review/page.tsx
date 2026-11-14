import Link from 'next/link';
import { AdminPage, AdminNotice } from '../../../../components/admin-page';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Settlement Review Unavailable | SafeReturn', robots: { index: false, follow: false } };
export default async function Page() { return <AdminPage path="/admin/payments" capability="payments.review">{(s, ur) => s.roles.includes('finance') ? <section><h1>Settlement review unavailable</h1><p>Payment verification and settlement actions are excluded because they can trigger prohibited QR-pair allocation. No payment status can be changed here.</p><Link href="/admin/payments" prefetch={false}>Back to payment lookup</Link></section> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
