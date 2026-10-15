import Link from "next/link";
import { cookies } from "next/headers";
import { verifiedSession } from "../../../lib/auth/server";
import { recoveryAllowed } from "../../../lib/auth/recovery";
import { getLanguage } from "../../../lib/i18n";
import { AuthShell } from "../shell";
import { EmailForm } from "../email-form";
export const metadata = { title: "New password | SafeReturn", robots: { index: false, follow: false } };
export default async function ResetPassword() {
  const ur = await getLanguage() === "ur";
  let allowed = false;
  try {
    const session = await verifiedSession();
    allowed = !!session && recoveryAllowed((await cookies()).get("sr-recovery")?.value ?? "", session.token);
  } catch { /* Fail closed. */ }
  return <AuthShell ur={ur}><h1>{ur ? "نیا پاس ورڈ" : "Set a new password"}</h1>
    {allowed ? <EmailForm mode="reset" ur={ur} /> : <>
      <p>{ur ? "یہ ری سیٹ لنک درست نہیں یا ختم ہو گیا ہے۔" : "This recovery session is invalid or expired."}</p>
      <Link href="/auth/forgot-password">{ur ? "نیا لنک حاصل کریں" : "Request a new link"}</Link></>}
  </AuthShell>;
}
