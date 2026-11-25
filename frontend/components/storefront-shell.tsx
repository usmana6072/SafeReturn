import Link from "next/link";
import { type ReactNode } from "react";
import { getLanguage } from "../lib/i18n";
import { verifiedSession } from "../lib/auth/server";
import { customerLanguage } from "../app/customer-actions";
import { CustomerIcon } from "./customer-icon";
import { StoreCartBadge, StoreMenu } from "./storefront-client";

export const viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

export async function StorefrontShell({ children }: { children: ReactNode }) {
  const language = await getLanguage();
  const ur = language === "ur";
  const session = await verifiedSession();

  return (
    <div className="storefront-shell" dir={ur ? "rtl" : "ltr"} lang={ur ? "ur" : "en"}>
      <a className="skip-link" href="#main-content">
        {ur ? "مواد پر جائیں" : "Skip to content"}
      </a>
      <header className="site-header storefront-header">
        <div className="home-container header-inner">
          <Link className="brand home-brand" href="/" aria-label="SafeReturn">
            <img src="/brand/safereturn_logo.svg" alt="" width="34" height="34" />
            <bdi>SafeReturn</bdi>
          </Link>
          <nav className="desktop-nav" aria-label={ur ? "دکان مینو" : "Store menu"}>
            <Link href="/">{ur ? "ہوم" : "Home"}</Link>
            <Link href="/shop">{ur ? "دکان" : "Shop"}</Link>
            <Link href="/#how-it-works">{ur ? "طریقہ کار" : "How it works"}</Link>
            <Link href="/help">{ur ? "مدد" : "Help"}</Link>
          </nav>
          <div className="storefront-actions">
            <StoreCartBadge ur={ur} />
            {session ? (
              <Link href="/dashboard" className="storefront-auth-link" title={ur ? "کسٹمر پورٹل" : "Customer Portal"}>
                <CustomerIcon name="account" />
                <span>{ur ? "پورٹل" : "Portal"}</span>
              </Link>
            ) : (
              <Link href="/login" className="storefront-auth-link">
                <span>{ur ? "لاگ اِن" : "Log in"}</span>
              </Link>
            )}
            <form action={customerLanguage}>
              <input type="hidden" name="language" value={ur ? "en" : "ur"} />
              <button className="language-button" lang={ur ? "en" : "ur"} type="submit">
                {ur ? "English" : "اردو"}
              </button>
            </form>
            <StoreMenu ur={ur} session={Boolean(session)} />
          </div>
        </div>
      </header>
      <main id="main-content" className="storefront-main home-container" tabIndex={-1}>
        {children}
      </main>
      <footer className="storefront-footer">
        <div className="home-container storefront-footer-inner">
          <div className="storefront-footer-brand">
            <Link className="brand home-brand" href="/">
              <img src="/brand/safereturn_logo.svg" width="28" height="28" alt="" />
              <bdi>SafeReturn</bdi>
            </Link>
            <small>{ur ? "محفوظ QR کوڈز سامان اور رابطے کے لیے" : "Connected QR identities for what matters."}</small>
          </div>
          <nav className="storefront-footer-nav" aria-label={ur ? "نیویگیشن" : "Footer navigation"}>
            <Link href="/">{ur ? "ہوم" : "Home"}</Link>
            <Link href="/shop">{ur ? "دکان" : "Shop"}</Link>
            <Link href="/cart">{ur ? "کارٹ" : "Cart"}</Link>
            <Link href="/help">{ur ? "مدد" : "Help"}</Link>
            {session ? <Link href="/dashboard">{ur ? "پورٹل" : "Portal"}</Link> : <Link href="/login">{ur ? "لاگ اِن" : "Log in"}</Link>}
          </nav>
          <div className="storefront-footer-bottom">
            <small>© 2026 SafeReturn</small>
          </div>
        </div>
      </footer>
    </div>
  );
}
