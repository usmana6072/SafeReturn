import { AdminPage, AdminNotice } from "../../../../components/admin-page";
import { AdminSupportCases } from "../../../../components/admin-support-cases";
import { supportMetadataAdmitted } from "../../../../lib/support-metadata-gate";
export const dynamic = "force-dynamic";
export const metadata = { title: "Support Case Details | SafeReturn", robots: { index: false, follow: false } };
export default async function Page({params}: {params: Promise<{caseId: string}>}) {
  const {caseId} = await params;
  return <AdminPage path="/admin/support" capability="support.manage">{(security, ur) => security.roles.includes("support") ? <AdminSupportCases caseId={caseId} ur={ur} admitted={supportMetadataAdmitted()}/> : <AdminNotice ur={ur} denied/>}</AdminPage>;
}
