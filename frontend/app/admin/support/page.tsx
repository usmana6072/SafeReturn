import { AdminPage, AdminNotice } from "../../../components/admin-page";
import { AdminSupportCases } from "../../../components/admin-support-cases";
import { supportMetadataAdmitted } from "../../../lib/support-metadata-gate";
export const dynamic = "force-dynamic";
export const metadata = { title: "Support Cases | SafeReturn", robots: { index: false, follow: false } };
export default async function Page() {
  return <AdminPage path="/admin/support" capability="support.manage">{(security, ur) => security.roles.includes("support") ? <AdminSupportCases ur={ur} admitted={supportMetadataAdmitted()}/> : <AdminNotice ur={ur} denied/>}</AdminPage>;
}
