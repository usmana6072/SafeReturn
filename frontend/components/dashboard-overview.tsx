import Link from "next/link";
import type { ReactNode } from "react";
import type { DashboardData } from "../lib/customer-dashboard";
import type { IndependentQR } from "../lib/independent-qr";
import { orderStatus } from "../lib/order-status";
import { CustomerIcon, type CustomerIconName } from "./customer-icon";
import { DashboardRetry } from "./dashboard-retry";

type Language = { ur: boolean };
const translate = (ur: boolean) => (en: string, translated: string) => ur ? translated : en;
export const qrName = (qr: IndependentQR, ur: boolean) => qr.tag_type === "ice"
  ? translate(ur)("Emergency QR", "ہنگامی QR") : translate(ur)("Lost QR", "گمشدہ QR");
function qrStatus(qr: IndependentQR, ur: boolean) {
  const t = translate(ur);
  if (qr.ownership_status === "revoked" || qr.public_status === "revoked") return t("Revoked", "منسوخ");
  if (qr.public_status === "admin_suspended") return t("Suspended", "معطل");
  if (qr.public_status === "owner_disabled") return t("Disabled", "غیر فعال");
  if (qr.can_activate) return t("Ready to Activate", "فعال کرنے کے لیے تیار");
  return qr.ownership_status === "active" ? t("Active", "فعال") : t("Pending Activation", "فعال ہونے کا انتظار");
}
function statusText(value: string, ur: boolean) {
  const labels: Record<string, [string, string]> = {
    verified: ["Paid", "ادائیگی ہو گئی"], awaiting_transfer: ["Payment Pending", "ادائیگی کا انتظار"],
    under_review: ["Payment Under Review", "ادائیگی زیرِ جائزہ"], preparing: ["Preparing Your Order", "آپ کا آرڈر تیار ہو رہا ہے"],
    dispatched: ["Shipped", "روانہ ہو گیا"],
  };
  return labels[value]?.[ur ? 1 : 0] ?? orderStatus(value, ur);
}
function ActionLink({ href, children }: { href: string; children: ReactNode }) {
  return <Link className="dash-link" href={href} prefetch={false}>{children}<CustomerIcon name="arrow"/></Link>;
}
function Metric({ icon, label, value, note, unread, ur }: Language & { icon: CustomerIconName; label: string; value?: string | number; note?: string; unread?: boolean }) {
  return <div className={unread ? "dash-metric has-unread" : "dash-metric"}>
    <div className="metric-top"><span className="metric-icon"><CustomerIcon name={icon}/></span>
      <strong>{value ?? <><span aria-hidden="true">—</span><span className="sr-only">{ur ? "دستیاب نہیں" : "Unavailable"}</span></>}</strong></div>
    <div className="metric-label">{label}</div>{note && <small>{note}</small>}
  </div>;
}
function QuickActions({ ur }: Language) {
  const actions: [string, CustomerIconName, string, string][] = [
    ["/my-qr", "qr", "Manage My QR Codes", "میرے QR کوڈز کا انتظام"], ["/portal/shop", "shop", "Shop QR Tags", "QR ٹیگز خریدیں"],
    ["/orders", "orders", "View My Orders", "میرے آرڈرز دیکھیں"], ["/inbox", "inbox", "Finder Messages", "فائنڈر پیغامات"],
  ];
  return <section><h2>{ur ? "فوری اقدامات" : "Quick Actions"}</h2><div className="dash-actions">
    {actions.map(([href, icon, en, translated]) => <Link href={href} key={href} prefetch={false}>
      <CustomerIcon name={icon}/><span>{ur ? translated : en}</span></Link>)}
  </div></section>;
}

