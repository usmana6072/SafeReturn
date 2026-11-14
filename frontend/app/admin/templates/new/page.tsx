import { AdminPage } from "../../../../components/admin-page";
import { AdminPageContainer } from "../../../../components/admin-ui";
import { CreatePrintTemplatePage } from "../../../../components/admin-create-template-key";
import { getLanguage } from "../../../../lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Create Print Template Key | SafeReturn Staff",
  robots: { index: false, follow: false },
};

export default async function Page() {
  const language = await getLanguage();
  const ur = language === "ur";

  return (
    <AdminPage path="/admin/templates/new" capability="printing.manage">
      <AdminPageContainer>
        <CreatePrintTemplatePage ur={ur} />
      </AdminPageContainer>
    </AdminPage>
  );
}
