import { AdminPage, AdminNotice } from "../../../components/admin-page";
import { AdminPageContainer } from "../../../components/admin-ui";
import { PrintTemplatesList } from "../../../components/admin-templates-list";
import { getLanguage } from "../../../lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Print Templates | SafeReturn Staff",
  robots: { index: false, follow: false },
};

export default async function Page() {
  const language = await getLanguage();
  const ur = language === "ur";

  return (
    <AdminPage path="/admin/templates">
      {(security) => security.roles.some(role => ['operations','security_admin','superadmin'].includes(role)) ? <AdminPageContainer>
        <PrintTemplatesList ur={ur} />
      </AdminPageContainer> : <AdminNotice ur={ur} denied/>}
    </AdminPage>
  );
}
