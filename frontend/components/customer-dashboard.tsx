import Link from "next/link";
import { ownerApi, ownerSession } from "../lib/qr-server";
import { collection } from "../lib/independent-qr";
import { getLanguage } from "../lib/i18n";
import { orderStatus } from "../lib/order-status";
import { Unavailable } from "./customer";

type RecentOrder = { id: string; order_number: string; payment_status: string; fulfillment_status: string; total_pkr: string; currency_code: string };
type RecentMessage = { id: string; qr_label: string | null; status: string };
function pageOf<T>(value: unknown, fields: string[]): {items:T[];next_cursor:string|null} {
  if (!value || typeof value !== "object") throw Error("Invalid collection");
  const page = value as {items:unknown[];next_cursor:unknown};
  if (!Array.isArray(page.items) || page.items.length > 100 || !(page.next_cursor === null || typeof page.next_cursor === "string") || page.items.some(item => !item || typeof item !== "object" || fields.some(key => typeof (item as Record<string,unknown>)[key] !== "string"))) throw Error("Invalid collection");
  return page as {items:T[];next_cursor:string|null};
}

export async function CustomerDashboard() {
  const ur = await getLanguage() === "ur", session = await ownerSession(), api = ownerApi(session.token);
  const t = (en:string, translated:string) => ur ? translated : en;
  const [identities, orders, inbox] = await Promise.allSettled([
    api<unknown>("/me/independent-qr?limit=100").then(collection),
    api<unknown>("/me/orders?limit=5").then(v => pageOf<RecentOrder>(v, ["id","order_number","payment_status","fulfillment_status","total_pkr","currency_code"])),
    api<unknown>("/me/finder-messages?status=new&limit=5").then(v => pageOf<RecentMessage>(v, ["id","status"])),
  ]);
  const data = identities.status === "fulfilled" ? identities.value : null;
  return <><h1>{t("Your dashboard", "آپ کا ڈیش بورڈ")}</h1><p className="lead">{t("Manage your QR identities, orders and finder messages.", "اپنی QR شناختیں، آرڈرز اور فائنڈر پیغامات دیکھیں۔")}</p>
    {data ? <><div className="grid three">{[
      [data.items.filter(i=>i.ownership_status==="active").length, t("Activated QRs","فعال QR")],
      [data.items.filter(i=>i.ownership_status==="unclaimed").length,t("Awaiting activation","فعال ہونے کے منتظر")],
      [data.items.filter(i=>i.can_activate).length,t("Eligible to activate","فعال کرنے کے اہل")],
    ].map(([count,label])=><article className="card" key={label}><div className="stat">{count}</div><div>{label}</div></article>)}</div>
    {data.next_cursor && <p>{t("Counts cover the first 100 allocated identities. Open My QR codes to browse further.","یہ تعداد پہلی ۱۰۰ مختص شناختوں کی ہے۔ مزید شناختیں میرے QR کوڈز میں دیکھیں۔")}</p>}
    {!data.activation_released && <p className="alert">{t("Activation is not available yet. Your purchased identities remain listed below.","فعال کرنا ابھی دستیاب نہیں۔ خریدی گئی شناختیں نیچے موجود ہیں۔")}</p>}
    <section className="card"><h2>{t("My QR codes","میرے QR کوڈز")}</h2>{!data.items.length ? <p>{t("No allocated QR identities yet. Payment submission alone does not allocate a QR.","ابھی کوئی QR مختص نہیں۔ صرف ادائیگی جمع کرانے سے QR مختص نہیں ہوتا۔")}</p> : data.items.slice(0,4).map(i=><p key={i.qr_id}>{i.product_name_snapshot} · {i.tag_type === "ice" ? t("Emergency","ہنگامی") : t("Lost","گمشدہ")} <Link href={i.ownership_status==="active"?`/my-qr/${i.qr_id}`:"/my-qr"}>{i.can_activate?t("Review activation","فعال کرنے کا جائزہ"):t("View details","تفصیلات")}</Link></p>)}<div className="actions"><Link className="button" href="/my-qr">{t("Manage QR codes","QR کوڈز کا انتظام")}</Link><Link className="button secondary" href="/shop">{t("Browse products","مصنوعات دیکھیں")}</Link></div></section></> : <Unavailable ur={ur}/>}
    <div className="grid"><section className="card"><h2>{t("Recent orders","حالیہ آرڈرز")}</h2>{orders.status === "rejected" ? <Unavailable ur={ur}/> : orders.value.items.length ? orders.value.items.map(o=><div key={o.id}><h3><Link href={`/orders/${o.id}`}>{o.order_number}</Link></h3><p>{o.currency_code} {o.total_pkr}</p><p><span className="pill">{orderStatus(o.payment_status,ur)}</span><span className="pill off">{orderStatus(o.fulfillment_status,ur)}</span></p></div>) : <p>{t("No orders yet.","ابھی کوئی آرڈر نہیں۔")}</p>}<Link href="/orders">{t("All orders","تمام آرڈرز")}</Link></section>
    <section className="card"><h2>{t("Finder inbox","فائنڈر اِن باکس")}</h2>{inbox.status === "rejected" ? <Unavailable ur={ur}/> : inbox.value.items.length ? <><p>{inbox.value.items.length}{inbox.value.next_cursor?"+":""} {t("unread messages","نئے پیغامات")}</p>{inbox.value.items.map(m=><p key={m.id}><Link href={`/inbox/${m.id}`}>{m.qr_label || t("View message","پیغام دیکھیں")}</Link></p>)}</> : <p>{t("No unread messages.","کوئی نیا پیغام نہیں۔")}</p>}<Link href="/inbox">{t("Open inbox","اِن باکس کھولیں")}</Link></section></div>
  </>;
}
