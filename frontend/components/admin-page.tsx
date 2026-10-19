import Link from "next/link";
import { redirect, unstable_rethrow } from "next/navigation";
import { type ReactNode } from "react";
import { getLanguage } from "../lib/i18n";
import { staffMfaSession, StaffAccessError } from "../lib/auth/staff";
import { type Capability, type StaffSecurityState } from "../lib/auth/staff-contract";
import { AdminShell } from "./admin-shell";
import styles from "./admin-shell.module.css";
export function AdminNotice({ ur, denied = false }: { ur: boolean; denied?: boolean }) {
  return <main className={`container section ${styles.notice}`}><h1>{denied ? (ur ? "رسائی کی اجازت نہیں" : "Access denied") : (ur ? "عملے کا کنسول دستیاب نہیں" : "Staff console unavailable")}</h1>
    <p role="alert">{denied ? (ur ? "آپ کے موجودہ کردار کو اس صفحے کی اجازت نہیں ہے۔" : "Your current role does not permit this page.") : (ur ? "رسائی کی تصدیق نہیں ہو سکی۔ دوبارہ کوشش کریں۔" : "Access could not be verified. Please try again.")}</p>
    <Link href="/admin" prefetch={false}>{ur ? "عملے کا کنسول" : "Staff console"}</Link><Link href="/account">{ur ? "میرا اکاؤنٹ" : "My account"}</Link></main>;
}
export async function AdminPage({ path, capability, children }: { path: string; capability?: Capability; children: ReactNode | ((security: StaffSecurityState, ur: boolean) => ReactNode) }) {
  const ur = await getLanguage() === "ur";
  let session;
  try { session = await staffMfaSession(path, capability); }
  catch (error) {
    // Framework redirects must escape this catch; no module renders on failure.
    unstable_rethrow(error);
    if (error instanceof StaffAccessError && error.status === 401) redirect("/login");
    return <AdminNotice ur={ur} denied={error instanceof StaffAccessError && error.status === 403}/>;
  }
  return <AdminShell security={session.security} ur={ur}>{typeof children === "function" ? children(session.security, ur) : children}</AdminShell>;
}
