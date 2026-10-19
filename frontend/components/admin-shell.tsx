"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, type ReactNode } from "react";
import { permittedModules, type StaffSecurityState } from "../lib/auth/staff-contract";
import { logout } from "../app/auth/actions";
import { adminLanguage } from "../app/admin/actions";
import styles from "./admin-shell.module.css";
export function AdminShell({ security, ur, children }: { security: StaffSecurityState; ur: boolean; children: ReactNode }) {
  const path = usePathname();
  const dialog = useRef<HTMLDialogElement>(null);
  const modules = permittedModules(security);
  const current = modules.find(module => module.path === path);
  const title = current ? (ur ? current.ur : current.en) : path.startsWith("/admin/print-jobs/") ? (ur ? "پرنٹ کی تفصیل" : "Print job") : (ur ? "عملے کا کنسول" : "Staff console");
  const navigation = (mobile = false) => <nav aria-label={ur ? "عملے کا مینو" : "Staff navigation"}>
    {[{ path: "/admin", en: "Workspace", ur: "کام کی جگہ" }, ...modules, { path: "/admin/security/mfa", en: "Security / MFA", ur: "سکیورٹی / MFA" }].map(module =>
      <Link key={module.path} href={module.path} prefetch={false} aria-current={path === module.path ? "page" : undefined} onClick={() => { if (mobile) dialog.current?.close(); }}>{ur ? module.ur : module.en}</Link>)}
    <Link href="/account" prefetch={false}>{ur ? "میرا اکاؤنٹ" : "My account"}</Link>
    <form action={logout}><button className="button secondary">{ur ? "لاگ آؤٹ" : "Log out"}</button></form>
  </nav>;
  return <div className={styles.workspace}>
    <a className="skip-link" href="#staff-content">{ur ? "مواد پر جائیں" : "Skip to content"}</a>
    <header className={styles.header}>
      <Link href="/admin" className="brand" prefetch={false}><bdi>SafeReturn</bdi></Link>
      <span>{ur ? "عملے کا کنسول" : "Staff console"}</span>
      <form action={adminLanguage}><input type="hidden" name="language" value={ur ? "en" : "ur"}/><input type="hidden" name="returnTo" value={path}/><button className="language-button" lang={ur ? "en" : "ur"}>{ur ? "English" : "اردو"}</button></form>
      <button className={`button secondary ${styles.menu}`} aria-haspopup="dialog" onClick={() => dialog.current?.showModal()}>{ur ? "مینو" : "Menu"}</button>
    </header>
    <div className={styles.layout}>
      <aside className={styles.sidebar}><p className={styles.eyebrow}>{ur ? "کام کی جگہ" : "Workspace"}</p>{navigation()}</aside>
      <div className={styles.content} id="staff-content" tabIndex={-1}>
        <nav className={styles.breadcrumb} aria-label={ur ? "راستہ" : "Breadcrumb"}><Link href="/admin" prefetch={false}>{ur ? "عملہ" : "Staff"}</Link><span aria-hidden="true">/</span><span aria-current="page">{title}</span></nav>
        {children}
      </div>
    </div>
    <dialog ref={dialog} className={styles.drawer} aria-label={ur ? "عملے کا مینو" : "Staff menu"}>
      <button className="button secondary" autoFocus onClick={() => dialog.current?.close()}>{ur ? "مینو بند کریں" : "Close menu"}</button>
      {navigation(true)}
    </dialog>
  </div>;
}