type PreviewNames = { names?: Record<string, ReactNode> };
function QRPreview({ ur, identities, hasNoOrders, names }: Language & Pick<DashboardData, "identities"> & PreviewNames & { hasNoOrders: boolean }) {
  const t = translate(ur);
  return <section className="dash-panel"><h2>{t("My QR Codes", "میرے QR کوڈز")}</h2>
    {!identities ? <DashboardRetry ur={ur}/> : <>
      {identities.items.length ? <>
        <ul className="dash-list">{identities.items.slice(0, 4).map(qr => <li key={qr.qr_id}>
          <div className="dash-item"><span className="item-icon"><CustomerIcon name="qr"/></span><div>
            <h3>{names?.[qr.qr_id] ?? qrName(qr, ur)}</h3><p><bdi>{qr.product_name_snapshot}</bdi></p>
          </div></div>
          <div className="dash-row"><span className="dash-status">{qrStatus(qr, ur)}</span>
            <ActionLink href={qr.ownership_status === "active" ? `/my-qr/${qr.qr_id}` : "/my-qr"}>
              {qr.can_activate ? t("Review Activation", "فعال کرنے کا جائزہ") : t("View QR Details", "QR کی تفصیلات دیکھیں")}
            </ActionLink></div>
        </li>)}</ul>
      </> : <div className="dash-empty"><CustomerIcon name="qr"/><h3>{t("No QR Codes Yet", "ابھی کوئی QR کوڈ نہیں")}</h3>
        <p>{hasNoOrders ? t("Purchase a QR tag to help protect your belongings.", "اپنے سامان کی حفاظت کے لیے QR ٹیگ خریدیں۔")
          : t("Your QR codes will appear here once they’re allocated to your order.", "آپ کے آرڈر کے لیے QR کوڈز مختص ہونے پر یہاں دکھائی دیں گے۔")}</p>
        {hasNoOrders && <ActionLink href="/portal/shop">{t("Shop QR Tags", "QR ٹیگز خریدیں")}</ActionLink>}</div>}
      {!identities.activation_released && <p className="dash-note">{t("Activation is currently unavailable.", "فعال کرنے کی سہولت فی الحال دستیاب نہیں۔")}</p>}
    </>}
    <div className="panel-footer"><ActionLink href="/my-qr">{t("Manage All QR Codes", "تمام QR کوڈز کا انتظام")}</ActionLink></div>
  </section>;
}
function Activity({ ur, identities, inbox }: Language & Pick<DashboardData, "identities" | "inbox">) {
  const t = translate(ur);
  const events = [
    ...(inbox?.items ?? []).map(m => ({ href: `/inbox/${m.id}`, at: m.submitted_at, icon: "inbox" as const,
      title: t("New finder message", "نیا فائنڈر پیغام"), label: m.qr_label })),
    ...(identities?.items ?? []).filter(q => q.activated_at && Number.isFinite(Date.parse(q.activated_at))).map(q => ({
      href: `/my-qr/${q.qr_id}`, at: q.activated_at!, icon: "check" as const, title: t("QR code activated", "QR کوڈ فعال ہو گیا"), label: q.product_name_snapshot })),
  ].sort((a, b) => Date.parse(b.at) - Date.parse(a.at)).slice(0, 3);
  return <section className="dash-panel"><h2>{t("Recent Activity", "حالیہ سرگرمیاں")}</h2>
    {events.length > 0 && <ul className="dash-list activity-list">{events.map(e => <li key={e.href}>
      <Link className="dash-item" href={e.href} prefetch={false}><span className="item-icon"><CustomerIcon name={e.icon}/></span><div>
        <strong>{e.title}</strong>{e.label && <p><bdi>{e.label}</bdi></p>}<time dateTime={e.at}>{formatDate(e.at, ur, true)}</time>
      </div><CustomerIcon name="arrow"/></Link>
    </li>)}</ul>}
    {(!inbox || !identities) ? <DashboardRetry ur={ur}/> : events.length === 0 && <p className="dash-note">{t("No recent QR activations or unread finder messages.", "حالیہ QR فعالیت یا نئے فائنڈر پیغامات موجود نہیں۔")}</p>}
    <div className="panel-footer"><ActionLink href="/inbox">{t("Open Finder Messages", "فائنڈر پیغامات دیکھیں")}</ActionLink></div>
  </section>;
}
function formatDate(stamp: string, ur: boolean, withTime = false) {
  return new Intl.DateTimeFormat(ur ? "ur-PK" : "en-GB", { dateStyle: "medium", ...(withTime && { timeStyle: "short" }), timeZone: "Asia/Karachi" }).format(new Date(stamp));
}
function Orders({ ur, orders }: Language & Pick<DashboardData, "orders">) {
  const t = translate(ur);
  return <section className="dash-panel recent-orders"><h2>{t("Recent Orders", "حالیہ آرڈرز")}</h2>
    {!orders ? <DashboardRetry ur={ur}/> : orders.items.length ? <ul className="dash-list">{orders.items.slice(0, 3).map(order => <li key={order.id}>
      <div className="order-preview"><div><time dateTime={order.created_at}>{formatDate(order.created_at, ur)}</time>
        <p><bdi>{order.order_number.length > 16 ? "…" + order.order_number.slice(-10) : order.order_number}</bdi></p></div>
        <strong><bdi>{order.currency_code} {order.total_pkr}</bdi></strong></div>
      <div className="dash-row"><div className="order-statuses">
        <span className="dash-status payment"><span className="sr-only">{t("Payment", "ادائیگی")} · </span>{statusText(order.payment_status, ur)}</span>
        <span className="dash-status"><span className="sr-only">{t("Fulfillment", "ترسیل")} · </span>{statusText(order.fulfillment_status, ur)}</span>
      </div><ActionLink href={`/orders/${order.id}`}>{t("View Order Details", "آرڈر کی تفصیلات دیکھیں")}</ActionLink></div>
    </li>)}</ul> : <div className="dash-empty"><CustomerIcon name="box"/><h3>{t("No Orders Yet", "ابھی کوئی آرڈر نہیں")}</h3>
      <p>{t("Your purchases will appear here once you place an order.", "آرڈر دینے کے بعد آپ کی خریداری یہاں دکھائی دے گی۔")}</p>
      <ActionLink href="/portal/shop">{t("Browse Products", "مصنوعات دیکھیں")}</ActionLink></div>}
    <div className="panel-footer"><ActionLink href="/orders">{t("View All Orders", "تمام آرڈرز دیکھیں")}</ActionLink></div>
  </section>;
}

