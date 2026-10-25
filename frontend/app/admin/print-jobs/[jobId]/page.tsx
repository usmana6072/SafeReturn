import { AdminPage, AdminNotice } from '../../../../components/admin-page';
import { AdminPrintJobs } from '../../../../components/admin-print-jobs';
export const dynamic = 'force-dynamic';
export const metadata = { title: 'Print Job Details | SafeReturn', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };
export default async function Page({ params }: {
    params: Promise<{
        jobId: string;
    }>;
}) { const { jobId } = await params; return <AdminPage path="/admin/print-jobs" capability="printing.manage">{(s, ur) => s.roles.includes('operations') ? <AdminPrintJobs ur={ur} jobId={jobId}/> : <AdminNotice ur={ur} denied/>}</AdminPage>; }
