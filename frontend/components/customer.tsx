import Link from "next/link";
import type { ReactNode } from "react";
import type { Pair, Tag } from "../lib/qr-contract";
import { CustomerIcon } from "./customer-icon";
import { CustomerNavigation } from "./customer-navigation";
import "./customer-portal.css";

export function CustomerShell({ ur, children, unread }: { ur: boolean; children: ReactNode; unread?: ReactNode }) {
  return <div className="customer-portal" dir={ur ? "rtl" : "ltr"} lang={ur ? "ur" : "en"}>
    <a className="skip-link" href="#main-content">{ur ? "مواد پر جائیں" : "Skip to content"}</a>
    <header className="portal-header">
      <Link className="brand" href="/dashboard"><img src="/icon-192.png" width="34" height="34" alt=""/>SafeReturn</Link>
      <div className="header-controls">
        <Link href="/inbox?status=new" prefetch={false} className="header-bell"><CustomerIcon name="bell"/>
          <span className="sr-only">{ur ? "فائنڈر پیغامات کی اطلاعات" : "Finder message notifications"}</span>{unread}</Link>
        <Link href="/account" prefetch={false} className="header-avatar" aria-label={ur ? "اکاؤنٹ کی ترتیبات" : "Account settings"}><CustomerIcon name="account"/></Link>
      </div>
    </header>
    <div className="layout"><main id="main-content" tabIndex={-1} className="portal-main">{children}</main>
      <CustomerNavigation ur={ur} unread={unread}/></div>
  </div>;
}
export function Unavailable({ ur }: { ur: boolean }) {
  return <p role="alert">{ur ? "معلومات دستیاب نہیں۔ دوبارہ کوشش کریں۔" : "Your information is unavailable. Please reload and try again."}</p>;
}
export function TagCard({ tag, ur }: { tag: Tag; ur: boolean }) {
  return <article className="qr-card"><span className="eyebrow">{tag.tag_type === "lost" ? (ur ? "گمشدہ چیز" : "LOST") : (ur ? "ہنگامی رابطہ" : "ICE")}</span>
    <h3>{tag.profile_label || (ur ? "پروفائل تیار کریں" : "Set up profile")}</h3>
    <p className="form-help"><bdi>{tag.pair_reference}</bdi></p>
    <p>{tag.published ? (ur ? "اشاعت آن" : "Publication on") : (ur ? "نجی مسودہ" : "Private draft")}</p>
    <p className="form-help">{ur ? "QR کی حالت" : "QR status"}: <bdi>{tag.public_status}</bdi></p>
    <Link className="button secondary" href={`/my-qr/${tag.qr_id}`}>{ur ? "تفصیلات میں ترمیم" : "Edit details"}</Link></article>;
}
export function PairCard({ pair, ur }: { pair: Pair; ur: boolean }) {
  return <section className="pair-card"><h2><Link href={`/kits/${pair.pair_id}`}><bdi>{pair.pair_reference}</bdi></Link></h2>
    <p>{ur ? "ملکیت" : "Ownership"}: <bdi>{pair.ownership_status}</bdi></p>
    {pair.activated_at && <p className="form-help">{ur ? "فعال ہونے کی تاریخ" : "Activated"}: <bdi>{pair.activated_at.slice(0,10)}</bdi></p>}
    <Link prefetch={false} href={`/kits/${pair.pair_id}/history`}>{ur ? "عوامی رسائی اور تاریخ" : "Public access and history"}</Link>
    <div className="qr-grid">{pair.tags.map(tag => <TagCard key={tag.qr_id} tag={tag} ur={ur} />)}</div></section>;
}
