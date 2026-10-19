import Link from "next/link";
import { redirect } from "next/navigation";
import { getLanguage } from "../../lib/i18n";
import { verifiedSession, accountRequest } from "../../lib/auth/server";
import { AuthShell } from "../auth/shell";
import { AccountForm } from "../auth/form";
import { logout } from "../auth/actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Account | SafeReturn", robots: { index: false, follow: false } };
export default async function AccountPage({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const ur = await getLanguage() === "ur";
  let session;
  try { session = await verifiedSession(); } catch {
    return <AuthShell ur={ur}><h1>{ur ? "اکاؤنٹ دستیاب نہیں" : "Account unavailable"}</h1>
      <p>{ur ? "تھوڑی دیر بعد دوبارہ کوشش کریں۔" : "Please try again shortly."}</p><Link href="/login">{ur ? "لاگ اِن" : "Log in"}</Link></AuthShell>;
  }
  if (!session) redirect("/login");
  const params = await searchParams;
  let account;
  try { account = await accountRequest(session.token); } catch {
    return <AuthShell ur={ur}><h1>{ur ? "اکاؤنٹ دستیاب نہیں" : "Account unavailable"}</h1>
      <p>{ur ? "معلومات لوڈ نہیں ہو سکیں۔ دوبارہ کوشش کریں۔" : "Your account could not be loaded. Please try again."}</p>
      <form action={logout}><button className="button">{ur ? "لاگ آؤٹ" : "Log out"}</button></form></AuthShell>;
  }
  const initialName = typeof session.user.user_metadata.display_name === "string"
    ? session.user.user_metadata.display_name.slice(0, 120) : "";
  return <AuthShell ur={ur}><h1>{ur ? "آپ کا اکاؤنٹ" : "Your account"}</h1>
    <Link className="text-link" href="/dashboard">{ur ? "میرے QR کوڈز" : "My QR dashboard"}</Link>
    <p>{account.email_verified ? (ur ? "ای میل کی تصدیق ہو چکی ہے۔" : "Email confirmed.")
      : (ur ? "حساس تبدیلیوں سے پہلے ای میل کی تصدیق کریں۔" : "Confirm your email before sensitive changes.")}</p>
    {params.saved === "1" && <p role="status">{ur ? "تبدیلیاں محفوظ ہو گئیں۔" : "Changes saved."}</p>}
    {params.logout === "failed" && <p role="status">{ur ? "لاگ آؤٹ نہیں ہو سکا۔ دوبارہ کوشش کریں۔" : "Logout could not be completed. Please try again."}</p>}
    <p><Link href="/admin/security/mfa">Staff security / MFA</Link></p>
    <AccountForm account={account} initialName={initialName} ur={ur} />
    <form action={logout} className="logout-form"><button className="button secondary">{ur ? "لاگ آؤٹ" : "Log out"}</button></form>
  </AuthShell>;
}