export function DashboardOverview({ ur, data, names }: Language & PreviewNames & { data: DashboardData }) {
  const { firstName, identities, orders, inbox } = data;
  const t = translate(ur);
  const activated = identities?.items.filter(qr => qr.ownership_status === "active");
  const publicAccessOff = activated?.filter(qr => qr.public_status !== "active").length;
  const count = (page: DashboardData["orders"] | DashboardData["inbox"]) => page ? page.items.length + (page.more ? "+" : "") : undefined;
  return <div className="dashboard">
    <header className="dash-welcome"><p className="dash-location"><CustomerIcon name="home"/>{t("Dashboard", "ڈیش بورڈ")}</p>
      <h1>{firstName ? <>{t("Welcome back, ", "خوش آمدید، ")}<bdi>{firstName}</bdi>!</> : t("Welcome back!", "خوش آمدید!")}</h1>
      <p>{t("Manage your QR codes, track orders, and stay connected.", "اپنے QR کوڈز کا انتظام کریں، آرڈرز پر نظر رکھیں اور رابطے میں رہیں۔")}</p>
    </header>
    <section aria-label={t("Account summary", "اکاؤنٹ کا خلاصہ")}><div className="dash-metrics">
      <Metric ur={ur} icon="qr" label={t("Active QR Codes", "فعال QR کوڈز")} value={activated?.length}
        note={publicAccessOff ? `${publicAccessOff} ${t("with public access off", "کی عوامی رسائی بند ہے")}` : undefined}/>
      <Metric ur={ur} icon="pending" label={t("Pending Activation", "فعال ہونے کا انتظار")} value={identities?.items.filter(i => i.ownership_status === "unclaimed").length}
        note={identities ? `${identities.items.filter(i => i.can_activate).length} ${t("Ready to Activate", "فعال کرنے کے لیے تیار")}` : undefined}/>
      <Metric ur={ur} icon="orders" label={t("My Orders", "میرے آرڈرز")} value={count(orders)}/>
      <Metric ur={ur} icon="inbox" label={t("Finder Messages", "فائنڈر پیغامات")} value={count(inbox)} unread={!!inbox?.items.length} note={t("Unread messages", "نئے پیغامات")}/>
    </div>{identities?.next_cursor && <p className="dash-note">{t("QR counts cover the first 100 allocated codes.", "QR کی تعداد پہلے ۱۰۰ مختص کردہ کوڈز کی ہے۔")}</p>}</section>
    <QuickActions ur={ur}/>
    <div className="dash-panels"><QRPreview ur={ur} identities={identities} names={names} hasNoOrders={orders?.items.length === 0}/>
      <Activity ur={ur} identities={identities} inbox={inbox}/><Orders ur={ur} orders={orders}/></div>
  </div>;
}
