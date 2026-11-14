import { AdminPage, AdminNotice } from "../../../../components/admin-page";
import { AdminEmptyState } from "../../../../components/admin-ui";
export const dynamic = "force-dynamic";
export default async function Page() {
  return <AdminPage path="/admin/support" capability="support.manage">{(security,ur) => security.roles.includes("support") ? <AdminEmptyState title="Create Case unavailable" description="Case creation requires a separately approved independent contract."/> : <AdminNotice ur={ur} denied/>}</AdminPage>;
}
