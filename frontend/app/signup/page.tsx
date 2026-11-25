import { getLanguage } from "../../lib/i18n";
import { AuthShell } from "../auth/shell";
import { IdentityForm } from "../auth/form";

export const metadata = { title: "Create account | SafeReturn", robots: { index: false, follow: false } };
export default async function Signup({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const ur = await getLanguage() === "ur";
  const params = await searchParams;
  return <AuthShell ur={ur}><span className="eyebrow">{ur ? "SafeReturn میں شامل ہوں" : "JOIN SAFERETURN"}</span>
    <h1>{ur ? "اپنا اکاؤنٹ بنائیں" : "Create your account"}</h1>
    <p>{ur ? "اپنے ذاتی QR اکاؤنٹ سے آغاز کریں۔" : "Get started with your personal QR account."}</p>
    <IdentityForm mode="signup" ur={ur} returnTo={params.returnTo} /></AuthShell>;
}
