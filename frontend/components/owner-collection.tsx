import Link from "next/link";
import { ownerApi, ownerSession } from "../lib/qr-server";
import type { Pair, Page, Tag } from "../lib/qr-contract";
import { PairCard, TagCard, Unavailable } from "./customer";
import { getLanguage } from "../lib/i18n";

export async function OwnerCollection({ mode, cursor, search = "", filter = "all" }: { mode: "dashboard" | "kits" | "my-qr"; cursor?: string; search?: string; filter?: string }) {
  const ur = await getLanguage() === "ur", session = await ownerSession();
  const title = mode === "dashboard" ? (ur ? "آپ کا QR ڈیش بورڈ" : "Your QR dashboard") : mode === "kits" ? (ur ? "میرے کٹس" : "My kits") : (ur ? "میرے QR کوڈز" : "My QR codes");
  let pairs: Page<Pair> | undefined, tags: Page<Tag> | undefined;
  try {
    const filters: Record<string, string> = { all: "", lost: "&tag_type=lost", ice: "&tag_type=ice", active: "&status=active", draft: "&publication=draft", suspended: "&status=admin_suspended" };
    const query = `?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}${mode === "my-qr" ? `${filters[filter] ?? ""}&search=${encodeURIComponent(search.slice(0,120))}` : ""}`;
    if (mode === "my-qr") tags = await ownerApi(session.token)<Page<Tag>>(`/me/qr${query}`);
    else pairs = await ownerApi(session.token)<Page<Pair>>(`/me/tag-pairs${query}`);
  } catch { return <><h1>{title}</h1><Unavailable ur={ur} /></>; }
  const page = pairs ?? tags!;
  return <><div className="customer-heading"><h1>{title}</h1><Link className="button secondary" href="/independent-qr">{ur?"الگ QR اور فعال کرنا":"Independent QRs and activation"}</Link><Link className="button" href="/activate">{ur ? "QR فعال کریں" : "Activate QR"}</Link></div>
    <p>{ur ? "ہر کٹ کے Lost اور ICE پروفائل الگ ہیں۔ ایک QR کی تمام پرنٹ کاپیاں ایک پروفائل استعمال کرتی ہیں۔" : "Each kit has separate Lost and ICE profiles. Every printed copy of the same QR shares its profile."}</p>
    {mode === "my-qr" && <><form method="GET" className="account-form qr-filters">
      <label>{ur ? "نام سے تلاش" : "Search by label"}<input name="search" defaultValue={search} maxLength={120} /></label>
      <label>{ur ? "فلٹر" : "Filter"}<select name="filter" defaultValue={filter}>{[["all", "All", "تمام"], ["lost", "Lost", "گمشدہ"], ["ice", "Emergency", "ہنگامی"], ["active", "Active", "فعال"], ["draft", "Draft", "مسودہ"], ["suspended", "Suspended", "معطل"]].map(([value,en,urLabel]) => <option key={value} value={value}>{ur ? urLabel : en}</option>)}</select></label>
      <button className="button secondary">{ur ? "فلٹر لگائیں" : "Apply filters"}</button></form>
      <p>{ur ? "حالیہ تبدیلی کے مطابق ترتیب۔" : "Sorted by most recently updated."} <Link className="text-link" href="/kits">{ur ? "کٹ کے لحاظ سے دیکھیں" : "View by pair"}</Link></p></>}
    {page.items.length === 0 && <div className="empty-state"><p>{ur ? "ابھی کوئی QR موجود نہیں۔ اپنی کٹ کے QR کو اسکین کر کے فعال کریں۔" : "No QR codes yet. Scan your kit’s QR to begin activation."}</p></div>}
    {pairs?.items.map(pair => <PairCard key={pair.pair_id} pair={pair} ur={ur} />)}
    {tags && <div className="qr-grid">{tags.items.map(tag => <TagCard key={tag.qr_id} tag={tag} ur={ur} />)}</div>}
    {page.next_cursor && <Link className="button secondary" href={`/${mode}?cursor=${encodeURIComponent(page.next_cursor)}&search=${encodeURIComponent(search)}&filter=${encodeURIComponent(filter)}`}>{ur ? "اگلا صفحہ" : "Next page"}</Link>}
  </>;
}
