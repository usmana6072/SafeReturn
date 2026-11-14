import { AdminPage, AdminNotice } from "../../../../components/admin-page";
import { AdminPageContainer } from "../../../../components/admin-ui";
import { AdminTemplateDetails } from "../../../../components/admin-template-details";
import { getLanguage } from "../../../../lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Template Details & Revisions | SafeReturn Staff",
  robots: { index: false, follow: false },
};

export default async function Page({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  const language = await getLanguage();
  const ur = language === "ur";

  return (
    <AdminPage path={`/admin/templates/${key}`}>
      {(security) => security.roles.some(role => ['operations','security_admin','superadmin'].includes(role)) ? <AdminPageContainer>
        <AdminTemplateDetails keyParam={key} ur={ur} />
      </AdminPageContainer> : <AdminNotice ur={ur} denied/>}
    </AdminPage>
  );
}
