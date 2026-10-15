import { getLanguage } from "../../lib/i18n";
import { AuthShell } from "../auth/shell";
import { IdentityForm } from "../auth/form";

export const metadata = { title: "Log in | SafeReturn", robots: { index: false, follow: false } };
export default async function Login({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const ur = await getLanguage() === "ur";
  const params = await searchParams;
  return <AuthShell ur={ur}><span className="eyebrow">{ur ? "خوش آمدید" : "WELCOME BACK"}</span>
    <h1>{ur ? "SafeReturn میں لاگ اِن" : "Log in to SafeReturn"}</h1>
    <p>{ur ? "اپنے QR پروفائلز ایک جگہ سنبھالیں۔" : "Manage your QR profiles in one simple place."}</p>
    {params.confirmation === "failed" && <p role="status">{ur ? "تصدیقی لنک مکمل نہیں ہو سکا۔ دوبارہ لاگ اِن کریں۔" : "That confirmation link could not be completed. Try logging in after confirming your email."}</p>}
    {params.reset === "done" && <p role="status">{ur ? "پاس ورڈ بدل گیا۔ دوبارہ لاگ اِن کریں۔" : "Password updated. Log in again."}</p>}
    <IdentityForm mode="login" ur={ur} /></AuthShell>;
}
