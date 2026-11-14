import { AdminPage, AdminNotice } from '../../../components/admin-page';
import { AdminPrintJobs } from '../../../components/admin-print-jobs';
import { uuid } from '../../../lib/admin-print-jobs-contract';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Print Jobs | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page({ searchParams }: {
    searchParams: Promise<{
        orderId?: string | string[];
    }>;
}) { let orderId: string | undefined, valid = true; try {
    const query = await searchParams;
    if (query.orderId !== undefined)
        orderId = uuid(query.orderId);
}
catch {
    valid = false;
} return <AdminPage path="/admin/print-jobs" capability="printing.manage">{(s, ur) => s.roles.includes('operations') && valid ? <AdminPrintJobs ur={ur} initialOrderId={orderId}/> : <AdminNotice ur={ur} denied={!s.roles.includes('operations')}/>}</AdminPage>; }
