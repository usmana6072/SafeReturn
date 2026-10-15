import Link from "next/link";
import { getLanguage } from "../../../lib/i18n";
import { AuthShell } from "../shell";
import { EmailForm } from "../email-form";
export const metadata = { title: "Confirm email | SafeReturn", robots: { index: false, follow: false } };
export default async function VerifyEmail() {
  const ur = await getLanguage() === "ur";
  return <AuthShell ur={ur}><h1>{ur ? "اپنی ای میل چیک کریں" : "Check your email"}</h1>
    <p>{ur ? "تصدیقی لنک اسی براؤزر میں کھولیں، پھر لاگ اِن کریں۔" : "Open the confirmation link in this browser, then log in."}</p>
    <EmailForm mode="resend" ur={ur} /><Link href="/auth/sign-in">{ur ? "لاگ اِن" : "Log in"}</Link></AuthShell>;
}
