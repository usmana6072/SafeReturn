import Link from "next/link";
import { getLanguage } from "../../../lib/i18n";
import { AuthShell } from "../shell";
import { EmailForm } from "../email-form";
export const metadata = { title: "Reset password | SafeReturn", robots: { index: false, follow: false } };
export default async function ForgotPassword() {
  const ur = await getLanguage() === "ur";
  return <AuthShell ur={ur}><h1>{ur ? "پاس ورڈ ری سیٹ کریں" : "Reset your password"}</h1>
    <EmailForm mode="recovery" ur={ur} /><Link href="/auth/sign-in">{ur ? "لاگ اِن پر واپس" : "Back to login"}</Link></AuthShell>;
}
