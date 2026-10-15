import Link from "next/link";
import { ReactNode } from "react";

export function AuthShell({ children, ur }: { children: ReactNode; ur: boolean }) {
  return <>
    <header className="container auth-header"><Link href="/" className="brand">
      <span className="brand-mark">S</span>SafeReturn</Link>
      <Link href="/">{ur ? "ویب سائٹ پر واپس" : "Back to website"}</Link></header>
    <main id="main-content" className="container auth-layout">
      <aside className="auth-promo"><span className="eyebrow">SAFERETURN</span>
        <h2>{ur ? "اپنی اہم چیزوں سے جڑے رہیں۔" : "Good things are worth keeping close."}</h2>
        <p>{ur ? "اپنے QR پروفائلز سنبھالیں اور صرف منتخب معلومات شیئر کریں۔"
          : "Manage your QR profiles, share the right details and stay connected."}</p>
        <div className="auth-art" aria-hidden="true"><span>♡</span><strong>SafeReturn</strong></div>
      </aside>
      <section className="auth-panel">{children}</section>
    </main>
  </>;
}
