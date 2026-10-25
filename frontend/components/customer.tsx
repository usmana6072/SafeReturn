import Link from "next/link";
import type { ReactNode } from "react";
import type { Pair, Tag } from "../lib/qr-contract";
import { logout } from "../app/auth/actions";

export function CustomerShell({ ur, children }: { ur: boolean; children: ReactNode }) {
  return <><a className="skip-link" href="#main-content">{ur ? "مواد پر جائیں" : "Skip to content"}</a>
    <header className="container auth-header"><Link className="brand" href="/">SafeReturn</Link><Link href="/account">{ur ? "اکاؤنٹ" : "Account"}</Link></header>
    <div className="container customer-layout"><nav className="customer-nav" aria-label={ur ? "اکاؤنٹ مینو" : "Customer navigation"}>
      <Link href="/dashboard">{ur ? "خلاصہ" : "Overview"}</Link><Link href="/my-qr">{ur ? "میرے QR کوڈز" : "My QR codes"}</Link>
      <Link href="/independent-qr">{ur?"الگ QR شناختیں":"Independent QRs"}</Link><Link href="/kits">{ur ? "میرے کٹس" : "My kits"}</Link><Link href="/activate">{ur ? "فعال کریں" : "Activate QR"}</Link>
      <Link href="/orders">{ur ? "میرے آرڈرز" : "My orders"}</Link>
      <Link href="/account/shipping-addresses">{ur ? "ترسیل کے پتے" : "Shipping addresses"}</Link>
      <Link href="/inbox">{ur ? "فائنڈر اِن باکس" : "Finder inbox"}</Link>
      <Link href="/settings">{ur ? "ترتیبات" : "Settings"}</Link>
      <Link href="/help">{ur ? "مدد" : "Help"}</Link>
      <form action={logout}><button className="button secondary">{ur ? "لاگ آؤٹ" : "Log out"}</button></form></nav>
      <main id="main-content" tabIndex={-1} className="customer-main">{children}</main></div></>;
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
