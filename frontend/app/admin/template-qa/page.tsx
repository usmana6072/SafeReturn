import { AdminPage, AdminNotice } from "../../../components/admin-page";
import { AdminPageContainer } from "../../../components/admin-ui";
import { TemplateQA } from "../../../components/admin-template-qa";
import { getLanguage } from "../../../lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Template QA | SafeReturn Staff",
  robots: { index: false, follow: false },
};

export default async function Page() {
  const language = await getLanguage();
  const ur = language === "ur";

  return (
    <AdminPage path="/admin/template-qa">
      {(security) => security.roles.some(role => ['operations','security_admin','superadmin'].includes(role)) ? <AdminPageContainer>
        <TemplateQA ur={ur} />
      </AdminPageContainer> : <AdminNotice ur={ur} denied/>}
    </AdminPage>
  );
}
