import Link from "next/link";
import type { IndependentQR } from "../lib/independent-qr";
import { customerOperationAvailable } from "../lib/customer-capabilities";
import { CustomerIcon } from "./customer-icon";
import "./qr-library.css";

export type FinderHints = Record<string, { count: number; partial: boolean }>;
export const translate = (ur: boolean) => (en: string, translated: string) => ur ? translated : en;
export const qrType = (item: IndependentQR, ur: boolean) => item.tag_type === "ice"
  ? translate(ur)("Emergency QR", "ہنگامی QR") : translate(ur)("Lost QR", "گمشدہ QR");
export function statusOf(item: IndependentQR) {
  if (item.ownership_status === "revoked" || item.public_status === "revoked") return "revoked";
  if (item.public_status === "admin_suspended") return "suspended";
  if (item.public_status === "owner_disabled") return "disabled";
  if (item.can_activate) return "ready";
  return item.ownership_status === "active" ? "active" : "pending";
}
export const statuses = {
  active: ["Active", "فعال"], pending: ["Pending Activation", "فعال ہونے کا انتظار"],
  ready: ["Ready to Activate", "فعال کرنے کے لیے تیار"], disabled: ["Public Access Off", "عوامی رسائی بند"],
  suspended: ["Suspended", "معطل"], revoked: ["Revoked", "منسوخ"],
} as const;
export type QRAction = "menu" | "activation" | "status" | "product" | "access" | "history";
export const canEdit = (item: IndependentQR) => item.ownership_status === "active" && customerOperationAvailable("GET", "/me/qr/" + item.qr_id);

export function QRLibrarySkeleton({ ur }: { ur: boolean }) {
  return <div className="qr-library lib-skeleton" aria-busy="true" role="status"><span className="sr-only">{ur ? "QR کوڈز لوڈ ہو رہے ہیں" : "Loading your QR codes"}</span>
    <div className="lib-skeleton-line" aria-hidden="true"/><div className="lib-skeleton-summary" aria-hidden="true"/>
    <div className="lib-skeleton-search" aria-hidden="true"/><div className="lib-grid" aria-hidden="true"><i/><i/></div></div>;
}

export function QRCard({ item, name, ur, hint, busy, released, act }: {
  item: IndependentQR; name?: string; ur: boolean; hint?: FinderHints[string]; busy: boolean; released: boolean;
  act: (action: QRAction, item: IndependentQR) => void;
}) {
  const t = translate(ur), status = statusOf(item);
  const title = name || item.product_name_snapshot || qrType(item, ur);
  const edit = canEdit(item), enable = status === "disabled" && item.ownership_status === "active" && released;
  let action: QRAction = "status", label = t("View Activation Status", "فعال ہونے کی حالت دیکھیں");
  if (enable) { action = "access"; label = t("Enable Public Access", "عوامی رسائی بحال کریں"); }
  else if (status === "ready") { action = "activation"; label = t("Activate QR", "QR فعال کریں"); }
  else if (status !== "pending") label = t("View QR Details", "QR کی تفصیلات دیکھیں");
  return <article className="lib-card" aria-labelledby={"tag-" + item.qr_id}>
    <div className="lib-card-head"><h2 id={"tag-" + item.qr_id}><bdi>{title}</bdi></h2>
      <span className={"lib-badge is-" + status}>{statuses[status][ur ? 1 : 0]}</span></div>
    <div className="lib-card-body">
      <div className={"lib-art " + item.tag_type} aria-hidden="true"><div className="lib-fob"><CustomerIcon name={item.tag_type === "ice" ? "medical" : "tag"}/></div></div>
      <div className="lib-card-info"><strong>{qrType(item, ur)}</strong>
        {name && name !== item.product_name_snapshot && <p><bdi>{item.product_name_snapshot}</bdi></p>}
        <span className="lib-reference">{t("Tag", "ٹیگ")} <bdi>· {item.qr_id.slice(-8).toUpperCase()}</bdi></span>
        {status === "disabled" && !released && <p>{t("Restoring access is currently unavailable.", "رسائی بحال کرنے کی سہولت فی الحال دستیاب نہیں۔")}</p>}
        {hint && <Link className="lib-finder" prefetch={false} href={`/inbox?qr_id=${item.qr_id}&status=new`}>
          <CustomerIcon name="inbox"/>{hint.partial ? t("New finder message", "نیا فائنڈر پیغام") :
            ur ? `${hint.count} نئے فائنڈر پیغامات` : `${hint.count} new finder message${hint.count === 1 ? "" : "s"}`}
        </Link>}
      </div></div>
    <div className="lib-card-actions">
      {edit && !enable ? <Link className="lib-primary" prefetch={false} href={`/my-qr/${item.qr_id}`}>{t("Manage QR", "QR کا انتظام")}<CustomerIcon name="arrow"/></Link>
        : <button type="button" className={status === "ready" || enable ? "lib-primary" : "lib-secondary"} disabled={busy} onClick={() => act(action, item)}>
          {label}<CustomerIcon name="arrow"/></button>}
      <button className="lib-round" type="button" aria-haspopup="dialog" aria-label={t("More actions for ", "مزید اقدامات، ") + title}
        disabled={busy} onClick={() => act("menu", item)}><CustomerIcon name="more"/></button>
    </div>
  </article>;
}
