import { redirect } from "next/navigation";
import { verifiedSession } from "../../../../lib/auth/server";
import { getLanguage } from "../../../../lib/i18n";
import { PrivacyExports } from "../../../../components/privacy-exports";
export const dynamic = "force-dynamic";
export default async function Page() {
  if (!await verifiedSession()) redirect("/login");
  return <main className="container section"><PrivacyExports ur={await getLanguage() === "ur"}/></main>;
}
